from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from datetime import datetime, timezone
import json
import os
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

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

        scout = Agent(
            role='Ecosystem Scout',
            goal='Virtuals Protocol内の最新トレンドと機会を特定する',
            backstory='Web検索を駆使して市場の機会を発掘するスカウト。',
            tools=[WebSearchTool()],
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            verbose=True
        )

        architect = Agent(
            role='ACP Architect',
            goal='機会をACP形式のペイロードに変換する',
            backstory='戦略をJSONデータに変換するエンジニア。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            verbose=True
        )

        research_task = Task(
            description=f"目標: {goal}\n文脈: {context}\n条件: {constraints}\n\n検索キーワード: '{query}' を使用して調査を行ってください。",
            expected_output='最新のトレンド情報と市場機会のリスト。',
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
