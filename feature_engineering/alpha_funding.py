import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("neo.quant.alpha.funding")

class FundingRateAlpha:
    """
    Enterprise-grade Funding Rate Alpha extracted from institutional practices.
    Reference: Qlib & AlphaTrade concepts.
    """
    
    @staticmethod
    def calculate_zscore(df: pd.DataFrame, window: int = 24, column: str = "funding_rate") -> pd.DataFrame:
        """
        Calculates the Rolling Z-Score of the Funding Rate to detect statistical anomalies.
        Z = (X - μ) / σ
        """
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found. Cannot calculate Funding Rate Z-Score.")
            return df
            
        df = df.copy()
        rolling_mean = df[column].rolling(window=window, min_periods=window//2).mean()
        rolling_std = df[column].rolling(window=window, min_periods=window//2).std()
        
        # ゼロ除算を回避
        rolling_std = rolling_std.replace(0, np.nan)
        
        feature_name = f"funding_zscore_{window}"
        df[feature_name] = (df[column] - rolling_mean) / rolling_std
        
        logger.info(f"Calculated {feature_name}")
        return df

    @staticmethod
    def calculate_term_structure_momentum(df: pd.DataFrame, short_window: int = 8, long_window: int = 72) -> pd.DataFrame:
        """
        Calculates the difference between short-term and long-term average funding rates.
        A sudden spike in the short-term relative to the long-term indicates a potential squeeze.
        """
        column = "funding_rate"
        if column not in df.columns:
            return df
            
        df = df.copy()
        short_ma = df[column].rolling(window=short_window).mean()
        long_ma = df[column].rolling(window=long_window).mean()
        
        feature_name = f"funding_momentum_{short_window}_{long_window}"
        df[feature_name] = short_ma - long_ma
        
        logger.info(f"Calculated {feature_name}")
        return df

    @staticmethod
    def build_all_features(df: pd.DataFrame) -> pd.DataFrame:
        """Master function to apply all Funding Rate related alphas."""
        logger.info("Building Funding Rate Alpha features...")
        df = FundingRateAlpha.calculate_zscore(df, window=24)
        df = FundingRateAlpha.calculate_zscore(df, window=72)
        df = FundingRateAlpha.calculate_term_structure_momentum(df)
        return df
