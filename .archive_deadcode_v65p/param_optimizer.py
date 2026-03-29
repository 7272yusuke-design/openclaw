"""
optuna ベイズ最適化パラメータ最適化モジュール（グリッドサーチから置き換え）
各戦略のハイパーパラメータをTPEサンプラーで効率的に最適化する
"""
import numpy as np
import pandas as pd
import vectorbt as vbt
import optuna
import logging

optuna.logging.set_verbosity(optuna.logging.WARNING)
logger = logging.getLogger("neo.param_optimizer")

def _manual_sharpe(close, entries, exits, fees=0.001):
    """vectorbt不使用の手動バックテスト + Sharpe計算"""
    import numpy as np
    import pandas as pd
    close   = pd.Series(close).reset_index(drop=True)
    entries = pd.Series(entries).reset_index(drop=True).fillna(False).astype(bool)
    exits   = pd.Series(exits).reset_index(drop=True).fillna(False).astype(bool)
    in_pos, entry_price, returns = False, 0.0, []
    for i in range(len(close)):
        if not in_pos and entries.iloc[i]:
            entry_price = close.iloc[i] * (1 + fees)
            in_pos = True
        elif in_pos and exits.iloc[i]:
            ret = (close.iloc[i] * (1 - fees) - entry_price) / entry_price
            returns.append(ret)
            in_pos = False
    if len(returns) < 2:
        return 0.0, len(returns)
    r = np.array(returns)
    sharpe = (r.mean() / (r.std() + 1e-9)) * np.sqrt(252)
    return round(float(sharpe) if np.isfinite(sharpe) else 0.0, 3), len(returns)



def optimize_macd_params(df: pd.DataFrame, symbol: str = "UNKNOWN", n_trials: int = 30) -> dict:
    """
    optunaでMACD戦略のfast/slow/signal期間を最適化
    グリッドサーチ(27通り)からTPEベイズ最適化(30試行)に変更
    → 同じ時間でより良いパラメータを発見できる
    """
    try:
        import pandas_ta as ta
        close = df["close"].copy()
        if len(close) < 50:
            return {"fast": 12, "slow": 26, "signal": 9, "sharpe": 0.0, "note": "データ不足"}

        def objective(trial):
            fast   = trial.suggest_int("fast", 6, 20)
            slow   = trial.suggest_int("slow", 20, 40)
            signal = trial.suggest_int("signal", 5, 15)
            if fast >= slow:
                return -999.0
            try:
                _macd = ta.macd(close, fast=fast, slow=slow, signal=signal)
                if _macd is None:
                    return -999.0
                # カラム名は動的に取得
                cols = _macd.columns.tolist()
                macd_col   = [c for c in cols if c.startswith("MACD_") and "MACDs" not in c and "MACDh" not in c]
                signal_col = [c for c in cols if c.startswith("MACDs_")]
                if not macd_col or not signal_col:
                    return -999.0
                macd_line   = _macd[macd_col[0]]
                macd_signal = _macd[signal_col[0]]
                entries = (macd_line > macd_signal) & (macd_line.shift(1) <= macd_signal.shift(1))
                exits   = (macd_line < macd_signal) & (macd_line.shift(1) >= macd_signal.shift(1))
                entries = entries.fillna(False)
                exits   = exits.fillna(False)
                if entries.sum() < 2:
                    return -999.0
                sharpe, n_trades = _manual_sharpe(close, entries, exits)
                return sharpe if np.isfinite(sharpe) else -999.0
            except Exception:
                return -999.0

        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        best = study.best_params
        best_sharpe = round(study.best_value, 3) if np.isfinite(study.best_value) else 0.0
        result = {
            "fast": best["fast"], "slow": best["slow"],
            "signal": best["signal"], "sharpe": best_sharpe,
            "n_trials": n_trials
        }
        logger.info(f"[{symbol}] MACD最適: fast={result['fast']}, slow={result['slow']}, signal={result['signal']}, Sharpe={result['sharpe']}")
        return result

    except Exception as e:
        logger.error(f"[optimize_macd_params] {e}")
        return {"fast": 12, "slow": 26, "signal": 9, "sharpe": 0.0, "note": str(e)[:60]}


def optimize_rsi_params(df: pd.DataFrame, symbol: str = "UNKNOWN", n_trials: int = 30) -> dict:
    """
    optunaでVP固有モメンタム戦略のRSI閾値を最適化
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

        def objective(trial):
            lo = trial.suggest_int("rsi_entry_lo", 25, 50)
            hi = trial.suggest_int("rsi_entry_hi", 55, 75)
            ex = trial.suggest_int("rsi_exit",     65, 85)
            if lo >= hi or ex <= hi:
                return -999.0
            try:
                entries = (rsi > lo) & (rsi < hi) & (macd_hist > 0) & (macd_hist.shift(1) <= 0)
                exits   = (rsi > ex) | (macd_hist < 0)
                entries = entries.fillna(False)
                exits   = exits.fillna(False)
                if entries.sum() < 2:
                    return -999.0
                sharpe, n_trades = _manual_sharpe(close, entries, exits)
                return sharpe if np.isfinite(sharpe) else -999.0
            except Exception:
                return -999.0

        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        best = study.best_params
        best_sharpe = round(study.best_value, 3) if np.isfinite(study.best_value) else 0.0
        result = {
            "rsi_entry_lo": best["rsi_entry_lo"],
            "rsi_entry_hi": best["rsi_entry_hi"],
            "rsi_exit":     best["rsi_exit"],
            "sharpe":       best_sharpe,
            "n_trials":     n_trials
        }
        logger.info(f"[{symbol}] RSI最適: lo={result['rsi_entry_lo']}, hi={result['rsi_entry_hi']}, exit={result['rsi_exit']}, Sharpe={result['sharpe']}")
        return result

    except Exception as e:
        logger.error(f"[optimize_rsi_params] {e}")
        return {"rsi_entry_lo": 40, "rsi_entry_hi": 65, "rsi_exit": 72, "sharpe": 0.0, "note": str(e)[:60]}


def run_param_optimization(df: pd.DataFrame, symbol: str = "UNKNOWN", n_trials: int = 30) -> dict:
    """
    全パラメータ最適化を実行して結果を返す（optuna TPEサンプラー使用）
    """
    if len(df) < 50:
        return {"symbol": symbol, "status": "skip", "note": "データ不足（50件未満）"}

    logger.info(f"[{symbol}] optuna最適化開始 (データ{len(df)}件, {n_trials}試行)")

    macd_params = optimize_macd_params(df, symbol, n_trials)
    rsi_params  = optimize_rsi_params(df, symbol, n_trials)

    result = {
        "symbol":      symbol,
        "data_points": len(df),
        "macd":        macd_params,
        "rsi":         rsi_params,
        "status":      "ok",
        "optimizer":   "optuna-TPE"
    }

    print(f"✅ [{symbol}] optuna最適化完了:")
    print(f"   MACD: fast={macd_params['fast']}, slow={macd_params['slow']}, signal={macd_params['signal']} → Sharpe={macd_params['sharpe']}")
    print(f"   RSI:  lo={rsi_params['rsi_entry_lo']}, hi={rsi_params['rsi_entry_hi']}, exit={rsi_params['rsi_exit']} → Sharpe={rsi_params['sharpe']}")

    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from tools.market_data import MarketData
    symbol = "VIRTUAL/USDT"
    print(f"[TEST] {symbol} optuna最適化テスト")
    df = MarketData.fetch_ohlcv_custom(symbol, days=30)
    if df is not None and len(df) > 0:
        print(f"データ取得: {len(df)}件")
        run_param_optimization(df, symbol, n_trials=30)
    else:
        print("データ取得失敗")
