"""
BacktestAgent v2 — 実データ直結バックテスト
CSV依存を廃止。CoinGecko OHLC APIから直接データ取得 → FeatureBuilder → CoreBacktest
"""
import sys
import math
import logging

logger = logging.getLogger("neo.backtest_agent")

class BacktestAgent:
    def __init__(self):
        self.name = "BacktestSpecialist_v2"

    def run(self, strategy_idea: str, target_symbol: str, initial_cash: float = 1000.0, logic: str = 'rsi') -> dict:
        """
        実データでバックテストを実行し、構造化された結果を返す。
        
        Returns:
            dict with keys: sharpe, total_return, max_dd, win_rate, total_trades, confidence, raw_report
        """
        print(f"🚀 [BacktestAgent v2] {target_symbol} — 実データバックテスト開始...")
        
        result = {
            "symbol": target_symbol,
            "sharpe": 0.0,
            "total_return": "0.00%",
            "max_dd": "0.00%",
            "win_rate": "0.00%",
            "total_trades": 0,
            "confidence": "NONE",
            "logic": logic,
            "initial_cash": initial_cash,
            "raw_report": "",
            "status": "unknown"
        }
        
        try:
            from tools.market_data import MarketData
            from feature_engineering.build_features import FeatureBuilder
            from research.backtests.run_backtest import CoreBacktest
            
            # 1. 実データ取得（CoinGecko 30日/180本4h足）
            # シンボル正規化: "ETH/USDT" → "ETH"
            clean_symbol = target_symbol.split('/')[0].strip()
            df = MarketData.fetch_ohlcv_custom(clean_symbol)
            
            if df.empty or len(df) < 20:
                result["status"] = "insufficient_data"
                result["raw_report"] = f"⚠️ {target_symbol}: データ不足（{len(df)}本）。最低20本必要。"
                logger.warning(result["raw_report"])
                return result
            
            # 2. 特徴量ビルド
            feat = FeatureBuilder.build_from_memory(df)
            
            if feat.empty or len(feat) < 10:
                result["status"] = "feature_build_failed"
                result["raw_report"] = f"⚠️ {target_symbol}: 特徴量ビルド後のデータ不足（{len(feat)}行）"
                logger.warning(result["raw_report"])
                return result
            
            # 3. バックテスト実行
            portfolio = CoreBacktest.run_alpha_strategy(feat)
            stats = portfolio.stats()
            
            total_trades = int(stats.get('Total Trades', 0))
            sharpe_raw = stats.get('Sharpe Ratio', 0.0)
            total_return = stats.get('Total Return [%]', 0.0)
            max_dd = stats.get('Max Drawdown [%]', 0.0)
            win_rate = stats.get('Win Rate [%]', 0.0)
            
            # Sharpe信頼度ガード
            if total_trades < 3 or math.isinf(sharpe_raw) or math.isnan(sharpe_raw):
                sharpe_adj = 0.0
                confidence = "LOW"
            else:
                sharpe_adj = round(sharpe_raw, 2)
                confidence = "HIGH" if total_trades >= 10 else "MEDIUM"
            
            result.update({
                "sharpe": sharpe_adj,
                "sharpe_raw": round(sharpe_raw, 2) if not (math.isinf(sharpe_raw) or math.isnan(sharpe_raw)) else 0.0,
                "total_return": f"{total_return:.2f}%",
                "max_dd": f"{max_dd:.2f}%",
                "win_rate": f"{win_rate:.2f}%",
                "total_trades": total_trades,
                "confidence": confidence,
                "candles": len(df),
                "features": len(feat),
                "status": "success",
                "raw_report": (
                    f"【実データバックテスト結果】{target_symbol}\n"
                    f"- データ: {len(df)}本 4h足 → {len(feat)}行の特徴量\n"
                    f"- Sharpe: {sharpe_adj} (raw: {sharpe_raw:.2f}, confidence: {confidence})\n"
                    f"- リターン: {total_return:.2f}%\n"
                    f"- 最大DD: {max_dd:.2f}%\n"
                    f"- 勝率: {win_rate:.2f}% ({total_trades}取引)\n"
                    f"- 戦略ロジック: {logic}"
                )
            })
            
            logger.info(f"✅ [BacktestAgent] {target_symbol}: Sharpe={sharpe_adj}, Return={total_return:.2f}%, Trades={total_trades}")
            
        except Exception as e:
            result["status"] = "error"
            result["raw_report"] = f"❌ バックテストエラー ({target_symbol}): {str(e)}"
            logger.error(result["raw_report"], exc_info=True)
        
        return result


if __name__ == "__main__":
    agent = BacktestAgent()
    r = agent.run(strategy_idea="test", target_symbol="ETH", logic="bb_reversal")
    print(r["raw_report"])
    print(f"\nFull result: {r}")
