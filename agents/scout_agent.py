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
        # ツール定義
        tools = []
        
        # Web検索ツール (提供されている場合のみ)
        if web_search_tool:
            class WebSearchTool(BaseTool):
                name: str = "Web Search Tool"
                description: str = "Useful for searching the internet to find current trends and news."
                def _run(self, search_query: str) -> str:
                    try:
                        results = web_search_tool(search_query)
                        if not results: return "No results found."
                        formatted = ""
                        for res in results:
                            formatted += f"Title: {res.get('title', 'N/A')}\nSnippet: {res.get('snippet', 'N/A')}\nURL: {res.get('url', 'N/A')}\n\n"
                        return formatted
                    except Exception as e:
                        return f"Search failed: {str(e)}"
            tools.append(WebSearchTool())

        # 暗号資産データツール (メイン武器: データをAIが読みやすい形式に要約する)
        class CryptoTool(BaseTool):
            name: str = "Crypto Market Data Tool"
            description: str = "Useful for getting real-time crypto prices, trending coins, and top coins. Actions: 'price <symbol>', 'trending', 'top'."
            
            def _run(self, action_query: str) -> str:
                try:
                    parts = action_query.split()
                    action = parts[0].lower()
                    
                    if action == "price":
                        coin_ids = parts[1:] if len(parts) > 1 else ["virtuals-protocol"]
                        raw = CryptoMarketData.get_price(coin_ids)
                        # AIが読みやすいように要約
                        summary = ""
                        for coin, data in raw.items():
                            usd = data.get("usd", "N/A")
                            change = data.get("usd_24h_change", 0)
                            summary += f"- {coin.upper()}: ${usd} ({change:+.2f}% 24h)\n"
                        return summary if summary else "No price data found."
                        
                    elif action == "trending":
                        raw = CryptoMarketData.get_trending()
                        # トレンド上位5件の情報を抽出
                        coins = raw.get("coins", [])[:5]
                        summary = "### Trending Coins (Top 5)\n"
                        for c in coins:
                            item = c.get("item", {})
                            summary += f"- {item.get('name')} ({item.get('symbol')}): Price BTC: {item.get('price_btc', 'N/A')}, Rank: {item.get('score', 'N/A')}\n"
                        return summary if summary else "No trending data found."
                        
                    elif action == "top":
                        raw = CryptoMarketData.get_top_coins(limit=10)
                        summary = "### Top 10 Coins by Market Cap\n"
                        for c in raw:
                            summary += f"- {c.get('name')} ({c.get('symbol').upper()}): Price: ${c.get('current_price')}, Market Cap: ${c.get('market_cap'):,}\n"
                        return summary if summary else "No top coins data found."
                        
                    return "Unknown action."
                except Exception as e:
                    return f"Crypto data fetch failed: {str(e)}"
        tools.append(CryptoTool())

        scout = Agent(
            role='Ecosystem Scout',
            goal='Virtuals Protocol内の市場データに基づき、具体的で実行可能なトレンドと機会を特定する',
            backstory='Crypto Market Data Toolの専門家。取得した生の数値データから市場のパターンを読み解き、論理的な投資機会や戦略的トレンドを抽出します。情報が不十分な場合でも、現状から最善の推論を導き出す責任を持ちます。',
            llm=NeoConfig.get_llm(NeoConfig.MODEL_EYES),
            tools=tools,
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            verbose=True
        )

        architect = Agent(
            role='ACP Architect',
            goal='市場データに基づく機会をACP形式のペイロードに変換する',
            backstory='分析結果を具体的なオンチェーン戦略（JSON）に変換するエンジニア。',
            llm=NeoConfig.get_llm(NeoConfig.MODEL_HANDS),
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            verbose=True
        )

        research_task = Task(
            description=f"""
## Identity
あなたはVirtuals Protocolエコシステムを専門とするEcosystem Scoutです。
**Crypto Market Data Tool** を駆使し、市場データを構造化されたインテリジェンスとして報告します。

## Context
### Rules (厳守)
1. **Crypto Market Data Toolを必ず使用せよ。**
2. 取得したデータ（価格、トレンド）に基づき、市場の機会を論理的に抽出せよ。
3. 出力は、後続のACP Architectが直接処理可能な、極めて具体的で構造化された形式とする。

### Current State
{context}

## Task
{goal}

## Process
1. Crypto Market Data Toolで 'trending' と 'price virtuals-protocol' を取得する。
2. データを解析し、現在の市場フェーズにおける最適な機会（Opportunity）を特定する。
3. その結果を、詳細にまとめよ。
""",
            expected_output='市場データに基づき構造化された、最新のトレンド情報と機会のリスト。',
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
