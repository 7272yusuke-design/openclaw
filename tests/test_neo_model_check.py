import sys
import os
sys.path.append(os.getcwd())

from core.config import NeoConfig

def check_neo_model():
    print("--- Checking Neo LLM Model Configuration ---")
    NeoConfig.setup_env()
    
    neo_llm = NeoConfig.get_neo_llm()
    print(f"Neo LLM Model: {neo_llm.model_name}")
    print(f"Neo LLM Base URL: {neo_llm.client.base_url}")
    
    expected_model = "google/gemini-3-flash-preview"
    if neo_llm.model_name == expected_model:
        print(f"✅ Neo is using correct model: {expected_model}")
    else:
        print(f"❌ Neo is using incorrect model: {neo_llm.model_name}")

if __name__ == "__main__":
    check_neo_model()
