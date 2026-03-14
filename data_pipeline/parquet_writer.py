import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger("neo.quant.datalake")

class ParquetDataLake:
    """Handles persistent storage of quantitative data in Parquet format."""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.cleaned_dir = self.base_dir / "cleaned"
        
        # ディレクトリが存在しない場合は作成 (聖域の確保)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)

    def save_cleaned(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Path:
        """Saves validated DataFrame to the cleaned data lake."""
        safe_symbol = symbol.replace("/", "_").lower()
        file_path = self.cleaned_dir / f"{safe_symbol}_{timeframe}.parquet"
        
        try:
            df.to_parquet(file_path, engine="pyarrow", compression="snappy")
            logger.info(f"Saved {len(df)} rows to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save Parquet file: {e}")
            raise
