"""
Neo Hybrid Radar v2 — 統合トリガーシステム
修正点:
  1. ボラティリティトリガー → TrinityCouncil直結（壊れたautonomous_post_cycle廃止）
  2. アルファトリガー → TrinityCouncil（既存、変更なし）
  3. 冷却期間をボラ/アルファ共通で管理
  4. 構造化ログ
"""
import time
import logging
from datetime import datetime, timezone
from tools.market_data import MarketData
from core.blackboard import NeoBlackboard
from agents.trinity_council import TrinityCouncil
from tools.discord_reporter import DiscordReporter
from orchestration.alpha_sweep_operation import run_sweep
from orchestration.data_collector import get_latest_price_from_db
from core.config import VOLATILITY_WATCH_SYMBOLS, COUNCIL_ELIGIBLE_SYMBOLS
from orchestration.performance_evaluator import evaluate_performance
from orchestration.nightly_research import run_nightly_research
from tools.arbitrage_monitor import check_arbitrage_spreads, send_arbitrage_discord_alert, get_spread_summary
from orchestration.vp_discovery import run_vp_discovery
from core.config import LEARNING_MODE, LEARNING_TARGET_TRADES, LEARNING_SHARPE_THRESHOLD
from core.cost_guard import CostGuard

# --- TP/SLサイクルチェック（Council非依存・毎30秒） ---
def check_tp_sl_all_positions():
    """保有中ポジションの利確/損切を毎サイクルチェック（Council召集不要）
    売却4層: SL固定(-3%) → TP固定(+7%) → テクニカル出口(RSI>65+含み益) → 時間制約(96h)
    Returns: True if any SELL was executed (triggers cooldown)"""
    from tools.paper_wallet import PaperWallet
    from core.memory_db import NeoMemoryDB
    import sqlite3
    from datetime import datetime, timezone
    pw = PaperWallet()
    holdings = pw.state.get("holdings", {})
    if not holdings:
        return False
    sell_executed = False
    memory = NeoMemoryDB()

    # RSI計算用ヘルパー（SQLiteの5分足から14期間RSI）
    def _calc_rsi(symbol, period=14):
        try:
            conn = sqlite3.connect("vault/market_db/prices.sqlite")
            cur = conn.cursor()
            cur.execute("SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT ?", (symbol, period + 1))
            rows = cur.fetchall()
            conn.close()
            if len(rows) < period + 1:
                return None
            closes = [r[0] for r in reversed(rows)]
            gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
            losses_list = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
            avg_gain = sum(gains) / period
            avg_loss = sum(losses_list) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except Exception:
            return None

    for clean_symbol, hdata in list(holdings.items()):
        amount = hdata.get("amount", 0)
        if amount <= 0:
            continue
        try:
            # VP銘柄はGeckoTerminal直接取得
            if clean_symbol in ("VIRTUAL", "AIXBT"):
                price_data = MarketData._fetch_price_from_geckoterminal(clean_symbol)
                if not price_data:
                    price_data = MarketData.fetch_token_data(clean_symbol)
            else:
                price_data = MarketData.fetch_token_data(clean_symbol)
            if not price_data or price_data.get("status") != "success":
                continue
            current_price = float(price_data.get("priceUsd", 0.0))
            if current_price <= 0:
                continue

            pnl = pw.get_unrealized_pnl(clean_symbol, current_price)
            sl_pct = 3.0 if LEARNING_MODE else 10.0
            full_tp_pct = 7.0 if LEARNING_MODE else 20.0

            sell_reason = ""
            sell_label = ""

            # === 第1層: 固定SL ===
            if pw.should_stop_loss(clean_symbol, current_price, stop_pct=sl_pct):
                sell_reason = f"Stop Loss at {pnl['pnl_pct']:.1f}% (limit: -{sl_pct}%)"
                sell_label = "SL"
                logger.warning(f"[TP/SL] 🛑 損切トリガー: {clean_symbol} {pnl['pnl_pct']:.1f}%")

            # === 第2層: トレーリングストップ（+5%からトレール開始、高値から-2.5%で利確）===
            elif pnl['pnl_pct'] >= 5.0 or hdata.get("high_water_pnl", 0) >= 5.0:
                # 高値更新チェック
                prev_hw = hdata.get("high_water_pnl", pnl['pnl_pct'])
                if pnl['pnl_pct'] > prev_hw:
                    # 高値更新 → 記録
                    hdata["high_water_pnl"] = pnl['pnl_pct']
                    pw.state["holdings"][clean_symbol]["high_water_pnl"] = pnl['pnl_pct']
                    pw._save()
                    logger.info(f"[TP/SL] 📈 高値更新: {clean_symbol} +{pnl['pnl_pct']:.1f}% (HWM)")
                    prev_hw = pnl['pnl_pct']
                # 高値から2.5%以上下落 → 利確
                drawdown_from_hw = prev_hw - pnl['pnl_pct']
                if drawdown_from_hw >= 2.5:
                    sell_reason = f"Trailing Stop at +{pnl['pnl_pct']:.1f}% (HWM: +{prev_hw:.1f}%, drawdown: -{drawdown_from_hw:.1f}%)"
                    sell_label = "Trail TP"
                    logger.warning(f"[TP/SL] 🎯 トレーリング利確: {clean_symbol} +{pnl['pnl_pct']:.1f}% (HWM: +{prev_hw:.1f}%)")
            # === 第2層b: 固定TP上限（安全装置: +15%で強制利確）===
            elif pnl['pnl_pct'] >= full_tp_pct * 2:
                sell_reason = f"Hard TP Ceiling at +{pnl['pnl_pct']:.1f}% (ceiling: +{full_tp_pct * 2:.0f}%)"
                sell_label = "Hard TP"
                logger.warning(f"[TP/SL] 🎯 固定上限利確: {clean_symbol} +{pnl['pnl_pct']:.1f}%")

            # === 第3層: テクニカル出口（RSI > 65 + 含み益 > 1.5%） === [v6.5i H.2分析: 手数料後でも+0.5%確保]
            elif pnl['pnl_pct'] > 1.5:
                rsi_val = _calc_rsi(clean_symbol)
                if rsi_val is not None and rsi_val > 65:
                    sell_reason = f"RSI Exit at RSI={rsi_val:.1f} with +{pnl['pnl_pct']:.1f}% profit"
                    sell_label = "RSI Exit"
                    logger.warning(f"[TP/SL] 📊 テクニカル出口: {clean_symbol} RSI={rsi_val:.1f} +{pnl['pnl_pct']:.1f}%")

            # === 第4層: 時間制約（96時間=4日超過） ===
            if not sell_reason:
                entry_time_str = hdata.get("entry_time", "")
                if entry_time_str:
                    try:
                        if entry_time_str.endswith('+00:00') or entry_time_str.endswith('Z'):
                            entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
                        else:
                            entry_time = datetime.fromisoformat(entry_time_str).replace(tzinfo=timezone.utc)
                        hours_held = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
                        if hours_held > 96:
                            sell_reason = f"Time Exit after {hours_held:.0f}h (limit: 96h) with {pnl['pnl_pct']:+.1f}%"
                            sell_label = "Time Exit"
                            logger.warning(f"[TP/SL] ⏰ 時間制約: {clean_symbol} {hours_held:.0f}h保有 {pnl['pnl_pct']:+.1f}%")
                    except Exception as _te:
                        logger.error(f"[TP/SL] entry_time解析エラー: {_te}")

            # === SELL実行 ===
            if sell_reason:
                sell_amount_usd = amount * current_price
                result = pw.execute_trade(symbol=clean_symbol, action="SELL", amount_usd=sell_amount_usd, price=current_price, reason=sell_reason)
                if result.get("status") == "success":
                    sell_executed = True
                    is_win = pnl['pnl_pct'] > 0
                    result_tag = "win" if is_win else "loss"
                    # サーキットブレーカー: SL記録
                    try:
                        _cg = CostGuard()
                        if sell_label == "SL":
                            _cg.record_sl_fire()
                            logger.info(f"[CFO] SL発火記録: {clean_symbol}")
                        else:
                            _cg.record_non_sl_exit()
                    except Exception as _cg_err:
                        logger.error(f"[CFO] SL記録エラー: {_cg_err}")
                    logger.info(f"[TP/SL] ✅ {sell_label}完了: {clean_symbol} ${sell_amount_usd:.2f} ({pnl['pnl_pct']:+.1f}%)")

                    # 損切時はGemini内省
                    introspection = ""
                    if not is_win:
                        introspection = f"-{sl_pct}%到達。センチメント・クジラ動向の見直しが必要。"
                        try:
                            import google.generativeai as _genai
                            import os as _os
                            _genai.configure(api_key=_os.environ.get("GEMINI_API_KEY",""))
                            _model = _genai.GenerativeModel("gemini-2.0-flash")
                            _resp = _model.generate_content(f"あなたは自律取引AIエージェントNeoです。{clean_symbol}をエントリー${pnl['avg_price']:.4f}→決済${current_price:.4f}({pnl['pnl_pct']:.1f}%)で{sell_label}しました。なぜ負けたか、次回どう判断すべきか、合計100字以内で内省してください。")
                            introspection = _resp.text.strip()
                        except Exception as _ie:
                            logger.error(f"[TP/SL] 内省生成失敗: {_ie}")

                    # メモリ保存
                    mem_text = f"【{sell_label}】{clean_symbol} エントリー${pnl['avg_price']:.4f}→決済${current_price:.4f} {pnl['pnl_pct']:+.1f}% (${pnl['pnl_usd']:+.2f})"
                    if introspection:
                        mem_text += "\n内省: " + introspection
                        logger.info(f"[TP/SL] 🧠 内省: {introspection}")
                    memory.store(mem_text, metadata={"symbol": clean_symbol, "category": "trade_result", "result": result_tag, "pnl_pct": str(pnl['pnl_pct']), "exit_type": sell_label, "tier": "2"})

                    # paper_trade.logに記録（Evaluatorが参照）
                    try:
                        from datetime import datetime, timezone
                        _now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        _bal = pw.get_balance()  # PaperWallet returns float directly
                        _acc = 0.0
                        try:
                            _bb = NeoBlackboard.read()
                            _ps = _bb.get("performance_summary", {})
                            _acc = _ps.get("accuracy_score", 0.0)
                        except Exception:
                            pass
                        _log_line = f"[{_now}] {clean_symbol}/USDT: ${current_price:.6f} | Action: SELL | Amount: ${sell_amount_usd:.2f} | Status: {sell_label} | Accuracy: {_acc}% | BT_Confidence: LOW\n"
                        with open("/docker/openclaw-taan/data/.openclaw/workspace/paper_trade.log", "a") as _lf:
                            _lf.write(_log_line)
                        logger.info(f"[TP/SL] 📝 paper_trade.log記録: {clean_symbol} SELL ${sell_amount_usd:.2f}")
                    except Exception as _le:
                        logger.error(f"[TP/SL] paper_trade.log記録失敗: {_le}")
                    # Discord報告
                    try:
                        DiscordReporter.send_trade_alert(
                            symbol=f"{clean_symbol} ({sell_label} {pnl['pnl_pct']:+.1f}%)",
                            action="SELL",
                            amount_usd=sell_amount_usd,
                            price=current_price,
                            status=f"{sell_label} | entry:${pnl['avg_price']:.4f} pnl:${pnl['pnl_usd']:+.2f}",
                            balance_after=_bal
                        )
                    except Exception as _de:
                        logger.error(f"[TP/SL] Discord報告失敗: {_de}")

        except Exception as e:
            logger.error(f"[TP/SL] {clean_symbol} チェックエラー: {e}")
    return sell_executed

# --- 設定 ---
CHECK_INTERVAL = 30           # 監視間隔（秒）
VOLATILITY_THRESHOLD = 2.0    # ボラティリティ閾値（%）
ALPHA_THRESHOLD = LEARNING_SHARPE_THRESHOLD if LEARNING_MODE else 5.0  # 学習モード中は緩和
COUNCIL_COOLDOWN = 1800       # 冷却期間（30分）— Moltbook Rate Limit保護
SWEEP_INTERVAL   = 120        # Sweepサイクル間隔（30秒×120=60分）
ARB_INTERVAL     = 60         # Arbitrageチェック間隔（30秒×60=30分）
EVAL_INTERVAL    = 720        # Evaluatorサイクル間隔（30秒×720=6時間）
ENGAGE_INTERVAL  = 240
PERIODIC_COUNCIL_INTERVAL = 480  # 4時間ごと（30秒×480=14400秒）
HEARTBEAT_INTERVAL = 60       # 稼働報告間隔（30秒×60=30分）        # Moltbookエンゲージメント間隔（30秒×240=2時間）
NIGHTLY_HOUR     = 2           # Nightly Batch実行時刻（JST 02:00 — now_jst_hourと比較）

from logging.handlers import RotatingFileHandler as _RFH
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        _RFH("radar.log", maxBytes=1_000_000, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("neo.radar")

def _run_nightly_batch():
    """
    Nightly Batch — JST 02:00に1日1回実行
    1. Alpha Sweep フルスキャン（全銘柄）
    2. Performance Evaluator（勝率更新 + Discordダッシュボード）
    3. Discord日次サマリー送信
    """
    batch_start = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info(f"[Nightly] === {today} バッチ開始 ===")

    # 1. Alpha Sweep フルスキャン
    logger.info("[Nightly] Step 1/8: Alpha Sweep フルスキャン")
    try:
        run_sweep(nightly=True)
        logger.info("[Nightly] Sweep完了（全Tier）")
    except Exception as e:
        logger.error(f"[Nightly] Sweep失敗: {e}")

    # 2. Performance Evaluator
    logger.info("[Nightly] Step 2/8: Performance Evaluator")
    try:
        evaluate_performance()
        logger.info("[Nightly] Evaluator完了（Discordダッシュボード送信済み）")
    except Exception as e:
        logger.error(f"[Nightly] Evaluator失敗: {e}")

    # 3. VP Discovery（週次・月曜のみ）
    if datetime.now(timezone.utc).weekday() == 0:  # 0=月曜
        logger.info("[Nightly] Step 3b: VP新興銘柄スキャン（週次）")
        try:
            result = run_vp_discovery()
            added = result.get("added", [])
            if added:
                DiscordReporter.send_log(
                    "🔍 VP Discovery: 新興銘柄発見",
                    f"**新規追加**: {', '.join(added)}\n**監視リスト**: {', '.join(result.get('current', []))}",
                    0x2ecc71
                )
        except Exception as e:
            logger.error(f"[Nightly] VP Discovery失敗: {e}")

    # 3. Nightly Research（洞察投稿・学習報告）
    logger.info("[Nightly] Step 3/8: Nightly Research")
    try:
        run_nightly_research()
    except Exception as e:
        logger.error(f"[Nightly] Nightly Research失敗: {e}")

    # 4. Tearsheetレポート生成（M.2）
    logger.info("[Nightly] Step 4/8: quantstats HTMLティアシート生成")
    try:
        from orchestration.tearsheet_generator import generate_tearsheet
        tearsheet_path = generate_tearsheet()
        if tearsheet_path:
            DiscordReporter.send_log(
                "📊 Neo Tearsheet生成完了",
                f"HTMLレポートを生成しました: `{tearsheet_path}`",
                0x3498db
            )
    except Exception as e:
        logger.error(f"[Nightly] Tearsheet生成失敗: {e}")

    # 5. WAIT品質検証
    logger.info("[Nightly] Step 5/8: WAIT品質検証")
    wait_quality_text = ""
    try:
        from research.wait_quality_analysis import run_nightly_summary
        wq = run_nightly_summary()
        wait_quality_text = "\n\n" + wq.get('discord_text', '')
        logger.info(f"[Nightly] WAIT品質: {wq.get('status')} (正解率={wq.get('overall_correct_rate', 0):.1f}%)")
    except Exception as e:
        logger.error(f"[Nightly] WAIT品質検証失敗: {e}")

    # 6. H.2取引分析進捗
    logger.info("[Nightly] Step 6/8: H.2取引分析進捗")
    h2_progress_text = ""
    try:
        from research.h2_trade_analysis import get_progress_report
        h2 = get_progress_report()
        h2_progress_text = "\n\n" + h2.get('discord_text', '')
        if h2.get('ready'):
            logger.info("[Nightly] H.2分析: データ十分 → v2完全分析を自動実行")
            try:
                from research.h2_trade_analysis import run_full_analysis
                run_full_analysis()
                # ダッシュボードに週次レポート送信（日曜のみ）
                import datetime as _dt
                if _dt.datetime.now(_dt.timezone.utc).weekday() == 6:  # 日曜
                    _h2_webhook = DiscordReporter.DASHBOARD_WEBHOOK or DiscordReporter.REPORT_WEBHOOK
                    _h2_payload = {"embeds": [{"title": "📊 H.2 週次分析レポート", "description": h2_progress_text.strip(), "color": 0x9b59b6}]}
                    import requests as _req
                    _req.post(_h2_webhook, json=_h2_payload, timeout=10)
                    logger.info("[Nightly] H.2週次レポートをダッシュボードに送信")
            except Exception as _h2e:
                logger.error(f"[Nightly] H.2完全分析エラー: {_h2e}")
        else:
            logger.info(f"[Nightly] H.2分析: 完結ペア{h2.get('completed',0)}/{h2.get('remaining',20)+h2.get('completed',0)}件")
    except Exception as e:
        logger.error(f"[Nightly] H.2進捗取得失敗: {e}")

    # 6b. Voyagerスキル更新
    try:
        from research.voyager_skills import run_voyager_update
        run_voyager_update()
        logger.info("[Nightly] Voyager: スキル更新完了")
    except Exception as _ve:
        logger.error(f"[Nightly] Voyager更新失敗: {_ve}")

    # 6c. EvolveRルール更新
    try:
        from research.evolver_rules import run_evolver_update
        run_evolver_update()
        logger.info("[Nightly] EvolveR: ルール更新完了")
    except Exception as _ve:
        logger.error(f"[Nightly] EvolveR更新失敗: {_ve}")

    # 6d. gplearn Nightly進化（G4: 毎晩1シード×2銘柄）
    gplearn_nightly_text = ""
    try:
        from research.gplearn_strategy import run_nightly_evolution
        logger.info("[Nightly] Step 6d: gplearn Nightly進化")
        _gp_results = run_nightly_evolution()
        _gp_lines = []
        for _sym, _r in _gp_results.items():
            _gp_lines.append(f"{_sym}: acc={_r['acc']}% recall={_r['recall']}% [{_r['saved']}]")
        gplearn_nightly_text = "\n\n🧬 **gplearn G4**: " + " / ".join(_gp_lines)
        logger.info(f"[Nightly] gplearn G4完了: {' / '.join(_gp_lines)}")
    except Exception as _gpe:
        logger.error(f"[Nightly] gplearn G4失敗: {_gpe}")

    # 6e. ACP Provider宣伝投稿（水曜のみ — 週1回）
    if datetime.now(timezone.utc).weekday() == 2:  # 2=水曜
        logger.info("[Nightly] Step 6e: ACP Provider宣伝投稿")
        try:
            from tools.moltbook_tool import MoltbookTool
            MoltbookTool.post_acp_service_promo()
            logger.info("[Nightly] ACP宣伝投稿完了")
        except Exception as _acp_e:
            logger.error(f"[Nightly] ACP宣伝投稿失敗: {_acp_e}")

    # 7. Discord日次サマリー
    logger.info("[Nightly] Step 7/8: Discord日次サマリー送信")
    try:
        from core.blackboard import NeoBlackboard
        board = NeoBlackboard.load()
        perf = board.get("performance_summary", {})
        opps = board.get("active_opportunities", {})
        accuracy = perf.get("accuracy_score", 0.0)
        total_trades = perf.get("total_evaluated_trades", 0)
        opp_count = len(opps)
        elapsed = round(time.time() - batch_start, 1)

        # Moltbook反響レポート取得
        moltbook_report = ""
        try:
            from tools.moltbook_tracker import run_tracking
            moltbook_report = "\n\n" + run_tracking()
        except Exception as e:
            logger.error(f"[Nightly] MoltbookTracker失敗: {e}")

        # Moltbookエンゲージメントレポート取得
        engage_report = ""
        try:
            from tools.moltbook_engager import MoltbookEngager
            engage_report = "\n\n" + MoltbookEngager.get_engagement_report()
        except Exception as e:
            logger.error(f"[Nightly] MoltbookEngager統計失敗: {e}")

        summary = (
            f"📅 **日次バッチ完了** — {today}\n"
            f"⏱️ 実行時間: {elapsed}秒\n"
            f"🎯 現在の勝率: {accuracy}% ({total_trades}件)\n"
            f"🔍 Alpha機会: {opp_count}件\n"
            f"✅ Sweep / Evaluator / Dashboard 完了"
            f"{moltbook_report}"
            f"{engage_report}"
            f"{wait_quality_text}"
            f"{h2_progress_text}"
            f"{gplearn_nightly_text}"
        )
        # Nightly専用チャンネルに送信
        import requests as _req
        _nightly_url = DiscordReporter.NIGHTLY_WEBHOOK or DiscordReporter.LOG_WEBHOOK
        _payload = {
            "embeds": [{
                "title": "🌙 Nightly Batch Report",
                "description": summary,
                "color": 0x9b59b6
            }]
        }
        _req.post(_nightly_url, json=_payload, timeout=10)
        logger.info(f"[Nightly] === バッチ完了 ({elapsed}秒) ===")
    except Exception as e:
        logger.error(f"[Nightly] サマリー送信失敗: {e}")

    # Step 8: radar_output.log 自動切り詰め（最新10000行を保持）
    logger.info("[Nightly] Step 8/8: ログ自動切り詰め")
    try:
        import subprocess
        _log_path = "radar_output.log"
        _result = subprocess.run(["wc", "-l", _log_path], capture_output=True, text=True)
        _lines = int(_result.stdout.strip().split()[0])
        if _lines > 10000:
            subprocess.run(f"tail -10000 {_log_path} > {_log_path}.tmp && mv {_log_path}.tmp {_log_path}", shell=True)
            logger.info(f"[Nightly] ログ切り詰め: {_lines}行 → 10000行")
    except Exception as e:
        logger.error(f"[Nightly] ログ切り詰め失敗: {e}")


def start_hybrid_radar():
    print("=" * 60)
    print(f" 📡 Neo Hybrid Radar v2: UNIFIED TRIGGER MODE")
    print(f" ⏱️  Interval: {CHECK_INTERVAL}s | Vol: {VOLATILITY_THRESHOLD}% | Alpha: {ALPHA_THRESHOLD}")
    print(f" 🧊 Cooldown: {COUNCIL_COOLDOWN // 60}min")
    print("=" * 60)
    
    # 初期価格の取得（Tier1全銘柄）
    anchor_prices = {}
    for _sym in VOLATILITY_WATCH_SYMBOLS:
        _data = MarketData.fetch_token_data(_sym)
        _price = float(_data.get("priceUsd", 0.0)) if _data else 0.0
        if _price <= 0:
            logger.error(f"❌ {_sym} 初期価格取得失敗。5秒後リトライ...")
            time.sleep(5)
            _data = MarketData.fetch_token_data(_sym)
            _price = float(_data.get("priceUsd", 0.0)) if _data else 0.0
        anchor_prices[_sym] = _price
        logger.info(f"🎯 Anchor price [{_sym}]: ${_price:.6f}")
    anchor_price = anchor_prices.get("VIRTUAL", 0.0)  # ステータス表示用
    
    processed_alphas = {}     # 処理済みアルファのタイムスタンプ
    last_nightly_date = None  # 最後にNightly Batchを実行した日付
    last_council_time = 0     # 最後に評議会を開いた時刻
    cycle_count = 0
    consecutive_errors = 0
    last_trade_time = time.time()
    NO_TRADE_ALERT_HOURS = 24
    no_trade_alerted = False

    try:
        while True:
            cycle_count += 1
            current_time = time.time()
            time_since_last = current_time - last_council_time
            cooldown_remaining = max(0, COUNCIL_COOLDOWN - time_since_last)
            is_cooled_down = cooldown_remaining == 0
            
            trigger_type = None
            trigger_symbol = None
            trigger_context = None

            # ============================================================
            # 0. Alpha Sweep 自動実行（60分ごと）
            # ============================================================
            if cycle_count % EVAL_INTERVAL == 0:
                logger.info(f"[Evaluator] 定期評価開始 (cycle={cycle_count})")
                try:
                    evaluate_performance(send_dashboard=True)
                except Exception as e:
                    logger.error(f"[Evaluator] エラー: {e}")

            if cycle_count % SWEEP_INTERVAL == 0:
                logger.info(f"[Sweep] 定期スキャン開始 (cycle={cycle_count})")
                try:
                    run_sweep()
                    logger.info("[Sweep] 完了 — Blackboard更新済み")
                except Exception as e:
                    logger.error(f"[Sweep] エラー: {e}")

            # ============================================================
            # 0a-1b. Arbitrage Spread Monitor（30分ごと）
            # ============================================================
            if cycle_count % ARB_INTERVAL == 0:
                logger.info(f"[Arb] スプレッドチェック開始 (cycle={cycle_count})")
                try:
                    arb_result = check_arbitrage_spreads()
                    arb_alerts = arb_result.get("alerts", [])
                    if arb_alerts:
                        send_arbitrage_discord_alert(arb_alerts, arb_result["results"])
                        logger.warning(f"[Arb] {len(arb_alerts)}件のアラート検知")
                    else:
                        logger.info("[Arb] 完了 — スプレッド正常範囲内")
                except Exception as e:
                    logger.error(f"[Arb] エラー: {e}")
            # ============================================================
            # 0a-2. Moltbookエンゲージメント（2時間ごと）
            # ============================================================
            if cycle_count % ENGAGE_INTERVAL == 0:
                logger.info(f"[Engager] Moltbookエンゲージメント開始 (cycle={cycle_count})")
                try:
                    from tools.moltbook_engager import MoltbookEngager
                    engage_result = MoltbookEngager.run_engagement_cycle()
                    r = engage_result.get("replies", {})
                    f = engage_result.get("feed", {})
                    logger.info(f"[Engager] 完了 — 返信:{r.get('replied',0)} upvote:{f.get('upvoted',0)} コメント:{f.get('commented',0)}")
                except Exception as e:
                    logger.error(f"[Engager] エラー: {e}")

            # ============================================================
            # 0a-3. Heartbeat稼働報告（30分ごと）
            # ============================================================
            if cycle_count > 0 and cycle_count % HEARTBEAT_INTERVAL == 0:
                try:
                    from tools.paper_wallet import PaperWallet as _HBW
                    _hbw = _HBW()
                    _hb_usdc = _hbw.state.get("usd_balance", 0)
                    _hb_holdings = _hbw.state.get("holdings", {})
                    _hb_hist = len(_hbw.state.get("history", []))
                    _hb_lines = []
                    _hb_lines.append("USDC: ${:,.0f}".format(_hb_usdc))
                    _hb_total = _hb_usdc
                    for _hbs, _hbd in _hb_holdings.items():
                        try:
                            _hbp = MarketData._fetch_price_from_geckoterminal(_hbs) if _hbs in ("VIRTUAL","AIXBT") else MarketData.fetch_token_data(_hbs)
                            _hbpr = float(_hbp.get("priceUsd", 0)) if _hbp and _hbp.get("status") == "success" else 0
                            if _hbpr > 0:
                                _hb_val = _hbd["amount"] * _hbpr
                                _hb_total += _hb_val
                                _hb_pnl = ((_hbpr - _hbd["avg_price"]) / _hbd["avg_price"] * 100) if _hbd["avg_price"] > 0 else 0
                                _hb_lines.append("{}: ${:.6f} ({:+.2f}%)".format(_hbs, _hbpr, _hb_pnl))
                        except Exception:
                            pass
                    _hb_lines.append("Total: ${:,.0f}".format(_hb_total))
                    _hb_lines.append("Learn: {}/{}".format(_hb_hist, LEARNING_TARGET_TRADES))
                    _hb_lines.append("Cycle: #{}".format(cycle_count))
                    DiscordReporter.send_log("Heartbeat", chr(10).join(_hb_lines), 0x3498db)
                    logger.info("[Heartbeat] ✅ 送信完了 (cycle #{})".format(cycle_count))
                except Exception as _hbe:
                    logger.error("[Heartbeat] error: {}".format(_hbe))

            # ============================================================
            # 0b. Nightly Batch（JST 02:00 = UTC 17:00 に1日1回）
            # ============================================================
            now_utc = datetime.now(timezone.utc)
            now_jst_hour = (now_utc.hour + 9) % 24
            today_str = now_utc.strftime('%Y-%m-%d')
            if now_jst_hour == NIGHTLY_HOUR and last_nightly_date != today_str:
                last_nightly_date = today_str
                logger.info(f'[Nightly] 深夜バッチ開始 JST{now_jst_hour:02d}:00 ({today_str})')
                try:
                    _run_nightly_batch()
                except Exception as e:
                    logger.error(f'[Nightly] バッチ失敗: {e}')


            # ============================================================
            # 0. TP/SLサイクルチェック（毎30秒・Council非依存）
            # ============================================================
            try:
                if check_tp_sl_all_positions():
                    last_council_time = time.time()
                    logger.info("[TP/SL] 🧊 SELL発火 → 冷却開始（30分）")
                    time.sleep(CHECK_INTERVAL)
                    continue  # SL/TP発火サイクルではCouncil召集しない
            except Exception as _tpsl_e:
                logger.error(f"[TP/SL] サイクルチェックエラー: {_tpsl_e}")

                        # ============================================================
            # 1. ボラティリティ監視 (Tier1: VIRTUAL / AIXBT)
            # ============================================================
            current_price = anchor_prices.get("VIRTUAL", 0.0)  # ステータス表示用
            for _vsym in VOLATILITY_WATCH_SYMBOLS:
                try:
                    # SQLite優先（API呼び出し削減・429対策）
                    _vprice = get_latest_price_from_db(_vsym)
                    if _vprice is None:
                        _vdata = MarketData.fetch_token_data(_vsym)
                        _vprice = float(_vdata.get("priceUsd", 0.0)) if _vdata and _vdata.get("status") == "success" else 0.0
                    if _vprice > 0:
                        _anchor = anchor_prices.get(_vsym, 0.0)
                        _change = abs((_vprice - _anchor) / _anchor) * 100 if _anchor > 0 else 0

                        if _vsym == "VIRTUAL":
                            current_price = _vprice  # ステータス表示用更新

                        if _change >= VOLATILITY_THRESHOLD:
                            _dir = "上昇" if _vprice > _anchor else "下落"
                            logger.warning(f"🚨 [VOLATILITY] {_vsym} {_dir} {_change:.2f}% (${_anchor:.6f} → ${_vprice:.6f})")

                            if is_cooled_down and trigger_type is None:
                                trigger_type = "VOLATILITY"
                                trigger_symbol = _vsym
                                trigger_context = f"{_vsym}価格が{_change:.2f}%{_dir}（${_anchor:.6f}→${_vprice:.6f}）"
                            else:
                                logger.info(f"  ⏳ 冷却中（残り{int(cooldown_remaining/60)}分）— {_vsym}ボラトリガーを保留")

                        # アンカー価格はトリガー発火時のみ更新（毎サイクル更新すると30秒で2%必要になる）
                        if _change >= VOLATILITY_THRESHOLD:
                            anchor_prices[_vsym] = _vprice
                except Exception as e:
                    logger.error(f"ボラティリティ監視エラー [{_vsym}]: {e}")

            # ============================================================
            # 2. アルファ監視 (Blackboard経由)
            # ============================================================
            if trigger_type is None and is_cooled_down:
                try:
                    board = NeoBlackboard.load()
                    strat = board.get("strategic_intel", {})
                    opps = strat.get("active_opportunities", {})

                    eligible = []
                    council_ok = [sym + "/USDT" for sym in COUNCIL_ELIGIBLE_SYMBOLS]
                    for s, d in opps.items():
                        if s not in council_ok:
                            logger.debug(f"⏭️ [ALPHA] {s} はCouncil対象外 — スキップ")
                            continue
                        sharpe = d.get("sharpe", 0.0)
                        last_detected = d.get("last_detected")
                        if sharpe >= ALPHA_THRESHOLD and processed_alphas.get(s) != last_detected:
                            eligible.append((s, d))

                    if eligible:
                        eligible.sort(key=lambda x: x[1].get("sharpe", 0.0), reverse=True)
                        symbol, data = eligible[0]
                        
                        trigger_type = "ALPHA"
                        trigger_symbol = symbol
                        trigger_context = f"Alpha Sweep Hit: Sharpe={data['sharpe']}, confidence={data.get('confidence', 'N/A')}"
                        
                        logger.warning(f"🔥 [ALPHA] {symbol} (Sharpe: {data['sharpe']}) 採択")
                except Exception as e:
                    logger.error(f"アルファ監視エラー: {e}")

            # ============================================================
            # 2b. 定期Council召集（横ばい相場でも学習を進める）
            # ============================================================
            if cycle_count % PERIODIC_COUNCIL_INTERVAL == 0 and cycle_count > 0:
                logger.info(f"🔍 [PERIODIC-DBG] cycle={cycle_count} trigger_type={trigger_type} cooled={is_cooled_down}")
            if trigger_type is None and cycle_count % PERIODIC_COUNCIL_INTERVAL == 0 and cycle_count > 0:
                if is_cooled_down:
                    # Tier1銘柄を交互に召集（永続トグル: Blackboardに最後の銘柄を記録）
                    _periodic_symbols = [s for s in COUNCIL_ELIGIBLE_SYMBOLS]
                    try:
                        import json as _json_toggle
                        with open("vault/blackboard/live_intel.json", "r") as _f_bb:
                            _bb_data = _json_toggle.load(_f_bb)
                        _last_periodic = _bb_data.get("last_periodic_symbol", "")
                    except Exception:
                        _last_periodic = ""
                    # 前回と異なる銘柄を選択（初回はリスト先頭）
                    if _last_periodic and _last_periodic in _periodic_symbols:
                        _periodic_idx = (_periodic_symbols.index(_last_periodic) + 1) % len(_periodic_symbols)
                    else:
                        _periodic_idx = 0
                    _periodic_sym = _periodic_symbols[_periodic_idx]
                    trigger_type = "PERIODIC"
                    trigger_symbol = _periodic_sym
                    trigger_context = f"定期Council召集（4時間ごと・学習促進）: {_periodic_sym}"
                    # 永続トグル: Blackboardに今回の銘柄を記録
                    try:
                        import json as _json_toggle
                        with open("vault/blackboard/live_intel.json", "r") as _f_bb:
                            _bb_write = _json_toggle.load(_f_bb)
                        _bb_write["last_periodic_symbol"] = _periodic_sym
                        with open("vault/blackboard/live_intel.json", "w") as _f_bb:
                            _json_toggle.dump(_bb_write, _f_bb, indent=2, ensure_ascii=False)
                    except Exception as _bb_err:
                        logger.warning(f"[PERIODIC] Blackboard書き込み失敗: {_bb_err}")
                    logger.info(f"⏰ [PERIODIC] 定期Council召集: {_periodic_sym}（cycle={cycle_count}）")
                else:
                    logger.info(f"⏰ [PERIODIC] 定期Council時刻だが冷却中（残り{int(cooldown_remaining/60)}分）— スキップ")

            # ============================================================
            # 3. Council召集（トリガー発火時のみ）
            # ============================================================
            if trigger_type and trigger_symbol:
                # 最終ガード: COUNCIL_ELIGIBLE_SYMBOLSに含まれない銘柄はブロック
                _clean_sym = trigger_symbol.split('/')[0].strip()
                if _clean_sym not in COUNCIL_ELIGIBLE_SYMBOLS:
                    logger.warning(f"🚫 [GUARD] {trigger_symbol} はCOUNCIL_ELIGIBLE_SYMBOLS外 → Council召集ブロック")
                    trigger_type = None
                    trigger_symbol = None

            if trigger_type and trigger_symbol:
                # サーキットブレーカー: 全レイヤーチェック
                try:
                    _cg = CostGuard()
                    _cg_ok, _cg_reason = _cg.approve_council()
                    if not _cg_ok:
                        logger.warning(f"🚫 [CFO] Council召集ブロック: {_cg_reason}")
                        DiscordReporter.send_log(
                            "🚫 サーキットブレーカー発動",
                            f"**Trigger:** {trigger_type} {trigger_symbol}\n**Reason:** {_cg_reason}",
                            0xff6600
                        )
                        trigger_type = None
                        trigger_symbol = None
                except Exception as _cg_err:
                    logger.error(f"[CFO] サーキットブレーカーチェックエラー: {_cg_err}")

            if trigger_type and trigger_symbol:
                logger.info(f"🏛️ Council召集: [{trigger_type}] {trigger_symbol}")
                
                # Discord通知: Council開始
                DiscordReporter.send_log(
                    f"📡 Radar Trigger: {trigger_type}",
                    f"**Symbol:** {trigger_symbol}\n**Context:** {trigger_context}\n**Council召集中...**",
                    0xf39c12
                )
                
                try:
                    council = TrinityCouncil()
                    result = council.run(
                        sentiment_score=1.0 if trigger_type == "ALPHA" else 0.5,
                        context=trigger_context,
                        target_symbol=trigger_symbol
                    )
                    
                    last_council_time = time.time()
                    
                    # アルファの処理済みマーク
                    if trigger_type == "ALPHA":
                        board = NeoBlackboard.load()
                        opp_data = board.get("strategic_intel", {}).get("active_opportunities", {}).get(trigger_symbol, {})
                        processed_alphas[trigger_symbol] = opp_data.get("last_detected")
                    
                    verdict = result.get("verdict", "UNKNOWN")
                    logger.info(f"✅ Council完了: {verdict} | 冷却開始（{COUNCIL_COOLDOWN//60}分）")
                    consecutive_errors = 0
                    if verdict in ("BUY", "SELL"):
                        last_trade_time = time.time()
                        no_trade_alerted = False
                    # 取引後に勝率を即時更新
                    try:
                        evaluate_performance(send_dashboard=False)
                    except Exception as _e:
                        logger.error(f"[Evaluator] Post-council error: {_e}")
                    
                except Exception as e:
                    logger.error(f"⚠️ Council Error: {e}", exc_info=True)
                    last_council_time = time.time()  # エラー時も冷却開始（連続エラー防止）
                    consecutive_errors += 1
                    
                    DiscordReporter.send_log(
                        "❌ Council Error",
                        f"**Symbol:** {trigger_symbol}\n**Error:** {str(e)[:500]}",
                        0xe74c3c
                    )
                    if consecutive_errors >= 5:
                        DiscordReporter.send_log(
                            "🚨 連続エラー警告",
                            f"Councilが{consecutive_errors}回連続エラー。手動確認が必要です。",
                            0xff0000
                        )

            # ============================================================
            # 3b. 長時間無取引検知
            # ============================================================
            hours_since_trade = (time.time() - last_trade_time) / 3600
            if hours_since_trade > NO_TRADE_ALERT_HOURS and not no_trade_alerted:
                DiscordReporter.send_log(
                    "⏰ 無取引アラート",
                    f"直近の取引から {hours_since_trade:.1f} 時間経過。\n"
                    f"BUYデッドロック再発や市場データ障害の可能性。",
                    0xf39c12
                )
                no_trade_alerted = True
                logger.warning(f"[Monitor] 無取引 {hours_since_trade:.1f}h")

            # ============================================================
            # 4. ステータス表示
            # ============================================================
            if is_cooled_down:
                alpha_status = "🟢 Ready"
            else:
                alpha_status = f"🧊 Cooling ({int(cooldown_remaining/60)}m)"
            
            status = f"[Radar #{cycle_count}] VIRTUAL ${current_price:.4f} | {alpha_status}"
            
            # 100サイクルごとにログ出力（ノイズ抑制）
            if cycle_count % 100 == 0:
                logger.info(status)
            else:
                print(f"\r{status}", end="", flush=True)
            
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("\n[Radar] Terminated by Commander. 👋")

if __name__ == "__main__":
    start_hybrid_radar()
