import os

class NeoConfig:
    """
    Neoのシステム全体で共有される設定クラス。
    ガイドラインに基づき、コストと安全性を制御する。
    """
    # LLM設定 (最善のモデルにアップデート)
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openrouter/deepseek/deepseek-chat" # DeepSeek-V3 (最新)
    REASONING_MODEL = "openrouter/deepseek/deepseek-r1" # 推論特化モデル
    
    # 安全装置 (安定化プロトコル v1.0)
    MAX_ITER = 3             # 無限ループ防止 (5→3に削減)
    MAX_RPM = 10             # APIレート制限遵守
    MAX_EXEC_TIME = 300      # 1タスク最大300秒 (5分)
    VERBOSE = False          # メインログの肥大化を抑制 (True→False)
    
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
