import time
import json
import os
import sys
import traceback
from datetime import datetime
from neo_main import NeoSystem
from agents.paper_trader import PaperTraderAgent

# OpenClawのweb_searchツールを模倣するラッパー (バックグラウンド実行用)
def background_search_wrapper(query):
    print(f"[Background] Searching for: {query}")
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
    
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    market_cycle_log_file = os.path.join(log_dir, "market_cycle.jsonl")
    performance_log_file = os.path.join(log_dir, "performance_metrics.jsonl")

    system = NeoSystem(web_search_tool=background_search_wrapper)
    paper_trader = PaperTraderAgent()

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Executing cycle...")
            
            topic = "Virtuals Protocol Market Update"
            
            # パフォーマンスメトリクスの読み込み
            scout_performance_metrics = []
            if os.path.exists(performance_log_file):
                try:
                    with open(performance_log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                scout_performance_metrics.append(json.loads(line))
                except Exception as e:
                    print(f"Warning: Error reading performance logs: {e}")
            
            if scout_performance_metrics:
                system.execution_history.extend(scout_performance_metrics)
                print(f"Collected {len(scout_performance_metrics)} performance metrics.")

            # サイクル実行
            cycle_output = system.autonomous_post_cycle(topic)
            
            # --- [Pydantic 構造化データ取得] ---
            strategy_json = None
            planning_output = cycle_output.get("planning_output", None)
            
            if hasattr(planning_output, 'pydantic'):
                # CrewAIのTaskOutputからPydanticオブジェクトを取得
                pydantic_obj = planning_output.pydantic
                if pydantic_obj:
                    # オブジェクトをdictに変換してPaperTraderに渡す
                    strategy_json = pydantic_obj.model_dump()
                    print(f"[Pydantic] Successfully extracted structured plan: {strategy_json.get('status')}")
            
            # フォールバック: 既存のdict/str処理 (念のため)
            if not strategy_json:
                if isinstance(planning_output, dict):
                    strategy_json = planning_output
                elif isinstance(planning_output, str):
                    try:
                        import re
                        json_match = re.search(r"```json\s*(\{.*?\})\s*```", planning_output, re.DOTALL)
                        if json_match:
                            strategy_json = json.loads(json_match.group(1))
                    except Exception as e:
                        print(f"Warning: Failed to extract fallback JSON: {e}")
            # --- [Pydantic 構造化データ取得 END] ---
            
            # ペーパートレード実行
            trade_result = {"status": "skipped", "reason": "No planning output found"}
            
            if strategy_json:
                print("[Paper Trader] Executing trades based on planning strategy...")
                trade_result = paper_trader.execute_strategy(strategy_json)
                print(f"[Paper Trader] Trade execution result: {trade_result}")

            # システム改善提案の生成
            print("[Development Crew] Analyzing performance and seeking improvements...")
            improvement_result = system.improve_system(
                performance_log_path=performance_log_file,
                market_cycle_log_path=market_cycle_log_file
            )

            # 結果のログ保存
            final_result = {
                "timestamp": current_time,
                "cycle_output": cycle_output,
                "paper_trading_execution": trade_result,
                "self_improvement_proposal": improvement_result
            }
            
            with open(market_cycle_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(final_result, ensure_ascii=False) + "\n")
            
            print(f"Cycle completed. Next run in 1 hour.")
            time.sleep(3600) # 1時間待機

        except Exception as e:
            print(f"ERROR in run_loop: {e}")
            traceback.print_exc()
            print("Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    # シンプルな引数処理
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else "Virtuals Protocol"
        system = NeoSystem(web_search_tool=background_search_wrapper)
        
        if cmd == "post":
            print(json.dumps(system.autonomous_post_cycle(arg), indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(system.plan_project(arg, "Neo 2.0 Ecosystem"))
        else:
            print(f"Unknown command: {cmd}")
    else:
        # デフォルトはループ実行
        run_loop()
