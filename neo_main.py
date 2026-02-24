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

# --- 環境変数からの設定読み込み ---
# デフォルトは 'development' とし、未設定の場合は開発モードとみなす
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
# 本番環境以外ではキャッシュを有効にする
USE_CACHE = ENVIRONMENT != "production"
# 開発モードではデバッグログを有効にする（例）
DEBUG_LOGGING = ENVIRONMENT == "development"

# --- LLM モデル設定 ---
# ユーザーの指示により、全ての LLM 呼び出しで DeepSeek V3 を使用する
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
    def __init__(self):
        print(f"Initializing NeoSystem in '{ENVIRONMENT}' mode.")
        self.llm_client = LLMClient(model_name=DEFAULT_LLM_MODEL)
        self.cache_enabled = USE_CACHE
        self.debug_logging_enabled = DEBUG_LOGGING

        # --- コンテキストのロード ---
        self.system_context = self._load_base_context()
        if self.debug_logging_enabled:
            self.system_context.extend(self._load_debug_context())

        # Crew の初期化などはここで行う
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

    def scout_ecosystem(self, goal: str, context: str, constraints: str) -> str:
        """
        エコシステム調査部隊を派遣する
        """
        prompt = f"""
        Goal: {goal}
        Context: {context}
        Constraints: {constraints}
        System Context:
        {self._get_current_prompt_context()}
        """
        response = self.llm_client.call(prompt, model=self.llm_client.model_name)
        return response

    def plan_project(self, goal: str, context: str):
        """企画部隊を派遣する"""
        print(f"派遣中: StrategicPlanningCrew...")
        return self.planning_crew.run(goal, context)

    def execute_acp(self, strategy: str, context: str):
        """ACP運用部隊を派遣する"""
        print(f"派遣中: ACPExecutorCrew...")
        return self.acp_executor_crew.run(strategy, context)

    def calculate_credit(self, profile_data: dict):
        """信用スコア計算ツールを実行する"""
        print(f"実行中: CreditScoreCalculator...")
        try:
            profile = CreditProfile(**profile_data)
            return CreditScoreCalculator.calculate(profile)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def autonomous_post_cycle(self, topic: str):
        """
        リサーチ -> 分析 -> 投稿生成 -> 実行 の本番用自律サイクル
        """
        try:
            raw_data = [{"title": "aGDP Growth", "snippet": "Virtuals aGDP $470M, high growth.", "url": "N/A"}]
            analysis = self.analyze_sentiment(f"{topic}の分析", "Price: $0.62", raw_data)
            
            summary = str(getattr(analysis, 'raw', analysis))
            print(f"派遣中: ContentCreatorCrew...")
            creation = self.creator_crew.run(summary, topic)
            
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
                return {"status": "success" if success else "failed", "content": clean_content}
            
            return {"status": "error", "message": "Failed to extract content"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def execute_credit_transaction(self, target_agent_profile_data: dict, transaction_details: dict) -> dict:
        """
        信用スコアリング結果に基づき、ACP Executor Crew を実行して信用取引を行う。
        """
        print("Executing credit-based transaction...")

        # 1. 信用スコアの取得
        credit_score_result = self.calculate_credit(target_agent_profile_data)
        
        if credit_score_result.get("status") == "error":
            return {"status": "error", "message": f"Failed to get credit score: {credit_score_result.get('message')}"}

        score = credit_score_result.get("total_score")
        rating = credit_score_result.get("rating")

        print(f"Target Agent Credit Score: {score}, Rating: {rating}")

        # 2. 信用スコアに基づいた取引パラメータの決定
        # (これはあくまで例であり、より詳細なロジックが必要)
        interest_rate = 0.05 # デフォルト金利
        collateral_ratio = 1.5 # デフォルト担保比率
        loan_amount_limit = 10000 # デフォルト貸付上限

        if rating == "AAA":
            interest_rate = 0.03
            collateral_ratio = 1.1
            loan_amount_limit = 50000
        elif rating == "AA":
            interest_rate = 0.04
            collateral_ratio = 1.2
            loan_amount_limit = 30000
        elif rating == "A":
            interest_rate = 0.05
            collateral_ratio = 1.5
            loan_amount_limit = 15000
        elif rating == "BBB":
            interest_rate = 0.07
            collateral_ratio = 2.0
            loan_amount_limit = 7000
        else: # BB, B
            interest_rate = 0.10
            collateral_ratio = 2.5
            loan_amount_limit = 3000
            print("Warning: Low credit rating, high risk transaction parameters applied.")

        # transaction_details から実際の貸付希望額などを取得
        requested_amount = transaction_details.get("amount", 0)
        
        # 貸付上限を超えないように調整
        actual_loan_amount = min(requested_amount, loan_amount_limit)

        if actual_loan_amount <= 0:
            return {"status": "info", "message": "Transaction amount is zero or exceeds limits based on credit score."}

        # ACP Executor に渡す戦略とコンテキストを構築
        strategy = f"Lend {actual_loan_amount} units of asset X to agent with {rating} rating at {interest_rate*100}% interest, collateral ratio {collateral_ratio}."
        context = f"Executing credit transaction for {actual_loan_amount} based on {rating} credit score. Details: {transaction_details}"

        print(f"ACP Executor Strategy: {strategy}")

        # 3. ACP Executor Crew の実行
        return self.execute_acp(strategy=strategy, context=context)


if __name__ == "__main__":
    # 環境変数からの設定を読み込む
    import os
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    USE_CACHE = ENVIRONMENT != "production"
    DEBUG_LOGGING = ENVIRONMENT == "development"

    # NeoSystem インスタンス化時のモデル設定は LLMClient の __init__ で行われる
    # system = NeoSystem()

    # 開発モードでの実行例 (キャッシュ有効、デバッグログ有効)
    if ENVIRONMENT == "development":
        os.environ["ENVIRONMENT"] = "development" # 環境変数を明示的に設定
        system_dev = NeoSystem()
        print(f"Running in development mode. Cache enabled: {system_dev.cache_enabled}, Debug logging: {system_dev.debug_logging_enabled}")
        # system_dev.develop_skill("Implement a function to add two numbers", "python")

    # 本番モードでの実行例 (キャッシュ無効、デバッグログ無効)
    elif ENVIRONMENT == "production":
        os.environ["ENVIRONMENT"] = "production" # 環境変数を明示的に設定
        system_prod = NeoSystem()
        print(f"Running in production mode. Cache enabled: {system_prod.cache_enabled}, Debug logging: {system_prod.debug_logging_enabled}")
        # system_prod.develop_skill("Implement a function to add two numbers", "python")

    # コマンドライン引数からの実行（例）
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""
        current_system = NeoSystem() # コマンドライン実行時は NeoSystem を初期化
        if cmd == "post":
            print(json.dumps(current_system.autonomous_post_cycle(arg), indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(current_system.plan_project(arg, "Neo 2.0 Ecosystem"))
        elif cmd == "execute":
            print(current_system.execute_acp(arg, "Neo Strategy"))
