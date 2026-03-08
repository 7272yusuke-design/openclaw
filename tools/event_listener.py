import asyncio
import json
import time
import random
import sys
import os

# パス調整
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from tools.code_interpreter import run_code
except ImportError:
    # 直接実行用
    def run_code(code): pass

class PulseListener:
    def __init__(self, targets=None):
        self.targets = targets or ["VIRTUAL", "WAY", "AIXBT"]
        self.threshold = 0.03 # 3%
        self.is_active = True
        self.last_prices = {target: 1.0 for target in self.targets} # 初期価格(仮)

    async def fetch_price(self, target):
        # 本来はWebSocket/APIから取得。ここではシミュレーション。
        # 0.1%〜5%のランダムな変動を発生させる
        change = random.uniform(-0.05, 0.05)
        self.last_prices[target] *= (1 + change)
        return self.last_prices[target], change

    async def listen(self):
        print(f"[Pulse] Listener started. Monitoring: {self.targets}")
        while self.is_active:
            for target in self.targets:
                price, change = await self.fetch_price(target)
                
                if abs(change) >= self.threshold:
                    print(f"\n[ALERT] {target} anomaly detected! Change: {change:.2%}")
                    await self.dispatch_event(target, price, change)
            
            # 高頻度ポーリングからWebSocketライクな待機へ(ここでは擬似)
            await asyncio.sleep(1) 

    async def dispatch_event(self, target, price, change):
        print(f"[Dispatcher] Activating Trinity Council for {target}...")
        # ここで緊急評議会(emergency_council_runner)をキック
        # 実装上はsubprocessやsession_spawnを使用
        event_data = {
            "type": "MARKET_ANOMALY",
            "target": target,
            "price": price,
            "change": change,
            "timestamp": time.time()
        }
        with open("vault/alerts/critical_event.json", "w") as f:
            json.dump(event_data, f)
        print(f"[Dispatcher] Critical event logged. Council will wake up on next heartbeat.")

if __name__ == "__main__":
    listener = PulseListener()
    try:
        asyncio.run(listener.listen())
    except KeyboardInterrupt:
        print("Listener stopped.")
