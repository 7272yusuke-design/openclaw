from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult, NeoStrategicPlan
from tools.deepwiki_tool import DeepWikiTool
from tools.obsidian_tool import ObsidianTool
from tools.technical_analysis_tool import TechnicalAnalysisTool

class PlanningCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="StrategicPlanning")

    def run(self, goal: str, context: str, sentiment_score: float = 0.0, market_trends: str = ""):
        # Define Tools
        deepwiki_tool = DeepWikiTool()
        obsidian_tool = ObsidianTool()
        ta_tool = TechnicalAnalysisTool()

        # 1. Risk Manager: Determine risk appetite based on market conditions
        risk_manager = Agent(
            role='Risk Manager',
            goal='Determine optimal risk appetite and operational limits based on market environment',
            backstory='Responsible for analyzing market fear and greed to set guardrails that protect and grow Neo\'s assets.',
            llm=NeoConfig.get_agent_llm(NeoConfig.MODEL_BRAIN),
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # 2. Strategic Planner: Formulate specific operational strategies
        planner = Agent(
            role='Strategic Planner',
            goal='Integrate Technical Analysis and DeepWiki to formulate data-driven operational strategies',
            backstory='A strategist who approaches from both market psychology (Sentiment) and market facts (TA/DeepWiki). Relies on RSI and Bollinger Bands rather than intuition.',
            tools=[deepwiki_tool, obsidian_tool, ta_tool],
            llm=NeoConfig.get_agent_llm(NeoConfig.MODEL_BRAIN),
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # 3. Strategic Auditor: Strictly audit strategy validity and risk
        auditor = Agent(
            role='Strategic Auditor',
            goal='Critically verify the Planner\'s strategy and check for overlooked risks or logical flaws',
            backstory='Former risk officer. Doubts optimistic predictions and assumes worst-case scenarios (Black Swans) to refine strategies.',
            llm=NeoConfig.get_agent_llm(NeoConfig.REASONING_MODEL),
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # Task Definitions
        risk_task_desc = f"""
        【Goal】: {goal}
        【Market Sentiment】: {sentiment_score} (-1.0: Extreme Fear, 1.0: Extreme Greed)
        【Market Trends】: {market_trends}
        【Context】: {context}

        Analyze the current market environment and formulate a "Risk Policy" including:
        1. Risk Appetite (Conservative / Moderate / Aggressive)
        2. Minimum Credit Rating (e.g., A, BBB, BB) for new loans
        3. Maximum LTV (Loan-to-Value) Ratio (e.g., 60%, 80%)
        4. Sector Allocation Advice (e.g., Focus on Gaming agents, Avoid DeFi agents)
        """
        
        risk_task = Task(
            description=risk_task_desc,
            expected_output='Risk Policy including risk appetite, min credit rating, max LTV, and sector allocation advice.',
            agent=risk_manager
        )

        strategy_task_desc = f"""
        Based on the Risk Policy from the Risk Manager, use the Technical Analysis Tool and DeepWiki Tool to conduct the following research and create a specific "Strategy Draft".
        
        1. **Technical Analysis (TA)**:
           - Execute the Technical Analysis Tool to get current RSI, Bollinger Bands, and EMA values.
           - Determine the signal with the following logic:
             - STRONG BUY: (Sentiment > 0.8) AND (RSI < 30 OR TA Signal == 'BUY/STRONG_BUY')
             - SELL: (Sentiment < 0.2) OR (TA Signal == 'SELL/STRONG_SELL')
             - HOLD: Divergence (Sentiment vs TA) or Neutral conditions.
        
        2. **DeepWiki Intelligence**:
           - Search for the target AI Agent's (especially AIXBT) technical foundation, team, and roadmap.
           - **IMPORTANT**: Append the research results (Deep Intelligence) to `vault/intelligence/deep_analysis.md` using the Obsidian Tool.
        
        3. **Strategy Formulation**:
           - Based on TA and DeepWiki results, set high-confidence entry points and take-profit targets.
        """

        strategy_task = Task(
            description=strategy_task_desc,
            expected_output='Strategy Draft including target sectors, DeepWiki research (recorded in Vault), specific action directives, and risk parameters.',
            agent=planner,
            context=[risk_task]
        )

        audit_task_desc = f"""
        Audit the Strategic Planner's strategy draft (especially the DeepWiki backing) and improve/correct it from the following perspectives:
        1. Is risk underestimated? (Technical vulnerabilities, roadmap delays)
        2. Is the strategy specific enough? (Can the ACP Executor execute without ambiguity?)
        3. Is there a contradiction between sentiment and action?
        
        【IMPORTANT】After the audit, output the "Finalized Strategy Directive" executable by ACP Executor and PaperTrader.
        Think as DeepSeek-R1 (Thought), and finally output ONLY the following JSON format.
        JSON must be enclosed in ```json ... ```.

        Elements to include (NeoStrategicPlan type):
        - risk_policy: {{"risk_appetite": "...", "min_rating": "...", "max_ltv": 0.65, "sector_advice": "..."}}
        - strategy: {{
            "target_sectors": [...], 
            "action_directive": "...", 
            "deepwiki_intelligence": "...",
            "arbitrage_opportunity": {{"dex_pair": "Virtuals-Uniswap", "expected_profit_pct": 0.85, "token": "VIRTUAL", "route": "..."}},
            "audit_summary": "..."
          }}
        """

        audit_task = Task(
            description=audit_task_desc,
            expected_output='Finalized Strategy Directive (NeoStrategicPlan object) after audit and correction.',
            agent=auditor,
            context=[strategy_task],
            output_pydantic=NeoStrategicPlan
        )

        # Crew Formation (Sequential)
        common_params = NeoConfig.get_common_crew_params()
        if "process" in common_params:
            del common_params["process"]

        crew = Crew(
            agents=[risk_manager, planner, auditor],
            tasks=[risk_task, strategy_task, audit_task],
            process=Process.sequential,
            **common_params
        )

        return self.execute(crew)
