import sys
import os
import time
sys.path.append(os.getcwd())

from agents.development_agent import DevelopmentCrew
from core.config import NeoConfig

# tools.gsd_tool is imported inside the method, so path needs to be correct

def test_parallel_dispatch():
    print("--- Testing Parallel Dispatch Loop ---")
    
    # Patch NeoConfig to prevent CrewAI from trying to load Google Native Provider
    # We use a standard OpenAI model name for the mock agent, as execution is mocked anyway.
    original_get_agent_llm = NeoConfig.get_agent_llm
    NeoConfig.get_agent_llm = lambda model_name=None: "gpt-3.5-turbo"
    
    # Also patch get_neo_llm because GSDTool uses it
    NeoConfig.get_neo_llm = lambda model_name=None: "gpt-3.5-turbo"
    
    # 1. Create Dummy ROADMAP.md
    roadmap_path = "TEST_ROADMAP_PARALLEL.md"
    dummy_roadmap = """
# Dummy Parallel Roadmap

## Phase 1
- [ ] Task 1: Create file A.txt with content 'Hello A' [Depends on: None]
- [ ] Task 2: Create file B.txt with content 'Hello B' [Depends on: None]

## Phase 2
- [ ] Task 3: Create file C.txt with content 'Done AB' [Depends on: Task 1, Task 2]
    """
    with open(roadmap_path, 'w') as f:
        f.write(dummy_roadmap)
        
    # Monkey-patching Crew.kickoff for simulation
    # We want to verify that Task 1 and Task 2 are dispatched in the first loop iteration,
    # and Task 3 in the second.
    
    from crewai import Crew
    original_kickoff = Crew.kickoff
    
    def simulated_kickoff(self, inputs=None):
        print(f"👻 [Simulated] Kickoff called with {len(self.tasks)} tasks (incl. aggregator).")
        
        # Extract async tasks (excluding aggregator)
        async_tasks = [t for t in self.tasks if t.async_execution]
        print(f"  -> Async Tasks: {len(async_tasks)}")
        
        for task in async_tasks:
            desc = task.description
            if "A.txt" in desc:
                with open("A.txt", "w") as f: f.write("Hello A")
                print("    -> Executing Task A (Simulated Async)")
            elif "B.txt" in desc:
                with open("B.txt", "w") as f: f.write("Hello B")
                print("    -> Executing Task B (Simulated Async)")
            elif "C.txt" in desc:
                # Check dependencies
                if os.path.exists("A.txt") and os.path.exists("B.txt"):
                    with open("C.txt", "w") as f: f.write("Done AB")
                    print("    -> Executing Task C (Dependencies met)")
                else:
                    print("    -> ❌ Failed Task C (Dependencies missing!)")
        
        return "Simulated Success"

    Crew.kickoff = simulated_kickoff
    
    try:
        dev_crew = DevelopmentCrew()
        # Mocking gsd_tools to avoid initialization error if tools missing
        dev_crew.gsd_tools = [] 
        
        dev_crew.run_parallel_roadmap(roadmap_path)
        
        # 3. Verify Results
        print("\n--- Verification ---")
        if os.path.exists("A.txt") and os.path.exists("B.txt"):
            print("✅ Phase 1 (Parallel) Complete: A.txt and B.txt exist.")
        else:
            print("❌ Phase 1 Failed.")
            
        if os.path.exists("C.txt"):
            print("✅ Phase 2 (Dependent) Complete: C.txt exists.")
        else:
            print("❌ Phase 2 Failed.")
            
    finally:
        # Cleanup
        Crew.kickoff = original_kickoff
        if os.path.exists(roadmap_path): os.remove(roadmap_path)
        if os.path.exists("A.txt"): os.remove("A.txt")
        if os.path.exists("B.txt"): os.remove("B.txt")
        if os.path.exists("C.txt"): os.remove("C.txt")

if __name__ == "__main__":
    test_parallel_dispatch()
