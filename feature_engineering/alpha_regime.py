import pandas as pd
import logging

logger = logging.getLogger("neo.quant.alpha.regime")

class RegimeAlpha:
    """Classifies the market regime (Trend vs Range, Bull vs Bear)."""
    
    @staticmethod
    def detect_trend_regime(df: pd.DataFrame, short_w: int = 20, mid_w: int = 50, long_w: int = 100) -> pd.DataFrame:
        """
        移動平均線の配列でレジームを判定。
        long_w を 200→100 に変更（4h足180本に適合）
        """
        if "close" not in df.columns:
            return df
            
        df = df.copy()
        # min_periods を設定して、短いデータでもNaN地獄を回避
        df["ma_short"] = df["close"].rolling(window=short_w, min_periods=short_w//2).mean()
        df["ma_mid"] = df["close"].rolling(window=mid_w, min_periods=mid_w//2).mean()
        df["ma_long"] = df["close"].rolling(window=long_w, min_periods=long_w//2).mean()
        
        # レジーム判定 (1: Bull Trend, -1: Bear Trend, 0: Chop/Range)
        bull_cond = (df["close"] > df["ma_short"]) & (df["ma_short"] > df["ma_mid"]) & (df["ma_mid"] > df["ma_long"])
        bear_cond = (df["close"] < df["ma_short"]) & (df["ma_short"] < df["ma_mid"]) & (df["ma_mid"] < df["ma_long"])
        
        df["market_regime"] = 0
        df.loc[bull_cond, "market_regime"] = 1
        df.loc[bear_cond, "market_regime"] = -1
        
        logger.info(f"Calculated Market Regime (Bull=1, Bear=-1, Range=0) [windows: {short_w}/{mid_w}/{long_w}]")
        return df
