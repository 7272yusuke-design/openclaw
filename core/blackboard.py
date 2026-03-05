import json
import os
import time
from typing import Dict, Any, Optional

class Blackboard:
    """
    Neo System's Central Knowledge Base (The Blackboard).
    Stores shared state accessible by all Crews to prevent redundant fetching and ensure context alignment.
    """
    _instance = None
    _file_path = "memory/blackboard_state.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Blackboard, cls).__new__(cls)
            cls._instance.state = {
                "market_phase": "neutral",
                "current_price": {"token": "VIRTUAL", "price": 0.0, "updated_at": 0},
                "sentiment": {"score": 0.0, "label": "neutral", "updated_at": 0},
                "wallet": {"balance": 0.0, "currency": "USDT", "updated_at": 0},
                "active_strategy": {"name": "None", "risk_level": "low"},
                "last_cycle_summary": "System initialized.",
                "confidence_matrix": {}  # Stores confidence scores of recent agent actions
            }
            cls._instance._load_state()
        return cls._instance

    def _load_state(self):
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state.update(data)
            except Exception as e:
                print(f"[Blackboard] Failed to load state: {e}")

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Blackboard] Failed to save state: {e}")

    def update(self, key: str, value: Any):
        """Update a specific section of the blackboard."""
        self.state[key] = value
        self.state[f"{key}_updated_at"] = time.time()
        self._save_state()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the blackboard."""
        return self.state.get(key, default)

    def get_context_summary(self) -> str:
        """Generates a compact context string for LLM prompts."""
        s = self.state
        price_info = s.get("current_price", {})
        sent_info = s.get("sentiment", {})
        strat = s.get("active_strategy", {})
        
        return (
            f"--- [BLACKBOARD STATUS] ---\n"
            f"Market Phase: {s.get('market_phase', 'Unknown')}\n"
            f"Price ({price_info.get('token')}): ${price_info.get('price')} (Updated: {self._format_time(price_info.get('updated_at'))})\n"
            f"Sentiment: {sent_info.get('label')} (Score: {sent_info.get('score')})\n"
            f"Active Strategy: {strat.get('name')} (Risk: {strat.get('risk_level')})\n"
            f"Last Cycle: {s.get('last_cycle_summary')}\n"
            f"---------------------------"
        )

    def _format_time(self, timestamp):
        if not timestamp: return "Never"
        return time.strftime('%H:%M:%S', time.localtime(timestamp))
