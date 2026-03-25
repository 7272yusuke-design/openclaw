"""
Neo Resource API — ACP Resource endpoints for VP Market data
Runs on port 8099. Registered as ACP Resources.
"""
import sys
sys.path.insert(0, '/docker/openclaw-taan/data/.openclaw/workspace')

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json

app = FastAPI(title="Neo Resource API", version="1.1")

# --- v1 versioned routes (canonical) ---
@app.get("/v1/resources/active_positions")
def active_positions_v1():
    return active_positions()

@app.get("/v1/resources/historical_performance")
def historical_performance_v1():
    return historical_performance()

@app.get("/v1/resources/vp_market_pulse")
def vp_market_pulse_v1():
    return vp_market_pulse()

@app.get("/health")
def health():
    return {"status": "ok", "agent": "Neo"}

@app.get("/resources/active_positions")
def active_positions():
    """Resource 1: Active Positions — 現在の保有ポジションと含み損益"""
    try:
        from tools.paper_wallet import PaperWallet
        from tools.market_data import MarketData
        pw = PaperWallet()
        prices = {}
        for symbol in pw.state.get('holdings', {}).keys():
            data = MarketData.fetch_token_data(symbol)
            if data and data.get('priceUsd'):
                prices[symbol] = float(data['priceUsd'])
        summary = pw.get_portfolio_summary(prices)
        return JSONResponse({
            "usd_balance": summary["usd_balance"],
            "total_value_usd": summary["total_value_usd"],
            "positions": summary["positions"],
            "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/resources/historical_performance")
def historical_performance():
    """Resource 2: Historical Performance — 勝率・取引回数・PnL統計"""
    try:
        import re
        from tools.paper_wallet import PaperWallet
        pw = PaperWallet()
        hist = pw.state.get("history", [])
        sells = [h for h in hist if h.get("action") == "SELL"]
        # PnLをreasonテキストから抽出（SELLレコードにpnl_pctキーがないため）
        pnls = []
        for h in sells:
            m = re.search(r'([+-]?\d+\.?\d*)%', h.get("reason", ""))
            if m:
                pnls.append(float(m.group(1)))
        wins = sum(1 for p in pnls if p > 0)
        wr = (wins / len(pnls) * 100) if pnls else 0
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        max_dd = min(pnls) if pnls else 0
        return JSONResponse({
            "total_trades": len(hist),
            "closed_trades": len(sells),
            "win_rate": round(wr, 1),
            "wins": wins,
            "losses": len(sells) - wins,
            "avg_pnl_pct": round(avg_pnl, 2),
            "worst_trade_pct": round(max_dd, 2),
            "best_trade_pct": round(max(pnls) if pnls else 0, 2),
            "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/resources/vp_market_pulse")
def vp_market_pulse():
    """Resource 3: VP Market Pulse — テクニカルサマリー"""
    try:
        from tools.market_data import MarketData
        from feature_engineering.build_features import FeatureBuilder
        result = {}
        for sym in ["VIRTUAL", "AIXBT"]:
            try:
                df = MarketData.fetch_ohlcv_custom(sym, days=30)
                df = FeatureBuilder.build_from_memory(df)
                last = df.iloc[-1]
                result[sym] = {
                    "price": round(float(last['close']), 6),
                    "rsi_14": round(float(last.get('rsi_14', 0)), 1),
                    "ma20": round(float(last.get('ma20', 0)), 6),
                    "ma50": round(float(last.get('ma50', 0)), 6),
                    "bb_bandwidth": round(float(last.get('bb_bandwidth_20', 0)), 4),
                    "returns_1h": round(float(last.get('returns', 0)) * 100, 2),
                }
            except Exception as e:
                result[sym] = {"error": str(e)}
        # Sentiment（複数ソースから直接取得）
        try:
            import urllib.request, json as _json
            # Fear & Greed Index
            _fg_resp = urllib.request.urlopen("https://api.alternative.me/fng/?limit=1", timeout=10)
            _fg_data = _json.loads(_fg_resp.read())
            _fg_val = _fg_data["data"][0]["value"]
            _fg_class = _fg_data["data"][0]["value_classification"]
            result["sentiment"] = {
                "fear_greed_value": int(_fg_val),
                "fear_greed_class": _fg_class,
            }
            # BTC trend (simple: price vs 7d ago)
            try:
                _btc_resp = urllib.request.urlopen("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=10)
                _btc_data = _json.loads(_btc_resp.read())
                _btc_change = _btc_data.get("bitcoin", {}).get("usd_24h_change", 0)
                if _btc_change > 2: _trend = "BULLISH"
                elif _btc_change < -2: _trend = "BEARISH"
                else: _trend = "NEUTRAL"
                result["sentiment"]["btc_24h_change"] = round(_btc_change, 2)
                result["sentiment"]["btc_trend"] = _trend
            except:
                result["sentiment"]["btc_trend"] = "unknown"
        except:
            result["sentiment"] = {"error": "unavailable"}
        result["timestamp"] = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099, log_level="info")
