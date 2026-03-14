from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from pydantic import BaseModel, Field
import json
import logging

logger = logging.getLogger("neo.sentiment_agent")

class SentimentPayload(BaseModel):
    market_sentiment_score: float = Field(..., description="Fear/Greed score from -1.0 to 1.0")
    sentiment_label: str = Field(..., description="neutral, bullish, bearish, etc.")
    risk_factors: list[str] = Field(..., description="Key risks identified")

class SentimentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="SentimentAnalysis")

    def run(self, goal: str, context: str, constraints: str = "", web_search_tool=None) -> dict:
        """
        センチメント分析を実行し、dictを返す。
        Returns: {"market_sentiment_score": float, "sentiment_label": str, "risk_factors": list}
        """
        try:
            analyst = Agent(
                role='Market Sentiment Analyst',
                goal='Assess the psychological state of the market and assign a precise sentiment score.',
                backstory='Expert in crypto-psychology and social signal processing.',
                llm=self.llm,
                verbose=False
            )
            task = Task(
                description=(
                    f"Analyze market sentiment.\n"
                    f"Goal: {goal}\n"
                    f"Context: {context}\n"
                    f"Constraints: {constraints}\n\n"
                    f"Return ONLY a JSON object with keys: "
                    f"market_sentiment_score (float -1.0 to 1.0), "
                    f"sentiment_label (bullish/neutral/bearish), "
                    f"risk_factors (list of strings)."
                ),
                expected_output='JSON object with market_sentiment_score, sentiment_label, risk_factors.',
                agent=analyst,
            )
            crew = Crew(agents=[analyst], tasks=[task], verbose=False)
            result = crew.kickoff()
            raw = str(result)

            # JSON抽出を試みる
            try:
                # ```json ... ``` ブロックを除去
                clean = raw.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                parsed = json.loads(clean.strip())
                return {
                    "market_sentiment_score": float(parsed.get("market_sentiment_score", 0.0)),
                    "sentiment_label": str(parsed.get("sentiment_label", "neutral")),
                    "risk_factors": list(parsed.get("risk_factors", [])),
                }
            except Exception:
                # JSON解析失敗時はテキストからラベルを推定
                label = "neutral"
                if any(w in raw.lower() for w in ["bullish", "強気", "上昇"]):
                    label = "bullish"
                elif any(w in raw.lower() for w in ["bearish", "弱気", "下落"]):
                    label = "bearish"
                return {
                    "market_sentiment_score": 0.0,
                    "sentiment_label": label,
                    "risk_factors": ["センチメント解析は参考値"],
                }

        except Exception as e:
            logger.warning(f"[SentimentCrew] 失敗: {e}")
            raise
