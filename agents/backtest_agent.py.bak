import os
from tools.backtest_engine import run_neo_backtest

class BacktestAgent:
    def __init__(self):
        self.name = "BacktestSpecialist"

    def run(self, strategy_idea: str, target_symbol: str, initial_cash: float = 1000.0, logic: str = 'rsi'):
        print(f"🚀 [BacktestAgent] {target_symbol} に対して戦略 '{logic}' を適用中...")
        csv_path = f"/docker/openclaw-taan/data/.openclaw/workspace/vault/market_data/{target_symbol}.csv"
        
        # 🛡️ 防衛線: CSVデータがない場合は安全にスキップ
        if not os.path.exists(csv_path):
            return f"⚠️ {target_symbol} の過去データが存在しないため、シミュレーションはスキップされました。データ不足による未知のリスク（ボラティリティ等）に最大限警戒してください。"

        try:
            res = run_neo_backtest(csv_path=csv_path, initial_cash=initial_cash, logic=logic)
            final_val = res.get("final_value", initial_cash)
            chart_path = res.get("chart_path", "N/A")
            
            return (
                f"【確定バックテスト結果】\n"
                f"- 戦略ロジック: {logic}\n"
                f"- 最終資産額: {final_val:.2f} USDC\n"
                f"- 収支: {final_val - initial_cash:.2f} USDC\n"
                f"- チャート保存先: {chart_path}\n"
            )
        except Exception as e:
            return f"バックテスト実行エラー: {e}"
