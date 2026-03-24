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
                # pandas-ta BB列名はバージョンにより BBU_20_2.0 or BBU_20_2.0_2.0
                _bbu_col = next((c for c in _bb.columns if c.startswith(f"BBU_{window}")), None)
                _bbl_col = next((c for c in _bb.columns if c.startswith(f"BBL_{window}")), None)
                _bbm_col = next((c for c in _bb.columns if c.startswith(f"BBM_{window}")), None)
                upper_band = _bb[_bbu_col] if _bbu_col else df["close"]
                lower_band = _bb[_bbl_col] if _bbl_col else df["close"]
                rolling_mean = _bb[_bbm_col] if _bbm_col else df["close"].rolling(window).mean()
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
