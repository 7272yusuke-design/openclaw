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

# --- 設定 ---
CHECK_INTERVAL = 30           # 監視間隔（秒）
VOLATILITY_THRESHOLD = 2.0    # ボラティリティ閾値（%）
ALPHA_THRESHOLD = 5.0         # Sharpe閾値
COUNCIL_COOLDOWN = 1800       # 冷却期間（30分）— Moltbook Rate Limit保護

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("radar.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("neo.radar")

def start_hybrid_radar():
    print("=" * 60)
    print(f" 📡 Neo Hybrid Radar v2: UNIFIED TRIGGER MODE")
    print(f" ⏱️  Interval: {CHECK_INTERVAL}s | Vol: {VOLATILITY_THRESHOLD}% | Alpha: {ALPHA_THRESHOLD}")
    print(f" 🧊 Cooldown: {COUNCIL_COOLDOWN // 60}min")
    print("=" * 60)
    
    # 初期価格の取得
    initial_data = MarketData.fetch_token_data("VIRTUAL")
    anchor_price = float(initial_data.get("priceUsd", 0.0)) if initial_data else 0.0
    
    if anchor_price <= 0:
        logger.error("❌ 初期価格の取得に失敗。5秒後にリトライ...")
        time.sleep(5)
        initial_data = MarketData.fetch_token_data("VIRTUAL")
        anchor_price = float(initial_data.get("priceUsd", 0.0)) if initial_data else 0.0
        if anchor_price <= 0:
            logger.error("❌ リトライ失敗。レーダーを停止します。")
            return
    
    logger.info(f"🎯 Anchor price: ${anchor_price:.6f}")
    
    processed_alphas = {}     # 処理済みアルファのタイムスタンプ
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
            # 1. ボラティリティ監視 (VIRTUAL)
            # ============================================================
            try:
                current_data = MarketData.fetch_token_data("VIRTUAL")
                if current_data and current_data.get("status") == "success":
                    current_price = float(current_data.get("priceUsd", 0.0))
                    change_percent = abs((current_price - anchor_price) / anchor_price) * 100 if anchor_price > 0 else 0
                    
                    if change_percent >= VOLATILITY_THRESHOLD:
                        direction = "上昇" if current_price > anchor_price else "下落"
                        logger.warning(f"🚨 [VOLATILITY] VIRTUAL {direction} {change_percent:.2f}% (${anchor_price:.6f} → ${current_price:.6f})")
                        
                        if is_cooled_down:
                            trigger_type = "VOLATILITY"
                            trigger_symbol = "VIRTUAL"
                            trigger_context = f"VIRTUAL価格が{change_percent:.2f}%{direction}（${anchor_price:.6f}→${current_price:.6f}）"
                        else:
                            logger.info(f"  ⏳ 冷却中（残り{int(cooldown_remaining/60)}分）— ボラトリガーを保留")
                        
                        # アンカー価格を更新（トリガーの有無に関わらず）
                        anchor_price = current_price
                else:
                    current_price = anchor_price  # フォールバック
            except Exception as e:
                logger.error(f"ボラティリティ監視エラー: {e}")
                current_price = anchor_price

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
