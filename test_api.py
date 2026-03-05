from langchain_openai import ChatOpenAI
import os
from core.config import NeoConfig

def test_openrouter():
    # Setup environment variables using NeoConfig logic
    NeoConfig.setup_env()
    
    # Get values directly
    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = NeoConfig.OPENROUTER_BASE_URL
    model = "google/gemini-2.5-flash" # Use EYES model name as it should appear in ChatOpenAI
    
    print(f"Testing OpenRouter with:")
    print(f"  Model: {model}")
    print(f"  Base URL: {base_url}")
    print(f"  API Key: {api_key[:10]}...")
    
    try:
        llm = ChatOpenAI(
            model=model,
            openai_api_base=base_url,
            base_url=base_url,
            api_key=api_key
        )
        response = llm.invoke("Hello, are you there?")
        print("\nSuccess! Response:")
        print(response.content)
    except Exception as e:
        print(f"\nFailed: {e}")

if __name__ == "__main__":
    test_openrouter()
