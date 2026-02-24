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

    def run(self, strategy: str, context: str):
        # 1. オンチェーン・アーキテクト：ACPペイロードの構築
        architect = Agent(
            role='On-chain Architect',
            goal=f'戦略 {strategy} に基づき、Virtuals Protocol ACP準拠のJSONを生成せよ。',
            backstory='Virtuals ProtocolとACPの技術仕様に精通したエンジニア。正確なJSONを組み立てます。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=True
        )

        # 2. リスク・バリデーター：安全性の最終確認
        validator = Agent(
            role='Risk Validator',
            goal='生成されたACPペイロードの安全性とリスクレベル（Low/Medium/High）を検証せよ。',
            backstory='オンチェーン操作のリスク管理の専門家。スリッページや金額設定が適切かチェックします。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        construct_task = Task(
            description=f'【戦略】: {strategy}\n【コンテキスト】: {context}\n具体的なACPアクションのJSON案を構築せよ。',
            expected_output='ACPアクションのJSON構造。',
            agent=architect
        )

        validate_task = Task(
            description='構築されたJSON案を検証し、リスクレベルを設定した最終的なACPスキーマを完成させよ。',
            expected_output='AcpSchema形式のJSONデータ。',
            agent=validator,
            context=[construct_task],
            output_pydantic=AcpSchema
        )

        # Crew編成
        crew = Crew(
            agents=[architect, validator],
            tasks=[construct_task, validate_task],
            process=Process.hierarchical,
            manager_agent=Agent(role='Manager', goal='運用の監督', backstory='Neoの戦略監督。'),
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
