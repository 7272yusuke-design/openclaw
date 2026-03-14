import vectorbt as vbt
import pandas as pd
import logging

logger = logging.getLogger("neo.quant.backtest")

class CoreBacktest:
    """High-performance backtesting using vectorbt."""
    
    @staticmethod
    def run_alpha_strategy(df: pd.DataFrame):
        try:
            close = df["close"]
            
            # --- アルファを組み合わせた実戦的ロジック ---
            # 条件1: レジームが「Bull(1)」であること（上昇トレンドでのみ買いを許可）
            # 条件2: RSI(14) が 40 以下（短期的な売られすぎ）
            # 条件3: ボラティリティ・スクイーズが発生していない（動意づいている）
            
            entries = (df["market_regime"] == 1) & (df["rsi_14"] < 55) & (df["is_vol_squeeze"] == 0)
            
            # 決済条件: レジームが「Bear(-1)」に転落するか、RSIが買われすぎ(70以上)になったら逃げる
            exits = (df["market_regime"] == -1) | (df["rsi_14"] > 70)

            # 手数料(0.1%)を加味したポートフォリオ生成
            portfolio = vbt.Portfolio.from_signals(
                close, entries, exits, fees=0.001, freq='1h'
            )
            logger.info("Alpha-driven backtest execution completed.")
            return portfolio
            
        except KeyError as e:
            logger.error(f"Required Alpha column missing for backtest: {e}")
            raise
        except Exception as e:
            logger.error(f"Backtest execution failed: {e}")
            raise

    # 互換性維持のため、古いメソッド名は残しつつ新しいロジックへ流す
    @staticmethod
    def run_ma_cross(df: pd.DataFrame):
        return CoreBacktest.run_alpha_strategy(df)
