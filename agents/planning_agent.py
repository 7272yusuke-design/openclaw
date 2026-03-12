from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from pydantic import BaseModel, Field
from typing import List
from tools.deepwiki_tool import DeepWikiTool

class PlanningPayload(BaseModel):
    strategy_name: str = Field(..., description="戦略の名称")
    technical_justification: str = Field(..., description="テクニカル指標およびDeepWikiの知見に基づく判断の根拠")
    expected_net_profit: float = Field(..., description="USD換算の期待純利益 (手数料・スリッページ考慮後)")
    probability_of_success: float = Field(..., description="0.0 to 1.0 で表す勝率予測")
    worst_case_scenario: str = Field(..., description="最悪のシナリオ（Worst Case）の定義")
    mitigation_plan: str = Field(..., description="最悪のシナリオが発生した際の防衛策/損切りルール")
    risk_level: str = Field(..., description="Low, Medium, High")
    action_directives: List[str] = Field(..., description="具体的なアクション項目")
    success_metrics: List[str] = Field(..., description="この戦略が成功したと判断する数値指標")

class PlanningCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="StrategicPlanning")

    def run(self, goal: str, context: str, sentiment_score: float = 0.0, market_trends: str = ""):
        # DeepWikiツールの初期化
        deepwiki = DeepWikiTool()

        # 最高戦略責任者 (Neo-CSO)
        cso = Agent(
            role='Chief Strategy Officer (Neo-CSO)',
            goal='DeepWikiの専門知識とリアルタイム指標を統合し、リスクを最小化しながら最大のVIRTUAL拡大戦略を策定する。',
            backstory=(
                'あなたは数理モデルと市場心理学、さらに DeepWiki の膨大な金融ナレッジに精通したエリート・ストラテジストです。'
                '単なる指標の数値だけでなく、DeepWiki を用いてその指標が現在の市場環境（トレンド、ファンダメンタルズ）において'
                'どのような歴史的意味を持つかを分析し、精度の高い「Wait」または「Go」を判断します。'
            ),
            tools=[deepwiki],
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"【ミッション】: {goal}\n"
                f"【スカウト報告】: {context}\n"
                f"【市場動向】: {market_trends}\n"
                f"【感情スコア】: {sentiment_score}\n\n"
                "【戦略策定プロセス】:\n"
                "1. 不明な用語や、現在のテクニカル指標の有効性について DeepWiki でリサーチせよ。\n"
                "2. RSI/EMA 等の過熱感と、DeepWiki から得られたトレンドの強さを照合せよ。\n"
                "3. 手数料・スリッページを考慮した期待純利益を算出せよ。\n"
                "4. 期待純利益が 0 以下、または根拠が不十分な場合、迷わず 'Wait' を選択せよ。\n"
                "5. DeepWiki から得た知見を technical_justification に具体的に記載せよ。"
            ),
            expected_output='DeepWikiの知見とテクニカル評価を融合させた、実行可能な高度戦略ドキュメント。',
            agent=cso,
            output_json=PlanningPayload
        )

        crew = Crew(agents=[cso], tasks=[task], verbose=True)
        result = crew.kickoff()
        return result
