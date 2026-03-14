import sys
import os
import time
import logging
from pathlib import Path

BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
sys.path.append(str(BASE_DIR))

from data_pipeline.market_data import QuantMarketData
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest
from core.blackboard import NeoBlackboard

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("neo.live_monitor")

def monitor_and_signal():
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    fetcher = QuantMarketData(exchange_id="binance")
    
    logger.info("=== 🛡️ Multi-Asset Live Monitor Started ===")
    
    while True:
        for symbol in symbols:
            try:
                # 1. 最新データ取得
                df = fetcher.fetch_ohlcv(symbol=symbol, timeframe="1h", limit=100)
                
                # 2. 特徴量計算
                feat_df = FeatureBuilder.build_from_memory(df)
                
                # 3. 最新の1行からシグナル判定
                # バックテストエンジンのロジックを流用し、最新の意思決定を取得
                last_signal = "NEUTRAL"
                # (ここに具体的なシグナル抽出ロジックを配置)
                
                logger.info(f"[{symbol}] Price: {df['close'].iloc[-1]:.2f} | Signal: {last_signal}")
                
                # Blackboardを更新
                NeoBlackboard.update("market_intel", {
                    symbol.split('/')[0]: {
                        "price": float(df['close'].iloc[-1]),
                        "price_24h_avg": float(df['close'].mean()),
                        "social_velocity": 1.0,
                        "whale_alert": "None"
                    }
                })
                
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
        
        logger.info("--- Waiting for next cycle (60s) ---")
        time.sleep(60)

if __name__ == "__main__":
    monitor_and_signal()
