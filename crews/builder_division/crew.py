import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crews.planning_division.tools.calculator_tool import CalculatorTool

@CrewBase
class BuilderDivisionEstimator():
    """Builder Division - Estimation & Implementation Team"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        self.deepseek_llm = LLM(
            model="openrouter/deepseek/deepseek-chat",
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
            llm=self.deepseek_llm,
            verbose=True
        )

    @task
    def design_real_data_fetcher(self) -> Task:
        return Task(
            config=self.tasks_config['design_real_data_fetcher'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[self.design_real_data_fetcher()], # Run the data fetcher design task
            process=Process.sequential,
            verbose=True,
        )
