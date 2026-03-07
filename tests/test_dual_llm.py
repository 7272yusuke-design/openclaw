import sys
import os
sys.path.append(os.getcwd())

from core.config import NeoConfig
from tools.memory_hygiene import ContextManager

def test_neo_llm_connection():
    print("--- Testing Neo LLM Connection (Google API) ---")
    NeoConfig.setup_env()
    
    # 1. Initialize ContextManager (uses get_neo_llm)
    cm = ContextManager()
    
    # 2. Test direct invocation
    try:
        print(f"Neo Model: {NeoConfig.NEO_MODEL}")
        print(f"Endpoint: {NeoConfig.GOOGLE_OPENAI_BASE_URL}")
        
        # Fake long text to trigger compression or direct invoke
        text = "This is a test message. " * 50
        print("Invoking compression (Neo LLM)...")
        # Force compression by setting very low max_tokens
        summary = cm.compress_context(text, max_tokens=10) 
        
        print(f"Summary Result: {summary[:100]}...")
        if "[SUMMARY]" in summary:
             print("✅ Neo LLM invoked successfully.")
        elif "[TRUNCATED ERROR]" in summary:
             print("❌ Neo LLM invocation failed (Error caught).")
        else:
             print("⚠️ Unexpected result format.")
             
    except Exception as e:
        print(f"❌ Neo LLM Connection Failed: {e}")

if __name__ == "__main__":
    test_neo_llm_connection()
