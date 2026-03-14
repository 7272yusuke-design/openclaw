import ccxt
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("neo.quant.pipeline")

class QuantMarketData:
    def __init__(self, exchange_id="binance"):
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}})

    def fetch_ohlcv(self, symbol="BTC/USDT", timeframe="1h", limit=1000):
        logger.info(f"Fetching {symbol} price and optimized funding history...")
        
        # 1. 価格データ取得 (1000件程度が最も安定します)
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 2. Funding Rate の取得 (sinceを指定せず、取引所が許す最大件数を取得)
        try:
            fr = self.exchange.fetch_funding_rate_history(symbol, limit=1000)
            fr_df = pd.DataFrame(fr)
            fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp'], unit='ms')
            fr_df = fr_df[['timestamp', 'fundingRate']].rename(columns={'fundingRate': 'funding_rate'})
            
            # 結合
            df = pd.merge_asof(df.sort_values('timestamp'), fr_df.sort_values('timestamp'), on='timestamp', direction='backward')
            df['funding_rate'] = df['funding_rate'].ffill()
            logger.info(f"Integrated {len(fr_df)} real Funding points.")
        except Exception as e:
            logger.warning(f"Funding sync failed: {e}")
            df['funding_rate'] = 0.0

        # 他のカラムを維持
        df['open_interest'] = 0.0
        df['liq_long'] = 0.0
        df['liq_short'] = 0.0
        
        return df
