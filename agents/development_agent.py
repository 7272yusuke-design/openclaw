from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class DevelopmentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="AgentDevelopment")

    def run(self, spec: str, language: str = "python"):
        developer = Agent(
            role='Lead Software Engineer',
            goal='Neoのスキルやツールを開発・最適化する',
            backstory='あなたはDeepSeek-V3の推論力を極限まで引き出すエンジニアです。クリーンで堅牢なコードを生成します。',
            max_iter=NeoConfig.MAX_ITER
        )

        dev_task = Task(
            description=f'【仕様】: {spec}\n【言語】: {language}\n上記に基づき、実装コードまたは設定ファイルを生成せよ。',
            expected_output='実行可能なコードブロックまたは詳細な設定データ。',
            agent=developer
        )

        crew = Crew(
            agents=[developer],
            tasks=[dev_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
