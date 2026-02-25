from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class PlanningCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="StrategicPlanning")

    def run(self, goal: str, context: str, sentiment_score: float = 0.0, market_trends: str = ""):
        # 1. Risk Manager: 市場環境に基づきリスク許容度を決定
        risk_manager = Agent(
            role='Risk Manager',
            goal='市場環境に基づき、最適なリスク許容度と運用制限を決定する',
            backstory='市場の恐怖と強欲を冷静に分析し、Neoの資産を守りつつ増やすためのガードレールを設定する責任者。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # 2. Strategic Planner: 具体的な運用戦略を策定
        planner = Agent(
            role='Strategic Planner',
            goal='リスク許容度に基づき、ACP Executorが実行すべき具体的な運用戦略を策定する',
            backstory='Virtuals Protocolの動向を捉え、どのエージェントセクターに資金を配分すべきかを決定する戦略家。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        # Risk Assessment Task
        risk_task_desc = f"""
        【目標】: {goal}
        【市場センチメント】: {sentiment_score} (-1.0: Extreme Fear, 1.0: Extreme Greed)
        【市場トレンド】: {market_trends}
        【コンテキスト】: {context}

        現在の市場環境を分析し、以下の項目を含む「リスクポリシー」を策定せよ:
        1. Risk Appetite (Conservative / Moderate / Aggressive)
        2. Minimum Credit Rating (e.g., A, BBB, BB) for new loans
        3. Maximum LTV (Loan-to-Value) Ratio (e.g., 60%, 80%)
        4. Sector Allocation Advice (e.g., Focus on Gaming agents, Avoid DeFi agents)
        """
        
        risk_task = Task(
            description=risk_task_desc,
            expected_output='リスク許容度、最低信用格付け、最大LTV、セクター配分アドバイスを含むリスクポリシー。',
            agent=risk_manager
        )

        # Strategy Formulation Task
        strategy_task_desc = f"""
        Risk Managerが策定したリスクポリシーに基づき、ACP Executorが実行可能な具体的な「戦略指令書」を作成せよ。
        出力はCrewResult形式のJSONとし、以下の要素を含めること:
        - target_sectors: 重点投資セクター
        - risk_policy: {{"min_rating": "...", "max_ltv": 0.8, ...}}
        - action_directive: 具体的な行動指針（例: "AA以上のエージェントへの流動性提供を優先"）
        """

        strategy_task = Task(
            description=strategy_task_desc,
            expected_output='CrewResult形式のJSONデータ（戦略指令書）。',
            agent=planner,
            context=[risk_task], # Risk Managerの出力を参照
            output_pydantic=CrewResult
        )

        # Crew編成 (Hierarchical Processは使用せず、Sequentialで連携)
        crew = Crew(
            agents=[risk_manager, planner],
            tasks=[risk_task, strategy_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
