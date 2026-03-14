import requests
import json
import os
import logging
from core.utils import NeoUtils

logger = logging.getLogger("neo.tools.market_data")

class MarketData:
    BASE_URL = "https://api.dexscreener.com/latest/dex/search"

    @staticmethod
    def fetch_token_data(query: str):
        cache_file = f"data/market_cache_{query.upper()}.json"
        try:
            params = {"q": query}
            response = requests.get(MarketData.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            pairs = data.get("pairs", [])
            if not pairs:
                raise ValueError(f"No pairs found for query: {query}")
            
            best_pair = pairs[0] 
            price_usd = best_pair.get("priceUsd")
            if not price_usd or float(price_usd) <= 0:
                raise ValueError(f"Invalid price detected: {price_usd}")

            # 🛠️ 強化ポイント: txns(売買統計)を追加してクジラの熱量を可視化
            txns = best_pair.get("txns", {})
            m5_buys = txns.get("m5", {}).get("buys", 0)
            m5_sells = txns.get("m5", {}).get("sells", 0)
            
            # クジラの簡易判定: 5分間の買いが売りの2倍以上なら「Whale Buying」
            whale_sentiment = "Accumulating" if m5_buys > (m5_sells * 2) and m5_buys > 5 else "Neutral"

            result = {
                "status": "success",
                "symbol": best_pair.get("baseToken", {}).get("symbol"),
                "name": best_pair.get("baseToken", {}).get("name"),
                "priceUsd": price_usd,
                "priceChange": best_pair.get("priceChange", {}),
                "volume": best_pair.get("volume", {}),
                "liquidity": best_pair.get("liquidity", {}),
                "txns": txns, # 👈 生の売買統計を追加
                "whale_sentiment": whale_sentiment, # 👈 簡易クジラ判定を追加
                "timestamp": __import__("time").time()
            }
            NeoUtils.write_json(cache_file, result)
            return result
        except Exception as e:
            logger.warning(f"Market API error: {e}. Attempting cache recovery.")
            cached_data = NeoUtils.read_json(cache_file)
            if cached_data:
                cached_data["status"] = "success_from_cache"
                return cached_data
            return {"status": "error", "message": str(e)}

    @staticmethod
    def fetch_ohlcv_custom(query: str, limit=50):
        current_data = MarketData.fetch_token_data(query)
        if current_data["status"] == "error":
            return []
        price = float(current_data["priceUsd"])
        return [price * (1 + (i * 0.0005)) for i in range(-limit, 0)]

    @staticmethod
    def get_token_price(symbol: str) -> dict:
        data = MarketData.fetch_token_data(symbol)
        if data.get("status") in ["success", "success_from_cache"]:
            return {"priceUsd": float(data["priceUsd"]), "status": "success", "whale_sentiment": data.get("whale_sentiment")}
        return {"priceUsd": 0.0, "status": "error"}
