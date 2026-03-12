import os
import logging
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

class NeoConfig:
    # Model Aliases
    MODEL_BRAIN = "google/gemini-3-pro-preview" # or Claude 3.5 Sonnet via OpenRouter
    MODEL_EYES = "google/gemini-2.5-flash"
    MODEL_HANDS = "openai/gpt-4o"
    MODEL_CREATIVE = "google/gemini-3-flash-preview"
    
    DEFAULT_AGENT_MODEL = "google/gemini-3-flash-preview"
    NEO_CORE_MODEL = "google/gemini-3-flash-preview"

    @staticmethod
    def setup_env():
        """環境変数の初期化とバリデーション"""
        if not os.getenv("GOOGLE_API_KEY"):
            logging.warning("GOOGLE_API_KEY is not set.")
        if not os.getenv("OPENROUTER_API_KEY"):
            logging.warning("OPENROUTER_API_KEY is not set.")

def get_agent_llm(crew_name: str):
    """Crewごとの最適なLLMを取得する"""
    model_name = os.getenv("AGENT_MODEL_OVERRIDE", NeoConfig.DEFAULT_AGENT_MODEL)
    
    if "google" in model_name:
        return ChatGoogleGenerativeAI(model=model_name.split("/")[-1])
    else:
        return ChatOpenAI(
            model=model_name,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

def get_neo_llm():
    """司令官Neo自身のLLMを取得する"""
    return ChatGoogleGenerativeAI(model=NeoConfig.NEO_CORE_MODEL.split("/")[-1])
