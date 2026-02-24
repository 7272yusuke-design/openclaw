from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class SentimentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="SentimentAnalysis")

    def run(self, goal: str, context: str, constraints: str):
        # エージェント定義
        analyst = Agent(
            role='Sentiment Analyst',
            goal='市場の感情スコアを特定し、トレンドの転換点を見極める',
            backstory='市場の「空気」を読み取る専門家。DeepSeek-V3により高度な分析を行います。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        planner = Agent(
            role='Strategic Action Planner',
            goal='分析を元に具体的なACPアクションを立案する',
            backstory='感情データを利益に変える戦略家。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        analysis_task = Task(
            description=f'分析目標: {goal}\nデータ: {context}',
            expected_output='市場の感情スコア(-1.0 to 1.0)と主要要因。',
            agent=analyst
        )

        action_task = Task(
            description=f'制約: {constraints}',
            expected_output='CrewResult形式のJSONデータ。',
            agent=planner,
            context=[analysis_task],
            output_pydantic=CrewResult
        )

        # Crew編成
        crew = Crew(
            agents=[analyst, planner],
            tasks=[analysis_task, action_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
