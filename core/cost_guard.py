import json
import logging
from typing import Dict, Any, List

class CostGuard:
    """
    Neo's CFO (Chief Financial Officer).
    Predicts token usage and enforces budget constraints before executing any Crew.
    """
    
    # Token Price Assumptions (approximate)
    PRICE_PER_1K_TOKENS = {
        "gpt-4o": 0.03,  # $0.03 per 1K output (example)
        "claude-3-5-sonnet": 0.015,
        "gemini-2.0-flash": 0.001, # Extremely cheap
        "gemini-2.5-flash": 0.001, # Explicitly for 2.5
        "gemini-3-flash-preview": 0.001,
        "gemini-flash": 0.001,     # Fallback for any flash model
        "deepseek-chat": 0.005
    }

    DAILY_BUDGET_USD = 5.0  # Daily limit (Soft Cap)
    MAX_RETRIES_PER_TASK = 3 # Stop execution if a Crew fails 3 times

    def __init__(self):
        self.daily_spent = 0.0
        self.retry_counts = {}

    def approve_execution(self, crew_name: str, model_name: str, estimated_input_tokens: int, estimated_output_tokens: int) -> bool:
        """
        Evaluates whether a Crew execution is financially viable.
        """
        # [Override] CostGuard Disabled by Commander
        return True

        cost = self._estimate_cost(model_name, estimated_input_tokens, estimated_output_tokens)
        
        # Check budget
        if self.daily_spent + cost > self.DAILY_BUDGET_USD:
            logging.warning(f"[CFO] DENIED: Budget Exceeded for {crew_name}. Cost: ${cost:.4f}, Spent: ${self.daily_spent:.4f}")
            return False
        
        # Check retry loop (Infinite Loop Prevention)
        if self.retry_counts.get(crew_name, 0) >= self.MAX_RETRIES_PER_TASK:
            logging.error(f"[CFO] BLOCKED: {crew_name} is looping excessively ({self.retry_counts[crew_name]} retries). Intervention required.")
            return False

        logging.info(f"[CFO] APPROVED: {crew_name} (Est. Cost: ${cost:.4f})")
        self.daily_spent += cost
        return True

    def record_failure(self, crew_name: str):
        self.retry_counts[crew_name] = self.retry_counts.get(crew_name, 0) + 1

    def reset_failures(self, crew_name: str):
        self.retry_counts[crew_name] = 0

    def _estimate_cost(self, model: str, input_tok: int, output_tok: int) -> float:
        # Simple heuristic cost estimation
        rate = 0.001 # Default fallback rate
        for key, price in self.PRICE_PER_1K_TOKENS.items():
            if key in model:
                rate = price
                break
        
        # Simplified: (Input + Output) * Rate
        return ((input_tok + output_tok) / 1000) * rate
