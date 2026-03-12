from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from tools.code_interpreter import CodeInterpreter

class DevelopmentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="AgentDevelopment")

    def run(self, spec: str, language: str = "python", execution_logs: str = "", error_report: str = "", **kwargs):
        developer = Agent(
            role='Senior AI Software Architect',
            goal='Improve system integrity and implement self-evolution logic.',
            backstory='Expert in Python, AI orchestration, and automated CI/CD pipelines.',
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"Spec: {spec}\n"
                f"Target Language: {language}\n"
                f"Execution Logs: {execution_logs}\n"
                f"Error Report: {error_report}"
            ),
            expected_output='A clean code patch or an improvement analysis report.',
            agent=developer
        )

        crew = Crew(agents=[developer], tasks=[task], verbose=True)
        result = crew.kickoff()
        return CrewResult.from_crew_output(result)
