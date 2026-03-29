import json
import os
import time

BLACKBOARD_PATH = "vault/blackboard/live_intel.json"

def read_blackboard():
    if not os.path.exists(BLACKBOARD_PATH):
        return {}
    with open(BLACKBOARD_PATH, "r") as f:
        return json.load(f)

def write_blackboard(crew_name, data):
    blackboard = read_blackboard()
    blackboard[crew_name] = data
    blackboard["last_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 警告（alerts）への追記ロジック
    if "alert" in data:
        blackboard["alerts"].append({
            "from": crew_name,
            "content": data["alert"],
            "timestamp": blackboard["last_sync"]
        })
        # 直近10件のみ保持
        blackboard["alerts"] = blackboard["alerts"][-10:]

    with open(BLACKBOARD_PATH, "w") as f:
        json.dump(blackboard, f, indent=2, ensure_ascii=False)
    return True

if __name__ == "__main__":
    # Test
    print("Initializing test write from Scout...")
    write_blackboard("scout", {"price_action": "VIRTUAL +15% spike", "alert": "High volatility detected"})
    print("Current Blackboard State:")
    print(json.dumps(read_blackboard(), indent=2))
