import time
from tools.market_data import MarketData
from neo_main import NeoSystem

# --- レーダー設定 ---
CHECK_INTERVAL = 60
TRIGGER_THRESHOLD = 2.0

def start_volatility_radar():
    print("===================================================")
    print(f" 📡 Neo Radar: Active (Fixed Anchor Mode) ")
    print("===================================================")
    
    initial_data = MarketData.fetch_token_data("VIRTUAL")
    if not initial_data or initial_data.get("status") != "success":
        print("[Radar] Error: Could not fetch initial price. Retrying in 10s...")
        time.sleep(10)
        return start_volatility_radar()

    # 基準価格（アンカー）を固定
    anchor_price = float(initial_data.get("priceUsd", 0.0))
    print(f"[*] Radar Anchor Price set to: ${anchor_price:.4f}")
    
    neo = None

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            current_data = MarketData.fetch_token_data("VIRTUAL")
            if not current_data or current_data.get("status") != "success":
                continue
                
            current_price = float(current_data.get("priceUsd", 0.0))
            
            # アンカー価格との比較
            price_diff = current_price - anchor_price
            change_percent = abs(price_diff / anchor_price) * 100
            
            direction = "UP 🚀" if price_diff > 0 else "DOWN 🩸"
            
            if change_percent >= TRIGGER_THRESHOLD:
                print(f"\n🚨 [TRIGGER ALERT] VIRTUAL {direction} ({change_percent:.2f}% from anchor)!")
                print(f"    Anchor: ${anchor_price:.4f} -> Current: ${current_price:.4f}")
                print("    >>> Waking up Neo System... <<<")
                
                if neo is None:
                    neo = NeoSystem()
                
                topic = f"VIRTUAL価格がアンカーから{change_percent:.2f}%の{'上昇' if price_diff > 0 else '下落'}"
                neo.autonomous_post_cycle(topic=topic)
                
                # トリガー発動時のみアンカーを更新
                anchor_price = current_price
                print(f"\n[*] Anchor updated to: ${anchor_price:.4f}. Resuming watch...")
            else:
                # 閾値未満ならアンカーを維持（じわじわ上昇を逃さない）
                print(f"[Radar] Price: ${current_price:.4f} (Rel to Anchor: {change_percent:.2f}%)", end="\r")

    except KeyboardInterrupt:
        print("\n[Radar] Terminated by Commander.")

if __name__ == "__main__":
    start_volatility_radar()
