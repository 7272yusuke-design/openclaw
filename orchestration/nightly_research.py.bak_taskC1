import sys
import os
from pathlib import Path
import logging
import pandas as pd

BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
sys.path.append(str(BASE_DIR))

from data_pipeline.market_data import QuantMarketData
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("neo.quant.orchestrator")

def run_sprint1_pipeline():
    logger.info("=== 🚀 Final Synchronization (Sprint 1) ===")
    
    # 1. データ取得（funding_rate/liqを含むDataFrameを直接取得）
    fetcher = QuantMarketData(exchange_id="binance")
    raw_df = fetcher.fetch_ohlcv(symbol="BTC/USDT", timeframe="1h", limit=1000)
    
    # 2. 特徴量生成（パスではなくDataFrameを直接渡すように修正したメソッドを呼ぶ）
    # ※build_core_featuresを修正し、DFを直接受け取れるようにします
    feature_df = FeatureBuilder.build_from_memory(raw_df)

    # 3. バックテスト
    portfolio = CoreBacktest.run_alpha_strategy(feature_df)
    
    # 4. 結果表示
    stats = portfolio.stats()
    logger.info("=== 📊 Sprint 1 Final Results ===")
    logger.info(f"Total Return : {stats['Total Return [%]']:.2f}%")
    logger.info(f"Sharpe Ratio : {stats['Sharpe Ratio']:.2f}")
    logger.info(f"Max Drawdown : {stats['Max Drawdown [%]']:.2f}%")
    logger.info("=======================================")

if __name__ == "__main__":
    run_sprint1_pipeline()
