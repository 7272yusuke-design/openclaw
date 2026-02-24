from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="EcosystemScout")

    def run(self, goal: str, context: str, constraints: str):
        scout = Agent(
            role='Ecosystem Scout',
            goal='Virtuals Protocol内の最新トレンドと機会を特定する',
            backstory='オンチェーンとSNSから真の価値を抽出するスカウト。',
            max_iter=NeoConfig.MAX_ITER
        )

        architect = Agent(
            role='ACP Architect',
            goal='機会をACP形式のペイロードに変換する',
            backstory='戦略を厳密なJSONに落とし込むエンジニア。',
            max_iter=NeoConfig.MAX_ITER
        )

        research_task = Task(
            description=f'目標: {goal}\n文脈: {context}',
            expected_output='具体的な3つの機会とアクション案。',
            agent=scout
        )

        acp_task = Task(
            description=f'制約: {constraints}\n最も優先度の高いアクションをACP形式にせよ。',
            expected_output='CrewResult形式のJSON。',
            agent=architect,
            context=[research_task],
            output_pydantic=CrewResult
        )

        # 共通パラメータをコピーし、階層型に設定
        params = NeoConfig.get_common_crew_params()
        params["process"] = Process.hierarchical

        crew = Crew(
            agents=[scout, architect],
            tasks=[research_task, acp_task],
            manager_agent=Agent(role='Manager', goal='全体監督', backstory='Neoの戦略監督。'),
            **params
        )

        return self.execute(crew)
