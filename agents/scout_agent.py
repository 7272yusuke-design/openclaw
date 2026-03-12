from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
import json
import os
from pydantic import BaseModel, Field
from core.base_crew import NeoBaseCrew
from tools.market_data import MarketData
from tools.indicators import NeoIndicators

class ScoutPayload(BaseModel):
    observed_fact: str = Field(..., description="発生した事象")
    technical_analysis: dict = Field(..., description="freqtradeベースのテクニカル指標(RSI, Trend, EMA等)")
    social_velocity: float = Field(..., description="熱量倍率")
    whale_movement: str = Field(..., description="クジラの動向 (Accumulating/Neutral/Selling)")
    liquidity_depth: dict = Field(..., description="流動性")
    causal_link: str = Field(..., description="原因特定")
    predicted_drift: str = Field(..., description="テクニカル根拠に基づく価格予測")
    alert_level: str = Field(..., description="Normal, Warning, Critical")

class MarketTool(BaseTool):
    name: str = "Enhanced Market Data Tool"
    description: str = "価格、指標、およびクジラの売買動向(whale_sentiment)を取得する。"
    def _run(self, query: str) -> str:
        data = MarketData.fetch_token_data(query)
        history = MarketData.fetch_ohlcv_custom(query)
        indicators = NeoIndicators.calculate_freqtrade_vibe(history)
        
        # 🛠️ 強化点: MarketDataから届いたクジラの判定を統合
        return json.dumps({
            "realtime": data,
            "technical": indicators,
            "whale_sentiment": data.get("whale_sentiment", "Neutral")
        })

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        self.custom_llm = LLM(
            model="openrouter/google/gemini-2.0-flash-001",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        super().__init__(name="EcosystemScout")

    def run(self, goal: str, context: str, **kwargs):
        analyst = Agent(
            role='Chief Technical Analyst (Neo-CTA)',
            goal='市場数値とクジラの動き(whale_sentiment)を統合し、真実を抽出する',
            backstory='あなたは数学的背景とオンチェーンの動向を読み解く勘を併せ持つアナリストです。日本語で出力せよ。',
            tools=[MarketTool()],
            llm=self.custom_llm,
            verbose=True,
            allow_delegation=False
        )

        task = Task(
            description=(
                f"Mission: {goal}\nContext: {context}\n"
                "最新の価格、テクニカル指標、およびクジラの動向(whale_sentiment)を分析せよ。\n"
                "特に『クジラの買い(Accumulating)』が検知されている場合は、その要因を深掘りして報告すること。"
            ),
            expected_output='クジラの動向を含む日本語の市場分析レポート(JSON形式)',
            agent=analyst,
            output_json=ScoutPayload
        )

        crew = Crew(agents=[analyst], tasks=[task], verbose=True)
        return crew.kickoff()
