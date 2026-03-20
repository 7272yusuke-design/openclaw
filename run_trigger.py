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
from orchestration.vp_discovery import run_vp_discovery
from core.config import LEARNING_MODE, LEARNING_TARGET_TRADES, LEARNING_SHARPE_THRESHOLD

# --- TP/SLサイクルチェック（Council非依存・毎30秒） ---
def check_tp_sl_all_positions():
    """保有中ポジションの利確/損切を毎サイクルチェック（Council召集不要）"""
    from tools.paper_wallet import PaperWallet
    from core.memory_db import NeoMemoryDB
    pw = PaperWallet()
    holdings = pw.state.get("holdings", {})
    if not holdings:
        return
    memory = NeoMemoryDB()
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
            partial_tp_pct = 3.0 if LEARNING_MODE else 20.0
            full_tp_pct = 7.0 if LEARNING_MODE else 20.0

            sell_amount_usd = 0
            tp_label = ""
            tp_reason = ""

            # 全量利確チェック
            if pw.should_take_profit(clean_symbol, current_price, target_pct=full_tp_pct):
                sell_amount_usd = amount * current_price
                tp_label = "Full TP"
                tp_reason = f"Full Take Profit at +{pnl['pnl_pct']:.1f}% (target: +{full_tp_pct}%)"
                logger.warning(f"[TP/SL] 🎯 全量利確トリガー: {clean_symbol} +{pnl['pnl_pct']:.1f}%")
            # 半量利確チェック（学習モードのみ）
            elif LEARNING_MODE and pw.should_take_profit(clean_symbol, current_price, target_pct=partial_tp_pct):
                sell_amount_usd = (amount * current_price) * 0.5
                tp_label = "Partial TP (50%)"
                tp_reason = f"Partial Take Profit at +{pnl['pnl_pct']:.1f}% (learning mode, target: +{partial_tp_pct}%)"
                logger.warning(f"[TP/SL] 🎯 半量利確トリガー: {clean_symbol} +{pnl['pnl_pct']:.1f}%")

            if sell_amount_usd > 0:
                result = pw.execute_trade(symbol=clean_symbol, action="SELL", amount_usd=sell_amount_usd, price=current_price, reason=tp_reason)
                if result.get("status") == "success":
                    logger.info(f"[TP/SL] ✅ 利確完了: {clean_symbol} ${sell_amount_usd:.2f} ({tp_label})")
                    tp_memory = f"【{tp_label}利確成功】{clean_symbol} エントリー${pnl['avg_price']:.4f}→利確${current_price:.4f} +{pnl['pnl_pct']:.1f}% (${pnl['pnl_usd']:+.2f})"
                    memory.store(tp_memory, metadata={"symbol": clean_symbol, "category": "trade_result", "result": "win", "pnl_pct": str(pnl['pnl_pct']), "tp_type": tp_label, "tier": "2"})
                    try:
                        _bal = pw.get_balance().get('USDC', 0)
                        DiscordReporter.send_trade_alert(symbol=f"{clean_symbol} ({tp_label} +{pnl['pnl_pct']:.1f}%)", action="SELL", amount_usd=sell_amount_usd, price=current_price, status=f"success | entry:${pnl['avg_price']:.4f} pnl:${pnl['pnl_usd']:+.2f}", balance_after=_bal)
                    except Exception as _de:
                        logger.error(f"[TP/SL] Discord報告失敗: {_de}")
                continue  # 利確したらこの銘柄は損切チェック不要

            # 損切チェック
            sl_pct = 3.0 if LEARNING_MODE else 10.0
            if pw.should_stop_loss(clean_symbol, current_price, stop_pct=sl_pct):
                logger.warning(f"[TP/SL] 🛑 損切トリガー: {clean_symbol} {pnl['pnl_pct']:.1f}%")
                sell_amount_usd = amount * current_price
                result = pw.execute_trade(symbol=clean_symbol, action="SELL", amount_usd=sell_amount_usd, price=current_price, reason=f"Stop Loss at {pnl['pnl_pct']:.1f}% (limit: -{sl_pct}%)")
                if result.get("status") == "success":
                    logger.info(f"[TP/SL] ✅ 損切完了: {clean_symbol} ${sell_amount_usd:.2f}")
                    # Gemini内省
                    _introspection = f"-{sl_pct}%到達。センチメント・クジラ動向の見直しが必要。"
                    try:
                        import google.generativeai as _genai
                        import os as _os
                        _genai.configure(api_key=_os.environ.get("GEMINI_API_KEY",""))
                        _model = _genai.GenerativeModel("gemini-2.0-flash")
                        _resp = _model.generate_content(f"あなたは自律取引AIエージェントNeoです。{clean_symbol}をエントリー${pnl['avg_price']:.4f}→損切${current_price:.4f}({pnl['pnl_pct']:.1f}%)で損切しました。なぜ負けたか、次回どう判断すべきか、合計100字以内で内省してください。")
                        _introspection = _resp.text.strip()
                    except Exception as _ie:
                        logger.error(f"[TP/SL] 内省生成失敗: {_ie}")
                    sl_memory = f"【損切実行】{clean_symbol} エントリー${pnl['avg_price']:.4f}→損切${current_price:.4f} {pnl['pnl_pct']:.1f}% (${pnl['pnl_usd']:+.2f})\n内省: {_introspection}"
                    logger.info(f"[TP/SL] 🧠 損切内省: {_introspection}")
                    memory.store(sl_memory, metadata={"symbol": clean_symbol, "category": "trade_result", "result": "loss", "pnl_pct": str(pnl['pnl_pct']), "tier": "2"})
                    try:
                        _bal = pw.get_balance().get('USDC', 0)
                        DiscordReporter.send_trade_alert(symbol=f"{clean_symbol} (Stop Loss {pnl['pnl_pct']:.1f}%)", action="SELL", amount_usd=sell_amount_usd, price=current_price, status=f"stop_loss | entry:${pnl['avg_price']:.4f} pnl:${pnl['pnl_usd']:+.2f}", balance_after=_bal)
                    except Exception as _de:
                        logger.error(f"[TP/SL] Discord報告失敗: {_de}")
        except Exception as e:
            logger.error(f"[TP/SL] {clean_symbol} チェックエラー: {e}")

# --- 設定 ---
CHECK_INTERVAL = 30           # 監視間隔（秒）
VOLATILITY_THRESHOLD = 2.0    # ボラティリティ閾値（%）
ALPHA_THRESHOLD = LEARNING_SHARPE_THRESHOLD if LEARNING_MODE else 5.0  # 学習モード中は緩和
COUNCIL_COOLDOWN = 1800       # 冷却期間（30分）— Moltbook Rate Limit保護
SWEEP_INTERVAL   = 120        # Sweepサイクル間隔（30秒×120=60分）
EVAL_INTERVAL    = 720        # Evaluatorサイクル間隔（30秒×720=6時間）
ENGAGE_INTERVAL  = 240
HEARTBEAT_INTERVAL = 60       # 稼働報告間隔（30秒×60=30分）        # Moltbookエンゲージメント間隔（30秒×240=2時間）
NIGHTLY_HOUR     = 1           # Nightly Batch実行時刻（UTC=JST-9、1=JST10時→夜間は17UTC=JST02:00）

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
    logger.info("[Nightly] Step 1/3: Alpha Sweep フルスキャン")
    try:
        run_sweep(nightly=True)
        logger.info("[Nightly] Sweep完了（全Tier）")
    except Exception as e:
        logger.error(f"[Nightly] Sweep失敗: {e}")

    # 2. Performance Evaluator
    logger.info("[Nightly] Step 2/3: Performance Evaluator")
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
    logger.info("[Nightly] Step 3/4: Nightly Research")
    try:
        run_nightly_research()
    except Exception as e:
        logger.error(f"[Nightly] Nightly Research失敗: {e}")

    # 4. Tearsheetレポート生成（M.2）
    logger.info("[Nightly] Step 4/5: quantstats HTMLティアシート生成")
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

    # 5. Discord日次サマリー
    logger.info("[Nightly] Step 5/5: Discord日次サマリー送信")
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
                except Exception as _hbe:
                    logger.error("[Heartbeat] error: {}".format(_hbe))

            # ============================================================
            # 0b. Nightly Batch（JST 02:00 = UTC 17:00 に1日1回）
            # ============================================================
            now_utc = datetime.now(timezone.utc)
            now_jst_hour = (now_utc.hour + 9) % 24
            today_str = now_utc.strftime('%Y-%m-%d')
            if now_jst_hour == 2 and last_nightly_date != today_str:
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
                check_tp_sl_all_positions()
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

                        # アンカー価格を更新
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
            # 3. Council召集（トリガー発火時のみ）
            # ============================================================
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
