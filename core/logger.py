import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

class ExecutionLogger:
    """
    Lightweight logger for batch optimization.
    Appends execution metrics to a daily JSONL file without blocking the main thread.
    """
    
    def __init__(self, log_dir: str = "logs/execution"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def log_interaction(self, 
                        crew_name: str, 
                        task_name: str,
                        status: str, 
                        turns: int, 
                        duration_seconds: float, 
                        cost_estimate: float,
                        error_message: Optional[str] = None):
        
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(self.log_dir, f"exec_{today}.jsonl")
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "crew": crew_name,
            "task": task_name,
            "status": status,
            "turns": turns,
            "duration": round(duration_seconds, 2),
            "cost_est": round(cost_estimate, 5),
            "error": error_message
        }
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Logger] Failed to write log: {e}")

    def get_logs_for_date(self, date_str: str):
        """
        Reads logs for a specific date (YYYY-MM-DD).
        """
        file_path = os.path.join(self.log_dir, f"exec_{date_str}.jsonl")
        if not os.path.exists(file_path):
            return []
        
        logs = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return logs
