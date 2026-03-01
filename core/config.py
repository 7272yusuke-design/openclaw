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
    
    # 安全装置 (ガイドライン第5項)
    MAX_ITER = 5
    MAX_RPM = 10
    
    @classmethod
    def setup_env(cls):
        """環境変数の同期"""
        os.environ["OPENAI_API_BASE"] = cls.OPENROUTER_BASE_URL
        os.environ["OPENAI_MODEL_NAME"] = cls.DEFAULT_MODEL
        
        # OPENROUTER_API_KEY を OPENAI_API_KEY に同期
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # ログディレクトリの確保
        os.makedirs("logs/crewai", exist_ok=True)

    @classmethod
    def get_common_crew_params(cls):
        """Crewの共通パラメータを返す"""
        return {
            "process": "sequential", # 必要に応じて階層型に変更
            "memory": False,         # Embedding問題解決まで一時オフ
            "verbose": True,
            "max_rpm": cls.MAX_RPM
        }
