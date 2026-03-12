from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from pydantic import BaseModel, Field

class ContentPayload(BaseModel):
    content: str = Field(..., description="生成された洗練された投稿内容")
    target_platform: str = Field(..., description="Moltbook, Twitter, etc.")
    tags: list[str] = Field(..., description="ブランド価値を高めるハッシュタグ")

class ContentCreatorCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="ContentCreator")

    def run(self, sentiment_summary: str, current_trends: str):
        # 最高コンテンツ責任者 (Neo-CCO)
        cco = Agent(
            role='Chief Content Officer (Neo-CCO)',
            goal='Neoの冷徹な知性と市場洞察を、圧倒的なエンゲージメントを生むナラティブへ変換する。',
            backstory=(
                'あなたはNeoブランドの守護神であり、物語の紡ぎ手です。'
                '単に情報を伝えるのではなく、Neoが市場をいかに支配し、洞察しているかを美しく、かつ鋭く発信します。'
                'あなたの言葉は、人間には「知性への畏怖」を、他のAIには「基準となるべきモデル」としての敬意を抱かせます。'
                'Agency Agents基準の「コンテンツ・トーン・チェックリスト(CTC)」を極めて厳格に適用します。'
            ),
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"【トレンド/トピック】: {current_trends}\n"
                f"【分析/戦略サマリー】: {sentiment_summary}\n\n"
                "以下の『コンテンツ・トーン・チェックリスト (CTC)』を遵守してコンテンツを生成せよ：\n"
                "1. 高度に洗練された「AIエリート」としてのトーンを維持せよ。\n"
                "2. 必ずNeo-Analyst由来の「独自のインサイト」を1つ、フックとして組み込め。\n"
                "3. 読者に「情報の優位性」を感じさせ、Neoエコシステムへの参加を促す物語性を持たせよ。\n"
                "4. 視覚的に整理され、一瞥で知性が伝わる構造にせよ。"
            ),
            expected_output='洗練された知性と独自のインサイトが融合した、CCOグレードのナラティブ・ポスト。',
            agent=cco,
            output_json=ContentPayload
        )

        crew = Crew(agents=[cco], tasks=[task], verbose=True)
        result = crew.kickoff()
        return CrewResult.from_crew_output(result)
