import time
import json
import os
import sys
import traceback
from datetime import datetime, timezone
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

def check_manager_health():
    """マネージャーによる自己健康診断: 前回のサイクルが正常に完了したか確認する"""
    health_file = "logs/manager_heartbeat.json"
    if not os.path.exists(health_file):
        print("[Manager] No previous heartbeat found. Initializing first run.")
        return True

    try:
        with open(health_file, "r") as f:
            heartbeat = json.load(f)
            last_run = datetime.fromisoformat(heartbeat.get("timestamp"))
            # タイムゾーンなしのdatetimeに比較を合わせる
            if last_run.tzinfo:
                last_run = last_run.replace(tzinfo=None)
            
            time_diff = (datetime.now() - last_run).total_seconds() / 3600

            if time_diff > 1.5:
                print(f"⚠️ [CRITICAL] Manager Alert: Silence detected for {time_diff:.2f} hours!")
                print(f"⚠️ [CRITICAL] Potential system stall detected in previous run.")
                return False
            else:
                print(f"✅ [Manager] Health Check: System stable. Last run was {time_diff*60:.1f} minutes ago.")
                return True
    except Exception as e:
        print(f"Warning: Failed to read health check: {e}")
        return True

def update_heartbeat():
    """健康診断の記録を更新する"""
    health_file = "logs/manager_heartbeat.json"
    os.makedirs("logs", exist_ok=True)
    with open(health_file, "w") as f:
        json.dump({"status": "healthy", "timestamp": datetime.now().isoformat()}, f)

def run_loop():
    print("Starting Neo Autonomous Cycle Loop (Hourly)...")
    
    # 起動時に自己診断を実行
    check_manager_health()
    
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
            
            # --- サイクル実行の開始 ---
            update_heartbeat() # 活動開始を記録
            
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
                pydantic_obj = planning_output.pydantic
                if pydantic_obj:
                    strategy_json = pydantic_obj.model_dump()
                    print(f"[Pydantic] Successfully extracted structured plan: {strategy_json.get('status')}")
            
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
            def serializable_dict(obj):
                """CrewOutputなどのPydantic/特殊オブジェクトをJSON保存可能な形式に変換"""
                if isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                if isinstance(obj, dict):
                    return {k: serializable_dict(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [serializable_dict(i) for i in obj]
                
                if hasattr(obj, 'pydantic') and obj.pydantic:
                    return obj.pydantic.model_dump()
                if hasattr(obj, 'model_dump'):
                    return obj.model_dump()
                if hasattr(obj, 'json'):
                    try: return json.loads(obj.json())
                    except: pass
                if hasattr(obj, 'dict'):
                    try: return obj.dict()
                    except: pass
                
                return str(obj)

            # cycle_outputの中身をシリアライズ可能にする
            clean_cycle_output = serializable_dict(cycle_output)

            final_result = {
                "timestamp": current_time,
                "cycle_output": clean_cycle_output,
                "paper_trading_execution": trade_result,
                "self_improvement_proposal": serializable_dict(improvement_result)
            }
            
            with open(market_cycle_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(final_result, ensure_ascii=False) + "\n")
            
            # --- [能動的報告プロトコル] ---
            try:
                # 司令官への報告内容を構築
                content_val = clean_cycle_output.get('content', '情報収集完了')
                if isinstance(content_val, dict):
                    content_val = content_val.get('summary', str(content_val))
                
                report_text = f"【Neo 自律哨戒報告】\n時刻: {current_time}\n状況: サイクル完了\n内容要約: {str(content_val)[:300]}..."
                
                print(f"📣 [Proactive Report]\n{report_text}")
                
            except Exception as msg_e:
                print(f"Warning: Failed to build proactive report: {msg_e}")
            # --- [能動的報告プロトコル END] ---
            
            print(f"Cycle completed. Next run in 1 hour.")
            time.sleep(3600) # 1時間待機

        except Exception as e:
            print(f"ERROR in run_loop: {e}")
            traceback.print_exc()
            print("Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else "Virtuals Protocol"
        system = NeoSystem(web_search_tool=background_search_wrapper)
        
        if cmd == "post":
            result = system.autonomous_post_cycle(arg)
            def quick_serialize(obj):
                if hasattr(obj, 'pydantic') and obj.pydantic: return obj.pydantic.model_dump()
                if hasattr(obj, 'json'): 
                    try: return json.loads(obj.json())
                    except: pass
                return str(obj)
            
            clean_res = {k: quick_serialize(v) for k, v in result.items()}
            print(json.dumps(clean_res, indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(system.plan_project(arg, "Neo 2.0 Ecosystem"))
        else:
            print(f"Unknown command: {cmd}")
    else:
        run_loop()
