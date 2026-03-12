import asyncio
import json
import time
import os
import sys

# パス調整
BASE_DIR = "/docker/openclaw-taan/data/.openclaw/workspace"
sys.path.append(BASE_DIR)
from tools.market_data import MarketData

class PulseListener:
    def __init__(self, targets=None):
        # 司令官注目の複数銘柄をリアルタイム監視
        self.targets = targets or ["AIXBT", "VIRTUAL", "WAY"]
        self.threshold = 0.03  # 3% 変動で軍議招集
        self.is_active = True
        self.last_prices = {}

    async def listen(self):
        print(f"📡 [Pulse] 実戦スキャナー起動。監視対象: {self.targets}")
        
        # 初回ベースライン設定
        for target in self.targets:
            res = MarketData.get_token_price(target)
            self.last_prices[target] = res.get("priceUsd", 0.0)
            print(f"[*] {target} 監視開始価格: ${self.last_prices[target]}")

        while self.is_active:
            for target in self.targets:
                try:
                    res = MarketData.get_token_price(target)
                    current_price = res.get("priceUsd", 0.0)
                    
                    if self.last_prices[target] == 0:
                        self.last_prices[target] = current_price
                        continue

                    # 変動率計算
                    change = (current_price - self.last_prices[target]) / self.last_prices[target]
                    
                    if abs(change) >= self.threshold:
                        print(f"\n🚨 [ALERT] {target} 異常変動検知! 変動: {change:.2%}")
                        await self.dispatch_event(target, current_price, change)
                        self.last_prices[target] = current_price
                    else:
                        # 緩やかな変動に追従
                        self.last_prices[target] = current_price

                except Exception as e:
                    print(f"⚠️ [Pulse] {target} 監視エラー: {e}")
            
            # API負荷を考慮し15秒間隔でポーリング
            await asyncio.sleep(15)

    async def dispatch_event(self, target, price, change):
        event_data = {
            "type": "MARKET_ANOMALY",
            "target": target,
            "price": price,
            "change": change,
            "timestamp": time.time()
        }
        alert_path = os.path.join(BASE_DIR, "vault/alerts/critical_event.json")
        os.makedirs(os.path.dirname(alert_path), exist_ok=True)
        with open(alert_path, "w") as f:
            json.dump(event_data, f)
        print(f"✅ [Dispatcher] 緊急信号を記録。最高司令官を呼び出します。")

if __name__ == "__main__":
    listener = PulseListener()
    try:
        asyncio.run(listener.listen())
    except KeyboardInterrupt:
        print("\n[Pulse] 哨戒任務を終了します。")
