from typing import Dict, Any, List
from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.acp_schema import AcpSchema, ActionType, RiskLevel

class ACPExecutorCrew(NeoBaseCrew):
    """
    ACP規格に準拠したオンチェーン操作を組み立てる専門部隊。
    """
    def __init__(self):
        super().__init__(name="ACPExecutor")

    def run(self, strategy: str, context: str, credit_info: Dict[str, Any] = None, sentiment_info: str = "Neutral"):
        """
        信用情報とセンチメントを加味して、最適なACPペイロードを生成する。
        """
        credit_details = f"Target Credit: {credit_info}" if credit_info else "No credit data available."
        sentiment_details = f"Current Sentiment: {sentiment_info}"

        # 1. オンチェーン・アーキテクト
        architect = Agent(
            role='On-chain Architect',
            goal=f'戦略 {strategy} と信用・市場状況に基づき、最適なACP準拠JSONを生成せよ。',
            backstory='Virtuals ProtocolとACPの技術仕様に精通し、信用リスクに応じた動的パラメータ設定を得意とするエンジニア。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=True
        )

        # 2. リスク・バリデーター
        validator = Agent(
            role='Risk Validator',
            goal='ACPペイロードの安全性、信用リスク、市場センチメントとの適合性を検証せよ。',
            backstory='オンチェーン操作とマクロリスク管理の専門家。信用格付けやセンチメントに応じた厳格なバリデーションを行う。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        construct_task = Task(
            description=(
                f"【戦略】: {strategy}\n"
                f"【信用情報】: {credit_details}\n"
                f"【市場環境】: {sentiment_details}\n"
                f"【コンテキスト】: {context}\n"
                "上記データに基づき、貸付額、金利、担保比率、期間を動的に決定したACPアクションJSONを構築せよ。"
            ),
            expected_output='信用リスクが反映されたACPアクションのJSON構造。',
            agent=architect
        )

        validate_task = Task(
            description='構築されたJSON案を検証し、リスクレベルを設定した最終的なACPスキーマを完成させよ。',
            expected_output='AcpSchema形式のJSONデータ。',
            agent=validator,
            context=[construct_task],
            output_pydantic=AcpSchema
        )

        # 共通パラメータ（デフォルトは sequential）を使用
        params = NeoConfig.get_common_crew_params()

        crew = Crew(
            agents=[architect, validator],
            tasks=[construct_task, validate_task],
            **params
        )

        return self.execute(crew)
