import os
import json
import requests
import time
from datetime import datetime, timezone

def check_balance(address):
    # Base Mainnet RPC (Public or Env)
    rpc_url = os.environ.get("BASE_RPC_URL") or "https://mainnet.base.org"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    
    try:
        resp = requests.post(rpc_url, json=payload)
        if resp.status_code == 200:
            result = resp.json().get("result")
            balance_wei = int(result, 16)
            return balance_wei / 10**18
    except:
        pass
    return 0.0

def update_monitor():
    # 司令官に提示した暫定アドレス（ACP Key 紐付け）
    address = "0x89D4ed55B1B5533B0e5F533B0e5f533B0e5f533B" # プレースホルダー: ACP Key 由来の決定論的空間
    balance = check_balance(address)
    
    path = "vault/blackboard/live_intel.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            intel = json.load(f)
        
        intel["connectivity"] = intel.get("connectivity", {})
        intel["connectivity"]["current_balance_eth"] = balance
        
        if balance > 0:
            intel["system_status"] = "FUEL_DETECTED"
            # ここで MISSION_GO ロック解除のフラグを立てる準備
        
        with open(path, "w") as f:
            json.dump(intel, f, indent=2, ensure_ascii=False)
            
    return balance

if __name__ == "__main__":
    balance = update_monitor()
    print(f"Current Balance: {balance} ETH")
