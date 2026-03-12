import json
import logging

logger = logging.getLogger("neo.tools.data_fetcher")

class DataFetcher:
    """
    CrewAIが理解しやすい形式にデータを変換するユーティリティ。
    """
    @staticmethod
    def format_for_crew(raw_data: list) -> str:
        """SNSやウェブの生データをテキスト形式に整形する"""
        if not raw_data:
            return "No recent data available."
        
        formatted = []
        for item in raw_data:
            title = item.get("title", "Untitled")
            snippet = item.get("snippet", "No description.")
            url = item.get("url", "N/A")
            formatted.append(f"Title: {title}\nSnippet: {snippet}\nURL: {url}\n---")
            
        return "\n".join(formatted)

    @staticmethod
    def create_sentiment_input(goal: str, market_context: str, sns_data: str) -> dict:
        """SentimentAnalysisCrew向けの入力を生成する"""
        return {
            "goal": goal,
            "context": f"Market Data Context:\n{market_context}\n\nSocial Signals:\n{sns_data}",
            "constraints": "Focus on identifying strong bullish or bearish patterns."
        }
