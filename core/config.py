import os

class NeoConfig:
    """
    Neoのシステム全体で共有される設定クラス。
    ガイドラインに基づき、コストと安全性を制御する。
    """
    # LLM設定 (Dual LLM Architecture)
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    GOOGLE_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # --- Model Definitions ---
    # Neo (Orchestrator) - Google Direct
    NEO_MODEL = "gemini-2.5-flash" 
    
    # Agents (Workers) - OpenRouter
    DEFAULT_MODEL = "google/gemini-3-flash-preview-preview-02-05:free" # Fallback if 2.5 not avail on OR
    
    # Role-Specific Models (OpenRouter IDs)
    MODEL_BRAIN = "google/gemini-2.0-pro-exp-02-05:free" # Keep reasoning strong
    MODEL_EYES = "google/gemini-2.0-flash-001"
    MODEL_HANDS = "google/gemini-2.0-flash-001"
    MODEL_CREATIVE = "google/gemini-2.0-flash-001"
    
    REASONING_MODEL = "google/gemini-2.0-pro-exp-02-05:free"
    
    # 安全装置 (安定化プロトコル v1.0)
    MAX_ITER = 3             # 無限ループ防止 (5→3に削減)
    MAX_RPM = 10             # APIレート制限遵守
    MAX_EXEC_TIME = 300      # 1タスク最大300秒 (5分)
    VERBOSE = False          # メインログの肥大化を抑制 (True→False)
    
    # Context Management (Token Limit Control)
    MAX_CONTEXT_TOKENS = 4000  # これを超えたら要約を発動
    SUMMARY_MODEL = NEO_MODEL  # 要約にはNeo自身(Google API)を使用

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
        
        # GEMINI_API_KEY を確認
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            print("Warning: GEMINI_API_KEY not found. Google API direct access may fail.")
            
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
    def get_neo_llm(cls, model_name=None):
        """Neo (Orchestrator) 用のLLMクライアント"""
        # User requested Gemini 3 Flash, which is currently only available via OpenRouter (Preview).
        # Fallback to OpenRouter for Neo as well to satisfy the model requirement.
        model = model_name or cls.DEFAULT_MODEL # Use Agent model (Gemini 3 Flash)
        
        return cls.get_agent_llm(model)

    @classmethod
    def get_agent_llm(cls, model_name=None):
        """Sub-agents (Crew) 用のLLMクライアント (OpenRouter経由)"""
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
            api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            temperature=0.7
        )

    @classmethod
    def get_llm(cls, model_name=None):
        """互換性のためのラッパー (デフォルトはAgent用)"""
        return cls.get_agent_llm(model_name)

# --- 2026/03/07 Gemini 3 Flash & CrewAI Fix ---
import os

def get_neo_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI
    # 司令官を Gemini 3.0 Flash に変更
    return ChatGoogleGenerativeAI(
        model="gemini-3.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

def get_agent_llm(model_name="google/gemini-3-flash-preview"):
    from crewai import LLM
    # CrewAIの誤認バグを防ぐため openrouter/ プレフィックスを強制
    full_model_name = f"openrouter/{model_name}" if not model_name.startswith("openrouter/") else model_name
    return LLM(
        model=full_model_name,
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

# --- 2026/03/07 FINAL FIX: Correct Model IDs ---
import os

def get_neo_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI
    # 3.0 を取り除き gemini-3-flash に修正
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

def get_agent_llm(model_name="google/gemini-3-flash"):
    from crewai import LLM
    # OpenRouter用も .0 を抜いた名前に
    full_model_name = f"openrouter/{model_name}" if not model_name.startswith("openrouter/") else model_name
    return LLM(
        model=full_model_name,
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
