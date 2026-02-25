import json
from typing import List, Dict

class DataFetcher:
    """
    OpenClawのツール(web_search/web_fetch)を活用し、
    CrewAIに渡すための整形済みデータを生成するクラス。
    """
    
    @staticmethod
    def format_for_crew(raw_results: List[Dict]) -> str:
        """
        検索結果などの生データを、トークン節約のために
        「Context」として最適な短いテキスト形式に整形する。
        """
        formatted_text = ""
        for i, res in enumerate(raw_results):
            title = res.get("title", "No Title")
            snippet = res.get("snippet", "No Content")
            source = res.get("url", "No URL")
            formatted_text += f"--- Source {i+1} ---\nTitle: {title}\nContent: {snippet}\nURL: {source}\n\n"
        
        return formatted_text

    @staticmethod
    def fetch_realtime_data(query: str) -> List[Dict]:
        """
        実際に Web 検索を行い、最新のデータを取得する (OpenClaw の web_search を想定)
        """
        print(f"Searching for: {query}...")
        return [] # このメソッドは neo_main.py から OpenClaw の web_search 呼び出しを介在して利用される

    @staticmethod
    def create_sentiment_input(goal: str, market_data: str, sns_data: str):
        """
        SentimentWorkerに渡すための3要素(Goal, Context, Constraints)を生成する。
        """
        context = f"【市場データ】\n{market_data}\n\n【SNS/ニュースデータ】\n{sns_data}"
        constraints = (
            "1. 客観的な事実と主観的な感情を分離して分析せよ。\n"
            "2. Virtuals Protocol(ACP)でのアクションに直結するインサイトを抽出せよ。\n"
            "3. 200文字以内で要約せよ。"
        )
        
        return {
            "goal": goal,
            "context": context,
            "constraints": constraints
        }
