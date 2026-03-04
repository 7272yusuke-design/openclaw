from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from datetime import datetime, timezone
import json
import os
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult
from tools.crypto_data import CryptoMarketData

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="EcosystemScout")

    def run(self, goal: str, context: str, constraints: str, query: str = None, web_search_tool: callable = None):
        if web_search_tool is None:
            raise ValueError("web_search_tool must be provided to ScoutCrew.run")

        # シンプルな検索ツールラッパー
        class WebSearchTool(BaseTool):
            name: str = "Web Search Tool"
            description: str = "Useful for searching the internet to find current trends, news, and project details."
            
            def _run(self, search_query: str) -> str:
                # web_search_tool is captured from the closure
                try:
                    results = web_search_tool(search_query)
                    if not results:
                        return "No results found."
                    
                    formatted = ""
                    for res in results:
                        formatted += f"Title: {res.get('title', 'N/A')}\nSnippet: {res.get('snippet', 'N/A')}\nURL: {res.get('url', 'N/A')}\n\n"
                    return formatted
                except Exception as e:
                    return f"Search failed: {str(e)}"

        # 暗号資産データツール
        class CryptoTool(BaseTool):
            name: str = "Crypto Market Data Tool"
            description: str = "Useful for getting real-time crypto prices, trending coins, and top coins by market cap. Input should be a specific action ('price', 'trending', 'top') and optional parameters (e.g., 'bitcoin')."
            
            def _run(self, action_query: str) -> str:
                try:
                    # Parse simple action: "price bitcoin", "trending", "top"
                    parts = action_query.split()
                    action = parts[0].lower()
                    
                    if action == "price":
                        coin_ids = parts[1:] if len(parts) > 1 else ["bitcoin"]
                        return json.dumps(CryptoMarketData.get_price(coin_ids), indent=2)
                    elif action == "trending":
                        return json.dumps(CryptoMarketData.get_trending(), indent=2)
                    elif action == "top":
                        return json.dumps(CryptoMarketData.get_top_coins(limit=10), indent=2)
                    else:
                        return "Unknown action. Use 'price <coin_id>', 'trending', or 'top'."
                except Exception as e:
                    return f"Crypto data fetch failed: {str(e)}"

        scout = Agent(
            role='Ecosystem Scout',
            goal='Virtuals Protocol内の最新トレンドと機会を特定する',
            backstory='Web検索と市場データ分析を駆使して市場の機会を発掘するスカウト。',
            llm=NeoConfig.get_llm(NeoConfig.MODEL_EYES), # Gemini 2.0 Flash (Fast/Context)
            tools=[WebSearchTool(), CryptoTool()],
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            verbose=True
        )

        architect = Agent(
            role='ACP Architect',
            goal='機会をACP形式のペイロードに変換する',
            backstory='戦略をJSONデータに変換するエンジニア。',
            llm=NeoConfig.get_llm(NeoConfig.MODEL_HANDS), # GPT-4o (Structured Output)
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            verbose=True
        )

        research_task = Task(
            description=f"""
## Identity
あなたはVirtuals Protocolエコシステムを専門とするEcosystem Scoutです。
Web検索とリアルタイム市場データを駆使して市場の機会を発掘する達人であり、常に具体的で信頼性の高い情報を求めます。

## Context

### Rules (変更不可)
- Web検索ツールを最大限に活用し、信頼性の高い情報源からデータを収集すること。
- 必要に応じてCrypto Market Data Toolを使用し、価格やトレンドの裏付けを取ること。
- 抽出する情報は、以下の[Constraints]セクションに記載された条件を厳守すること。
- 出力はJSON形式ではなく、自然言語による箇条書きのリストであること。

### Current State (変動可能)
{context}

## Task
{goal}

## Process
1. まず、提供された検索キーワード '{query}' を用いて、市場トレンド、新しいエージェントローンチ、裁定機会に関する広範なWeb検索を実行する。
2. Crypto Market Data Toolを用いて、関連するトークンの現在価格や、市場全体のトレンド情報を取得し、検索結果を補強する。
3. 次に、収集した情報から最も関連性の高い情報源を3つ特定し、それぞれのタイトル、スニペット、URL、および市場データ（価格等）を抽出する。
4. その後、抽出した情報が以下の[Constraints]セクションの条件を満たしているか評価する。
5. 最後に、評価に基づき、最新のトレンド情報と市場機会のリストを詳細にまとめる。

## Output Format
最新のトレンド情報と市場機会のリスト。具体的な機会は、その内容、関連性、URL、市場データを明記して箇条書きで示す。不要な説明やコメントは含めないこと。

## Constraints
{constraints}
""",
            expected_output='最新のトレンド情報と市場機会のリストを箇条書きで詳細に記述したもの。'
,
            agent=scout
        )

        acp_task = Task(
            description=f'発見された機会に基づき、最も優先度の高いアクションを構造化データとして出力せよ。',
            expected_output='CrewResult形式のJSON。',
            agent=architect,
            context=[research_task],
            output_pydantic=CrewResult
        )

        crew = Crew(
            agents=[scout, architect],
            tasks=[research_task, acp_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
