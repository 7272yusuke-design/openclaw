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
from datetime import datetime
from tools.market_data import MarketData
from core.blackboard import NeoBlackboard
from agents.trinity_council import TrinityCouncil
from tools.discord_reporter import DiscordReporter
from orchestration.alpha_sweep_operation import run_sweep
from core.config import VOLATILITY_WATCH_SYMBOLS
from orchestration.performance_evaluator import evaluate_performance
from orchestration.nightly_research import run_nightly_research
from orchestration.vp_discovery import run_vp_discovery
from core.config import LEARNING_MODE, LEARNING_TARGET_TRADES, LEARNING_SHARPE_THRESHOLD

# --- 設定 ---
CHECK_INTERVAL = 30           # 監視間隔（秒）
VOLATILITY_THRESHOLD = 2.0    # ボラティリティ閾値（%）
ALPHA_THRESHOLD = LEARNING_SHARPE_THRESHOLD if LEARNING_MODE else 5.0  # 学習モード中は緩和
COUNCIL_COOLDOWN = 1800       # 冷却期間（30分）— Moltbook Rate Limit保護
SWEEP_INTERVAL   = 120        # Sweepサイクル間隔（30秒×120=60分）
EVAL_INTERVAL    = 720        # Evaluatorサイクル間隔（30秒×720=6時間）
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
    from datetime import datetime as _dt
    batch_start = time.time()
    today = _dt.now().strftime("%Y-%m-%d")
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
    from datetime import datetime as _dt2
    if _dt2.utcnow().weekday() == 0:  # 0=月曜
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

    # 4. Discord日次サマリー
    logger.info("[Nightly] Step 4/4: Discord日次サマリー送信")
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

        summary = (
            f"📅 **日次バッチ完了** — {today}\n"
            f"⏱️ 実行時間: {elapsed}秒\n"
            f"🎯 現在の勝率: {accuracy}% ({total_trades}件)\n"
            f"🔍 Alpha機会: {opp_count}件\n"
            f"✅ Sweep / Evaluator / Dashboard 完了"
            f"{moltbook_report}"
        )
        DiscordReporter.send_log("🌙 Nightly Batch Report", summary, color=0x9b59b6)
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
            # 0b. Nightly Batch（JST 02:00 = UTC 17:00 に1日1回）
            # ============================================================
            now_utc = datetime.utcnow()
            now_jst_hour = (now_utc.hour + 9) % 24
            today_str = now_utc.strftime('%Y-%m-%d')
            if now_jst_hour == 2 and last_nightly_date != today_str:
                last_nightly_date = today_str
                logger.info(f'[Nightly] 深夜バッチ開始 JST02:00 ({today_str})')
                try:
                    _run_nightly_batch()
                except Exception as e:
                    logger.error(f'[Nightly] エラー: {e}')


                        # ============================================================
            # 1. ボラティリティ監視 (Tier1: VIRTUAL / AIXBT)
            # ============================================================
            current_price = anchor_prices.get("VIRTUAL", 0.0)  # ステータス表示用
            for _vsym in VOLATILITY_WATCH_SYMBOLS:
                try:
                    _vdata = MarketData.fetch_token_data(_vsym)
                    if _vdata and _vdata.get("status") == "success":
                        _vprice = float(_vdata.get("priceUsd", 0.0))
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
                    for s, d in opps.items():
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
                    # 取引後に勝率を即時更新
                    try:
                        evaluate_performance(send_dashboard=False)
                    except Exception as _e:
                        logger.error(f"[Evaluator] Post-council error: {_e}")
                    
                except Exception as e:
                    logger.error(f"⚠️ Council Error: {e}", exc_info=True)
                    last_council_time = time.time()  # エラー時も冷却開始（連続エラー防止）
                    
                    DiscordReporter.send_log(
                        "❌ Council Error",
                        f"**Symbol:** {trigger_symbol}\n**Error:** {str(e)[:500]}",
                        0xe74c3c
                    )

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
