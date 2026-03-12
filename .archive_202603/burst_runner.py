import json
import time
import requests
import os
from datetime import datetime

from tools.market_data import MarketData
from tools.balance_monitor import check_balance
from tools.performance_analyzer import analyze_virtual_performance
from core.simulation_executor import SimulationExecutor
from core.state_manager import NeoState

# Webhook 分離設定
LIVE_LOG_URL = "https://discord.com/api/webhooks/1478693375090622559/f0AwGgXAWkyGWOZVk5LLI9A1MKYQBvzmdSGoc3crPNMZ2mCaJEe-JIbF9ATuAsQp8Ioe"
DAILY_REPORT_URL = "https://discord.com/api/webhooks/1479009905280028724/cX7C6pOTilIA4HeBzMwWOG_AhKMOcDH9KKU9_r955U0yr5z4hTsPRB0ISFfxjp3Otj64"

# --- 狩猟ルール (チャンス・トリガー) ---
VOLATILITY_THRESHOLD = 0.003  # 0.3% 以上の価格変動を「チャンス」と定義
SCAN_INTERVAL = 30           # 監視は30秒おき（爆速化）
TRADE_SYMBOL = "VIRTUAL"
VIRTUAL_ADDRESS = "0x3f0296bf652e19bca772ec3df08b32732f93014a"
STATE_FILE_PATH = "vault/neo_state.json"

def send_live(msg):
    try: requests.post(LIVE_LOG_URL, json={'content': str(msg)}, timeout=5)
    except: pass

def run_hunter_cycle():
    print("--- [NEO: HUNTER MODE ACTIVE] ---", flush=True)
    sim_executor = SimulationExecutor()
    neo_state = NeoState()
    last_price = 0.0
    
    while True:
        state = neo_state.load()
        if state.get('progress', 0) >= 35: # 目標を少し延長して実戦テスト
            break

        market_result = MarketData.get_token_price(TRADE_SYMBOL)
        if market_result.get("status") == "success":
            current_price = market_result["priceUsd"]
            
            # --- チャンス判定ロジック ---
            if last_price == 0.0:
                last_price = current_price
                print(f"Base price set: ${current_price:.6f}. Watching for {VOLATILITY_THRESHOLD*100}% move...", flush=True)
                continue

            price_diff = abs(current_price - last_price) / last_price
            
            if price_diff >= VOLATILITY_THRESHOLD:
                # チャンス到来！
                direction = "UP" if current_price > last_price else "DOWN"
                print(f"🎯 CHANCE DETECTED! {direction} {price_diff*100:.2f}%", flush=True)
                
                trade = sim_executor.execute_virtual_trade(TRADE_SYMBOL, "BUY", 100, current_price)
                
                if trade.get("status") == "COMPLETED":
                    state['progress'] += 1
                    with open(STATE_FILE_PATH, "w") as f: json.dump(state, f, indent=2)
                    send_live(f"【🎯 HUNTER】Price moved {price_diff*100:.2f}%! Target Acquired.\nProgress: {state['progress']}/35 | Price: ${current_price:.6f}")
                    last_price = current_price # 基準価格を更新
            else:
                # 静観
                print(f"Static: ${current_price:.6f} (Diff: {price_diff*100:.3f}%)", flush=True)
        
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_hunter_cycle()
