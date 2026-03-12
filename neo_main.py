import json
import sys
import os
import logging
from datetime import datetime
from agents.scout_agent import ScoutCrew
from agents.planning_agent import PlanningCrew
from agents.acp_executor_agent import ACPExecutorCrew
from tools.market_data import MarketData
from tools.publisher import NeoPublisher
from tools.discord_reporter import DiscordReporter
from core.blackboard import NeoBlackboard

class NeoSystem:
    def __init__(self):
        print(f"Initializing NeoSystem.")
        self.blackboard = NeoBlackboard()
        self.scout_crew = ScoutCrew()
        self.planning_crew = PlanningCrew()
        self.acp_executor_crew = ACPExecutorCrew()

    def autonomous_post_cycle(self, topic: str):
        print("\n--- 🟢 [NeoSystem] Autonomous Cycle Started ---")
        price = 0.0
        exec_dict = {"action": "Initial-Wait", "amount_usd": 0.0}

        try:
            # 実況ログ：サイクル開始
            DiscordReporter.send_log("🚀 Neo Cycle Start", f"Topic: {topic}\n分析を開始します...", 0x3498db)

            # 1. 市場データ取得
            market_price_data = MarketData.fetch_token_data("VIRTUAL")
            price = float(market_price_data.get("priceUsd", 0.0))
            
            # 2-5. 偵察・立案・執行 (既存ロジック)
            scout_context = f"Topic: {topic}, VIRTUAL Price: ${price}"
            scout_result = self.scout_crew.run(goal=f"{topic}の市場分析", context=scout_context)
            self.blackboard.update("market_intel", market_price_data)
            
            plan_result = self.planning_crew.run(goal="取引戦略立案", context=str(scout_result))
            exec_result = self.acp_executor_crew.run(strategy=str(plan_result), context="Simulation")
            
            try:
                if hasattr(exec_result, 'json_dict') and exec_result.json_dict:
                    exec_dict = exec_result.json_dict
                else:
                    exec_dict = json.loads(str(exec_result).replace("'", '"'))
            except:
                exec_dict = {"action": str(exec_result)[:50]}

        except Exception as e:
            print(f"⚠️ Error: {e}")
            exec_dict = {"action": f"Error: {str(e)[:20]}"}
            DiscordReporter.send_log("❌ System Error", f"エラーが発生しました: {str(e)}", 0xe74c3c)

        finally:
            # 📝 ペーパートレードログ記録
            log_path = "/docker/openclaw-taan/data/.openclaw/workspace/paper_trade.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            action = exec_dict.get("action", "Unknown")
            
            with open(log_path, "a", encoding="utf-8") as f:
                log_line = f"[{timestamp}] VIRTUAL: ${price:.4f} | Action: {action} | Topic: {topic}\n"
                f.write(log_line)
            
            # 📊 日報(SitRep)の自動生成とDiscord送信
            try:
                NeoPublisher.generate_daily_sitrep(auto_publish=True)
                print(f"✅ Daily SitRep Sent to Discord.")
            except Exception as e:
                print(f"⚠️ Failed to send SitRep: {e}")

        return {"status": "success"}

if __name__ == "__main__":
    NeoSystem().autonomous_post_cycle("Test Cycle")
