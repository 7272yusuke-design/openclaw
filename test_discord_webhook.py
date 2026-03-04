import urllib.request
import urllib.parse
import json
from core.config import NeoConfig

webhook_url = getattr(NeoConfig, 'DISCORD_WEBHOOK_URL', None)
print(f"Testing Webhook URL: {webhook_url}")

if webhook_url:
    payload = {
        "content": "⚡ [SYSTEM RECOVERY] Neo Autonomous Cycle restarted. Reporting system online.",
        "username": "Neo (Autonomous)",
        "avatar_url": "https://raw.githubusercontent.com/7272yusuke-design/openclaw/master/assets/neo-avatar.png"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        webhook_url, 
        data=data, 
        headers={'Content-Type': 'application/json', 'User-Agent': 'Neo-Agent/1.0'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.status}")
            print(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No Webhook URL configured.")
