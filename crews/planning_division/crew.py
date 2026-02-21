import os
import yaml
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from tools.calculator_tool import CalculatorTool
from tools.market_data_tool import MarketDataTool

@CrewBase
class PlanningDivisionCrew():
    """PlanningDivision crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        # OpenRouter経由のDeepSeek V3設定
        self.deepseek_llm = LLM(
            model="openrouter/deepseek/deepseek-chat",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        self.calc_tool = CalculatorTool()
        self.market_tool = MarketDataTool()

    @agent
    def lead_market_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['lead_market_analyst'],
            llm=self.deepseek_llm,
            tools=[self.market_tool], # 本物のデータツールを装備
            verbose=True
        )

    @agent
    def financial_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_analyst'],
            llm=self.deepseek_llm,
            tools=[self.calc_tool],
            verbose=True
        )

    @agent
    def creative_director(self) -> Agent:
        return Agent(
            config=self.agents_config['creative_director'],
            llm=self.deepseek_llm,
            verbose=True
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
        )

    @task
    def financial_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_analysis_task'],
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config['review_task'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
