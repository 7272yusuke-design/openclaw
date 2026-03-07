# Project: Neo Sentiment Logic Fix

## Vision
Stabilize the Neo autonomous cycle by ensuring precise data delivery to the SentimentCrew, eliminating hallucinated analysis caused by argument mismatches.

## Goals
- Resolve argument mismatch in `neo_main.py` when invoking SentimentCrew.
- Harden sentiment score extraction logic to prevent parsing failures.
- Implement automated verification of the data flow between core and crew.

## Tech Stack
- Python (Core Logic)
- CrewAI (Agent Orchestration)
- Pytest (Verification)
- Loguru/Logging (Traceability)

## User Context
The Neo autonomous cycle is currently failing because the SentimentCrew receives malformed or misplaced arguments. This leads the LLM to "hallucinate" context or fail to produce valid sentiment scores, breaking downstream automated trading/interaction logic.