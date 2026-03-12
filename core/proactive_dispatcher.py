import os
import json
import requests
import time
from datetime import datetime, timezone

class ProactiveDispatcher:
    """
    能動的発話機能を司るディスパッチャー。
    """
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
        self.heartbeat_path = "vault/HEARTBEAT.md"
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs("vault", exist_ok=True)
        if not os.path.exists(self.heartbeat_path):
            with open(self.heartbeat_path, "w") as f:
                f.write("# HEARTBEAT.md - Neo's Autonomous Pulse\n\n")

    def log_heartbeat(self, status_msg):
        """思考の軌跡を HEARTBEAT.md に記録"""
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(self.heartbeat_path, "a") as f:
            f.write(f"- [{timestamp}] {status_msg}\n")

    def notify_discord(self, title, message, color=0x00ff00):
        """Discord Webhook 経由で能動的発話"""
        if not self.webhook_url:
            return False
        
        payload = {
            "embeds": [{
                "title": f"🤖 {title}",
                "description": message,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            return resp.status_code == 204
        except Exception as e:
            self.log_heartbeat(f"DISCORD_NOTIFY_ERROR: {e}")
            return False

if __name__ == "__main__":
    # テスト送信
    dispatcher = ProactiveDispatcher()
    status = "Proactive Mode Activated. Progress: 0/30. Logic: Locked 1.1x."
    dispatcher.log_heartbeat(status)
    success = dispatcher.notify_discord("Proactive Mode Activated", status)
    print(f"Test Notify: {'SUCCESS' if success else 'FAILED (Check Webhook URL)'}")
