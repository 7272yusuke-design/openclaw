import os
from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from tools.technical_analysis_tool import TechnicalAnalysisTool
from tools.deepwiki_tool import DeepWikiTool
from tools.obsidian_tool import ObsidianTool
from langchain_google_genai import ChatGoogleGenerativeAI
# Import the MemoryRetrieverTool
from tools.memory_retriever import search_memory # Assuming search_memory is a direct function


class TrinityCouncil(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="TrinityCouncil")
        # Define models
        self.flash_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            verbose=True,
            temperature=0.7,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        self.pro_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", # Fallback to Flash as Pro caused 404
            verbose=True,
            temperature=0.2,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

    def run(self, sentiment_score: float, context: str, target_symbol: str = "AIXBT"):
        # Tools
        ta_tool = TechnicalAnalysisTool()
        obsidian_tool = ObsidianTool()

        # Pre-discussion Research: Run MemoryRetriever
        # Dynamically generate keywords. For now, use target_symbol and common indicators.
        # This could be more sophisticated later, extracting indicators from the context itself.
        search_keywords = [target_symbol, "RSI divergence", "sentiment", "price action"]
        
        # Combine keywords into a single query string for search_memory (if it only takes one)
        # The current `search_memory` function takes a single keyword.
        # Let's make multiple calls and combine results, ensuring no duplicates.
        
        historical_precedents_raw = []
        seen_snippets = set()
        for keyword in search_keywords:
            results = search_memory(keyword=keyword, base_paths=["vault/intelligence", "memory"], context_lines=3)
            for item in results:
                if item['snippet'] not in seen_snippets:
                    historical_precedents_raw.append(item)
                    seen_snippets.add(item['snippet'])

        # Format the historical precedents for inclusion in the prompt
        formatted_precedents = ""
        if historical_precedents_raw:
            for item in historical_precedents_raw:
                formatted_precedents += f"--- Source: {item['path']} #L{item['line_number']} ---\n{item['snippet']}\n\n"
        else:
            formatted_precedents = "No specific historical precedents found for this context."


        # 1. Agent-A (Bullish): Sentiment & Narrative Focus
        agent_bull = Agent(
            role='Bullish Analyst (Agent-A)',
            goal='Analyze market sentiment and narrative momentum to find reasons to BUY.',
            backstory='You are an optimistic visionary who believes in the power of narratives and community sentiment (Memecoins/AI Agents). You focus on "Why this will go up".',
            llm=self.flash_model,
            allow_delegation=False,
            verbose=True
        )

        # 2. Agent-B (Bearish): TA & Risk Focus
        agent_bear = Agent(
            role='Bearish Analyst (Agent-B)',
            goal='Analyze technical indicators and risk factors to find reasons to SELL or WAIT.',
            backstory='You are a skeptical risk manager who trusts only data and charts. You focus on "Why this will crash" and "Where is the trap". You use TA tools extensively.',
            tools=[ta_tool],
            llm=self.flash_model,
            allow_delegation=False,
            verbose=True
        )

        # 3. Neo (Moderator): Final Verdict
        agent_neo = Agent(
            role='Neo (Council Moderator)',
            goal='Synthesize the debate between Bull and Bear, considering historical precedents, to make a final investment decision for {target_symbol}.', # Updated goal
            backstory='You are the Supreme Commander. You listen to both the optimist and the pessimist, then make the cold, calculated final decision. You prioritize long-term survival over short-term gambling. You critically evaluate current arguments against historical patterns to avoid repeating past mistakes.', # Updated backstory
            tools=[obsidian_tool],
            llm=self.pro_model,
            allow_delegation=False,
            verbose=True
        )

        # Task 1: Bullish Draft
        task_bull = Task(
            description=f"""
            Context: {context}
            Current Sentiment Score: {sentiment_score} (0.0=Fear, 1.0=Greed)
            Target Symbol: {target_symbol}

            Argue for a **BULLISH** stance on {target_symbol}.
            - Highlight the strength of the sentiment ({sentiment_score}).
            - Why is the divergence between Price and Sentiment a buying opportunity?
            - What is the "Narrative" upside?
            """,
            expected_output="A persuasive argument for buying/holding, focusing on sentiment and potential.",
            agent=agent_bull
        )

        # Task 2: Bearish Review & Counter-Argument
        task_bear = Task(
            description=f"""
            Context: {context}
            Target Symbol: {target_symbol}
            
            Review Agent-A's bullish argument.
            Use the **Technical Analysis Tool** to get the hard data (RSI, Bollinger, Trends) for {target_symbol}.
            
            Argue for a **BEARISH/CAUTIOUS** stance.
            - Expose the weakness in the "feelings-based" argument using data.
            - Highlight the specific risks in the chart.
            - Why is the divergence a "Bull Trap"?
            """,
            expected_output="A data-backed counter-argument focusing on risks and technical signals.",
            agent=agent_bear,
            context=[task_bull] # Depends on Bull's argument
        )

        # Task 3: Final Verdict (Consensus)
        task_verdict = Task(
            description=f"""
            Review the debate between Agent-A (Bull) and Agent-B (Bear).
            
            Current State:
            - Sentiment: {sentiment_score} (Strong)
            - Technicals: (Refer to Agent-B's findings)
            - Target Symbol: {target_symbol}

            ## Historical Precedents (from Memory Retriever)
            {formatted_precedents}

            Make the **Final Decision** (GO / NO-GO) for {target_symbol}.
            - Resolve the divergence: Is the sentiment leading the price, or is the price correcting the sentiment?
            - Define the Action: BUY, SELL, or WAIT?
            - Critically evaluate current arguments against the 'Historical Precedents' to avoid repeating past mistakes or to leverage successful patterns.
            - Set the specific Entry/Exit conditions.
            
            **IMPORTANT**: Save the "Council Minutes" to `vault/intelligence/council_minutes.md` using the Obsidian Tool.
            Format:
            # Trinity Council Minutes
            ## Historical Precedents (from Memory Retriever)
            (Summarize findings from the 'Historical Precedents' section above, applying them to the current decision)
            ---
            ## 1. Bullish Stance (Agent-A)
            ...
            ## 2. Bearish Stance (Agent-B)
            ...
            ## 3. Neo's Verdict
            - **Decision**: ...
            - **Reasoning**: ...
            - **Action Item**: ...
            """,
            expected_output="A final recorded verdict in markdown format, incorporating historical precedents, saved to the Vault.",
            agent=agent_neo,
            context=[task_bull, task_bear]
        )

        # Crew Execution
        council_crew = Crew(
            agents=[agent_bull, agent_bear, agent_neo],
            tasks=[task_bull, task_bear, task_verdict],
            process=Process.sequential,
            verbose=True
        )

        return council_crew.kickoff()

if __name__ == "__main__":
    # Test Run
    # Simulate a scenario where AIXBT shows strong sentiment but lagging price, similar to 2026-02-15 RSI divergence
    print("\n--- Running Trinity Council Simulation for AIXBT ---")
    council = TrinityCouncil()
    result = council.run(
        sentiment_score=0.85,
        context="AIXBT is showing strong community engagement but price action is lagging. There is a potential RSI divergence.",
        target_symbol="AIXBT"
    )
    print("\n--- Trinity Council Simulation Result ---")
    print(result)
