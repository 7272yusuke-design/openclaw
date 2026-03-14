import sys
import os
import time
import logging
from pathlib import Path

# パス設定
BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from agents.scout_agent import ScoutCrew

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("neo.sweep_op")

def run_sweep():
    # 掃討対象：ボラティリティと歪みが期待できる主要アルト
    targets = ["VIRTUAL/USDT", "AIXBT/USDT", "LUNA/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
    
    logger.info(f"=== 🌊 Starting High-Alpha Sweep Operation: {len(targets)} targets ===")
    
    for symbol in targets:
        try:
            logger.info(f"🛰️ Scanning {symbol}...")
            # ScoutCrewを起動（先ほど実装した自動アラート機能が内蔵されています）
            scout = ScoutCrew()
            scout.run(
                goal=f"{symbol}の数学的優位性を洗え。",
                context="全域掃討作戦：Sharpe 5.0超えのモンスター銘柄を特定せよ。"
            )
            # レートリミット対策で少し待機
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Failed to scan {symbol}: {e}")

    logger.info("=== 🏁 Sweep Operation Completed. Check Blackboard for CRITICAL alerts. ===")

if __name__ == "__main__":
    run_sweep()
