import os
from crewai import LLM

class NeoConfig:
    DEFAULT_AGENT_MODEL = "openrouter/google/gemini-2.0-flash-001"
    MODEL_EYES = DEFAULT_AGENT_MODEL
    MODEL_BRAIN = DEFAULT_AGENT_MODEL
    MODEL_CREATIVE = DEFAULT_AGENT_MODEL
    MODEL_HANDS = DEFAULT_AGENT_MODEL

    @staticmethod
    def setup_env():
        pass

def get_agent_llm(name=None):
    # すべてのエージェントに OpenRouter 経由の LLM を強制配布
    return LLM(
        model=NeoConfig.DEFAULT_AGENT_MODEL,
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )

def get_neo_llm():
    return get_agent_llm()
