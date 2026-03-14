import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("neo.quant.validator")

class DataValidator:
    """Data Quality Layer: Ensures temporal alignment and removes anomalies."""
    
    @staticmethod
    def clean_ohlcv(df: pd.DataFrame, freq: str = "1min", spike_threshold: float = 0.2) -> pd.DataFrame:
        """Aligns timestamps, forward-fills gaps, and removes price spikes."""
        if df is None or df.empty:
            logger.warning("Received empty DataFrame for validation.")
            return pd.DataFrame()

        try:
            df = df.copy()
            df = df.set_index("timestamp")
            
            # 1. タイム整列 (Time Alignment)
            df = df.resample(freq).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            })
            
            # 2. 欠損値の補間 (Forward Fill)
            missing_before = df["close"].isna().sum()
            df = df.ffill()
            if missing_before > 0:
                logger.info(f"Forward-filled {missing_before} missing intervals.")
                
            # 3. 異常スパイクの検知と除去 (Spike Filter)
            returns = df["close"].pct_change()
            spike_mask = abs(returns) > spike_threshold
            spike_count = spike_mask.sum()
            
            if spike_count > 0:
                logger.warning(f"Detected and removed {spike_count} anomalies (Spike > {spike_threshold * 100}%).")
                df.loc[spike_mask, "close"] = np.nan
                df["close"] = df["close"].ffill() # スパイク部分を直前の正常値で埋める

            return df.reset_index()
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            raise
