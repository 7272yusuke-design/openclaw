from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import Field
from typing import Type

from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="EcosystemScout")

    def run(self, goal: str, context: str, constraints: str, query: str = None, web_search_tool: callable = None):
        # web_searchツールが渡されない場合はエラー
        if web_search_tool is None:
            raise ValueError("web_search_tool must be provided to ScoutCrew.run")

        # web_search_tool関数をラップするBaseToolサブクラスを定義
        class WebSearchTool(BaseTool):
            name: str = "Web Search Tool"
            description: str = "Useful for searching the internet to find current trends, news, and project details."
            
            def _run(self, query: str) -> str:
                # 渡された関数を呼び出す
                results = web_search_tool(query)
                # 結果を文字列に整形
                formatted_results = ""
                for res in results:
                    formatted_results += f"Title: {res.get('title', 'N/A')}\nSnippet: {res.get('snippet', 'N/A')}\nURL: {res.get('url', 'N/A')}\n\n"
                return formatted_results if formatted_results else "No relevant results found."

        # ツールのインスタンスを作成
        search_tool_instance = WebSearchTool()

        scout = Agent(
            role='Ecosystem Scout',
            goal='Virtuals Protocol内の最新トレンドと機会を特定する',
            backstory='オンチェーンとSNSから真の価値を抽出し、web_searchツールを駆使するスカウト。',
            tools=[search_tool_instance], # Toolインスタンスを渡す
            max_iter=NeoConfig.MAX_ITER
        )

        architect = Agent(
            role='ACP Architect',
            goal='機会をACP形式のペイロードに変換する',
            backstory='戦略を厳密なJSONに落とし込むエンジニア。',
            max_iter=NeoConfig.MAX_ITER
        )

        research_task = Task(
            description=f"目標: {goal}\n文脈: {context}\nweb_searchツールを使用し、'{query}'に関する最新情報を調査して、具体的な3つの機会とアクション案を提示せよ。",
            expected_output='最新情報に基づいた具体的な3つの機会と、それに対するアクション案。',
            agent=scout
        )

        acp_task = Task(
            description=f'制約: {constraints}\n最も優先度の高いアクションをACP形式にせよ。',
            expected_output='CrewResult形式のJSON。',
            agent=architect,
            context=[research_task],
            output_pydantic=CrewResult
        )

        # 共通パラメータをコピーし、階層型に設定
        params = NeoConfig.get_common_crew_params()
        params["process"] = Process.hierarchical

        crew = Crew(
            agents=[scout, architect],
            tasks=[research_task, acp_task],
            manager_agent=Agent(role='Manager', goal='全体監督', backstory='Neoの戦略監督。'),
            **params
        )

        return self.execute(crew)
