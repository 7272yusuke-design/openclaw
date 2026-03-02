from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult, NeoStrategicPlan

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

        # 3. Strategic Auditor: 戦略の妥当性とリスクを厳格に監査
        auditor = Agent(
            role='Strategic Auditor',
            goal='Plannerの戦略を批判的に検証し、リスクの見落としや論理的欠陥がないか確認する',
            backstory='元リスク管理責任者。Plannerの楽観的な予測を疑い、最悪のシナリオ（ブラックスワン）を想定して戦略を磨き上げる役割。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        # (Risk Assessment Task は変更なし)
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
        Risk Managerが策定したリスクポリシーに基づき、具体的な「戦略案」を作成せよ。
        """

        strategy_task = Task(
            description=strategy_task_desc,
            expected_output='ターゲットセクター、具体的行動指針、リスクパラメータを含む戦略案。',
            agent=planner,
            context=[risk_task]
        )

        # Strategy Audit & Refinement Task (Self-Reflection Loop)
        audit_task_desc = f"""
        Strategic Plannerの戦略案を監査し、以下の観点で改善・修正せよ:
        1. リスクの過小評価がないか（特に市場急変時のLTV超過リスク）
        2. 戦略に具体性があるか（ACP Executorが迷わないか）
        3. センチメントと行動に矛盾がないか
        4. 【新規】Scoutが報告したDEX間の価格乖離を精査し、手数料（0.3%〜）とスリッページを差し引いても 0.6% 以上の純利益が出るアービトラージ機会があるか検証せよ。

        【重要】監査を経て、最終的にACP ExecutorおよびPaperTraderが実行可能な「確定版戦略指令書」を出力せよ。
        DeepSeek-R1として思考（Thought）を行った後、最後に必ず以下のJSON形式のみを出力せよ。
        JSONは必ず ```json ... ``` で囲むこと。

        出力に含める要素 (NeoStrategicPlan型):
        - risk_policy: {{"risk_appetite": "...", "min_rating": "...", "max_ltv": 0.65, "sector_advice": "..."}}
        - strategy: {{
            "target_sectors": [...], 
            "action_directive": "...", 
            "arbitrage_opportunity": {{"dex_pair": "Virtuals-Uniswap", "expected_profit_pct": 0.85, "token": "VIRTUAL", "route": "..."}},
            "audit_summary": "..."
          }}
        """

        audit_task = Task(
            description=audit_task_desc,
            expected_output='監査と修正を経た確定版の戦略指令書（NeoStrategicPlanオブジェクト）。',
            agent=auditor,
            context=[strategy_task],
            output_pydantic=NeoStrategicPlan # Pydanticによる型出力を指定
        )

        # Crew編成 (Hierarchical Process を採用)
        crew = Crew(
            agents=[risk_manager, planner, auditor],
            tasks=[risk_task, strategy_task, audit_task],
            process=Process.hierarchical, # 階層型プロセスを有効化
            manager_llm=NeoConfig.get_llm("google/gemini-3-flash-preview"), # Neo自身がマネージャー
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
