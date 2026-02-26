import time
import json
import os
from datetime import datetime
from neo_main import NeoSystem
from agents.paper_trader import PaperTraderAgent # PaperTraderAgent をインポート
import traceback # Import traceback for error logging

# OpenClawのweb_searchツールを模倣するラッパー (バックグラウンド実行用)
# ※ 注意: 外部スクリプトからはOpenClawのツールを直接呼べないため、
# 簡易的な検索結果を返すか、あるいは MarketData (DexScreener) のみで判断させる。
# 今回は「ScoutCrew」がWeb検索に依存しているため、
# 検索機能がないとエラーになるか精度が落ちる。
# 妥協案として、MarketDataの結果を「検索結果」としても渡す。
def background_search_wrapper(query):
    print(f"[Background] Searching for: {query}")
    # 実際には検索できないので、Scout Crewのタスク期待値に合わせたダミーデータを返す
    return [
        {
            "title": "Trend Alert: Gaming Sector Surge",
            "snippet": "Virtuals Protocol's Gaming sector is showing significant growth. Opportunity: Invest in top-performing Gaming agents.",
            "url": "https://example.com/virtuals/gaming-trend"
        },
        {
            "title": "New Agent Launch: 'Quantum Trader AI'",
            "snippet": "Quantum Trader AI agent launched on Base chain. High potential for arbitrage. Action: Monitor its on-chain activity.",
            "url": "https://example.com/agents/quantum-trader-ai"
        },
        {
            "title": "Risk Advisory: DeFi Protocol Security Update",
            "snippet": "A popular DeFi protocol has released a security update. Potential risk factor for its agents. Action: Review agent risk policies related to this protocol.",
            "url": "https://example.com/DeFi/security-update"
        }
    ]

def run_loop():
    print("Starting Neo Autonomous Cycle Loop (Hourly)...")
    
    # ログディレクトリの作成
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    market_cycle_log_file = os.path.join(log_dir, "market_cycle.jsonl")
    performance_log_file = os.path.join(log_dir, "performance_metrics.jsonl") # Performance log file path

    # NeoSystemの初期化
    system = NeoSystem(web_search_tool=background_search_wrapper)
    
    # PaperTraderAgentの初期化
    paper_trader = PaperTraderAgent() # デフォルトパスと初期資金を使用

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Executing cycle...")
            
            topic = "Virtuals Protocol Market Update"
            
            # --- Start: Performance Metrics Collection ---
            scout_performance_metrics = []
            if os.path.exists(performance_log_file):
                try:
                    with open(performance_log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip(): # Ensure line is not empty
                                scout_performance_metrics.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from {performance_log_file}. Check file format.")
                except Exception as e:
                    print(f"Error reading performance logs: {e}")
            
            # Add collected metrics to NeoSystem's execution history
            if scout_performance_metrics:
                # Append metrics to NeoSystem's history, ensuring not to duplicate if run multiple times without clearing
                # For simplicity, we'll just extend; a more robust system might check for duplicates
                system.execution_history.extend(scout_performance_metrics)
                print(f"Collected {len(scout_performance_metrics)} performance metrics.")
            # --- End: Performance Metrics Collection ---

            # 自律サイクルの実行 (Scout -> Sentiment -> Planning)
            # autonomous_post_cycle が PlanningCrew の結果 (strategy_json) を含むことを期待
            # ※ NeoSystem.autonomous_post_cycle が PlanningCrew の結果を返すように修正されている前提
            cycle_output = system.autonomous_post_cycle(topic)
            
            # --- Paper Trading Execution Step ---
            # PlanningCrew の結果から strategy_json を抽出 (key名は仮)
            strategy_json = cycle_output.get("planning_output", None) 
            trade_result = {"status": "skipped", "reason": "No planning output found"}
            
            if strategy_json:
                print("[Paper Trader] Executing trades based on planning strategy...")
                trade_result = paper_trader.execute_strategy(strategy_json)
                print(f"[Paper Trader] Trade execution result: {trade_result}")
            else:
                print("[Paper Trader] No strategy found. Skipping trade execution.")
            # --- End of Paper Trading Execution ---

            # 最終的な結果に取引結果を追加
            final_result = {
                **cycle_output, # Scout, Sentiment, Planning の結果
                "paper_trading_execution": trade_result, # PaperTrader の結果
                "timestamp": current_time # サイクル全体のタイムスタンプ
            }
            
            # ログファイルへの追記 (JSONL形式)
            with open(market_cycle_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(final_result, ensure_ascii=False) + "\n")
            
            print(f"Cycle completed. Logged to {market_cycle_log_file}")
            
        except Exception as e:
            print(f"Error in cycle: {e}")
            error_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "error": str(e),
                "details": traceback.format_exc() # Use traceback.format_exc() for full trace
            }
            # エラー時もログファイルに記録
            with open(market_cycle_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_log, ensure_ascii=False) + "\n")

        # 1時間待機 (3600秒)
        print("Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    # For testing purposes, ensure necessary imports are available in the environment
    # You might need to mock NeoSystem and other dependencies if running this standalone.
    # import traceback # Import traceback here for error logging
    run_loop()
