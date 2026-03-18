"""
BacktestAgent v3 — 4戦略並列実行 + 最良Sharpe選択
Task 2.2: BB Reversal / Momentum Breakout / Mean Reversion 追加
"""
import logging

logger = logging.getLogger("neo.backtest_agent")


class BacktestAgent:
    def __init__(self):
        self.name = "BacktestSpecialist_v3"

    def run(self, strategy_idea: str = "", target_symbol: str = "VIRTUAL",
            initial_cash: float = 1000.0, logic: str = "all") -> dict:
        """
        4戦略を並列実行し、最良Sharpeの結果を返す。
        Returns dict: sharpe, total_return, max_dd, win_rate,
                      total_trades, confidence, best_strategy, raw_report
        """
        print(f"🚀 [BacktestAgent v3] {target_symbol} — 4戦略並列バックテスト開始...")

        result = {
            "symbol":        target_symbol,
            "sharpe":        0.0,
            "total_return":  "0.00%",
            "max_dd":        "0.00%",
            "win_rate":      "0.00%",
            "total_trades":  0,
            "confidence":    "NONE",
            "best_strategy": "none",
            "logic":         logic,
            "initial_cash":  initial_cash,
            "raw_report":    "",
            "status":        "unknown"
        }

        try:
            import sys
            sys.path.insert(0, '.')
            from tools.market_data import MarketData
            from feature_engineering.build_features import FeatureBuilder
            from research.backtests.run_backtest import CoreBacktest

            clean_symbol = target_symbol.split('/')[0].strip()

            # 1. GeckoTerminal4時間足優先（high/low/closeが独立した実データ）
            df_4h = None
            try:
                df_4h = MarketData.fetch_ohlcv_geckoterminal(clean_symbol, days=30)
            except Exception:
                pass
            if df_4h is not None and len(df_4h) >= 50:
                df = df_4h
                print(f'  📊 GeckoTerminal 4h足: {len(df)}本')
            else:
                df = MarketData.fetch_ohlcv_custom(clean_symbol)
                print(f'  📊 フォールバック: {len(df) if df is not None else 0}本')
            if df is None or df.empty or len(df) < 20:
                result["status"]     = "insufficient_data"
                result["raw_report"] = f"⚠️ {target_symbol}: データ不足（{len(df) if df is not None else 0}本）"
                return result

            # 2. 特徴量ビルド
            feat = FeatureBuilder.build_from_memory(df)
            if feat is None or feat.empty or len(feat) < 10:
                result["status"]     = "feature_build_failed"
                result["raw_report"] = f"⚠️ {target_symbol}: 特徴量ビルド失敗（{len(feat) if feat is not None else 0}行）"
                return result

            # 3. 6戦略一括実行（optuna最適化パラメータ使用）
            all_result = CoreBacktest.run_all_strategies(feat, symbol=target_symbol, use_optuna=True, optuna_df=df)
            best       = all_result["best"]
            all_r      = all_result["all_results"]

            # 4. result dict に反映
            result.update({
                "sharpe":        best["sharpe"],
                "sharpe_raw":    best.get("sharpe_raw", best["sharpe"]),
                "total_return":  best.get("total_return", "0.00%"),
                "max_dd":        best.get("max_dd", "0.00%"),
                "win_rate":      f"{best.get('win_rate', 0.0):.2f}%",
                "total_trades":  best.get("trades", 0),
                "confidence":    best.get("confidence", "LOW"),
                "best_strategy": best["strategy"],
                "candles":       len(df),
                "features":      len(feat),
                "status":        "success",
            })

            # 5. Council向けレポート生成
            lines = [
                f"【4戦略バックテスト結果】{target_symbol}",
                f"データ: {len(df)}本 4h足 → {len(feat)}行の特徴量",
                "",
                f"🏆 最良戦略: {best['strategy']}",
                f"   Sharpe: {best['sharpe']} | Win率: {best.get('win_rate', 0)}%"
                f" | 取引数: {best.get('trades', 0)} | 信頼度: {best.get('confidence', 'LOW')}",
            ]
            if "description" in best:
                lines.append(f"   説明: {best['description']}")

            lines += ["", "📋 全戦略サマリー:"]
            for name, r in all_r.items():
                mark = "✅" if r["sharpe"] >= 5.0 else "🔶" if r["sharpe"] >= 2.0 else "⬜"
                lines.append(
                    f"  {mark} {name}: Sharpe={r['sharpe']}"
                    f" Win={r.get('win_rate', 0)}%"
                    f" Trades={r.get('trades', 0)}"
                    f" [{r.get('confidence', 'LOW')}]"
                )

            verdict = ("Sharpe 5.0超え → アルファチャンスあり"
                       if best["sharpe"] >= 5.0
                       else "Sharpe 5.0未満 → WAIT推奨")
            lines += ["", f"💡 Council推奨: {verdict}"]
            # モンテカルロ結果をレポートに追加
            mc_label    = best.get("mc_label", "N/A")
            mc_p5       = best.get("mc_sharpe_p5", 0.0)
            mc_p50      = best.get("mc_sharpe_p50", 0.0)
            mc_p95      = best.get("mc_sharpe_p95", 0.0)
            mc_neg_prob = best.get("mc_neg_prob", 1.0)
            mc_emoji    = {"ROBUST": "🟢", "STABLE": "🟡", "FRAGILE": "🟠", "RISKY": "🔴"}.get(mc_label, "⬜")
            lines += [
                "",
                f"🎲 モンテカルロ信頼区間 (n=500):",
                f"   {mc_emoji} 堅牢性: {mc_label}",
                f"   Sharpe 5%ile={mc_p5} / 50%ile={mc_p50} / 95%ile={mc_p95}",
                f"   マイナスSharpe確率: {mc_neg_prob*100:.1f}%",
            ]
            result.update({
                "mc_label":      mc_label,
                "mc_sharpe_p5":  mc_p5,
                "mc_sharpe_p50": mc_p50,
                "mc_sharpe_p95": mc_p95,
                "mc_neg_prob":   mc_neg_prob,
            })
            result["raw_report"] = "\n".join(lines)
            logger.info(f"✅ [BacktestAgent v3] {target_symbol}: best={best['strategy']} Sharpe={best['sharpe']}")

        except Exception as e:
            result["status"]     = "error"
            result["raw_report"] = f"❌ バックテストエラー ({target_symbol}): {str(e)}"
            logger.error(result["raw_report"], exc_info=True)

        return result


if __name__ == "__main__":
    agent = BacktestAgent()
    r = agent.run(target_symbol="VIRTUAL")
    print(r["raw_report"])
