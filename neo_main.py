import json
import sys
import os
from agents.sentiment_agent import SentimentCrew
from agents.scout_agent import ScoutCrew
from agents.content_creator_agent import ContentCreatorCrew
from agents.planning_agent import PlanningCrew
from agents.development_agent import DevelopmentCrew
from agents.acp_executor_agent import ACPExecutorCrew
from tools.data_fetcher import DataFetcher
from tools.moltbook_tool import MoltbookTool
from tools.credit_score import CreditScoreCalculator, CreditProfile
from tools.market_data import MarketData # 追加

# --- 環境変数からの設定読み込み ---
# デフォルトは 'development' とし、未設定の場合は開発モードとみなす
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
# 本番環境以外ではキャッシュを有効にする
USE_CACHE = ENVIRONMENT != "production"
# 開発モードではデバッグログを有効にする（例）
DEBUG_LOGGING = ENVIRONMENT == "development"

# --- LLM モデル設定 ---
# Neoのメイン頭脳として DeepSeek-V3 (deepseek-chat) を使用
DEFAULT_LLM_MODEL = "openrouter/deepseek/deepseek-chat"

# --- キャッシュ設定 ---
# ユーザーの指示により、キャッシュ期間を短く設定
CACHE_TTL_SECONDS = 300 # 5分

# --- LLM 呼び出しクラス（例）--- 
# 既存の LLM 呼び出し処理をラップするクラス/関数を想定
class LLMClient:
    def __init__(self, model_name: str):
        self.model_name = model_name
        # ここで LLM API クライアントを初期化 (例: LiteLLM, OpenAI client など)
        print(f"Initializing LLM client with model: {self.model_name}")

    def call(self, prompt: str, **kwargs) -> str:
        # キャッシュ機構をここに実装
        cache_key = self._generate_cache_key(prompt, kwargs)
        if USE_CACHE and self._is_cache_valid(cache_key):
            print(f"Cache hit for key: {cache_key}")
            return self._get_from_cache(cache_key)
        else:
            print(f"Cache miss or disabled for key: {cache_key}")
            # 実際の LLM API 呼び出し
            response = self._call_llm_api(prompt, **kwargs)
            if USE_CACHE:
                self._save_to_cache(cache_key, response)
            return response

    def _generate_cache_key(self, prompt: str, kwargs: dict) -> str:
        # プロンプトとパラメータから一意のキャッシュキーを生成
        # (例: hash(prompt + json.dumps(kwargs)))
        import hashlib
        data_to_hash = prompt + json.dumps(kwargs, sort_keys=True)
        return hashlib.sha256(data_to_hash.encode()).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        # キャッシュデータが存在し、有効期限内かチェック
        # (実際には Redis やファイルシステムで実装)
        # 例: cache_data = redis_client.get(key); if cache_data and time.time() < cache_data['timestamp'] + CACHE_TTL_SECONDS: return True
        return False # 仮実装

    def _get_from_cache(self, key: str) -> str:
        # キャッシュからデータを取得
        # return redis_client.get(key)['response'] # 仮実装
        return "Cached Response" # 仮実装

    def _save_to_cache(self, key: str, response: str):
        # キャッシュにデータを保存
        # redis_client.set(key, {'response': response, 'timestamp': time.time()}) # 仮実装
        pass

    def _call_llm_api(self, prompt: str, **kwargs) -> str:
        # ここで実際の LLM API を呼び出す処理
        print("Calling actual LLM API...")
        # 例: return self.llm_provider.completions.create(...) 
        return "Response from LLM API" # 仮実装


# --- NeoSystem クラスの改修例 ---
class NeoSystem:
    def __init__(self, web_search_tool: callable = None):
        print(f"Initializing NeoSystem in '{ENVIRONMENT}' mode.")
        
        # OpenClawのweb_searchツールをNeoSystemで管理
        self.web_search_tool = web_search_tool
        
        # 実行ログの履歴 (自己改善用)
        self.execution_history = []

        # Crew-specific model configuration (Optimized for DeepSeek-V3 & R1)
        from core.config import NeoConfig
        default_v3 = NeoConfig.DEFAULT_MODEL
        reasoning_r1 = NeoConfig.REASONING_MODEL

        self.crew_model_map = {
            "sentiment_crew": default_v3,
            "scout_crew": default_v3,
            "creator_crew": default_v3,
            "planning_crew": reasoning_r1,   # 戦略立案には R1 (推論) を使用
            "development_crew": reasoning_r1, # コード修正・分析には R1 (推論) を使用
            "acp_executor_crew": default_v3,
        }
        
        # --- LLM Client Instances ---
        self.llm_clients = {}
        # Ensure default model client is created
        if DEFAULT_LLM_MODEL not in self.llm_clients:
            self.llm_clients[DEFAULT_LLM_MODEL] = LLMClient(model_name=DEFAULT_LLM_MODEL)
        
        # Create clients for other models specified in the map
        for model_name in set(self.crew_model_map.values()):
            if model_name not in self.llm_clients:
                self.llm_clients[model_name] = LLMClient(model_name=model_name)

        self.cache_enabled = USE_CACHE
        self.debug_logging_enabled = DEBUG_LOGGING

        # --- Context Loading ---
        self.system_context = self._load_base_context()
        if self.debug_logging_enabled:
            self.system_context.extend(self._load_debug_context())

        # --- Crew Initialization ---
        self.sentiment_crew = SentimentCrew()
        self.scout_crew = ScoutCrew()
        self.creator_crew = ContentCreatorCrew()
        self.planning_crew = PlanningCrew()
        self.development_crew = DevelopmentCrew()
        self.acp_executor_crew = ACPExecutorCrew()


    def _load_base_context(self) -> list[str]:
        # 常にロードする基本コンテキスト (例: SOUL.md, USER.md, MEMORY.md, etc.)
        # ファイル読み込み処理をここに追加
        context_files = ["SOUL.md", "USER.md", "MEMORY.md"] # 例
        loaded_context = []
        for f_path in context_files:
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    loaded_context.append(f.read())
            except FileNotFoundError:
                print(f"Warning: Base context file not found: {f_path}")
        return loaded_context

    def _load_debug_context(self) -> list[str]:
        # 開発モード時のみロードするデバッグ用コンテキスト
        loaded_context = []
        DEV_CONTEXT_PATHS = ["debug_logs/recent.log", "temp/dev_notes.md"] # 例
        for f_path in DEV_CONTEXT_PATHS:
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    loaded_context.append(f.read())
            except FileNotFoundError:
                print(f"Warning: Debug context file not found: {f_path}")
        return loaded_context

    def _get_current_prompt_context(self) -> str:
        # 現在のタスクやセッションに必要なコンテキストを生成
        # これは、単にロードされたコンテキストを結合するか、
        # より動的に生成される場合がある
        return "\n\n---\n\n".join(self.system_context)

    def develop_skill(self, spec: str, language: str = "python") -> str:
        """
        スキル開発タスク。キャッシュの有効/無効は LLMClient 側で制御される。
        """
        prompt = f"""
        Based on the following specification and language, implement the skill.
        ---
        Specification:
        {spec}
        ---
        Language: {language}
        ---
        System Context:
        {self._get_current_prompt_context()}
        ---
        """
        # LLMClient の call メソッドがキャッシュを処理してくれると仮定
        response = self.llm_client.call(prompt, model=self.llm_client.model_name)
        return response

    def scout_ecosystem(self, goal: str, context: str, constraints: str, query: str = None) -> str:
        """
        エコシステム調査部隊を派遣する
        """
        if query is None: # queryが指定されていない場合はgoalをqueryとして使用
            query = goal
        
        print(f"派遣中: EcosystemScoutCrew with query: {query}...")
        return self.scout_crew.run(
            goal=goal,
            context=context,
            constraints=constraints,
            query=query,
            web_search_tool=self.web_search_tool # web_searchツールを渡す
        )

    def analyze_sentiment(self, goal: str, market_data: str, raw_sns_data: list, context: str, constraints: str):
        """
        感情分析部隊を派遣する
        """
        formatted_sns = DataFetcher.format_for_crew(raw_sns_data)
        inputs = DataFetcher.create_sentiment_input(goal, context, constraints)
        print(f"Dispatching: SentimentAnalysisCrew...")
        return self.sentiment_crew.run(
            goal=inputs["goal"],
            context=inputs["context"],
            constraints=inputs["constraints"],
            web_search_tool=self.web_search_tool # web_searchツールを渡す
        )

    def plan_project(self, goal: str, context: str, sentiment_score: float = 0.0, market_trends: str = ""):
        """戦略企画部隊を派遣する"""
        print(f"派遣中: StrategicPlanningCrew...")
        return self.planning_crew.run(
            goal=goal,
            context=context,
            sentiment_score=sentiment_score,
            market_trends=market_trends
        )

    def execute_acp(self, strategy: str, context: str, credit_info: dict = None, sentiment_info: str = "Neutral"):
        """ACP運用部隊を派遣する"""
        print(f"派遣中: ACPExecutorCrew (with AI decision logic)...")
        return self.acp_executor_crew.run(
            strategy=strategy,
            context=context,
            credit_info=credit_info,
            sentiment_info=sentiment_info
        )

    def calculate_credit(self, profile_data: dict):
        """信用スコア計算ツールを実行する"""
        print(f"実行中: CreditScoreCalculator...")
        try:
            profile = CreditProfile(**profile_data)
            return CreditScoreCalculator.calculate(profile)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def autonomous_post_cycle(self, topic: str, search_results: list = None):
        """
        リサーチ -> 信用評価 -> センチメント分析 -> 投稿生成 -> 実行 の高度自律サイクル
        """
        try:
            # 0. 市場データの取得 (Real-time Price)
            market_price_data = MarketData.fetch_token_data("VIRTUAL")
            market_context = f"Current Market Data (VIRTUAL Token): {market_price_data}"

            # 1. リサーチフェーズ: ScoutCrewによる能動的調査
            if search_results is None:
                print(f"ScoutCrew is researching: {topic}...")
                scout_result = self.scout_ecosystem(
                    goal=f"{topic}に関する最新トレンドと機会の特定",
                    context=f"Virtuals Protocolにおける最新の市場動向を調査せよ。\n{market_context}",
                    constraints="Web検索を活用し、具体的で信頼性の高い情報を3つ抽出せよ。",
                    query=topic
                )
                
                # ScoutCrewの結果をraw_dataとして整形 (簡易的に文字列として渡す)
                raw_data = [{"title": "Scout Report", "snippet": str(scout_result), "url": "Internal Scout Crew"}]
            else:
                raw_data = search_results

            # 2. 主要エージェント(例: Quantify-X)の信用スコアをサンプルで取得
            # 本来はDBや検索からプロフィールを動的に構成するが、ここでは実証のために標準プロファイルを使用
            sample_profile = {
                "agent_id": "Quantify-X",
                "on_chain_volume": 500000,
                "reputation_score": 0.85,
                "successful_transactions": 1200,
                "failed_transactions": 5
            }
            credit_res = self.calculate_credit(sample_profile)
            # credit_res が辞書の場合(エラー時)とオブジェクトの場合を考慮
            if isinstance(credit_res, dict) and credit_res.get("status") == "error":
                credit_info = "Credit evaluation unavailable."
                rating = "N/A"
            else:
                credit_info = f"Target Agent(Quantify-X) Rating: {credit_res.rating}, Score: {credit_res.total_score}"
                rating = credit_res.rating
            
            # 3. センチメント分析 (信用情報もコンテキストに含める)
            context = f"Market Topic: {topic}\nCredit Info: {credit_info}\n{market_context}"
            constraints = "Analyze from both market sentiment and agent credit perspective."
            
            analysis = self.analyze_sentiment(
                goal=f"{topic}の総合分析と投稿戦略の立案",
                market_data=f"Focus on {topic} and {credit_info}",
                raw_sns_data=raw_data,
                context=context,
                constraints=constraints
            )
            
            summary = str(getattr(analysis, 'raw', analysis))
            
            # Sentiment Crew の結果からスコアを抽出 (簡易的な方法)
            sentiment_score = 0.0
            try:
                if hasattr(analysis, 'pydantic') and analysis.pydantic:
                    payload = getattr(analysis.pydantic, 'virtuals_payload', {})
                    if isinstance(payload, dict):
                        sentiment_score = payload.get('market_sentiment_score', 0.0)
                    else:
                        # Pydanticモデルの場合
                        sentiment_score = getattr(payload, 'market_sentiment_score', 0.0)
            except Exception as e:
                print(f"Warning: Failed to extract sentiment score: {e}")

            # 4. 戦略立案 (Risk Management & Strategy Formulation)
            print(f"Dispatching: StrategicPlanningCrew for Risk Assessment...")
            planning_result = self.plan_project(
                goal=f"{topic}に対するNeoの公式スタンスと投資戦略の策定",
                context=f"Sentiment Analysis: {summary}\nCredit Info: {credit_info}",
                sentiment_score=sentiment_score,
                market_trends=str(raw_data)
            )

            strategy_summary = str(getattr(planning_result, 'raw', planning_result))

            # 5. 投稿生成 (分析と戦略に基づいた内容)
            print(f"Dispatching: ContentCreatorCrew with Strategic Insight...")
            # ContentCreatorCrew.run は引数が (summary, topic) なので、contextに戦略を含める
            creation = self.creator_crew.run(f"Analysis: {summary}\n\nStrategic Stance: {strategy_summary}", topic)
            
            # 6. 投稿の抽出と実行
            post_content = ""
            if hasattr(creation, 'pydantic') and creation.pydantic:
                post_content = creation.pydantic.content
            elif hasattr(creation, 'raw'):
                post_content = creation.raw
            else:
                post_content = str(creation)

            if post_content:
                clean_content = post_content.strip().strip('"').strip("'")
                success = MoltbookTool.post(clean_content)
                return {
                    "status": "success" if success else "failed",
                    "content": clean_content,
                    "analysis_summary": summary,
                    "strategy_summary": strategy_summary,
                    "planning_output": planning_result, # オブジェクトごと返す
                    "credit_rating": rating
                }
            
            return {"status": "error", "message": "Failed to extract content"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def improve_system(self, error_report: str = "", recent_logs: list = None, performance_log_path: str = None, market_cycle_log_path: str = None):
        """
        自己改善部隊を派遣する。
        直近の実行ログやパフォーマンス指標に基づき、システム改善案（コード修正）を生成する。
        """
        print("派遣中: DevelopmentCrew for Self-Improvement...")
        logs_to_analyze = recent_logs if recent_logs else self.execution_history[-5:] # 最新5件
        logs_str = json.dumps(logs_to_analyze, indent=2, default=str)
        
        return self.development_crew.run(
            spec="実行ログ、エラー、およびパフォーマンスメトリクスを分析し、Scout Crewの精度向上やシステムの堅牢性を高めるための具体的なコード修正案を提示せよ。",
            language="python",
            execution_logs=logs_str,
            error_report=error_report,
            performance_log_path=performance_log_path,
            market_cycle_log_path=market_cycle_log_path
        )

    def execute_credit_transaction(self, target_agent_profile_data: dict, transaction_details: dict) -> dict:
        """
        信用スコアリング結果と市場センチメントに基づき、ACP Executor Crew に意思決定を委ねて信用取引を行う。
        """
        print("Executing credit-based transaction with AI-driven decision making...")

        # 1. 信用スコアの取得
        credit_score_result = self.calculate_credit(target_agent_profile_data)
        if isinstance(credit_score_result, dict) and credit_score_result.get("status") == "error":
            return {"status": "error", "message": f"Failed to get credit score: {credit_score_result.get('message')}"}

        # 2. 市場センチメントの簡易取得 (最新の分析結果があればそれを使用、なければデフォルト)
        # ここでは実証のために「Neutral」とするが、将来的には SentimentCrew の直近出力を反映させる
        current_sentiment = "Neutral (Stable)"

        # 3. 信用データと市場環境を ACP Executor に渡して意思決定させる
        credit_info = {
            "rating": credit_score_result.rating,
            "total_score": credit_score_result.total_score,
            "details": target_agent_profile_data
        }

        strategy = f"Credit-based {transaction_details.get('action', 'liquidity_provision')} for {target_agent_profile_data.get('agent_id', 'Unknown Agent')}"
        context = f"Transaction Details: {transaction_details}"

        print(f"Target Rating: {credit_info['rating']}, Sentiment: {current_sentiment}")

        # ACP Executor Crew の実行 (引数を拡張した新バージョンを呼び出し)
        return self.execute_acp(
            strategy=strategy,
            context=context,
            credit_info=credit_info,
            sentiment_info=current_sentiment
        )


if __name__ == "__main__":
    # 環境変数からの設定を読み込む
    import os
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    USE_CACHE = ENVIRONMENT != "production"
    DEBUG_LOGGING = ENVIRONMENT == "development"

    # NeoSystem インスタンス化時のモデル設定は LLMClient の __init__ で行われる
    # system = NeoSystem()

    # スタンドアロン実行用のダミー検索ツール
    def standalone_web_search(query):
        print(f"[Standalone] Mock web search for: {query}")
        return [{"title": "Mock Result", "snippet": f"Result for {query}", "url": "http://mock"}]

    # 開発モードでの実行例 (キャッシュ有効、デバッグログ有効)
    if ENVIRONMENT == "development":
        os.environ["ENVIRONMENT"] = "development" # 環境変数を明示的に設定
        system_dev = NeoSystem(web_search_tool=standalone_web_search)
        print(f"Running in development mode. Cache enabled: {system_dev.cache_enabled}, Debug logging: {system_dev.debug_logging_enabled}")
        # system_dev.develop_skill("Implement a function to add two numbers", "python")

    # 本番モードでの実行例 (キャッシュ無効、デバッグログ無効)
    elif ENVIRONMENT == "production":
        os.environ["ENVIRONMENT"] = "production" # 環境変数を明示的に設定
        system_prod = NeoSystem(web_search_tool=standalone_web_search)
        print(f"Running in production mode. Cache enabled: {system_prod.cache_enabled}, Debug logging: {system_prod.debug_logging_enabled}")
        # system_prod.develop_skill("Implement a function to add two numbers", "python")

    # コマンドライン引数からの実行（例）
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""
        current_system = NeoSystem(web_search_tool=standalone_web_search)
        if cmd == "post":
            print(json.dumps(current_system.autonomous_post_cycle(arg), indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(current_system.plan_project(arg, "Neo 2.0 Ecosystem"))
        elif cmd == "execute":
            print(current_system.execute_acp(arg, "Neo Strategy"))
