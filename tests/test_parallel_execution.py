import sys
import os
import re
import time
from typing import List, Dict, Any

# Mock CrewAI components for testing without actual LLM calls
class MockAgent:
    def __init__(self, role):
        self.role = role

class MockTask:
    def __init__(self, description, agent, async_execution=False, context=None):
        self.description = description
        self.agent = agent
        self.async_execution = async_execution
        self.context = context
        self.output = None

    def execute(self):
        # Simulate work
        time.sleep(1)
        self.output = f"Completed: {self.description}"
        return self.output

class TaskParser:
    """
    Parses a markdown formatted string (simulating ROADMAP.md) and extracts task dependencies.
    """
    def __init__(self, roadmap_content):
        self.roadmap_content = roadmap_content

    def parse(self) -> List[Dict[str, Any]]:
        tasks = []
        task_counter = 1
        lines = self.roadmap_content.split('\n')
        
        # Simple ID mapping: task_1, task_2... based on order
        # In a real implementation, we might want explicit IDs or hash-based IDs.
        
        for line in lines:
            line = line.strip()
            if line.startswith("- [ ]") or line.startswith("- [x]"):
                status = "completed" if line.startswith("- [x]") else "pending"
                
                # Remove checkbox marker
                raw_desc = line[5:].strip()
                
                # Extract Dependency Metadata: [Depends on: Task 1, Task 2]
                depends_on = []
                # Regex to find [Depends on: ...] at the end or within the string
                dep_match = re.search(r'\[Depends on: (.*?)\]', raw_desc, re.IGNORECASE)
                
                clean_desc = raw_desc
                if dep_match:
                    deps_str = dep_match.group(1)
                    if deps_str.lower() != 'none':
                        # Split by comma and strip whitespace
                        deps = [d.strip() for d in deps_str.split(',')]
                        # Map task names/descriptions to IDs if possible, 
                        # but here we'll assume the user writes "Task 1" which maps to our generated ID logic or name.
                        # For this prototype, we'll store the raw dependency string.
                        depends_on = deps
                    
                    # Remove metadata from description
                    clean_desc = raw_desc.replace(dep_match.group(0), '').strip()
                
                task = {
                    "id": f"Task {task_counter}", # Simple ID: "Task 1", "Task 2"
                    "desc": clean_desc,
                    "status": status,
                    "depends_on": depends_on
                }
                tasks.append(task)
                task_counter += 1
        return tasks

class ParallelDispatcher:
    """
    Manages task dependencies and returns executable tasks.
    """
    def __init__(self, tasks: List[Dict[str, Any]]):
        self.tasks = tasks
        self.completed_tasks = set(t['id'] for t in tasks if t['status'] == 'completed')

    def get_executable_tasks(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tasks that are:
        1. Pending
        2. Have all dependencies met (completed or None)
        """
        executable = []
        for task in self.tasks:
            if task['status'] == 'completed':
                continue
            
            dependencies_met = True
            for dep in task['depends_on']:
                # Dependency logic: Check if 'dep' (e.g., "Task 1") is in completed_tasks
                # This is a simple string match for the prototype.
                if dep not in self.completed_tasks:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                executable.append(task)
        
        return executable

    def mark_completed(self, task_id: str):
        self.completed_tasks.add(task_id)
        # Update internal state
        for t in self.tasks:
            if t['id'] == task_id:
                t['status'] = 'completed'


# --- Test Logic ---
def test_parallel_execution_logic():
    print("--- Testing Parallel Execution Logic ---")

    # 1. Define Dummy Roadmap with Dependencies
    roadmap_content = """
# Dummy Roadmap

## Phase 1
- [ ] Task 1: Research Agent Frameworks [Depends on: None]
- [ ] Task 2: Analyze Competitor Agents [Depends on: None]

## Phase 2
- [ ] Task 3: Write Comparison Report [Depends on: Task 1, Task 2]
    """
    
    print(f"Roadmap Content:\n{roadmap_content}")

    # 2. Parse Roadmap
    parser = TaskParser(roadmap_content)
    tasks = parser.parse()
    print(f"Parsed Tasks: {[t['id'] for t in tasks]}")

    # 3. Initialize Dispatcher
    dispatcher = ParallelDispatcher(tasks)
    
    # --- Iteration 1: Start ---
    print("\n[Iteration 1]")
    executable = dispatcher.get_executable_tasks()
    print(f"Executable Tasks: {[t['id'] for t in executable]}")
    
    # Expectation: Task 1 and Task 2 are executable (Parallel)
    assert "Task 1" in [t['id'] for t in executable]
    assert "Task 2" in [t['id'] for t in executable]
    assert "Task 3" not in [t['id'] for t in executable]
    print("✅ Verified: Task 1 and Task 2 are ready for parallel execution.")

    # Simulate Execution (Parallel)
    # In CrewAI, we would create tasks with async_execution=True and kickoff.
    print("Simulating parallel execution of Task 1 and Task 2...")
    dispatcher.mark_completed("Task 1")
    dispatcher.mark_completed("Task 2")

    # --- Iteration 2: After Phase 1 ---
    print("\n[Iteration 2]")
    executable_2 = dispatcher.get_executable_tasks()
    print(f"Executable Tasks: {[t['id'] for t in executable_2]}")

    # Expectation: Task 3 is now executable
    assert "Task 3" in [t['id'] for t in executable_2]
    assert len(executable_2) == 1
    print("✅ Verified: Task 3 is ready after dependencies met.")
    
    # Simulate Execution
    dispatcher.mark_completed("Task 3")
    
    # --- Iteration 3: Done ---
    print("\n[Iteration 3]")
    executable_3 = dispatcher.get_executable_tasks()
    if not executable_3:
        print("✅ All tasks completed.")

if __name__ == "__main__":
    test_parallel_execution_logic()
