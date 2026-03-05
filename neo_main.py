import json
import sys
import os
import logging
import time
from agents.sentiment_agent import SentimentCrew
from agents.scout_agent import ScoutCrew
from agents.content_creator_agent import ContentCreatorCrew
from agents.planning_agent import PlanningCrew
from agents.development_agent import DevelopmentCrew
from agents.acp_executor_agent import ACPExecutorCrew
from tools.data_fetcher import DataFetcher
from tools.moltbook_tool import MoltbookTool
from tools.credit_score import CreditScoreCalculator, CreditProfile
from tools.market_data import MarketData
from core.blackboard import Blackboard
from core.cost_guard import CostGuard
from core.logger import ExecutionLogger # 追加
from core.config import NeoConfig

# --- 環境変数からの設定読み込み ---
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
USE_CACHE = ENVIRONMENT != "production"
DEBUG_LOGGING = ENVIRONMENT == "development"

# --- LLM モデル設定 ---
DEFAULT_LLM_MODEL = NeoConfig.DEFAULT_MODEL # 統一管理に変更

# --- キャッシュ設定 ---
CACHE_TTL_SECONDS = 300 

class LLMClient:
    def __init__(self, model_name: str):
        self.model_name = model_name
        print(f"Initializing LLM client with model: {self.model_name}")

    def call(self, prompt: str, **kwargs) -> str:
        # 簡易キャッシュ実装 (本筋ではないため省略)
        return "Response from LLM API" 

class NeoSystem:
    def __init__(self, web_search_tool: callable = None):
        print(f"Initializing NeoSystem in '{ENVIRONMENT}' mode.")
        
        self.web_search_tool = web_search_tool
        self.execution_history = []
        
        # --- Core Modules (Phase 3.1) ---
        self.blackboard = Blackboard()
        self.cost_guard = CostGuard()
        self.logger = ExecutionLogger() # 追加
        print(f"[Neo] Blackboard, CostGuard & Logger activated.")

        # Crew-specific model configuration (Hybrid Architecture)
        self.crew_model_map = {
            "sentiment_crew": NeoConfig.MODEL_EYES,
            "scout_crew": NeoConfig.MODEL_EYES,
            "creator_crew": NeoConfig.MODEL_CREATIVE,
            "planning_crew": NeoConfig.MODEL_BRAIN,
            "development_crew": NeoConfig.MODEL_BRAIN,
            "acp_executor_crew": NeoConfig.MODEL_HANDS,
        }
        
        # --- LLM Client Instances ---
        self.llm_clients = {}
        if DEFAULT_LLM_MODEL not in self.llm_clients:
            self.llm_clients[DEFAULT_LLM_MODEL] = LLMClient(model_name=DEFAULT_LLM_MODEL)
        
        for model_name in set(self.crew_model_map.values()):
            if model_name not in self.llm_clients:
                self.llm_clients[model_name] = LLMClient(model_name=model_name)

        self.cache_enabled = USE_CACHE
        self.debug_logging_enabled = DEBUG_LOGGING
        self.system_context = self._load_base_context()

        # --- Crew Initialization ---
        self.sentiment_crew = SentimentCrew()
        self.scout_crew = ScoutCrew()
        self.creator_crew = ContentCreatorCrew()
        self.planning_crew = PlanningCrew()
        self.development_crew = DevelopmentCrew()
        self.acp_executor_crew = ACPExecutorCrew()

    def _load_base_context(self) -> list[str]:
        context_files = ["SOUL.md", "USER.md", "MEMORY.md"]
        loaded_context = []
        for f_path in context_files:
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    loaded_context.append(f.read())
            except FileNotFoundError:
                print(f"Warning: Base context file not found: {f_path}")
        return loaded_context

    def _safe_dispatch(self, crew_name: str, crew_instance: object, run_func_name: str, **kwargs):
        """
        CostGuardによる承認を経てCrewを実行するラッパーメソッド。
        ExecutionLoggerによるログ記録も行う。
        """
        model = self.crew_model_map.get(crew_name, NeoConfig.DEFAULT_MODEL)
        
        # 簡易的なトークン見積もり (本来はタスク内容から計算)
        est_input = 2000
        est_output = 1000
        
        if not self.cost_guard.approve_execution(crew_name, model, est_input, est_output):
            return f"[System] Execution Denied by CFO: {crew_name} (Budget/Loop Limit)"

        start_time = time.time()
        try:
            # 実行
            run_func = getattr(crew_instance, run_func_name)
            result = run_func(**kwargs)
            
            duration = time.time() - start_time
            self.cost_guard.reset_failures(crew_name) # 成功したらリセット
            
            # ログ記録 (TurnsはCrewAIの出力から抽出したいが、簡易的に1とする)
            # コスト計算も簡易実装
            cost = self.cost_guard._estimate_cost(model, est_input, est_output)
            self.logger.log_interaction(crew_name, run_func_name, "success", 1, duration, cost)
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"[System] Error in {crew_name}: {e}")
            self.cost_guard.record_failure(crew_name) # 失敗カウント
            
            # エラーログ記録
            self.logger.log_interaction(crew_name, run_func_name, "error", 0, duration, 0.0, str(e))
            return f"[System] Error: {str(e)}"

    def scout_ecosystem(self, goal: str, context: str, constraints: str, query: str = None) -> str:
        # Blackboardから共通コンテキストを注入
        shared_ctx = self.blackboard.get_context_summary()
        full_context = f"{shared_ctx}\n\nTask Specific Context:\n{context}"
        
        if query is None: query = goal
        return self._safe_dispatch(
            "scout_crew", self.scout_crew, "run",
            goal=goal, context=full_context, constraints=constraints, query=query, web_search_tool=self.web_search_tool
        )

    def analyze_sentiment(self, goal: str, market_data: str, raw_sns_data: list, context: str, constraints: str):
        formatted_sns = DataFetcher.format_for_crew(raw_sns_data)
        inputs = DataFetcher.create_sentiment_input(goal, context, constraints)
        
        shared_ctx = self.blackboard.get_context_summary()
        full_context = f"{shared_ctx}\n\n{inputs['context']}"

        return self._safe_dispatch(
            "sentiment_crew", self.sentiment_crew, "run",
            goal=inputs["goal"], context=full_context, constraints=inputs["constraints"], web_search_tool=self.web_search_tool
        )

    def plan_project(self, goal: str, context: str, sentiment_score: float = 0.0, market_trends: str = ""):
        shared_ctx = self.blackboard.get_context_summary()
        full_context = f"{shared_ctx}\n\n{context}"
        
        return self._safe_dispatch(
            "planning_crew", self.planning_crew, "run",
            goal=goal, context=full_context, sentiment_score=sentiment_score, market_trends=market_trends
        )

    def execute_acp(self, strategy: str, context: str, credit_info: dict = None, sentiment_info: str = "Neutral"):
        shared_ctx = self.blackboard.get_context_summary()
        full_context = f"{shared_ctx}\n\n{context}"

        return self._safe_dispatch(
            "acp_executor_crew", self.acp_executor_crew, "run",
            strategy=strategy, context=full_context, credit_info=credit_info, sentiment_info=sentiment_info
        )

    def calculate_credit(self, profile_data: dict):
        try:
            profile = CreditProfile(**profile_data)
            return CreditScoreCalculator.calculate(profile)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def autonomous_post_cycle(self, topic: str, search_results: list = None):
        """
        Blackboard駆動型の自律サイクル
        """
        try:
            # 0. 市場データ更新 & Blackboardへの書き込み
            market_price_data = MarketData.fetch_token_data("VIRTUAL")
            if market_price_data:
                 price = market_price_data.get("price", 0.0) if isinstance(market_price_data, dict) else 0.0
                 self.blackboard.update("current_price", {"token": "VIRTUAL", "price": price, "updated_at": time.time()})
            
            # 1. Scout
            if search_results is None:
                scout_output = self.scout_ecosystem(
                    goal=f"{topic}に関する最新トレンドと機会の特定",
                    context=f"Focus on: {topic}",
                    constraints="具体的かつ信頼性の高い情報。",
                    query=topic
                )
                # CrewOutputから確実にテキストを抽出
                scout_text = ""
                if hasattr(scout_output, 'raw'):
                    scout_text = scout_output.raw
                else:
                    scout_text = str(scout_output)
                
                print(f"[Neo] Scout Report Length: {len(scout_text)}")
                raw_data = [{"title": "Scout Intelligence", "snippet": scout_text, "url": "Internal Scout Crew"}]
            else:
                raw_data = search_results

            # 2. Credit Check (Sample)
            # ... (変更なし) ...
            sample_profile = {
                "agent_id": "Quantify-X",
                "on_chain_volume": 500000,
                "reputation_score": 0.85,
                "successful_transactions": 1200,
                "failed_transactions": 5
            }
            credit_res = self.calculate_credit(sample_profile)
            if isinstance(credit_res, dict) and credit_res.get("status") == "error":
                credit_info = "Credit evaluation unavailable."
                rating = "N/A"
            else:
                credit_info = f"Rating: {credit_res.rating}, Score: {credit_res.total_score}"
                rating = credit_res.rating

            # 3. Sentiment Analysis
            analysis = self.analyze_sentiment(
                goal=f"{topic}の分析",
                market_data=f"Focus on {topic}",
                raw_sns_data=raw_data,
                context=f"Credit Info: {credit_info}",
                constraints="Analyze sentiment."
            )
            
            # Blackboard Update (Sentiment)
            summary = ""
            if hasattr(analysis, 'raw'):
                summary = analysis.raw
            else:
                summary = str(analysis)
                
            print(f"[Neo] Sentiment Analysis Length: {len(summary)}")
            # 簡易的にスコア抽出と仮定
            sentiment_score = 0.5 
            self.blackboard.update("sentiment", {"score": sentiment_score, "label": "Analysis Done", "updated_at": time.time()})

            # 4. Planning
            planning_result = self.plan_project(
                goal=f"{topic}に対する戦略策定",
                context=f"Sentiment: {summary}",
                sentiment_score=sentiment_score,
                market_trends=str(raw_data)
            )
            strategy_summary = ""
            if hasattr(planning_result, 'raw'):
                strategy_summary = planning_result.raw
            else:
                strategy_summary = str(planning_result)
            
            print(f"[Neo] Planning Result Length: {len(strategy_summary)}")
            # Blackboard Update (Strategy)
            self.blackboard.update("active_strategy", {"name": "New Strategy", "risk_level": "Computed", "updated_at": time.time()})

            # 5. Creator
            # 材料が不完全（エラー等）な場合のフォールバックロジック
            creator_input = f"Analysis: {summary}\n\nStrategy: {strategy_summary}"
            if "Error" in strategy_summary or not strategy_summary:
                print("[Neo] Strategy failed. Falling back to Scout Report for content creation.")
                creator_input = f"Analysis: {summary}\n\nNote: Strategy planning is currently in maintenance. Focus on the scout report."

            creation = self._safe_dispatch(
                "creator_crew", self.creator_crew, "run",
                sentiment_summary=creator_input, current_trends=topic
            )
            
            post_content = ""
            if hasattr(creation, 'raw'):
                post_content = creation.raw
            elif hasattr(creation, 'pydantic') and creation.pydantic:
                post_content = creation.pydantic.content
            else:
                post_content = str(creation)

            # 万が一Creatorが空を返した場合の最終防衛ライン
            if (not post_content or "Error" in post_content) and len(summary) > 50:
                 print("[Neo] Creator failed. Using raw analysis as post content.")
                 post_content = f"【Neo市場調査速報】\n\n{summary[:1000]}"

            if post_content:
                clean_content = post_content.strip().strip('"').strip("'")
                success = MoltbookTool.post(clean_content)
                
                # サイクル完了を記録
                self.blackboard.update("last_cycle_summary", f"Posted about {topic}")
                
                return {
                    "status": "success" if success else "failed",
                    "content": clean_content,
                    "analysis_summary": summary,
                    "strategy_summary": strategy_summary,
                    "credit_rating": rating
                }
            
            return {"status": "error", "message": "Failed to extract content"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def improve_system(self, error_report: str = "", recent_logs: list = None, performance_log_path: str = None, market_cycle_log_path: str = None):
        logs_to_analyze = recent_logs if recent_logs else self.execution_history[-5:]
        logs_str = json.dumps(logs_to_analyze, indent=2, default=str)
        
        return self._safe_dispatch(
            "development_crew", self.development_crew, "run",
            spec="System Improvement", language="python", execution_logs=logs_str, error_report=error_report,
            performance_log_path=performance_log_path, market_cycle_log_path=market_cycle_log_path
        )

    def execute_credit_transaction(self, target_agent_profile_data: dict, transaction_details: dict) -> dict:
        print("Executing credit-based transaction with AI-driven decision making...")
        credit_score_result = self.calculate_credit(target_agent_profile_data)
        if isinstance(credit_score_result, dict) and credit_score_result.get("status") == "error":
            return {"status": "error", "message": f"Failed to get credit score: {credit_score_result.get('message')}"}

        current_sentiment = "Neutral (Stable)" # 将来的にBlackboardから取得

        credit_info = {
            "rating": credit_score_result.rating,
            "total_score": credit_score_result.total_score,
            "details": target_agent_profile_data
        }

        strategy = f"Credit-based {transaction_details.get('action', 'liquidity_provision')} for {target_agent_profile_data.get('agent_id', 'Unknown Agent')}"
        context = f"Transaction Details: {transaction_details}"
        
        # execute_acp は内部で _safe_dispatch を使用しているため、CostGuardによって保護される
        return self.execute_acp(
            strategy=strategy,
            context=context,
            credit_info=credit_info,
            sentiment_info=current_sentiment
        )


if __name__ == "__main__":
    # Ensure environment is set up correctly for CLI mode
    from core.config import NeoConfig
    NeoConfig.setup_env()
    
    # Use OpenClaw's native web_search tool for CLI execution
    # No need for GoogleSerperAPIWrapper as OpenClaw provides its own web_search tool
    
    def openclaw_web_search(query):
        print(f"[CLI] Web search is currently disabled. Query: {query}")
        return [] # 空の結果を返すことで、検索は行われません

    # Initialize System with OpenClaw's native web_search tool
    os.environ["ENVIRONMENT"] = "production"
    system_cli = NeoSystem(web_search_tool=openclaw_web_search)
    print("[CLI] NeoSystem initialized with OpenClaw's native web_search tool.")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""
        
        if cmd == "post":
            print(f"[CLI] Starting autonomous post cycle for topic: {arg}")
            result = system_cli.autonomous_post_cycle(arg)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(f"[CLI] Planning project: {arg}")
            print(system_cli.plan_project(arg, "Neo 2.0 Ecosystem"))
        elif cmd == "execute":
            print(f"[CLI] Executing ACP: {arg}")
            print(system_cli.execute_acp(arg, "Neo Strategy"))
