import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.development_agent import DevelopmentCrew
from core.config import NeoConfig

def run_audit():
    print("--- 🛡️ Operation System Audit Initiated 🛡️ ---")
    print(f"Target Roadmap: ROADMAP.md")
    
    # Initialize Development Crew (Engineer)
    # Monkey patch NeoConfig to use 'openai/' prefix to avoid CrewAI Google Native Provider trigger
    original_get_agent_llm = NeoConfig.get_agent_llm
    
    def patched_get_agent_llm(model_name=None):
        llm = original_get_agent_llm(model_name)
        # Force model name to start with openai/ so CrewAI treats it as OpenAI-compatible
        if hasattr(llm, 'model_name') and not llm.model_name.startswith('openai/'):
             llm.model_name = "openai/" + llm.model_name
        return llm
        
    NeoConfig.get_agent_llm = patched_get_agent_llm
    
    dev_crew = DevelopmentCrew()
    
    # Execute Parallel Roadmap
    try:
        dev_crew.run_parallel_roadmap("ROADMAP.md")
        print("--- ✅ Operation System Audit Completed Successfully ---")
    except Exception as e:
        print(f"--- ❌ Operation System Audit Failed: {e} ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_audit()
