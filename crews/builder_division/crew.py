import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crews.planning_division.tools.calculator_tool import CalculatorTool

@CrewBase
class BuilderDivisionEstimator():
    """Builder Division - Estimation Team"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        self.deepseek_llm = LLM(
            model="openrouter/deepseek/deepseek-chat",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        # 実装用に Claude 3.5 Sonnet を設定
        self.claude_llm = LLM(
            model="openrouter/anthropic/claude-3.5-sonnet",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        self.calc_tool = CalculatorTool()

    @agent
    def technical_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['technical_architect'],
            llm=self.deepseek_llm,
            verbose=True
        )

    @agent
    def builder_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['builder_engineer'],
            llm=self.deepseek_llm, # DeepSeek V3 に差し戻し
            verbose=True
        )

    @task
    def technical_design_task(self) -> Task:
        return Task(
            config=self.tasks_config['technical_design_task'],
        )

    @task
    def implementation_task_step1(self) -> Task:
        return Task(
            config=self.tasks_config['implementation_task_step1'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
