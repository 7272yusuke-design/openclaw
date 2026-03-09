from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from pydantic import BaseModel, Field

class SentimentPayload(BaseModel):
    market_sentiment_score: float = Field(..., description="Fear/Greed score from -1.0 to 1.0")
    sentiment_label: str = Field(..., description="neutral, bullish, bearish, etc.")
    risk_factors: list[str] = Field(..., description="Key risks identified")

class SentimentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="SentimentAnalysis")

    def run(self, goal: str, context: str, constraints: str, web_search_tool: callable = None):
        analyst = Agent(
            role='Market Sentiment Analyst',
            goal='Assess the psychological state of the market and assign a precise sentiment score.',
            backstory='Expert in crypto-psychology and social signal processing.',
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=f"Analyze market sentiment based on:\nGoal: {goal}\nContext: {context}",
            expected_output='A structured sentiment analysis report including a score between -1.0 and 1.0.',
            agent=analyst,
            output_json=SentimentPayload
        )

        crew = Crew(agents=[analyst], tasks=[task], verbose=True)
        result = crew.kickoff()
        return CrewResult.from_crew_output(result)
