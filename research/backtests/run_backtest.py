import vectorbt as vbt
import pandas as pd
import numpy as np
import math
import logging

logger = logging.getLogger("neo.quant.backtest")


def _extract_stats(portfolio, strategy_name: str) -> dict:
    """vectorbt portfolio から統一フォーマットのdictを生成"""
    try:
        stats = portfolio.stats()
        total_trades = int(stats.get('Total Trades', 0))
        sharpe_raw   = float(stats.get('Sharpe Ratio', 0.0) or 0.0)
        total_return = float(stats.get('Total Return [%]', 0.0) or 0.0)
        max_dd       = float(stats.get('Max Drawdown [%]', 0.0) or 0.0)
        win_rate     = float(stats.get('Win Rate [%]', 0.0) or 0.0)

        # Sharpeガード: 取引3回未満 or inf/nan → 0.0
        if total_trades < 3 or math.isinf(sharpe_raw) or math.isnan(sharpe_raw):
            sharpe_adj = 0.0
            confidence = "LOW"
        else:
            sharpe_adj = max(0.0, round(sharpe_raw, 3))
            confidence = "HIGH" if total_trades >= 10 else "MED"

        return {
            "strategy":     strategy_name,
            "sharpe":       sharpe_adj,
            "sharpe_raw":   round(sharpe_raw, 3) if math.isfinite(sharpe_raw) else 0.0,
            "total_return": f"{total_return:.2f}%",
            "max_dd":       f"{max_dd:.2f}%",
            "win_rate":     round(win_rate, 1),
            "trades":       total_trades,
            "confidence":   confidence,
        }
    except Exception as e:
        logger.error(f"[_extract_stats] {strategy_name}: {e}")
        return {
            "strategy": strategy_name, "sharpe": 0.0, "sharpe_raw": 0.0,
            "total_return": "0.00%", "max_dd": "0.00%",
            "win_rate": 0.0, "trades": 0, "confidence": "LOW",
            "note": str(e)[:60]
        }


class CoreBacktest:
    """High-performance backtesting using vectorbt — 4戦略対応版"""

    # ── 戦略1: Alpha Strategy（既存・変更なし）────────────────────────
    @staticmethod
    def run_alpha_strategy(df: pd.DataFrame) -> dict:
        """Regime + RSI + Bollinger Squeeze"""
        try:
            close   = df["close"]
            entries = (df["market_regime"] == 1) & (df["rsi_14"] < 55) & (df["is_vol_squeeze"] == 0)
            exits   = (df["market_regime"] == -1) | (df["rsi_14"] > 70)
            pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq='4h')
            return _extract_stats(pf, "alpha_strategy")
        except Exception as e:
            logger.error(f"[alpha_strategy] {e}")
            return {"strategy": "alpha_strategy", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # 後方互換エイリアス
    @staticmethod
    def run_ma_cross(df: pd.DataFrame) -> dict:
        return CoreBacktest.run_alpha_strategy(df)

    # ── 戦略2: BB Reversal（新規）────────────────────────────────────
    @staticmethod
    def run_bb_reversal(df: pd.DataFrame) -> dict:
        """ボリンジャーバンド逆張り: Lower割れBUY / Upper超えSELL"""
        try:
            close = df["close"]
            ma    = close.rolling(20).mean()
            std   = close.rolling(20).std()
            upper = ma + 2 * std
            lower = ma - 2 * std

            entries = close < lower
            exits   = close > upper

            pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq='4h')
            result = _extract_stats(pf, "bb_reversal")
            result["description"] = "BB逆張り（Lower割れBUY / Upper超えSELL）"
            return result
        except Exception as e:
            logger.error(f"[bb_reversal] {e}")
            return {"strategy": "bb_reversal", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 戦略3: Momentum Breakout（新規）──────────────────────────────
    @staticmethod
    def run_momentum_breakout(df: pd.DataFrame) -> dict:
        """直近20本高値ブレイク + 出来高確認、5本後エグジット"""
        try:
            close  = df["close"]
            high   = df["high"] if "high" in df.columns else close

            # volumeがない場合は全シグナル有効扱い
            if "volume" in df.columns and df["volume"].sum() > 0:
                volume = df["volume"]
                vol_ma = volume.rolling(20).mean()
                vol_ok = volume > vol_ma * 1.5
            else:
                vol_ok = pd.Series(True, index=close.index)

            high_roll = high.rolling(20).max().shift(1)
            entries   = (high > high_roll) & vol_ok

            # 5本後に強制エグジット（タイムベース決済）
            exits = entries.shift(5).fillna(False).infer_objects(copy=False)

            pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq='4h')
            result = _extract_stats(pf, "momentum_breakout")
            result["description"] = "高値ブレイク+出来高確認（5本後エグジット）"
            return result
        except Exception as e:
            logger.error(f"[momentum_breakout] {e}")
            return {"strategy": "momentum_breakout", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 戦略4: Mean Reversion（新規）────────────────────────────────
    @staticmethod
    def run_mean_reversion(df: pd.DataFrame) -> dict:
        """RSI<30 + レンジ相場エントリー / RSI>55 or -3%損切り"""
        try:
            close = df["close"]
            rsi   = df["rsi_14"] if "rsi_14" in df.columns else _calc_rsi(close)

            # ATRベースのレンジ判定
            high = df["high"] if "high" in df.columns else close
            low  = df["low"]  if "low"  in df.columns else close
            tr   = pd.concat([
                (high - low),
                (high - close.shift()).abs(),
                (low  - close.shift()).abs()
            ], axis=1).max(axis=1)
            atr    = tr.rolling(14).mean()
            atr_ma = atr.rolling(30).mean()
            is_range = atr < atr_ma  # ATR平均以下 = レンジ相場

            entries = (rsi < 30) & is_range
            exits   = (rsi > 55)

            pf = vbt.Portfolio.from_signals(
                close, entries, exits,
                fees=0.001, freq='4h',
                sl_stop=0.03   # 3%ストップロス
            )
            result = _extract_stats(pf, "mean_reversion")
            result["description"] = "RSI<30+レンジエントリー（RSI>55 or -3%損切り）"
            return result
        except Exception as e:
            logger.error(f"[mean_reversion] {e}")
            return {"strategy": "mean_reversion", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 全戦略一括実行（Task 2.2 メインAPI）─────────────────────────
    @staticmethod
    def run_all_strategies(df: pd.DataFrame) -> dict:
        """4戦略を実行し、最良Sharpeの戦略を返す"""
        results = {
            "alpha_strategy":    CoreBacktest.run_alpha_strategy(df),
            "bb_reversal":       CoreBacktest.run_bb_reversal(df),
            "momentum_breakout": CoreBacktest.run_momentum_breakout(df),
            "mean_reversion":    CoreBacktest.run_mean_reversion(df),
        }
        best = max(results.values(), key=lambda r: r.get("sharpe", 0.0))
        summary = (
            f"最良戦略: {best['strategy']} | "
            f"Sharpe: {best['sharpe']} | "
            f"Win: {best.get('win_rate', 0)}% | "
            f"Trades: {best.get('trades', 0)} | "
            f"Confidence: {best.get('confidence', 'LOW')}"
        )
        return {"best": best, "all_results": results, "summary": summary}


def _calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """FeatureBuilderが使えない場合のRSIフォールバック計算"""
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))
