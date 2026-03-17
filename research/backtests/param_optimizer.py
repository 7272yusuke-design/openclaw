"""
vectorbt パラメータ最適化モジュール
各戦略のハイパーパラメータをグリッドサーチで最適化する
"""
import numpy as np
import pandas as pd
import vectorbt as vbt
import logging

logger = logging.getLogger("neo.param_optimizer")

def optimize_macd_params(df: pd.DataFrame, symbol: str = "UNKNOWN") -> dict:
    """
    MACD戦略のfast/slow/signal期間をグリッドサーチで最適化
    返り値: {"fast": int, "slow": int, "signal": int, "sharpe": float}
    """
    try:
        import pandas_ta as ta
        close = df["close"].copy()
        if len(close) < 50:
            return {"fast": 12, "slow": 26, "signal": 9, "sharpe": 0.0, "note": "データ不足"}

        # グリッド定義（小規模で軽量に）
        fast_range   = [8, 12, 16]
        slow_range   = [20, 26, 32]
        signal_range = [7, 9, 11]

        best = {"fast": 12, "slow": 26, "signal": 9, "sharpe": -999}

        for fast in fast_range:
            for slow in slow_range:
                if fast >= slow:
                    continue
                for signal in signal_range:
                    try:
                        _macd = ta.macd(close, fast=fast, slow=slow, signal=signal)
                        if _macd is None:
                            continue
                        macd_line   = _macd.get(f"MACD_{fast}_{slow}_{signal}", None)
                        macd_signal = _macd.get(f"MACDs_{fast}_{slow}_{signal}", None)
                        if macd_line is None or macd_signal is None:
                            continue

                        entries = (macd_line > macd_signal) & (macd_line.shift(1) <= macd_signal.shift(1))
                        exits   = (macd_line < macd_signal) & (macd_line.shift(1) >= macd_signal.shift(1))
                        entries = entries.fillna(False)
                        exits   = exits.fillna(False)

                        if entries.sum() < 2:
                            continue

                        pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="4h")
                        sharpe = float(pf.sharpe_ratio() or 0.0)
                        if not np.isfinite(sharpe):
                            sharpe = 0.0

                        if sharpe > best["sharpe"]:
                            best = {"fast": fast, "slow": slow, "signal": signal, "sharpe": round(sharpe, 3)}
                    except Exception:
                        continue

        logger.info(f"[{symbol}] MACD最適パラメータ: fast={best['fast']}, slow={best['slow']}, signal={best['signal']}, Sharpe={best['sharpe']}")
        return best

    except Exception as e:
        logger.error(f"[optimize_macd_params] {e}")
        return {"fast": 12, "slow": 26, "signal": 9, "sharpe": 0.0, "note": str(e)[:60]}


def optimize_rsi_params(df: pd.DataFrame, symbol: str = "UNKNOWN") -> dict:
    """
    VP固有モメンタム戦略のRSI entry/exit閾値を最適化
    返り値: {"rsi_entry_lo": int, "rsi_entry_hi": int, "rsi_exit": int, "sharpe": float}
    """
    try:
        import pandas_ta as ta
        close = df["close"].copy()
        if len(close) < 50:
            return {"rsi_entry_lo": 40, "rsi_entry_hi": 65, "rsi_exit": 72, "sharpe": 0.0, "note": "データ不足"}

        rsi = ta.rsi(close, length=14)
        if rsi is None:
            return {"rsi_entry_lo": 40, "rsi_entry_hi": 65, "rsi_exit": 72, "sharpe": 0.0, "note": "RSI計算失敗"}

        _macd = ta.macd(close, fast=12, slow=26, signal=9)
        macd_hist = _macd.get("MACDh_12_26_9", pd.Series(0, index=close.index)) if _macd is not None else pd.Series(0, index=close.index)

        # グリッド定義
        entry_lo_range = [30, 35, 40, 45]
        entry_hi_range = [60, 65, 70]
        exit_range     = [68, 72, 76]

        best = {"rsi_entry_lo": 40, "rsi_entry_hi": 65, "rsi_exit": 72, "sharpe": -999}

        for lo in entry_lo_range:
            for hi in entry_hi_range:
                if lo >= hi:
                    continue
                for ex in exit_range:
                    if ex <= hi:
                        continue
                    try:
                        entries = (rsi > lo) & (rsi < hi) & (macd_hist > 0) & (macd_hist.shift(1) <= 0)
                        exits   = (rsi > ex) | (macd_hist < 0)
                        entries = entries.fillna(False)
                        exits   = exits.fillna(False)

                        if entries.sum() < 2:
                            continue

                        pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="4h")
                        sharpe = float(pf.sharpe_ratio() or 0.0)
                        if not np.isfinite(sharpe):
                            sharpe = 0.0

                        if sharpe > best["sharpe"]:
                            best = {
                                "rsi_entry_lo": lo, "rsi_entry_hi": hi,
                                "rsi_exit": ex, "sharpe": round(sharpe, 3)
                            }
                    except Exception:
                        continue

        logger.info(f"[{symbol}] RSI最適パラメータ: lo={best['rsi_entry_lo']}, hi={best['rsi_entry_hi']}, exit={best['rsi_exit']}, Sharpe={best['sharpe']}")
        return best

    except Exception as e:
        logger.error(f"[optimize_rsi_params] {e}")
        return {"rsi_entry_lo": 40, "rsi_entry_hi": 65, "rsi_exit": 72, "sharpe": 0.0, "note": str(e)[:60]}


def run_param_optimization(df: pd.DataFrame, symbol: str = "UNKNOWN") -> dict:
    """
    全パラメータ最適化を実行して結果を返す
    TrinityCouncilから呼び出し可能
    """
    if len(df) < 50:
        return {"symbol": symbol, "status": "skip", "note": "データ不足（50件未満）"}

    logger.info(f"[{symbol}] パラメータ最適化開始 (データ{len(df)}件)")

    macd_params = optimize_macd_params(df, symbol)
    rsi_params  = optimize_rsi_params(df, symbol)

    result = {
        "symbol":      symbol,
        "data_points": len(df),
        "macd":        macd_params,
        "rsi":         rsi_params,
        "status":      "ok"
    }

    print(f"✅ [{symbol}] 最適化完了:")
    print(f"   MACD: fast={macd_params['fast']}, slow={macd_params['slow']}, signal={macd_params['signal']} → Sharpe={macd_params['sharpe']}")
    print(f"   RSI:  lo={rsi_params['rsi_entry_lo']}, hi={rsi_params['rsi_entry_hi']}, exit={rsi_params['rsi_exit']} → Sharpe={rsi_params['sharpe']}")

    return result


if __name__ == "__main__":
    # 単体テスト用
    import sys
    sys.path.insert(0, ".")
    from tools.market_data import MarketData
    symbol = "VIRTUAL/USDT"
    print(f"[TEST] {symbol} パラメータ最適化テスト")
    df = MarketData.fetch_ohlcv_custom(symbol, days=30)
    if df is not None and len(df) > 0:
        run_param_optimization(df, symbol)
    else:
        print("データ取得失敗")
