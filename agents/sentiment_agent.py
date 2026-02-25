from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class SentimentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="SentimentAnalysis")

    def run(self, goal: str, context: str, constraints: str, web_search_tool: callable = None):
        # ツール設定
        tools = []
        if web_search_tool:
             # web_search_tool関数をラップするBaseToolサブクラスを定義
            class WebSearchTool(BaseTool):
                name: str = "Web Search Tool"
                description: str = "Useful for checking market sentiment, latest news, and community discussions."
                
                def _run(self, query: str) -> str:
                    # 渡された関数を呼び出す
                    results = web_search_tool(query)
                    # 結果を文字列に整形
                    formatted_results = ""
                    for res in results:
                        formatted_results += f"Title: {res.get('title', 'N/A')}\nSnippet: {res.get('snippet', 'N/A')}\nURL: {res.get('url', 'N/A')}\n\n"
                    return formatted_results if formatted_results else "No relevant results found."
            
            tools.append(WebSearchTool())

        # エージェント定義
        analyst = Agent(
            role='Sentiment Analyst',
            goal='市場の感情スコアを特定し、トレンドの転換点を見極める',
            backstory='市場の「空気」を読み取る専門家。必要であればWeb検索を駆使して最新情報を収集し、DeepSeek-V3により高度な分析を行います。',
            tools=tools, # ツールを追加
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        planner = Agent(
            role='Strategic Action Planner',
            goal='分析を元に具体的なACPアクションを立案する',
            backstory='感情データを利益に変える戦略家。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        # 分析タスクの説明にWeb検索の使用指示を追加
        task_desc = f'分析目標: {goal}\nデータ: {context}'
        if web_search_tool:
            task_desc += '\n必要に応じてWeb Search Toolを使用し、最新の市場センチメントや関連ニュースを調査して分析に反映させよ。'

        analysis_task = Task(
            description=task_desc,
            expected_output='市場の感情スコア(-1.0 to 1.0)と主要要因。',
            agent=analyst
        )

        action_task = Task(
            description=f'制約: {constraints}',
            expected_output='CrewResult形式のJSONデータ。',
            agent=planner,
            context=[analysis_task],
            output_pydantic=CrewResult
        )

        # Crew編成
        crew = Crew(
            agents=[analyst, planner],
            tasks=[analysis_task, action_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
