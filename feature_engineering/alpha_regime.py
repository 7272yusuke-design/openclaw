import pandas as pd
import logging
try:
    import pandas_ta as ta
    _HAS_TA = True
except ImportError:
    _HAS_TA = False

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
        if _HAS_TA:
            # pandas-ta EMA（自作rollingより精度が高い）
            df["ma_short"] = ta.ema(df["close"], length=short_w)
            df["ma_mid"]   = ta.ema(df["close"], length=mid_w)
            df["ma_long"]  = ta.ema(df["close"], length=long_w)
            # RSIもpandas-taで上書き（より正確）
            _rsi = ta.rsi(df["close"], length=14)
            if _rsi is not None:
                df["rsi_14"] = _rsi
            # MACDを追加
            _macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if _macd is not None:
                df["macd"]        = _macd.get("MACD_12_26_9", 0)
                df["macd_signal"] = _macd.get("MACDs_12_26_9", 0)
                df["macd_hist"]   = _macd.get("MACDh_12_26_9", 0)
            # ATRを追加（ストップロス計算用）
            if all(c in df.columns for c in ["high","low","close"]):
                _atr = ta.atr(df["high"], df["low"], df["close"], length=14)
                if _atr is not None:
                    df["atr_14"] = _atr
        else:
            # フォールバック: 自作rolling
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
