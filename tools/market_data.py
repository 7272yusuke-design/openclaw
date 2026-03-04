import requests
import json

class MarketData:
    """
    DexScreener APIを利用して、リアルタイムの市場データ（価格、変動率、流動性）を取得するクラス。
    API Key不要、Read-Onlyで安全に利用可能。
    """
    
    BASE_URL = "https://api.dexscreener.com/latest/dex/search"

    @staticmethod
    def fetch_token_data(query: str):
        """
        クエリ（トークン名、シンボル、アドレス）に基づいて市場データを取得する。
        キャッシュファイルを使用してAPIエラー時や異常値（価格0など）に対する耐性を持たせる。
        """
        cache_path = f"data/market_cache_{query.upper()}.json"
        
        try:
            params = {"q": query}
            response = requests.get(MarketData.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pairs = data.get("pairs", [])
            
            if not pairs:
                raise ValueError("No pairs found in API response")

            # 最も流動性が高いペアを抽出
            best_pair = pairs[0] 
            price_usd = best_pair.get("priceUsd")
            
            # 価格が0またはNoneの場合は異常値として扱う
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
                "pairAddress": best_pair.get("pairAddress"),
                "chainId": best_pair.get("chainId"),
                "timestamp": __import__("time").time()
            }
            
            # 正常データをキャッシュに保存
            os.makedirs("data", exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(result, f)
                
            return result
            
        except Exception as e:
            # APIエラー時はキャッシュから復旧を試みる
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    cached_data = json.load(f)
                    cached_data["status"] = "success_from_cache"
                    cached_data["error_info"] = str(e)
                    return cached_data
            
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_token_price(symbol: str) -> dict:
        """
        指定されたシンボルのトークン価格を取得する（PaperTrader用）。
        """
        data = MarketData.fetch_token_data(symbol)
        if data.get("status") == "success":
            return {"priceUsd": float(data["priceUsd"]), "status": "success"}
        return {"priceUsd": 0.0, "status": "error", "message": data.get("message", "Unknown error")}

if __name__ == "__main__":
    # テスト実行
    print("Fetching VIRTUAL token data...")
    result = MarketData.fetch_token_data("VIRTUAL")
    print(json.dumps(result, indent=2))
    
    print("\nFetching VIRTUAL token price...")
    price_result = MarketData.get_token_price("VIRTUAL")
    print(json.dumps(price_result, indent=2))
