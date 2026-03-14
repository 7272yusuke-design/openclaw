import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("neo.quant.alpha.liquidation")

class LiquidationAlpha:
    """
    Enterprise-grade Liquidation Cascade detection.
    Identifies panic selling/buying exhaustion using statistical thresholds.
    """
    
    @staticmethod
    def calculate_liquidation_imbalance(df: pd.DataFrame, window: int = 12) -> pd.DataFrame:
        """
        Calculates the normalized imbalance between Long and Short liquidations.
        +1 means 100% Long liquidations (Panic Sell), -1 means 100% Short liquidations (Short Squeeze).
        """
        required_cols = ["liq_long", "liq_short"]
        if not all(col in df.columns for col in required_cols):
            logger.warning("Liquidation columns missing. Skipping imbalance calculation.")
            return df
            
        df = df.copy()
        total_liq = df["liq_long"] + df["liq_short"]
        
        # ゼロ除算回避のための微小値(epsilon)を追加
        epsilon = 1e-8
        df["liq_imbalance"] = (df["liq_long"] - df["liq_short"]) / (total_liq + epsilon)
        
        # 移動平均で平滑化
        df[f"liq_imbalance_ma_{window}"] = df["liq_imbalance"].rolling(window=window).mean()
        
        logger.info(f"Calculated Liquidation Imbalance (window={window})")
        return df

    @staticmethod
    def detect_panic_exhaustion(df: pd.DataFrame, window: int = 48, z_threshold: float = 3.0) -> pd.DataFrame:
        """
        Detects 'Exhaustion' (Climax) by calculating the Z-Score of Long liquidations.
        If the Z-score exceeds the threshold (e.g., 3 sigma), it signals a potential bottom.
        """
        if "liq_long" not in df.columns:
            return df
            
        df = df.copy()
        rolling_mean = df["liq_long"].rolling(window=window, min_periods=window//4).mean()
        rolling_std = df["liq_long"].rolling(window=window, min_periods=window//4).std()
        
        rolling_std = rolling_std.replace(0, np.nan)
        df["liq_long_zscore"] = (df["liq_long"] - rolling_mean) / rolling_std
        
        # スレッショルドを超えたかどうかのフラグ（1 = パニック発生, 0 = 平常）
        df["panic_long_exhaustion"] = (df["liq_long_zscore"] > z_threshold).astype(int)
        
        logger.info(f"Calculated Panic Exhaustion Z-Score (threshold={z_threshold}σ)")
        return df

    @staticmethod
    def build_all_features(df: pd.DataFrame) -> pd.DataFrame:
        """Master function to apply all Liquidation related alphas."""
        logger.info("Building Liquidation Alpha features...")
        df = LiquidationAlpha.calculate_liquidation_imbalance(df)
        df = LiquidationAlpha.detect_panic_exhaustion(df)
        return df
