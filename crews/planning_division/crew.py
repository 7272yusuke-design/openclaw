import os
import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class PlanningDivisionCrew():
    """PlanningDivision crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def lead_market_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['lead_market_analyst'],
            verbose=True
        )

    @agent
    def financial_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_analyst'],
            verbose=True
        )

    @agent
    def creative_director(self) -> Agent:
        return Agent(
            config=self.agents_config['creative_director'],
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
