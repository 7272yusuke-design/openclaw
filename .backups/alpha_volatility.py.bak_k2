import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("neo.quant.alpha.volatility")

class VolatilityAlpha:
    """Detects volatility compression (Squeeze) and expansion."""
    
    @staticmethod
    def calculate_bollinger_squeeze(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        if "close" not in df.columns:
            return df
            
        df = df.copy()
        rolling_mean = df["close"].rolling(window=window).mean()
        rolling_std = df["close"].rolling(window=window).std()
        
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        
        # Bandwidth: 幅が狭いほどエネルギーが溜まっている(Squeeze)
        epsilon = 1e-8
        df[f"bb_bandwidth_{window}"] = (upper_band - lower_band) / (rolling_mean + epsilon)
        
        # 過去100期間での最小Bandwidthに対する現在の割合（0に近づくほど極端な収縮）
        min_bandwidth = df[f"bb_bandwidth_{window}"].rolling(window=100, min_periods=20).min()
        df["is_vol_squeeze"] = (df[f"bb_bandwidth_{window}"] <= (min_bandwidth * 1.1)).astype(int)
        
        logger.info(f"Calculated Volatility Squeeze (window={window})")
        return df
