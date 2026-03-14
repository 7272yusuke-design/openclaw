import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("neo.quant.alpha.crossasset")

class CrossAssetAlpha:
    """Measures relative strength and momentum acceleration."""
    
    @staticmethod
    def calculate_momentum_acceleration(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        if "close" not in df.columns:
            return df
            
        df = df.copy()
        # 1次微分（速度: Returns）
        df["returns"] = df["close"].pct_change()
        
        # 2次微分（加速度: 速度の変化率）
        df["acceleration"] = df["returns"].diff()
        
        # RSIの計算（指数移動平均ベース）
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/window, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/window, adjust=False).mean()
        rs = gain / (loss + 1e-8)
        df[f"rsi_{window}"] = 100 - (100 / (1 + rs))
        
        logger.info(f"Calculated Momentum Acceleration and RSI (window={window})")
        return df
