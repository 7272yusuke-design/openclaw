import os
import json
from datetime import datetime, timezone

class NeoState:
    def __init__(self, state_file_path="vault/neo_state.json"):
        self.state_file_path = state_file_path
        self._ensure_state_file_exists()

    def _ensure_state_file_exists(self):
        os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
        if not os.path.exists(self.state_file_path):
            initial_state = {"progress": 0, "target": 30, "last_updated": None}
            with open(self.state_file_path, "w") as f:
                json.dump(initial_state, f, indent=2)

    def load(self):
        self._ensure_state_file_exists() # Ensure it exists before loading
        with open(self.state_file_path, "r") as f:
            return json.load(f)

    def update(self, new_count):
        state = self.load()
        state["progress"] = new_count
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.state_file_path, "w") as f:
            json.dump(state, f, indent=2)
        return state
