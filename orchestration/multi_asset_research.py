import sys
import os
from pathlib import Path
import logging
import pandas as pd

# 既存の nightly_research.py と同じパス設定を継承
BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from data_pipeline.market_data import QuantMarketData
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("neo.multi_asset")

def run_multi_research(symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"]):
    results = []
    fetcher = QuantMarketData(exchange_id="binance")
    
    for symbol in symbols:
        try:
            logger.info(f"=== 🛰️ Scanning {symbol} ===")
            # 1. データ取得
            raw_df = fetcher.fetch_ohlcv(symbol=symbol, timeframe="1h", limit=1000)
            
            # 2. 特徴量生成
            feature_df = FeatureBuilder.build_from_memory(raw_df)
            
            if len(feature_df) < 50:
                logger.warning(f"Skipping {symbol}: Insufficient valid data range.")
                continue

            # 3. バックテスト (nightly_research.py と同じメソッドを使用)
            portfolio = CoreBacktest.run_alpha_strategy(feature_df)
            stats = portfolio.stats()
            
            results.append({
                "Symbol": symbol,
                "Return [%]": stats['Total Return [%]'],
                "Sharpe": stats['Sharpe Ratio'],
                "MaxDD [%]": stats['Max Drawdown [%]'],
                "Samples": len(feature_df)
            })
        except Exception as e:
            logger.error(f"Failed to scan {symbol}: {e}")

    # 4. レポート表示
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        print("\n" + "="*65)
        print("📊 MULTI-ASSET ALPHA REPORT (Recent Data Focus)")
        print("="*65)
        print(df_results.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        print("="*65)
    else:
        logger.error("No valid results. Check exchange connectivity or data range.")

if __name__ == "__main__":
    run_multi_research()
