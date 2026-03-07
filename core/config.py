import os
from langchain_openai import ChatOpenAI
from crewai import LLM

class NeoConfig:
    # --- Infrastructure Endpoints ---
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    GOOGLE_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # --- Model Definitions (3 Flash 固定) ---
    NEO_ORCHESTRATOR_MODEL = "gemini-3-flash"
    DEFAULT_AGENT_MODEL = "google/gemini-3-flash-preview"
    
    # 役割別設定
    MODEL_BRAIN = "google/gemini-2.0-pro-exp-02-05:free"
    MODEL_EYES = "google/gemini-3-flash-preview"
    MODEL_HANDS = "google/gemini-3-flash-preview"
    MODEL_CREATIVE = "google/gemini-3-flash-preview"
    REASONING_MODEL = "google/gemini-2.0-pro-exp-02-05:free"
    SUMMARY_MODEL = "gemini-3-flash"

    # システム設定
    MAX_ITER = 3
    MAX_RPM = 10
    MAX_EXEC_TIME = 300
    VERBOSE = False
    MAX_CONTEXT_TOKENS = 4000

    @staticmethod
    def get_neo_llm(model_name=None):
        model = model_name or NeoConfig.NEO_ORCHESTRATOR_MODEL
        return ChatOpenAI(
            model=model,
            openai_api_key=os.getenv("GEMINI_API_KEY"),
            openai_api_base=NeoConfig.GOOGLE_OPENAI_BASE_URL
        )

    @staticmethod
    def get_agent_llm(model_name=None):
        model = model_name or NeoConfig.DEFAULT_AGENT_MODEL
        full_model_name = f"openrouter/{model}" if not model.startswith("openrouter/") else model
        return LLM(
            model=full_model_name,
            base_url=NeoConfig.OPENROUTER_BASE_URL,
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    @classmethod
    def setup_env(cls):
        os.environ["OPENAI_API_BASE"] = cls.OPENROUTER_BASE_URL
        os.environ["OPENAI_MODEL_NAME"] = cls.DEFAULT_AGENT_MODEL
        os.environ["LITELLM_LOG"] = "ERROR"
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key: os.environ["OPENAI_API_KEY"] = api_key
        os.makedirs("logs/crewai", exist_ok=True)

    @classmethod
    def get_common_crew_params(cls):
        return {
            "process": "sequential",
            "memory": False,
            "verbose": cls.VERBOSE,
            "max_rpm": cls.MAX_RPM,
            "max_execution_time": cls.MAX_EXEC_TIME
        }

# 直接インポートする古いスクリプトへの互換性用
def get_neo_llm(model_name=None): return NeoConfig.get_neo_llm(model_name)
def get_agent_llm(model_name=None): return NeoConfig.get_agent_llm(model_name)
