```python
# Task: Refactor Argument Passing in neo_main.py
# File: neo_main.py
import argparse
import json
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from src.agents.researcher_agent import ResearcherAgent
from src.agents.sales_agent import SalesAgent
from src.crews.sentiment_crew import SentimentCrew
from src.utils.config_loader import ConfigLoader

load_dotenv()

# Configure logger
logger.add("logs/neo.log", rotation="10 MB", level="TRACE")

def main(raw_data, social_context, product_description, dry_run=False):
    """
    Main function to orchestrate the agents and crew.
    """
    logger.info("Starting Neo Agent...")

    # Initialize agents
    researcher = ResearcherAgent()
    sales_agent = SalesAgent()

    # Prepare SentimentCrew input
    sentiment_crew_input = {
        "raw_data": raw_data,
        "social_context": social_context,
        "product_description": product_description,
    }

    # Initialize SentimentCrew
    sentiment_crew = SentimentCrew()

    # Execute SentimentCrew
    if not dry_run:
        sentiment_result = sentiment_crew.kickoff(inputs=sentiment_crew_input)
        logger.info(f"Sentiment Crew Result: {sentiment_result}")
    else:
        logger.info("Dry run mode: SentimentCrew execution skipped.")
        sentiment_result = None

    # Example usage of Researcher and Sales Agents (replace with actual logic)
    research_summary = researcher.run(product_description)
    sales_pitch = sales_agent.run(research_summary, sentiment_result)

    logger.info(f"Research Summary: {research_summary}")
    logger.info(f"Sales Pitch: {sales_pitch}")

    logger.info("Neo Agent execution complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neo Agent CLI")
    parser.add_argument("--raw_data", type=str, default="Example raw data", help="Raw data input")
    parser.add_argument("--social_context", type=str, default="Example social context", help="Social context input")
    parser.add_argument("--product_description", type=str, default="Example product description", help="Product description input")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode")
    args = parser.parse_args()

    main(args.raw_data, args.social_context, args.product_description, args.dry_run)
```