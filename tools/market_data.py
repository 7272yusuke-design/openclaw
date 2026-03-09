import requests
import json
import os
import logging
from core.utils import NeoUtils

logger = logging.getLogger("neo.tools.market_data")

class MarketData:
    """
    DexScreener APIを利用して、リアルタイムの市場データを取得するクラス。
    NeoUtils を活用してパス解決とキャッシュ管理を行う。
    """
    
    BASE_URL = "https://api.dexscreener.com/latest/dex/search"

    @staticmethod
    def fetch_token_data(query: str):
        """
        クエリ（トークン名、シンボル、アドレス）に基づいて市場データを取得する。
        """
        cache_file = f"data/market_cache_{query.upper()}.json"
        
        try:
            params = {"q": query}
            response = requests.get(MarketData.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pairs = data.get("pairs", [])
            
            if not pairs:
                raise ValueError(f"No pairs found for query: {query}")

            # 最も流動性が高いペアを抽出
            best_pair = pairs[0] 
            price_usd = best_pair.get("priceUsd")
            
            if not price_usd or float(price_usd) <= 0:
                raise ValueError(f"Invalid price detected: {price_usd}")
            
            result = {
                "status": "success",
                "symbol": best_pair.get("baseToken", {}).get("symbol"),
                "name": best_pair.get("baseToken", {}).get("name"),
                "priceUsd": price_usd,
                "priceChange": best_pair.get("priceChange", {}),
                "volume": best_pair.get("volume", {}),
                "liquidity": best_pair.get("liquidity", {}),
                "url": best_pair.get("url"),
                "timestamp": __import__("time").time()
            }
            
            # キャッシュ保存
            NeoUtils.write_json(cache_file, result)
            return result
            
        except Exception as e:
            logger.warning(f"Market API error for {query}: {e}. Attempting cache recovery.")
            cached_data = NeoUtils.read_json(cache_file)
            if cached_data:
                cached_data["status"] = "success_from_cache"
                return cached_data
            
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_token_price(symbol: str) -> dict:
        """PaperTrader等で使用する簡略化された価格取得メソッド"""
        data = MarketData.fetch_token_data(symbol)
        if data.get("status") in ["success", "success_from_cache"]:
            return {"priceUsd": float(data["priceUsd"]), "status": "success"}
        return {"priceUsd": 0.0, "status": "error", "message": data.get("message", "Unknown error")}
