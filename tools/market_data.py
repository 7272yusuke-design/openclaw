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
        """
        try:
            params = {"q": query}
            response = requests.get(MarketData.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pairs = data.get("pairs", [])
            
            if not pairs:
                return {"status": "error", "message": "No pairs found"}

            # 最も流動性が高いペアを抽出
            # Virtuals Protocol関連 (Baseチェーン) を優先するロジックなどをここに追加可能
            best_pair = pairs[0] 
            
            return {
                "status": "success",
                "symbol": best_pair.get("baseToken", {}).get("symbol"),
                "name": best_pair.get("baseToken", {}).get("name"),
                "priceUsd": best_pair.get("priceUsd"),
                "priceChange": best_pair.get("priceChange", {}), # 5m, 1h, 6h, 24h
                "volume": best_pair.get("volume", {}),
                "liquidity": best_pair.get("liquidity", {}),
                "url": best_pair.get("url"),
                "pairAddress": best_pair.get("pairAddress"),
                "chainId": best_pair.get("chainId")
            }
            
        except Exception as e:
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
