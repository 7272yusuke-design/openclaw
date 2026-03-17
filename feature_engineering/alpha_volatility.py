import pandas as pd
import numpy as np
import logging
try:
    import pandas_ta as ta
    _HAS_TA = True
except ImportError:
    _HAS_TA = False

logger = logging.getLogger("neo.quant.alpha.volatility")

class VolatilityAlpha:
    """Detects volatility compression (Squeeze) and expansion."""
    
    @staticmethod
    def calculate_bollinger_squeeze(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        if "close" not in df.columns:
            return df
            
        df = df.copy()
        if _HAS_TA:
            _bb = ta.bbands(df["close"], length=window, std=2)
            if _bb is not None:
                upper_band = _bb.get(f"BBU_{window}_2.0", df["close"])
                lower_band = _bb.get(f"BBL_{window}_2.0", df["close"])
                rolling_mean = _bb.get(f"BBM_{window}_2.0", df["close"].rolling(window).mean())
            else:
                rolling_mean = df["close"].rolling(window=window).mean()
                rolling_std = df["close"].rolling(window=window).std()
                upper_band = rolling_mean + (rolling_std * 2)
                lower_band = rolling_mean - (rolling_std * 2)
            # OBVを追加（出来高と価格の乖離を検出）
            if "volume" in df.columns:
                _obv = ta.obv(df["close"], df["volume"])
                if _obv is not None:
                    df["obv"] = _obv
        else:
            rolling_mean = df["close"].rolling(window=window).mean()
            rolling_std = df["close"].rolling(window=window).std()
            upper_band = rolling_mean + (rolling_std * 2)
            lower_band = rolling_mean - (rolling_std * 2)
        epsilon = 1e-8
        df[f"bb_bandwidth_{window}"] = (upper_band - lower_band) / (rolling_mean + epsilon)
        
        # 過去100期間での最小Bandwidthに対する現在の割合（0に近づくほど極端な収縮）
        min_bandwidth = df[f"bb_bandwidth_{window}"].rolling(window=100, min_periods=20).min()
        df["is_vol_squeeze"] = (df[f"bb_bandwidth_{window}"] <= (min_bandwidth * 1.1)).astype(int)
        
        logger.info(f"Calculated Volatility Squeeze (window={window})")
        return df
