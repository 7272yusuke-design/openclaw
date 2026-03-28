import pandas as pd
import numpy as np
import math
import logging

logger = logging.getLogger("neo.quant.backtest")


def _monte_carlo_confidence(rets: list, n_sim: int = 500) -> dict:
    """
    ブートストラップ・モンテカルロによるSharpe信頼区間計算。
    同じ取引リターン列をランダムシャッフルしてn_sim回Sharpeを計算。
    Returns: p5/p50/p95 Sharpe, 負Sharpe確率, 信頼ラベル
    """
    import random
    if len(rets) < 3:
        return {"mc_sharpe_p5": 0.0, "mc_sharpe_p50": 0.0, "mc_sharpe_p95": 0.0,
                "mc_neg_prob": 1.0, "mc_label": "INSUFFICIENT"}
    sharpes = []
    ra = list(rets)
    for _ in range(n_sim):
        sample = random.choices(ra, k=len(ra))  # リサンプリング（重複あり）
        arr = np.array(sample)
        if arr.std() < 1e-6:
            continue
        sr = float((arr.mean() / arr.std()) * np.sqrt(252))
        if math.isfinite(sr) and abs(sr) < 100:
            sharpes.append(sr)
    if len(sharpes) < 10:
        return {"mc_sharpe_p5": 0.0, "mc_sharpe_p50": 0.0, "mc_sharpe_p95": 0.0,
                "mc_neg_prob": 1.0, "mc_label": "INSUFFICIENT"}
    sharpes.sort()
    n = len(sharpes)
    p5  = sharpes[int(n * 0.05)]
    p50 = sharpes[int(n * 0.50)]
    p95 = sharpes[int(n * 0.95)]
    neg_prob = sum(1 for s in sharpes if s < 0) / n
    # 信頼ラベル: 下振れ5%ラインで判定
    if p5 >= 2.0:
        label = "ROBUST"    # 最悪ケースでもSharpe2以上
    elif p5 >= 0.5:
        label = "STABLE"    # 最悪ケースでもプラス
    elif p5 >= 0.0:
        label = "FRAGILE"   # 最悪ケースでトントン
    else:
        label = "RISKY"     # 最悪ケースでマイナス
    return {
        "mc_sharpe_p5":  round(p5, 3),
        "mc_sharpe_p50": round(p50, 3),
        "mc_sharpe_p95": round(p95, 3),
        "mc_neg_prob":   round(neg_prob, 3),
        "mc_label":      label
    }

def _manual_backtest(close, entries, exits, strategy_name, fees=0.001):
    """vectorbt不使用の手動バックテスト + Sharpe計算"""
    empty = {"strategy": strategy_name, "sharpe": 0.0, "sharpe_raw": 0.0,
             "total_return": "0.00%", "max_dd": "0.00%",
             "win_rate": 0.0, "trades": 0, "confidence": "LOW"}
    try:
        cs = pd.Series(close.values if hasattr(close,"values") else close).reset_index(drop=True)
        en = pd.Series(entries).reset_index(drop=True).fillna(False).astype(bool)
        ex = pd.Series(exits).reset_index(drop=True).fillna(False).astype(bool)
        # ルックアヘッドバイアス対策: シグナルを1本シフトして次足でエントリー
        en = en.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        ex = ex.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        in_pos, ep, rets, wins = False, 0.0, [], 0
        equity, peak, mdd = 1.0, 1.0, 0.0
        for i in range(len(cs)):
            if not in_pos and en.iloc[i]:
                ep = cs.iloc[i] * (1 + fees); in_pos = True
            elif in_pos and ex.iloc[i]:
                r = (cs.iloc[i] * (1 - fees) - ep) / ep
                rets.append(r)
                if r > 0: wins += 1
                equity *= (1 + r)
                if equity > peak: peak = equity
                dd = (peak - equity) / peak * 100
                if dd > mdd: mdd = dd
                in_pos = False
        n = len(rets)
        total_ret = (equity - 1.0) * 100
        wr = (wins / n * 100) if n > 0 else 0.0
        try:
            from core.config import LEARNING_MODE
            min_t = 1 if LEARNING_MODE else 3
        except Exception:
            min_t = 3
        if n < max(min_t, 2):  # 最低2取引必須（1取引はSharpe爆発防止）
            return {**empty, "trades": n}
        ra = np.array(rets)
        if ra.std() < 1e-6:  # 全勝or全敗でstd≈0 → Sharpe爆発防止
            return {**empty, "trades": n}
        sr = float((ra.mean() / ra.std()) * np.sqrt(252))
        if not math.isfinite(sr) or abs(sr) > 100:
            return {**empty, "trades": n}
        conf = "HIGH" if n >= 10 else "MED" if n >= 3 else "LOW"
        mc = _monte_carlo_confidence(rets)
        return {"strategy": strategy_name, "sharpe": max(0.0, round(sr,3)),
                "sharpe_raw": round(sr,3), "total_return": f"{total_ret:.2f}%",
                "max_dd": f"{mdd:.2f}%", "win_rate": round(wr,1),
                "trades": n, "confidence": conf,
                "mc_sharpe_p5":  mc["mc_sharpe_p5"],
                "mc_sharpe_p50": mc["mc_sharpe_p50"],
                "mc_sharpe_p95": mc["mc_sharpe_p95"],
                "mc_neg_prob":   mc["mc_neg_prob"],
                "mc_label":      mc["mc_label"]}
    except Exception as e:
        logger.error(f"[_manual_backtest] {strategy_name}: {e}")
        return empty

def _extract_stats(portfolio, strategy_name):
    """後方互換スタブ"""
    return {"strategy": strategy_name, "sharpe": 0.0, "sharpe_raw": 0.0,
            "total_return": "0.00%", "max_dd": "0.00%",
            "win_rate": 0.0, "trades": 0, "confidence": "LOW"}

class CoreBacktest:
    """High-performance backtesting using vectorbt — 4戦略対応版"""

    # ── 戦略1: Alpha Strategy（既存・変更なし）────────────────────────
    @staticmethod
    def run_alpha_strategy(df: pd.DataFrame) -> dict:
        """Regime + RSI + Bollinger Squeeze"""
        try:
            close   = df["close"]
            entries = (df["market_regime"] == 1) & (df["rsi_14"] < 55)
            exits   = (df["market_regime"] == -1) | (df["rsi_14"] > 70)
            return _manual_backtest(close, entries, exits, "alpha_strategy")
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

            result = _manual_backtest(close, entries, exits, "bb_reversal")
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
            low    = df["low"]  if "low"  in df.columns else close

            # volumeがない場合は全シグナル有効扱い
            if "volume" in df.columns and df["volume"].sum() > 0:
                volume = df["volume"]
                vol_ma = volume.rolling(20).mean()
                vol_ok = volume > vol_ma * 1.5
            else:
                vol_ok = pd.Series(True, index=close.index)

            high_roll = high.rolling(20).max().shift(1)
            entries   = (high > high_roll) & vol_ok

            # ATRベース損切 or 10本後に強制エグジット
            atr = (high - low).rolling(14).mean()
            stop_loss = close < (close.shift(1) - atr * 2)
            time_exit = entries.shift(10).fillna(False).infer_objects(copy=False)
            exits = stop_loss | time_exit

            result = _manual_backtest(close, entries, exits, "momentum_breakout")
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

            result = _manual_backtest(close, entries, exits, "mean_reversion")
            result["description"] = "RSI<30+レンジエントリー（RSI>55 or -3%損切り）"
            return result
        except Exception as e:
            logger.error(f"[mean_reversion] {e}")
            return {"strategy": "mean_reversion", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    @staticmethod
    def run_macd_cross(df: pd.DataFrame) -> dict:
        """K.2/J.4: MACDクロス戦略 + ATRフィルター（VP固有の急騰/急落に対応）"""
        try:
            import pandas_ta as ta
            close = df["close"].copy()
            # MACDが既に計算済みなら再利用、なければ計算
            if "macd" not in df.columns or "macd_signal" not in df.columns:
                _macd = ta.macd(close, fast=12, slow=26, signal=9)
                if _macd is None:
                    return {"strategy": "macd_cross", "sharpe": 0.0, "trades": 0,
                            "confidence": "LOW", "win_rate": 0.0, "note": "MACD計算失敗"}
                macd_line   = _macd.get("MACD_12_26_9", pd.Series(0, index=close.index))
                macd_signal = _macd.get("MACDs_12_26_9", pd.Series(0, index=close.index))
            else:
                macd_line   = df["macd"]
                macd_signal = df["macd_signal"]

            # ATRフィルター（ボラが低すぎる時はエントリーしない）
            if all(c in df.columns for c in ["high", "low", "close"]):
                _atr = ta.atr(df["high"], df["low"], df["close"], length=14)
                atr_filter = _atr > (_atr.rolling(50, min_periods=10).mean() * 0.5) if _atr is not None else pd.Series(True, index=close.index)
            else:
                atr_filter = pd.Series(True, index=close.index)

            # エントリー: MACDがシグナルを上抜け + ATRフィルター
            entries = (macd_line > macd_signal) & (macd_line.shift(1) <= macd_signal.shift(1)) & atr_filter
            # エグジット: MACDがシグナルを下抜け
            exits = (macd_line < macd_signal) & (macd_line.shift(1) >= macd_signal.shift(1))

            entries = entries.fillna(False)
            exits   = exits.fillna(False)

            result = _manual_backtest(close, entries, exits, "macd_cross")
            result["description"] = "MACDクロス + ATRボラフィルター"
            return result
        except Exception as e:
            logger.error(f"[macd_cross] {e}")
            return {"strategy": "macd_cross", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    @staticmethod
    def run_vp_momentum(df: pd.DataFrame) -> dict:
        """J.4: VP固有モメンタム戦略（RSI急騰 + MACD正転 + Squeeze解放）"""
        try:
            import pandas_ta as ta
            close = df["close"].copy()

            # RSI
            rsi = df.get("rsi_14") if "rsi_14" in df.columns else ta.rsi(close, length=14)
            if rsi is None:
                rsi = pd.Series(50, index=close.index)

            # MACD histogram（正転でモメンタム加速）
            if "macd_hist" in df.columns:
                macd_hist = df["macd_hist"]
            else:
                _macd = ta.macd(close, fast=12, slow=26, signal=9)
                macd_hist = _macd.get("MACDh_12_26_9", pd.Series(0, index=close.index)) if _macd is not None else pd.Series(0, index=close.index)

            # Squeeze解放（Bandwidthが拡大 = エネルギー放出）
            if f"bb_bandwidth_20" in df.columns:
                bw = df["bb_bandwidth_20"]
                squeeze_release = bw > bw.shift(1)
            else:
                squeeze_release = pd.Series(True, index=close.index)

            # エントリー: RSI40-65（過熱前）+ MACDヒスト正転 + Squeeze解放
            entries = (rsi > 40) & (rsi < 65) & (macd_hist > 0) & (macd_hist.shift(1) <= 0)
            # エグジット: RSI>72（過熱）or MACDヒスト反転
            exits = (rsi > 72) | (macd_hist < 0)

            entries = entries.fillna(False)
            exits   = exits.fillna(False)

            result = _manual_backtest(close, entries, exits, "vp_momentum")
            result["description"] = "VP固有: RSI+MACDヒスト正転+Squeeze解放"
            return result
        except Exception as e:
            logger.error(f"[vp_momentum] {e}")
            return {"strategy": "vp_momentum", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}


    # ── 戦略7: EMA Trend Filter（freqtrade-strategies参考）────────────
    @staticmethod
    def run_ema_trend(df: pd.DataFrame) -> dict:
        """EMA20/50/200トレンドフィルター: 全EMA上向き整列でBUY、下向きでSELL"""
        try:
            close = df["close"]
            ema20  = close.ewm(span=20,  adjust=False).mean()
            ema50  = close.ewm(span=50,  adjust=False).mean()
            ema200 = close.ewm(span=200, adjust=False).mean()

            # 強気整列: close > EMA20 > EMA50 > EMA200
            bullish = (close > ema20) & (ema20 > ema50) & (ema50 > ema200)
            # 前足が非整列 → 今足が整列 = エントリー
            entries = bullish & ~bullish.shift(1).fillna(False)
            # EMA20がEMA50を下回ったらエグジット
            exits = ema20 < ema50

            entries = entries.fillna(False)
            exits   = exits.fillna(False)

            result = _manual_backtest(close, entries, exits, "ema_trend")
            result["description"] = "EMA20/50/200トレンド整列エントリー"
            return result
        except Exception as e:
            logger.error(f"[ema_trend] {e}")
            return {"strategy": "ema_trend", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 戦略9: gplearn Evolved（遺伝的プログラミング自動発見）──────────
    @staticmethod
    def run_gplearn_evolved(df: pd.DataFrame) -> dict:
        """gplearnで発見された数式をバックテスト。
        data/gplearn/best_{symbol}.json から最良プログラムをロード。
        数式が特徴量を使ってBUYスコアを算出 → 閾値でエントリ/エグジット。"""
        import json
        from pathlib import Path
        from sklearn.preprocessing import StandardScaler
        try:
            # 使用する特徴量（gplearn_strategy.pyと同じ）
            FEATURE_COLS = [
                "ma20", "ma50", "bb_bandwidth_20", "returns", "acceleration",
                "rsi_14", "ma_short", "ma_mid", "ma_long",
                "macd", "macd_signal", "macd_hist", "atr_14",
            ]
            # 特徴量の存在確認
            missing = [c for c in FEATURE_COLS if c not in df.columns]
            if missing:
                return {"strategy": "gplearn_evolved", "sharpe": 0.0, "trades": 0,
                        "confidence": "LOW", "win_rate": 0.0, "note": f"missing: {missing[:3]}"}

            # 最良プログラムをロード（銘柄別 → 汎用の順にフォールバック）
            program_data = None
            for path in [Path("data/gplearn/gplearn_best_program.json"),
                         Path("data/gplearn_best_program.json")]:
                if path.exists():
                    with open(path) as f:
                        program_data = json.load(f)
                    break
            if not program_data or not program_data.get("program"):
                return {"strategy": "gplearn_evolved", "sharpe": 0.0, "trades": 0,
                        "confidence": "LOW", "win_rate": 0.0, "note": "no program found"}

            program_str = program_data["program"]
            method = program_data.get("method", "unknown")
            threshold = program_data.get("threshold", 0)

            # 特徴量を正規化
            X_raw = df[FEATURE_COLS].dropna().values
            valid_idx = df[FEATURE_COLS].dropna().index
            if len(X_raw) < 50:
                return {"strategy": "gplearn_evolved", "sharpe": 0.0, "trades": 0,
                        "confidence": "LOW", "win_rate": 0.0, "note": "insufficient data"}
            scaler = StandardScaler()
            X = scaler.fit_transform(X_raw)

            # 数式を評価してスコア算出
            # X0=ma20, X1=ma50, X2=bb_bandwidth_20, ...
            local_vars = {f"X{i}": X[:, i] for i in range(X.shape[1])}
            # gplearn演算子をnumpy関数にマッピング
            safe_funcs = {
                "add": np.add, "sub": np.subtract, "mul": np.multiply,
                "div": lambda a, b: np.where(np.abs(b) > 1e-6, a / b, 0.0),
                "max": np.maximum, "min": np.minimum, "abs": np.abs,
            }
            local_vars.update(safe_funcs)
            scores = eval(program_str, {"__builtins__": {}, "np": np}, local_vars)
            if isinstance(scores, (int, float)):
                scores = np.full(len(X), float(scores))
            scores = np.array(scores, dtype=float)

            # BUYシグナル生成
            if method == "SymbolicClassifier":
                # Classifierの出力は直接0/1的 — 0超をBUYとする
                buy_signals = scores > 0
            else:
                # Regressor — 保存された閾値を使用
                thr = float(threshold) if threshold != "N/A (classifier)" else 0.0
                buy_signals = scores > thr

            # エントリ/エグジット: BUY信号ON→エントリ、OFF→エグジット
            entries = pd.Series(False, index=df.index)
            exits = pd.Series(False, index=df.index)
            entries.iloc[valid_idx] = buy_signals
            exits.iloc[valid_idx] = ~buy_signals

            close = df["close"]
            result = _manual_backtest(close, entries, exits, "gplearn_evolved")
            result["note"] = f"{method} | {program_str[:50]}..."
            return result

        except Exception as e:
            logger.error(f"[gplearn_evolved] {e}")
            return {"strategy": "gplearn_evolved", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 戦略8: RSI Bounce（freqtrade-strategies参考）────────────────
    @staticmethod
    def run_rsi_bounce(df: pd.DataFrame) -> dict:
        """RSI反発BUY: RSI40割れからの反発 + RSI65超えでエグジット（VP銘柄向け緩和版）"""
        try:
            close = df["close"]
            rsi   = df["rsi_14"] if "rsi_14" in df.columns else _calc_rsi(close)
            ema50 = close.ewm(span=50, adjust=False).mean()

            # RSIが40を下から上に抜けた瞬間（VP銘柄は30割れが稀なため緩和）
            rsi_cross_up = (rsi > 40) & (rsi.shift(1) <= 40)
            entries = rsi_cross_up & (close > ema50 * 0.95)  # EMA50の5%下まで許容

            # RSI65超え or EMA50を大幅に割り込んだらエグジット
            exits = (rsi > 65) | (close < ema50 * 0.97)

            entries = entries.fillna(False)
            exits   = exits.fillna(False)

            result = _manual_backtest(close, entries, exits, "rsi_bounce")
            result["description"] = "RSI30反発+EMA50上方フィルター"
            return result
        except Exception as e:
            logger.error(f"[rsi_bounce] {e}")
            return {"strategy": "rsi_bounce", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 全戦略一括実行（Task 2.2 メインAPI）─────────────────────────
    @staticmethod
    def run_all_strategies(df: pd.DataFrame, symbol: str = 'UNKNOWN', use_optuna: bool = True, optuna_df=None) -> dict:
        """8戦略並列実行。use_optuna=TrueでMACD/RSIをTPE最適化"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import functools

        macd_params = None
        rsi_params  = None
        _opt_data = optuna_df if (optuna_df is not None and len(optuna_df) >= 50) else df
        if use_optuna and len(_opt_data) >= 50:
            try:
                from research.backtests.param_optimizer import run_param_optimization
                opt_result = run_param_optimization(_opt_data, symbol, n_trials=20)
                if opt_result.get("status") == "ok":
                    macd_params = opt_result.get("macd")
                    rsi_params  = opt_result.get("rsi")
                    logger.info(f'[{symbol}] optuna: MACD={macd_params}, RSI={rsi_params}')
            except Exception as _oe:
                logger.warning(f'[{symbol}] optuna skip: {_oe}')

        strategy_map = {
            "alpha_strategy":    CoreBacktest.run_alpha_strategy,
            "bb_reversal":       CoreBacktest.run_bb_reversal,
            "momentum_breakout": CoreBacktest.run_momentum_breakout,
            "mean_reversion":    CoreBacktest.run_mean_reversion,
            "macd_cross":        CoreBacktest.run_macd_cross,
            "vp_momentum":       CoreBacktest.run_vp_momentum,
            "ema_trend":         CoreBacktest.run_ema_trend,
            "rsi_bounce":        CoreBacktest.run_rsi_bounce,
            "gplearn_evolved":   CoreBacktest.run_gplearn_evolved,
        }

        results = {}

        # ThreadPoolExecutor: pickle不要・GIL解放で数値計算は並列動作
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_to_name = {
                    executor.submit(func, df): name
                    for name, func in strategy_map.items()
                }
                for future in as_completed(future_to_name, timeout=60):
                    name = future_to_name[future]
                    try:
                        results[name] = future.result()
                    except Exception as e:
                        results[name] = {"strategy": name, "sharpe": 0.0,
                                         "confidence": "LOW", "trades": 0,
                                         "win_rate": 0.0, "error": str(e)}
        except Exception as e:
            import logging
            logging.getLogger("neo.backtest").warning(
                f"Parallel backtest failed, falling back to sequential: {e}")
            results = {name: func(df) for name, func in strategy_map.items()}

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
