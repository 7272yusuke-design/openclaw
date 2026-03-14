import json
import logging
from datetime import date
from pathlib import Path

BUDGET_FILE = Path("vault/cost_guard_daily.json")

class CostGuard:
    """
    Neo's CFO (Chief Financial Officer).
    日次予算を管理し、超過時はCouncil召集をスキップする。
    再起動後もvaultに永続化。
    """
    PRICE_PER_1K_TOKENS = {
        "gpt-4o": 0.03,
        "claude-3-5-sonnet": 0.015,
        "gemini-2.0-flash": 0.001,
        "gemini-2.5-flash": 0.001,
        "gemini-3-flash-preview": 0.001,
        "gemini-flash": 0.001,
        "deepseek-chat": 0.005
    }
    DAILY_BUDGET_USD = 5.0
    MAX_RETRIES_PER_TASK = 3

    def __init__(self):
        self.retry_counts = {}
        self._load()

    def _load(self):
        """今日の消費額をvaultからロード。日付が変わっていたらリセット。"""
        today = str(date.today())
        if BUDGET_FILE.exists():
            try:
                data = json.loads(BUDGET_FILE.read_text())
                if data.get("date") == today:
                    self.daily_spent = data.get("spent", 0.0)
                    logging.info(f"[CFO] 本日消費額ロード: ${self.daily_spent:.4f}")
                    return
            except Exception:
                pass
        self.daily_spent = 0.0
        self._save()

    def _save(self):
        """消費額をvaultに保存。"""
        BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_FILE.write_text(json.dumps({
            "date": str(date.today()),
            "spent": self.daily_spent
        }))

    def approve_execution(self, crew_name: str, model_name: str, estimated_input_tokens: int, estimated_output_tokens: int) -> bool:
        cost = self._estimate_cost(model_name, estimated_input_tokens, estimated_output_tokens)

        if self.daily_spent + cost > self.DAILY_BUDGET_USD:
            logging.warning(f"[CFO] DENIED: 日次予算超過 ({crew_name}) 消費済み=${self.daily_spent:.4f} 推定=${cost:.4f} 上限=${self.DAILY_BUDGET_USD}")
            return False

        if self.retry_counts.get(crew_name, 0) >= self.MAX_RETRIES_PER_TASK:
            logging.error(f"[CFO] BLOCKED: {crew_name} が{self.retry_counts[crew_name]}回ループ中。介入が必要。")
            return False

        logging.info(f"[CFO] APPROVED: {crew_name} (推定=${cost:.4f} 本日合計=${self.daily_spent + cost:.4f})")
        self.daily_spent += cost
        self._save()
        return True

    def record_failure(self, crew_name: str):
        self.retry_counts[crew_name] = self.retry_counts.get(crew_name, 0) + 1

    def reset_failures(self, crew_name: str):
        self.retry_counts[crew_name] = 0

    def _estimate_cost(self, model: str, input_tok: int, output_tok: int) -> float:
        rate = 0.001
        for key, price in self.PRICE_PER_1K_TOKENS.items():
            if key in model:
                rate = price
                break
        return ((input_tok + output_tok) / 1000) * rate
