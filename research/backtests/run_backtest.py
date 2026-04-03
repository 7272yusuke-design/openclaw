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

    # ═══════════════════════════════════════════════════════════
    # 短期戦略（Short-term: 14-50本 = 2-8日保有目安）
    # ═══════════════════════════════════════════════════════════

    # ── 短期戦略1: MACD Cross（MACDクロス+ATRフィルター）──────
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

    # ── 短期戦略2: Mean Reversion（RSI30+レンジエントリー）────
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

    # ── 短期戦略3: gplearn Evolved（遺伝的プログラミング自動発見）──
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


    # ═══════════════════════════════════════════════════════════
    # 中期戦略（Mid-term: 50-100本 = 8-17日保有目安）
    # ═══════════════════════════════════════════════════════════

    # ── 中期戦略1: Triple MA Cross（EMA20/50クロス+EMA100方向フィルター）──
    @staticmethod
    def run_triple_ma_cross(df: pd.DataFrame) -> dict:
        """Triple MA Cross: EMA20/50ゴールデンクロス + EMA100が方向フィルター"""
        try:
            close = df["close"]
            ema20 = close.ewm(span=20, adjust=False).mean()
            ema50 = close.ewm(span=50, adjust=False).mean()
            ema100 = close.ewm(span=100, adjust=False).mean()

            # エントリー: EMA20がEMA50を上抜け + EMA100が下向きでない（横ばい以上）
            cross_up = (ema20 > ema50) & (ema20.shift(1) <= ema50.shift(1))
            ema100_ok = ema100 >= ema100.shift(5)  # 5本前と比較して下がっていない
            entries = cross_up & ema100_ok

            # エグジット: EMA20がEMA50を下抜け
            exits = (ema20 < ema50) & (ema20.shift(1) >= ema50.shift(1))

            result = _manual_backtest(close, entries, exits, "triple_ma_cross")
            result["description"] = "EMA20/50クロス+EMA100方向フィルター（中期トレンド追従）"
            result["timeframe"] = "mid"
            return result
        except Exception as e:
            logger.error(f"[triple_ma_cross] {e}")
            return {"strategy": "triple_ma_cross", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 中期戦略2: Ichimoku Cloud（一目均衡表・雲抜け+転換/基準線クロス）──
    @staticmethod
    def run_ichimoku_cloud(df: pd.DataFrame) -> dict:
        """Ichimoku Cloud: 雲抜け+転換線/基準線クロス（暗号通貨で特に有効）"""
        try:
            close = df["close"]
            high = df["high"]
            low = df["low"]

            # 一目均衡表の各線
            tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2      # 転換線
            kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2     # 基準線
            span_a = ((tenkan + kijun) / 2).shift(26)                        # 先行スパンA
            span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)  # 先行スパンB
            cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
            cloud_bottom = pd.concat([span_a, span_b], axis=1).min(axis=1)

            # エントリー: 終値が雲の上 + 転換線が基準線を上抜け
            above_cloud = close > cloud_top
            tk_cross = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
            entries = above_cloud & tk_cross

            # エグジット: 終値が雲の中に入る or 転換線が基準線を下抜け
            exits = (close < cloud_bottom) | ((tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1)))

            result = _manual_backtest(close, entries, exits, "ichimoku_cloud")
            result["description"] = "一目均衡表・雲抜け+TK Cross（中期トレンド確認）"
            result["timeframe"] = "mid"
            return result
        except Exception as e:
            logger.error(f"[ichimoku_cloud] {e}")
            return {"strategy": "ichimoku_cloud", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 中期戦略3: ATR Breakout（50本レンジブレイク+ATR拡大確認）──────
    @staticmethod
    def run_atr_breakout(df: pd.DataFrame) -> dict:
        """ATR Breakout: 50本レンジ上限ブレイク+ATR拡大でモメンタム確認"""
        try:
            close = df["close"]
            high = df["high"]
            low = df["low"]

            range_high = close.rolling(50).max().shift(1)
            atr = (high - low).rolling(14).mean()
            atr_avg = atr.rolling(50).mean()

            # エントリー: 50本高値を上抜け + ATRが平均の1.5倍以上（モメンタム確認）
            entries = (close > range_high) & (atr > atr_avg * 1.5)

            # エグジット: ATR2倍分の損切り or 30本経過
            stop = close < (close.shift(1) - atr * 2)
            time_exit = entries.shift(30).fillna(False).infer_objects(copy=False)
            exits = stop | time_exit

            result = _manual_backtest(close, entries, exits, "atr_breakout")
            result["description"] = "50本レンジブレイク+ATR拡大確認（中期ブレイクアウト）"
            result["timeframe"] = "mid"
            return result
        except Exception as e:
            logger.error(f"[atr_breakout] {e}")
            return {"strategy": "atr_breakout", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ═══════════════════════════════════════════════════════════
    # 長期戦略（Long-term: 100-300本 = 17-50日保有目安）
    # ═══════════════════════════════════════════════════════════

    # ── 長期戦略1: Macro Value（底値圏+安定化=仕込み機会）────────────
    @staticmethod
    def run_macro_value(df: pd.DataFrame) -> dict:
        """Macro Value: close < SMA200 & close > SMA50 = 底値圏で安定化中"""
        try:
            close = df["close"]
            sma50 = close.rolling(50).mean()
            sma200 = close.rolling(200).mean()

            # エントリー: 長期MA以下（割安）だが中期MA以上（安定化中）
            entries = (close < sma200) & (close > sma50) & (close.shift(1) <= sma50.shift(1))

            # エグジット: SMA200まで回復（適正価格到達）or SMA50割れ（安定崩壊）
            exits = (close > sma200) | (close < sma50 * 0.97)

            result = _manual_backtest(close, entries, exits, "macro_value")
            result["description"] = "SMA200以下+SMA50以上（底値圏の仕込み機会）"
            result["timeframe"] = "long"
            return result
        except Exception as e:
            logger.error(f"[macro_value] {e}")
            return {"strategy": "macro_value", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 長期戦略2: Golden Cross（SMA50/200ゴールデンクロス）──────────
    @staticmethod
    def run_golden_cross(df: pd.DataFrame) -> dict:
        """Golden Cross: SMA50がSMA200を上抜け = 大局トレンド転換"""
        try:
            close = df["close"]
            sma50 = close.rolling(50).mean()
            sma200 = close.rolling(200).mean()

            # エントリー: SMA50がSMA200を上抜け（ゴールデンクロス）
            entries = (sma50 > sma200) & (sma50.shift(1) <= sma200.shift(1))

            # エグジット: SMA50がSMA200を下抜け（デスクロス）
            exits = (sma50 < sma200) & (sma50.shift(1) >= sma200.shift(1))

            result = _manual_backtest(close, entries, exits, "golden_cross")
            result["description"] = "SMA50/200ゴールデンクロス（大局トレンド転換）"
            result["timeframe"] = "long"
            return result
        except Exception as e:
            logger.error(f"[golden_cross] {e}")
            return {"strategy": "golden_cross", "sharpe": 0.0, "trades": 0,
                    "confidence": "LOW", "win_rate": 0.0, "note": str(e)[:60]}

    # ── 長期戦略3: DCA Accumulation（大底圏での積み立てエントリー）───
    @staticmethod
    def run_dca_accumulation(df: pd.DataFrame) -> dict:
        """DCA Accumulation: 200本最安値圏+RSI<35 = 大底での仕込み"""
        try:
            close = df["close"]
            rsi = _calc_rsi(close, 14)
            sma100 = close.rolling(100).mean()

            low_200 = close.rolling(200).min()
            # エントリー: 200本最安値から10%以内 + RSI35以下
            near_bottom = close <= low_200 * 1.10
            entries = near_bottom & (rsi < 35)

            # エグジット: SMA100回復 or RSI65超え
            exits = (close > sma100) | (rsi > 65)

            result = _manual_backtest(close, entries, exits, "dca_accumulation")
            result["description"] = "200本最安値圏+RSI<35（大底での仕込み）"
            result["timeframe"] = "long"
            return result
        except Exception as e:
            logger.error(f"[dca_accumulation] {e}")
            return {"strategy": "dca_accumulation", "sharpe": 0.0, "trades": 0,
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
            # 短期3
            "macd_cross":        CoreBacktest.run_macd_cross,
            "mean_reversion":    CoreBacktest.run_mean_reversion,
            "gplearn_evolved":   CoreBacktest.run_gplearn_evolved,
            # 中期3
            "triple_ma_cross":   CoreBacktest.run_triple_ma_cross,
            "ichimoku_cloud":    CoreBacktest.run_ichimoku_cloud,
            "atr_breakout":      CoreBacktest.run_atr_breakout,
            # 長期3
            "macro_value":       CoreBacktest.run_macro_value,
            "golden_cross":      CoreBacktest.run_golden_cross,
            "dca_accumulation":  CoreBacktest.run_dca_accumulation,
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
