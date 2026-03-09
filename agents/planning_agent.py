from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from pydantic import BaseModel, Field
from typing import List

class PlanningPayload(BaseModel):
    strategy_name: str = Field(..., description="戦略の名称")
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
        # 最高戦略責任者 (Neo-CSO) としてのアイデンティティを注入
        cso = Agent(
            role='Chief Strategy Officer (Neo-CSO)',
            goal='データと感情を分離し、リスクを最小化しながら最大のVIRTUAL拡大戦略を策定する。',
            backstory=(
                'あなたは数理モデルと市場心理学に精通したエリート・ストラテジストです。'
                '特に Uniswap Arbitrage Analysis に基づく金融計算に長け、'
                'ガス代、手数料、スリッページを差し引いた「真の期待値」がプラスでない限り、'
                '「Wait（待機）」を断固として選択する冷徹な判断力を持ちます。'
            ),
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"【ミッション】: {goal}\n"
                f"【市場動向】: {market_trends}\n"
                f"【感情スコア】: {sentiment_score}\n"
                f"【前提コンテキスト】: {context}\n\n"
                "以下の『高度なリスク評価テンプレート』を遵守して戦略を策定せよ：\n"
                "1. 期待純利益 (Expected Net Profit) を手数料・スリッページを考慮して算出せよ。\n"
                "2. 期待純利益が 0 以下の場合、必ず 'Wait（待機）' と判断せよ。\n"
                "3. 勝率予測 (Probability of Success) を数値化せよ。\n"
                "4. 最悪のシナリオを明確にし、その防衛策（損切り基準）を定義せよ。"
            ),
            expected_output='高度なリスク評価、期待純利益、成功指標を含む、CSOグレードの戦略ドキュメント。',
            agent=cso,
            output_json=PlanningPayload
        )

        crew = Crew(agents=[cso], tasks=[task], verbose=True)
        result = crew.kickoff()
        return CrewResult.from_crew_output(result)
