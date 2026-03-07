import os
import re
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from crewai.tools import tool
from core.config import NeoConfig
from tools.memory_hygiene import ContextManager

# プロンプトの保存場所
PROMPT_DIR = "skills/get-shit-done/prompts"

# --- Task Parser & Dispatcher Logic ---
class TaskParser:
    """Parses a markdown ROADMAP.md and extracts task dependencies."""
    def __init__(self, roadmap_path="ROADMAP.md"):
        self.roadmap_path = roadmap_path

    def parse(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.roadmap_path):
            print(f"DEBUG: Roadmap file not found at {self.roadmap_path}")
            return []
            
        with open(self.roadmap_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tasks = []
        task_counter = 1
        lines = content.split('\n')
        
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith("- [ ]") or stripped_line.startswith("- [x]"):
                print(f"DEBUG: Found task: {stripped_line}")
                status = "completed" if stripped_line.startswith("- [x]") else "pending"
                raw_desc = stripped_line[5:].strip()
                
                # Extract Dependency Metadata
                depends_on = []
                dep_match = re.search(r'\[Depends on: (.*?)\]', raw_desc, re.IGNORECASE)
                
                clean_desc = raw_desc
                if dep_match:
                    deps_str = dep_match.group(1)
                    if deps_str.lower() != 'none':
                        depends_on = [d.strip() for d in deps_str.split(',')]
                    clean_desc = raw_desc.replace(dep_match.group(0), '').strip()
                
                task = {
                    "id": f"Task {task_counter}",
                    "desc": clean_desc,
                    "status": status,
                    "depends_on": depends_on,
                    "original_line": line # Keep original line for exact replacement
                }
                tasks.append(task)
                task_counter += 1
        return tasks

class ParallelDispatcher:
    """Manages task dependencies and returns executable tasks."""
    def __init__(self, tasks: List[Dict[str, Any]]):
        self.tasks = tasks
        self.completed_tasks = set(t['id'] for t in tasks if t['status'] == 'completed')

    def get_executable_tasks(self) -> List[Dict[str, Any]]:
        executable = []
        for task in self.tasks:
            if task['status'] == 'completed':
                continue
            
            dependencies_met = True
            for dep in task['depends_on']:
                # Heuristic: check if dependency matches any completed task ID or Description
                is_resolved = False
                
                # 1. Direct ID match (e.g., "Task 1")
                if dep in self.completed_tasks:
                    is_resolved = True
                
                # 2. Description match (e.g., "Research Agent" in "Task 1: Research Agent...")
                if not is_resolved:
                    for t in self.tasks:
                        if t['status'] == 'completed' and (dep in t['desc'] or dep in t['id']):
                            is_resolved = True
                            break
                
                if not is_resolved:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                executable.append(task)
        
        return executable

class GSDTool:
    """
    Get-Shit-Done (GSD) Framework Tool Adapter for OpenClaw.
    Manages project initialization, planning, and execution using GSD methodology.
    """
    def __init__(self):
        NeoConfig.setup_env()  # Initialize environment variables
        self.context_manager = ContextManager()
        # Initialize LLMs (Dual Architecture)
        self.planner_llm = NeoConfig.get_neo_llm(model_name=NeoConfig.MODEL_BRAIN)
        self.executor_llm = NeoConfig.get_agent_llm(model_name=NeoConfig.MODEL_HANDS)

    def _read_prompt(self, filename):
        path = os.path.join(PROMPT_DIR, filename)
        if not os.path.exists(path):
            return ""
        with open(path, 'r') as f:
            return f.read()

    def _save_file(self, filename, content):
        with open(filename, 'w') as f:
            f.write(content)
        print(f"Created/Updated: {filename}")

    def init_project(self, vision: str, goals: list):
        prompt_template = self._read_prompt("init_project.md")
        full_prompt = f"{prompt_template}\n\n# User Input\nVision: {vision}\nGoals: {', '.join(goals)}"
        
        print("GSD: Initializing project...")
        response = self.planner_llm.invoke([HumanMessage(content=full_prompt)]).content
        
        project_match = re.search(r"PROJECT\.md.*?\n+```(?:markdown)?\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
        roadmap_match = re.search(r"ROADMAP\.md.*?\n+```(?:markdown)?\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
        
        saved_files = []
        if project_match:
            self._save_file("PROJECT.md", project_match.group(1))
            saved_files.append("PROJECT.md")
        if roadmap_match:
            self._save_file("ROADMAP.md", roadmap_match.group(1))
            saved_files.append("ROADMAP.md")
            
        if not saved_files:
            return self.context_manager.compress_context(response, max_tokens=500)

        summary = f"Project initialized. Files created: {', '.join(saved_files)}.\n\nVision: {vision[:100]}..."
        return self.context_manager.compress_context(summary, max_tokens=500)

    def plan_phase(self):
        if not os.path.exists("ROADMAP.md") or not os.path.exists("PROJECT.md"):
            return "Error: Project files not found."
            
        with open("ROADMAP.md", 'r') as f: roadmap = f.read()
        with open("PROJECT.md", 'r') as f: project = f.read()

        prompt_template = self._read_prompt("plan_phase.md")
        full_prompt = f"{prompt_template}\n\n# Current State\n## PROJECT.md\n{project}\n\n## ROADMAP.md\n{roadmap}"
        
        print("GSD: Planning next phase...")
        response = self.planner_llm.invoke([HumanMessage(content=full_prompt)]).content
        
        plan_match = re.search(r"```(?:xml|markdown)?\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
        if plan_match:
            plan_content = plan_match.group(1)
            self._save_file("PLAN.md", plan_content)
            return self.context_manager.compress_context(f"Created PLAN.md:\n{plan_content}", max_tokens=1000)
        else:
            return self.context_manager.compress_context(f"Failed to extract plan.\n{response}", max_tokens=500)

    def execute_phase(self):
        if not os.path.exists("PLAN.md"):
            return "Error: PLAN.md not found."
        with open("PLAN.md", 'r') as f: plan = f.read()
            
        prompt_template = self._read_prompt("execute_phase.md")
        full_prompt = f"{prompt_template}\n\n# Current Plan\n{plan}"
        
        print("GSD: Executing phase...")
        response = self.executor_llm.invoke([HumanMessage(content=full_prompt)]).content
        self._save_file("EXECUTION_LOG.md", response)
        return self.context_manager.compress_context(response, max_tokens=2000)

    def get_parallel_tasks(self, roadmap_path="ROADMAP.md") -> List[Dict[str, Any]]:
        """
        Parses ROADMAP.md and returns a list of tasks ready for parallel execution.
        """
        parser = TaskParser(roadmap_path)
        tasks = parser.parse()
        dispatcher = ParallelDispatcher(tasks)
        return dispatcher.get_executable_tasks()

# Global GSD Tool Instance
_gsd_instance = GSDTool()

class GSDTools:
    @tool("Initialize Project")
    def init_project(input_str: str):
        """Initialize a new project or milestone. Input: 'Vision: ... Goals: ...'"""
        vision = "Project Vision"
        goals = ["Goal 1"]
        if "Vision:" in input_str:
            parts = input_str.split("Goals:")
            vision = parts[0].replace("Vision:", "").strip()
            if len(parts) > 1:
                goals = [g.strip() for g in parts[1].split(",")]
        return _gsd_instance.init_project(vision, goals)

    @tool("Plan Phase")
    def plan_phase(dummy: str):
        """Generate a detailed plan (PLAN.md). Input can be ignored."""
        return _gsd_instance.plan_phase()

    @tool("Execute Phase")
    def execute_phase(dummy: str):
        """Execute the current plan defined in PLAN.md. Input can be ignored."""
        return _gsd_instance.execute_phase()

    @tool("Get Parallel Tasks")
    def get_parallel_tasks(roadmap_path: str = "ROADMAP.md"):
        """Get a list of tasks from ROADMAP.md that are ready for parallel execution. Input: 'ROADMAP.md'"""
        # Note: CrewAI passes string arguments, ensure roadmap_path is correctly handled
        # If input is empty string or None, default to "ROADMAP.md"
        path = roadmap_path if roadmap_path and roadmap_path.strip() else "ROADMAP.md"
        return str(_gsd_instance.get_parallel_tasks(path))

def get_gsd_tools():
    return [
        GSDTools.init_project,
        GSDTools.plan_phase,
        GSDTools.execute_phase,
        GSDTools.get_parallel_tasks
    ]
