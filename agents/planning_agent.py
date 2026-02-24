from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class PlanningCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="StrategicPlanning")

    def run(self, goal: str, context: str):
        planner = Agent(
            role='Strategic Planner',
            goal='Neoのエージェント経済圏における価値最大化のための戦略を策定する',
            backstory='あなたはNeoの頭脳の一部です。Virtuals Protocolの動向を捉え、次に作るべき機能やエージェントの企画を立てます。',
            max_iter=NeoConfig.MAX_ITER
        )

        planning_task = Task(
            description=f'【目標】: {goal}\n【現状】: {context}\n新しいプロジェクトまたは機能の企画書を作成せよ。',
            expected_output='企画の概要、期待される収益性、および実装に必要なリソースのリスト。',
            agent=planner
        )

        crew = Crew(
            agents=[planner],
            tasks=[planning_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
