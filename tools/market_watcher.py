import time
import json
import os
import random
from datetime import datetime, timedelta

# --- Configuration ---
TARGET_ASSETS = ["AIXBT", "$VIRTUAL", "$WAY"]
PRICE_VOLATILITY_THRESHOLD = 0.03  # 3%
VOLUME_SPIKE_FACTOR = 2.0        # 2x
EMA50_BREAKTHROUGH_TARGET = {"AIXBT": 0.0256} # Example EMA50 for AIXBT

ALERTS_DIR = "vault/alerts"
ALERT_FILE = os.path.join(ALERTS_DIR, "critical_event.json")

# Create alerts directory if it doesn't exist
os.makedirs(ALERTS_DIR, exist_ok=True)

# --- Mock Data/State (for physical completion) ---
# In a real scenario, this would come from a real-time API
mock_prices = {asset: random.uniform(0.02, 0.03) for asset in TARGET_ASSETS}
mock_volumes = {asset: random.uniform(1000, 10000) for asset in TARGET_ASSETS}
price_history = {asset: [] for asset in TARGET_ASSETS} # Stores (timestamp, price) tuples
volume_history = {asset: [] for asset in TARGET_ASSETS} # Stores (timestamp, volume) tuples

def fetch_mock_market_data(asset):
    """Simulates fetching real-time market data."""
    # Simulate price fluctuations
    current_price = mock_prices[asset] * random.uniform(0.99, 1.01)
    mock_prices[asset] = current_price
    
    # Simulate volume fluctuations
    current_volume = mock_volumes[asset] * random.uniform(0.8, 1.5)
    mock_volumes[asset] = current_volume

    # Simulate closing price for EMA50 check (for now, assume current price is closing price)
    closing_price = current_price 
    
    return {
        "price": current_price,
        "volume": current_volume,
        "closing_price": closing_price,
        "timestamp": datetime.now().isoformat()
    }

def check_price_volatility(asset, current_data):
    """Checks for significant price change over the last 5 minutes."""
    current_time = datetime.now()
    price_history[asset].append((current_time, current_data["price"]))

    # Keep only data from the last 5 minutes
    five_minutes_ago = current_time - timedelta(minutes=5)
    price_history[asset] = [
        (t, p) for t, p in price_history[asset] if t > five_minutes_ago
    ]

    if len(price_history[asset]) < 2:
        return None # Not enough data

    oldest_price = price_history[asset][0][1]
    latest_price = price_history[asset][-1][1]

    if oldest_price == 0: # Avoid division by zero
        return None

    percentage_change = abs((latest_price - oldest_price) / oldest_price)
    
    if percentage_change >= PRICE_VOLATILITY_THRESHOLD:
        return {
            "type": "price_volatility",
            "asset": asset,
            "change": f"{percentage_change:.2%}",
            "current_price": latest_price,
            "previous_price": oldest_price
        }
    return None

def check_volume_spike(asset, current_data):
    """Checks for sudden increase in volume (2x average over last hour)."""
    current_time = datetime.now()
    volume_history[asset].append((current_time, current_data["volume"]))

    # Keep only data from the last hour
    one_hour_ago = current_time - timedelta(hours=1)
    volume_history[asset] = [
        (t, v) for t, v in volume_history[asset] if t > one_hour_ago
    ]

    if len(volume_history[asset]) < 2:
        return None
    
    # Calculate average volume over the last hour
    historical_volumes = [v for t, v in volume_history[asset]]
    if not historical_volumes:
        return None
    
    average_volume = sum(historical_volumes) / len(historical_volumes)

    if current_data["volume"] >= average_volume * VOLUME_SPIKE_FACTOR:
        return {
            "type": "volume_spike",
            "asset": asset,
            "current_volume": current_data["volume"],
            "average_hourly_volume": average_volume
        }
    return None

def check_ema50_breakthrough(asset, current_data):
    """Checks if the closing price breaks above the 50-day EMA."""
    if asset in EMA50_BREAKTHROUGH_TARGET:
        ema50 = EMA50_BREAKTHROUGH_TARGET[asset]
        if current_data["closing_price"] > ema50:
            return {
                "type": "ema50_breakthrough",
                "asset": asset,
                "closing_price": current_data["closing_price"],
                "ema50": ema50
            }
    return None

def generate_alert(anomaly_data):
    """Writes anomaly details to a JSON file."""
    with open(ALERT_FILE, "w") as f:
        json.dump(anomaly_data, f, indent=4)
    print(f"Alert saved to {ALERT_FILE}")

def run_market_watcher(iterations=3, interval_seconds=1):
    print("--- Real-time Market Watcher initialized ---")
    for i in range(iterations):
        anomalies_detected = False
        for asset in TARGET_ASSETS:
            current_data = fetch_mock_market_data(asset)
            
            anomaly = None
            # Check conditions
            if not anomaly:
                anomaly = check_price_volatility(asset, current_data)
            if not anomaly:
                anomaly = check_volume_spike(asset, current_data)
            if not anomaly:
                anomaly = check_ema50_breakthrough(asset, current_data)

            if anomaly:
                print(f"\n--- Anomaly Detected for {asset} ---")
                print(f"Event: {anomaly['type']}")
                print(f"Details: {anomaly}")
                generate_alert(anomaly)
                anomalies_detected = True
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {asset}: Status - No anomaly detected. Price: {current_data['price']:.4f}, Volume: {current_data['volume']:.0f}.")
        
        if not anomalies_detected and i == iterations -1: # Ensure the last iteration produces a clean status if no anomaly
             print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] All assets: No anomalies detected in this run.")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    # For initial testing, let's make sure some anomalies can be triggered
    # by adjusting mock data or thresholds if needed.
    # For now, it focuses on demonstrating the watcher runs and checks.
    run_market_watcher(iterations=3, interval_seconds=1)
