import requests
import pandas as pd
from crewai.tools import BaseTool
from pydantic import Field
from typing import Any

class MarketDataTool(BaseTool):
    name: str = "Market Data Tool"
    description: str = (
        "Fetches real-time market data for the Virtuals Protocol ($VIRTUAL) on Base chain. "
        "Returns price, market cap, volume, and raw data for pandas analysis."
    )
    token_address: str = Field(default="0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b")

    def _run(self, query: str = None) -> str:
        """DEX Screener APIから$VIRTUALのデータを取得し、解析用テキストを返す"""
        url = f"https://api.dexscreener.com/latest/dex/tokens/{self.token_address}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("pairs"):
                return "Error: No trading pairs found for the token."
            
            # 最も流動性が高いペアを取得
            pair = data["pairs"][0]
            
            # 基本統計
            price = pair.get("priceUsd", "N/A")
            mcap = pair.get("marketCap", 0)
            vol_24h = pair.get("volume", {}).get("h24", 0)
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            
            # pandas解析用の簡易サマリーを作成
            summary = (
                f"--- $VIRTUAL Real-time Stats ---\n"
                f"Price: ${price}\n"
                f"Market Cap: ${mcap:,.2f}\n"
                f"24h Volume: ${vol_24h:,.2f}\n"
                f"Liquidity: ${liquidity:,.2f}\n"
                f"DEX: {pair.get('dexId', 'unknown')}\n"
                f"URL: {pair.get('url', '')}\n"
                f"---------------------------------\n"
                f"Data fetched from DEX Screener. You can use these numbers for ROI calculations or pandas trend analysis."
            )
            return summary
            
        except Exception as e:
            return f"Failed to fetch market data: {str(e)}"

if __name__ == "__main__":
    # 単体テスト
    tool = MarketDataTool()
    print(tool._run())
