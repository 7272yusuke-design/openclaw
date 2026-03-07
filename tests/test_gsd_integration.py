import sys
import os
sys.path.append(os.getcwd())

from tools.gsd_tool import TaskParser, ParallelDispatcher

def test_gsd_integration():
    print("--- Testing GSD Tool Integration ---")
    
    # 1. Create a temporary dummy ROADMAP.md
    dummy_roadmap = """
# Dummy Roadmap for Integration Test

## Phase 1
- [ ] Task A: Independent Task 1 [Depends on: None]
- [ ] Task B: Independent Task 2 [Depends on: None]
- [ ] Task C: Dependent Task [Depends on: Task A]
"""
    with open("TEST_ROADMAP.md", "w") as f:
        f.write(dummy_roadmap)
    
    # 2. Parse using the tool's parser
    parser = TaskParser("TEST_ROADMAP.md")
    tasks = parser.parse()
    
    print(f"Parsed Tasks: {[t['id'] for t in tasks]}")
    assert len(tasks) == 3
    
    # 3. Dispatch
    dispatcher = ParallelDispatcher(tasks)
    executable = dispatcher.get_executable_tasks()
    
    print(f"Executable Tasks: {[t['id'] for t in executable]}")
    
    # Task A and Task B should be executable
    ids = [t['id'] for t in executable]
    if "Task 1" in ids and "Task 2" in ids and "Task 3" not in ids:
        print("✅ Integration Test Passed: Task 1 and 2 are executable.")
    else:
        print(f"❌ Integration Test Failed. Executable: {ids}")

    # Cleanup
    os.remove("TEST_ROADMAP.md")

if __name__ == "__main__":
    test_gsd_integration()
