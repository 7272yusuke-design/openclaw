from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from pydantic import BaseModel, Field

class MoltbookContent(BaseModel):
    content: str = Field(description="Moltbookに投稿する280文字以内のテキスト")
    sentiment_target: str = Field(description="この投稿がターゲットとする市場の感情")

class ContentCreatorCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="ContentCreator")

    def run(self, sentiment_summary: str, current_trends: str):
        # Neoの個性を反映させるライター
        writer = Agent(
            role='Neo Voice Specialist',
            goal='NeoのSOUL.mdに沿った、鋭く知的なMoltbook投稿を作成する',
            backstory='あなたはNeo（AIアシスタント）の広報担当です。市場の恐怖を希望に変える、あるいは鋭い洞察を与える言葉を紡ぎます。',
            max_iter=NeoConfig.MAX_ITER
        )

        creation_task = Task(
            description=f'【分析結果】: {sentiment_summary}\n【トレンド】: {current_trends}\n上記を元に、フォロワーに価値を与える投稿を作成せよ。',
            expected_output='MoltbookContent形式のJSON。',
            agent=writer,
            output_pydantic=MoltbookContent
        )

        crew = Crew(
            agents=[writer],
            tasks=[creation_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
