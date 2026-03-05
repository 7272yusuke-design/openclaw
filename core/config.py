import os

class NeoConfig:
    """
    Neoのシステム全体で共有される設定クラス。
    ガイドラインに基づき、コストと安全性を制御する。
    """
    # OpenRouter API Base URL
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # --- Model Definitions (Optimization Strategy) ---
    # Default (General Purpose - Neo Orchestrator uses Google AI Studio Direct)
    DEFAULT_MODEL = "gemini/gemini-2.5-flash"  # Switched to 2.5 Flash for stability and limits
    
    # Role-Specific Models (Enforcing the requested hybrid architecture via OpenRouter)
    MODEL_BRAIN = "openrouter/anthropic/claude-3.5-sonnet"        # Strategic Planning, Dev (Logic/Code)
    MODEL_EYES = "openrouter/google/gemini-2.5-flash"             # Scout, Sentiment (Context/Speed)
    MODEL_HANDS = "openrouter/openai/gpt-4o"                      # Executor, ACP Architect (Tool use/JSON)
    MODEL_CREATIVE = "openrouter/anthropic/claude-3.5-sonnet"     # Content Creator (Writing nuance)
    
    REASONING_MODEL = "openrouter/openai/o1-mini"                 # Strategic Auditor (Pure Logic)
    
    # Notification
    DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1478693375090622559/f0AwGgXAWkyGWOZVk5LLI9A1MKYQBvzmdSGoc3crPNMZ2mCaJEe-JIbF9ATuAsQp8Ioe"

    # 安全装置 (安定化プロトコル v1.0)
    MAX_ITER = 3             # 無限ループ防止 (5→3に削減)
    MAX_RPM = 10             # APIレート制限遵守
    MAX_EXEC_TIME = 300      # 1タスク最大300秒 (5分)
    VERBOSE = False          # メインログの肥大化を抑制
    
    @classmethod
    def setup_env(cls):
        """環境変数の同期とOpenRouterへの物理的固定"""
        # OpenRouterを唯一のエンドポイントとして強制
        os.environ["OPENAI_API_BASE"] = cls.OPENROUTER_BASE_URL
        
        # 混乱の元となるキーをOpenRouterのキーで完全に上書き
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key
            # LiteLLM/CrewAI用のプレフィックス指定
            os.environ["OPENAI_MODEL_NAME"] = cls.DEFAULT_MODEL
        
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
        # Import conditionally to avoid overhead or errors if packages missing
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            pass
            
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOpenAI
            except ImportError:
                from langchain.chat_models import ChatOpenAI
        
        target_model = model_name or cls.DEFAULT_MODEL

        # --- Case A: Google AI Studio Direct API (gemini/ prefix) ---
        # Neo本体で使用。Googleの無料枠/高速枠を利用するため直接アクセス。
        if target_model.startswith("gemini/") and "openrouter" not in target_model:
            if not os.environ.get("GOOGLE_API_KEY"):
                print("[Config] Critical: GOOGLE_API_KEY missing. Falling back to OpenRouter.")
            else:
                try:
                    # 'gemini/gemini-3-flash' -> 'gemini-3-flash'
                    clean_name = target_model.split("/")[-1]
                    return ChatGoogleGenerativeAI(
                        model=clean_name,
                        google_api_key=os.environ.get("GOOGLE_API_KEY"),
                        convert_system_message_to_human=True,
                        temperature=0.7
                    )
                except ImportError:
                    print("[Config] langchain_google_genai not installed. Using OpenRouter fallback.")

        # --- Case B: OpenRouter via ChatOpenAI ---
        # プレフィックスを維持し、LiteLLMがOpenRouterを確実に認識するようにする
        final_model_name = target_model
        if not final_model_name.startswith("openrouter/"):
            final_model_name = f"openrouter/{final_model_name}"
        
        # 不要なprovider名の重複を避ける (例: openrouter/openrouter/ -> openrouter/)
        final_model_name = final_model_name.replace("openrouter/openrouter/", "openrouter/")

        return ChatOpenAI(
            model=final_model_name,
            base_url=cls.OPENROUTER_BASE_URL,
            api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "https://openclaw.ai",
                "X-Title": "Neo Autonomous Agent"
            }
        )
