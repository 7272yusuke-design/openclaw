import requests
import json
import os

class DiscordReporter:
    # 既存のWebhook
    REPORT_WEBHOOK = "https://discord.com/api/webhooks/1479009905280028724/cX7C6pOTilIA4HeBzMwWOG_AhKMOcDH9KKU9_r955U0yr5z4hTsPRB0ISFfxjp3Otj64"
    LOG_WEBHOOK = "https://discord.com/api/webhooks/1478693375090622559/f0AwGgXAWkyGWOZVk5LLI9A1MKYQBvzmdSGoc3crPNMZ2mCaJEe-JIbF9ATuAsQp8Ioe"

    @classmethod
    def send_council_minutes(cls, title, discussion_data, color=0x3498db, image_path=None):
        embed = {
            "title": title,
            "color": color,
            "fields": [
                {"name": "🐂 Bullish Opinion", "value": discussion_data.get('bull', 'N/A')[:1024], "inline": False},
                {"name": "🐻 Bearish Opinion", "value": discussion_data.get('bear', 'N/A')[:1024], "inline": False},
                {"name": "📊 Simulation Stats", "value": discussion_data.get('stats', 'N/A')[:1024], "inline": False},
                {"name": "🤖 Neo's Verdict", "value": discussion_data.get('verdict', 'Final Decision Pending')[:1024], "inline": False},
            ],
            "footer": {"text": f"Mode: {os.getenv('NEO_MODE', 'PAPER')}"}
        }
        
        # 🛠️ 画像がある場合、Embedの中で展開させるための記述を追加
        if image_path and os.path.exists(image_path):
            filename = os.path.basename(image_path)
            embed["image"] = {"url": f"attachment://{filename}"}
        
        payload = {"embeds": [embed]}
        return cls._post(cls.REPORT_WEBHOOK, payload, image_path)

    @classmethod
    def _post(cls, url, payload, image_path=None):
        try:
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    filename = os.path.basename(image_path)
                    files = {f'file': (filename, f, 'image/png')}
                    response = requests.post(url, data={'payload_json': json.dumps(payload)}, files=files, timeout=15)
            else:
                response = requests.post(url, json=payload, timeout=10)
            
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Discord送信失敗: {e}")
            return False

    @classmethod
    def send_log(cls, title, message, color=0x3498db):
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color
            }]
        }
        return cls._post(cls.LOG_WEBHOOK, payload)
