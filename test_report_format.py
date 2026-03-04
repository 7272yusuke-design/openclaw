import urllib.request
import json
from core.config import NeoConfig

webhook_url = getattr(NeoConfig, 'DISCORD_WEBHOOK_URL', None)

if webhook_url:
    current_time = "2026-03-04 17:05:00"
    report_text = f"""### 📣 【Neo 自律哨戒報告】 ({current_time}) (TEST)

**ステータス**: ✅ 正常完了 (Cycle Completed)

#### 1. 📈 市場分析 (Scout & Sentiment)
- **トレンド**: データ取得完了
- **センチメント**: Greed (0.65)

#### 2. 🛡️ 戦略判断 (Strategic Planning)
- **リスク判定**: **Aggressive**
- **アクション**: **BUY VIRTUAL**

#### 3. 💰 資産状況 (Paper Wallet)
- **総資産評価額**: **$100,500.00** (+$500.00)
- **保有内訳**:
  - VIRTUAL: 15,000 トークン

#### 4. ✍️ 対外発信 (Content Creator)
> 🚀 VIRTUALエコシステムは爆発的成長フェーズへ。今が仕込み時。 #VirtualsProtocol
"""

    payload = {
        "content": report_text,
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
            print(f"Test Status: {response.status}")
    except Exception as e:
        print(f"Error: {e}")
