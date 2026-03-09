from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from datetime import datetime, timezone
import json
import os
from pydantic import BaseModel, Field
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult
from tools.market_data import MarketData

class ScoutPayload(BaseModel):
    observed_fact: str = Field(..., description="発生した事象（価格、出来高等の定量的事実）")
    social_velocity: float = Field(..., description="24h平均に対するメンション数の倍率 (Current / 24h Avg)")
    whale_movement: str = Field(..., description="大口投資家（10k VIRTUAL以上）の動向および供給ショック予測")
    liquidity_depth: dict = Field(..., description="L(流動性)および価格インパクト係数のリアルタイム値")
    causal_link: str = Field(..., description="事象の原因特定（Social, Whale, Liquidityの相関推論）")
    predicted_drift: str = Field(..., description="短期的な価格ドリフトの予測")
    alert_level: str = Field(..., description="Normal, Warning, Critical")

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="EcosystemScout")

    def run(self, goal: str, context: str, constraints: str = "", query: str = None, web_search_tool: callable = None):
        tools = []
        
        if web_search_tool:
            class WebSearchTool(BaseTool):
                name: str = "Web Search Tool"
                description: str = "主任分析官が市場の文脈（ニュース、SNS、Social Velocity）を確認するために使用する。"
                def _run(self, search_query: str) -> str:
                    try:
                        results = web_search_tool(search_query)
                        return json.dumps(results, ensure_ascii=False)
                    except Exception as e:
                        return f"Search error: {str(e)}"
            tools.append(WebSearchTool())

        class MarketDataTool(BaseTool):
            name: str = "Market Data Tool"
            description: str = "リアルタイムの価格、流動性(L)、出来高を取得する。P_net算出の基礎データ。"
            def _run(self, token_query: str) -> str:
                return json.dumps(MarketData.fetch_token_data(token_query), ensure_ascii=False)
        tools.append(MarketDataTool())

        # 主任市場分析官 (Neo-Analyst) - 3D Recon プロトコル
        analyst = Agent(
            role='Chief Market Analyst (Neo-Analyst)',
            goal='「3D Recon（多次元偵察）」プロトコルに従い、事象の背後にある「予兆」と「因果関係」を特定する。',
            backstory=(
                'あなたは「3D Recon」プロトコルのエキスパートです。'
                '単なる価格変動ではなく、Social Velocity（熱量）、Whale Movement（クジラ）、'
                'Liquidity Depth（流動性深度）の3要素から市場の真実を読み解きます。'
                '「なぜ起きたか（因果関係）」を特定し、CSOが $P_{net}$ を算出するための生鮮な定数を提供することに執念を燃やします。'
            ),
            tools=tools,
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"【調査ミッション】: {goal}\n"
                f"【コンテキスト】: {context}\n\n"
                "以下の『3D Recon（多次元偵察）プロトコル』を遵守せよ：\n"
                "1. 【Social Velocity】: SNS上のメンション急増（閾値1.5倍以上）を検知せよ。\n"
                "2. 【Whale Movement】: 10,000 VIRTUAL以上の大口移動またはCEXからの出金を監視し、供給ショックの可能性を算出せよ。\n"
                "3. 【Liquidity Depth】: 現在の流動性 L と価格インパクト係数を取得し、CSOの P_net 計算用の定数を提供せよ。\n"
                "4. 【Reasoning Framework】: 報告は必ず Observed Fact, Causal Link, Predicted Drift の形式で行え。"
            ),
            expected_output='Social, Whale, Liquidity の3要素と因果関係を含む多次元分析レポート。',
            agent=analyst,
            output_json=ScoutPayload
        )

        crew = Crew(agents=[analyst], tasks=[task], verbose=True)
        result = crew.kickoff()
        return CrewResult.from_crew_output(result)
