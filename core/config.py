import os

class NeoConfig:
    """
    Neoのシステム全体で共有される設定クラス。
    ガイドラインに基づき、コストと安全性を制御する。
    """
    # LLM設定 (最善のモデルにアップデート)
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # --- Model Definitions (Optimization Strategy) ---
    # Default (General Purpose)
    DEFAULT_MODEL = "google/gemini-3-pro-preview" 
    
    # Role-Specific Models
    MODEL_BRAIN = "google/gemini-3-pro-preview"      # Planning, Dev (Logic/Code)
    MODEL_EYES = "google/gemini-3-pro-preview"       # Scout, Sentiment (Context/Speed)
    MODEL_HANDS = "google/gemini-3-pro-preview"      # Executor (Tool use/JSON)
    MODEL_CREATIVE = "google/gemini-3-pro-preview"   # Creator (Writing nuance)
    
    REASONING_MODEL = "google/gemini-3-pro-preview"  # DeepSeek-R1 alternative (Pure Logic)
    
    # 安全装置 (安定化プロトコル v1.0)
    MAX_ITER = 3             # 無限ループ防止 (5→3に削減)
    MAX_RPM = 10             # APIレート制限遵守
    MAX_EXEC_TIME = 300      # 1タスク最大300秒 (5分)
    VERBOSE = False          # メインログの肥大化を抑制 (True→False)
    
    # Context Management (Token Limit Control)
    MAX_CONTEXT_TOKENS = 4000  # これを超えたら要約を発動
    SUMMARY_MODEL = MODEL_EYES # 要約には高速なモデルを使用 (Gemini 2.0 Flash)

    @classmethod
    def setup_env(cls):
        """環境変数の同期"""
        os.environ["OPENAI_API_BASE"] = cls.OPENROUTER_BASE_URL
        os.environ["OPENAI_MODEL_NAME"] = cls.DEFAULT_MODEL
        
        # 安定性のための環境変数 (CrewAI/LiteLLM用)
        os.environ["LITELLM_LOG"] = "ERROR" # 冗長なログを抑制
        
        # OPENROUTER_API_KEY を OPENAI_API_KEY に同期
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # ログディレクトリの確保
        os.makedirs("logs/crewai", exist_ok=True)

    @classmethod
    def get_common_crew_params(cls):
        """Crewの共通パラメータを返す (安定化設定)"""
        return {
            "process": "sequential", 
            "memory": False,         
            "verbose": cls.VERBOSE,
            "max_rpm": cls.MAX_RPM,
            "max_execution_time": cls.MAX_EXEC_TIME
        }

    @classmethod
    def get_llm(cls, model_name=None):
        """指定されたモデル名のLLMインスタンスを返す"""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOpenAI
            except ImportError:
                from langchain.chat_models import ChatOpenAI
        
        model = model_name or cls.DEFAULT_MODEL
        return ChatOpenAI(
            model=model,
            base_url=cls.OPENROUTER_BASE_URL,
            api_key=os.environ.get("OPENAI_API_KEY")
        )
