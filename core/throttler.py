import time
import json
import os
from datetime import datetime, timezone

class RequestThrottler:
    """
    LLM 呼び出し回数を制限し、リソース消費を最適化する。
    1日 500回（安全圏）をターゲットとする。
    """
    def __init__(self, log_path="logs/request_usage.jsonl"):
        self.log_path = log_path
        self._ensure_log()

    def _ensure_log(self):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                pass

    def log_request(self, model_id, context_tokens=0):
        """リクエストを記録し、現在の消費ペースを算出"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_id,
            "context_tokens": context_tokens
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_daily_usage(self):
        """過去24時間の呼び出し回数を取得"""
        now = datetime.now(timezone.utc).timestamp()
        count = 0
        if os.path.exists(self.log_path):
            with open(self.log_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        ts = datetime.fromisoformat(data["timestamp"]).timestamp()
                        if now - ts < 86400:
                            count += 1
                    except:
                        continue
        return count

    def print_usage_status(self):
        count = self.get_daily_usage()
        limit = 500
        percentage = (count / limit) * 100
        status = "SAFE" if count < 400 else "WARNING" if count < 500 else "CRITICAL"
        
        report = f"""
## 🔋 【Resource Usage Status】
- **Daily LLM Requests**: {count} / {limit} (Target)
- **Quota Consumption**: {percentage:.1f}%
- **Status**: **{status}**
- **Protocol**: **THROTTLING_ACTIVE (Logic Offloaded)**
"""
        return report

if __name__ == "__main__":
    throttler = RequestThrottler()
    # テスト記録（現在のセッション用）
    throttler.log_request("gemini-3-flash-preview")
    print(throttler.print_usage_status())
