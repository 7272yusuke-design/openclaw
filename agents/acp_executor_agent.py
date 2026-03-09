from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from pydantic import BaseModel, Field

class ACPPayload(BaseModel):
    action: str = Field(..., description="Action to perform (swap, stake, etc.)")
    token_address: str = Field(..., description="Target token address")
    amount_usd: float = Field(..., description="Amount in USD")
    validated: bool = Field(..., description="Is the transaction validated by the crew?")

class ACPExecutorCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="ACPExecutor")

    def run(self, strategy: str, context: str, credit_info: dict = None, sentiment_info: str = "Neutral"):
        executor = Agent(
            role='On-chain Execution Expert',
            goal='Execute risk-adjusted transactions based on strategic policies.',
            backstory='Expert in smart contracts and credit-based trading protocols.',
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"Strategy: {strategy}\n"
                f"Sentiment Info: {sentiment_info}\n"
                f"Credit Info: {credit_info}\n"
                f"Context: {context}"
            ),
            expected_output='A valid JSON payload for the Virtuals Protocol ACP.',
            agent=executor,
            output_json=ACPPayload
        )

        crew = Crew(agents=[executor], tasks=[task], verbose=True)
        result = crew.kickoff()
        return CrewResult.from_crew_output(result)
