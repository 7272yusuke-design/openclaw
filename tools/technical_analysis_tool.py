import requests
import pandas as pd
import pandas_ta as ta
import json
import datetime
import os
from crewai.tools import BaseTool

# Configuration
NETWORK = "base"
POOL_ADDRESS = "0x22a52bb644f855ebd5ca2edb643ff70222d70c31" # AIXBT/WETH on Base
API_URL = f"https://api.geckoterminal.com/api/v2/networks/{NETWORK}/pools/{POOL_ADDRESS}/ohlcv/hour"

def fetch_ohlcv(limit=100):
    """
    Fetch OHLCV data from GeckoTerminal.
    """
    try:
        response = requests.get(API_URL, params={"limit": limit})
        response.raise_for_status()
        data = response.json()
        
        # Parse data
        ohlcv_list = data['data']['attributes']['ohlcv_list']
        df = pd.DataFrame(ohlcv_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Sort by timestamp ascending (oldest first) for TA calculation
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"Error fetching OHLCV: {e}")
        return None

def analyze_market():
    """
    Perform technical analysis on AIXBT.
    """
    df = fetch_ohlcv()
    if df is None or df.empty:
        return {"error": "No data available"}
    
    # Calculate Indicators
    # RSI (14)
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # Bollinger Bands (20, 2)
    bbands = ta.bbands(df['close'], length=20, std=2)
    if bbands is not None:
        df = pd.concat([df, bbands], axis=1)
    else:
        return {"error": "Insufficient data for TA (Bollinger)"}
    
    # EMA (20, 50)
    df['EMA_20'] = ta.ema(df['close'], length=20)
    df['EMA_50'] = ta.ema(df['close'], length=50)
    
    # Get latest values
    latest = df.iloc[-1]
    
    # Initialize variables
    score = 0
    reasons = []
    
    # RSI Logic
    rsi = latest['RSI']
    if rsi < 30:
        score += 1
        reasons.append(f"RSI Oversold ({rsi:.2f})")
    elif rsi > 70:
        score -= 1
        reasons.append(f"RSI Overbought ({rsi:.2f})")
    else:
        reasons.append(f"RSI Neutral ({rsi:.2f})")
        
    # Bollinger Logic
    # Dynamically find columns
    bbl_col = [c for c in df.columns if c.startswith('BBL_')][0]
    bbu_col = [c for c in df.columns if c.startswith('BBU_')][0]
    
    close_price = latest['close']
    lower_band = latest[bbl_col]
    upper_band = latest[bbu_col]
    
    if close_price <= lower_band:
        score += 1
        reasons.append("Price at Lower Bollinger Band")
    elif close_price >= upper_band:
        score -= 1
        reasons.append("Price at Upper Bollinger Band")
        
    # Trend Logic (EMA)
    ema20 = latest['EMA_20']
    ema50 = latest['EMA_50']
    
    # Check if EMA exists (might be NaN if not enough history)
    if pd.notna(ema20) and pd.notna(ema50):
        if close_price > ema20 > ema50:
            score += 1
            reasons.append("Bullish Trend (Price > EMA20 > EMA50)")
        elif close_price < ema20 < ema50:
            score -= 1
            reasons.append("Bearish Trend (Price < EMA20 < EMA50)")
        else:
             reasons.append("Trend Indeterminate")
    else:
         reasons.append("Insufficient data for EMA Trend")

    # Final Verdict
    signal = "NEUTRAL"
    if score >= 2:
        signal = "STRONG_BUY"
    elif score == 1:
        signal = "BUY"
    elif score == -1:
        signal = "SELL"
    elif score <= -2:
        signal = "STRONG_SELL"
        
    result = {
        "timestamp": latest['timestamp'].isoformat(),
        "price": close_price,
        "signal": signal,
        "score": score,
        "indicators": {
            "rsi": rsi,
            "bb_lower": lower_band,
            "bb_upper": upper_band,
            "ema_20": ema20,
            "ema_50": ema50
        },
        "reasons": reasons
    }
    
    return result

class TechnicalAnalysisTool(BaseTool):
    name: str = "Technical Analysis Tool"
    description: str = "Analyzes market data for AIXBT using technical indicators (RSI, Bollinger Bands, EMA). Returns a signal (BUY/SELL/HOLD) and detailed metrics."

    def _run(self) -> str:
        analysis = analyze_market()
        if "error" in analysis:
            return f"Error: {analysis['error']}"
        return json.dumps(analysis, indent=2, default=str)

if __name__ == "__main__":
    print(analyze_market())
