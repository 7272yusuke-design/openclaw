import os
import re
from langchain_core.messages import HumanMessage
from core.config import NeoConfig
from tools.memory_hygiene import ContextManager

# プロンプトの保存場所
PROMPT_DIR = "skills/get-shit-done/prompts"

class GSDTool:
    """
    Get-Shit-Done (GSD) Framework Tool Adapter for OpenClaw.
    Manages project initialization, planning, and execution using GSD methodology.
    """
    def __init__(self):
        self.context_manager = ContextManager()
        # Initialize LLMs
        self.planner_llm = NeoConfig.get_llm(model_name=NeoConfig.MODEL_BRAIN) # Brain (Claude) for planning
        self.executor_llm = NeoConfig.get_llm(model_name=NeoConfig.MODEL_HANDS) # Hands (GPT-4o) for execution

    def _read_prompt(self, filename):
        path = os.path.join(PROMPT_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, 'r') as f:
            return f.read()

    def _save_file(self, filename, content):
        with open(filename, 'w') as f:
            f.write(content)
        print(f"Created/Updated: {filename}")

    def init_project(self, vision: str, goals: list):
        """
        Initializes a new GSD project.
        Creates PROJECT.md and ROADMAP.md based on vision and goals.
        """
        prompt_template = self._read_prompt("init_project.md")
        full_prompt = f"{prompt_template}\n\n# User Input\nVision: {vision}\nGoals: {', '.join(goals)}"
        
        print("GSD: Initializing project...")
        response = self.planner_llm.invoke([HumanMessage(content=full_prompt)]).content
        print("GSD: LLM Response received.")
        print(f"DEBUG Response Snippet: {response[:200]}...")
        
        # Parse output (More flexible regex)
        # Try finding ```markdown (optional) blocks after headers
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
            print("Warning: Could not parse PROJECT.md or ROADMAP.md from LLM response.")
            return self.context_manager.compress_context(response, max_tokens=500)

        # Return a summary via ContextManager
        summary = f"Project initialized. Files created: {', '.join(saved_files)}.\n\nVision: {vision[:100]}..."
        return self.context_manager.compress_context(summary, max_tokens=500)

    def plan_phase(self):
        """
        Generates a detailed plan (PLAN.md) for the current phase in ROADMAP.md.
        """
        if not os.path.exists("ROADMAP.md"):
            return "Error: ROADMAP.md not found. Run init_project first."
        if not os.path.exists("PROJECT.md"):
            return "Error: PROJECT.md not found. Run init_project first."
            
        with open("ROADMAP.md", 'r') as f:
            roadmap = f.read()
        with open("PROJECT.md", 'r') as f:
            project = f.read()

        prompt_template = self._read_prompt("plan_phase.md")
        full_prompt = f"{prompt_template}\n\n# Current State\n## PROJECT.md\n{project}\n\n## ROADMAP.md\n{roadmap}"
        
        print("GSD: Planning next phase...")
        response = self.planner_llm.invoke([HumanMessage(content=full_prompt)]).content
        print("GSD: LLM Response received (Planning).")
        print(f"DEBUG Plan Response: {response[:200]}...")
        
        # Extract PLAN.md content (Flexible)
        plan_match = re.search(r"```(?:xml|markdown)?\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
        
        if plan_match:
            plan_content = plan_match.group(1)
            self._save_file("PLAN.md", plan_content)
            return self.context_manager.compress_context(f"Created PLAN.md:\n{plan_content}", max_tokens=1000)
        else:
            return self.context_manager.compress_context(f"Failed to extract plan. Raw response:\n{response}", max_tokens=500)

    def execute_phase(self):
        """
        Executes the tasks defined in PLAN.md.
        Generates code and verification steps.
        """
        if not os.path.exists("PLAN.md"):
            return "Error: PLAN.md not found. Run plan_phase first."
            
        with open("PLAN.md", 'r') as f:
            plan = f.read()
            
        prompt_template = self._read_prompt("execute_phase.md")
        full_prompt = f"{prompt_template}\n\n# Current Plan\n{plan}"
        
        print("GSD: Executing phase...")
        # Use Executor model for code generation
        response = self.executor_llm.invoke([HumanMessage(content=full_prompt)]).content
        print("GSD: LLM Response received (Execution).")
        
        # Save execution log
        self._save_file("EXECUTION_LOG.md", response)
        
        return self.context_manager.compress_context(response, max_tokens=2000)

def get_gsd_tools():
    """
    Returns a list of LangChain Tools for GSD operations.
    Used by CrewAI agents.
    """
    from langchain_core.tools import Tool
    gsd = GSDTool()
    
    def init_wrapper(input_str):
        # Simple parsing for string input
        # Expected: "Vision: ..., Goals: ..."
        vision = "Project Vision"
        goals = ["Goal 1"]
        if "Vision:" in input_str:
            parts = input_str.split("Goals:")
            vision = parts[0].replace("Vision:", "").strip()
            if len(parts) > 1:
                goals = [g.strip() for g in parts[1].split(",")]
        return gsd.init_project(vision, goals)

    return [
        Tool(
            name="GSD_Init_Project",
            func=init_wrapper,
            description="Initialize a new project or milestone. Input string must contain 'Vision: ... Goals: ...'"
        ),
        Tool(
            name="GSD_Plan_Phase",
            func=lambda x: gsd.plan_phase(),
            description="Generate a detailed plan (PLAN.md) for the current phase based on ROADMAP.md. Input: empty string."
        ),
        Tool(
            name="GSD_Execute_Phase",
            func=lambda x: gsd.execute_phase(),
            description="Execute the current plan defined in PLAN.md. Generates code. Input: empty string."
        )
    ]
