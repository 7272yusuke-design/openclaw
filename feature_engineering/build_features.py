import pandas as pd
import logging
from feature_engineering.alpha_funding import FundingRateAlpha
from feature_engineering.alpha_liquidation import LiquidationAlpha
from feature_engineering.alpha_volatility import VolatilityAlpha
from feature_engineering.alpha_cross_asset import CrossAssetAlpha
from feature_engineering.alpha_regime import RegimeAlpha

logger = logging.getLogger("neo.quant.features")

class FeatureBuilder:
    @staticmethod
    def build_from_memory(df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"Processing {len(df)} rows.")
        
        # 基礎指標
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['ma50'] = df['close'].rolling(window=50, min_periods=1).mean()

        # アルファ計算
        has_funding = "funding_rate" in df.columns
        has_liquidation = all(c in df.columns for c in ["liq_long", "liq_short"])
        if has_funding:
            df = FundingRateAlpha.build_all_features(df)
        else:
            logger.info("funding_rate unavailable — skipping FundingRateAlpha (CoinGecko mode)")
        if has_liquidation:
            df = LiquidationAlpha.build_all_features(df)
        else:
            logger.info("liquidation data unavailable — skipping LiquidationAlpha (CoinGecko mode)")
        df = VolatilityAlpha.calculate_bollinger_squeeze(df)
        df = CrossAssetAlpha.calculate_momentum_acceleration(df)
        df = RegimeAlpha.detect_trend_regime(df)

        # 窓関数による欠損を許容し、データがある「後半部分」を確実に残す
        df_clean = df.dropna().reset_index(drop=True)
        
        # もし全滅しそうなら、直近200件だけでも無理やり残す（インデックスエラー回避）
        if len(df_clean) < 1:
            logger.warning("Applying emergency recovery for zero-row state.")
            df_clean = df.tail(200).ffill().fillna(0).reset_index(drop=True)

        logger.info(f"Final Valid Range: {len(df_clean)} rows.")
        return df_clean

    @staticmethod
    def build_core_features(path: str) -> pd.DataFrame:
        return FeatureBuilder.build_from_memory(pd.read_parquet(path))
