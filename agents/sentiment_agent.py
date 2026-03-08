from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig, get_agent_llm
from bridge.crewai_bridge import CrewResult
from tools.obsidian_tool import ObsidianTool

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

        # Obsidian MCP Tool (Append Capability)
        obsidian_tool = ObsidianTool()
        tools.append(obsidian_tool)

        # エージェント定義
        analyst = Agent(
            role='Sentiment Analyst',
            goal='市場の感情スコアを特定し、Obsidian Vaultに記録する',
            backstory='市場の「空気」を読み取る専門家。分析結果は必ずObsidianの `vault/strategy/sentiment_analysis.md` に追記します。',
            tools=tools, # ツールを追加
            llm=get_agent_llm(model_name=NeoConfig.MODEL_EYES), # Agent LLM (OpenRouter)
            max_iter=10, # 試行回数を増やす
            allow_delegation=False,
            verbose=True # デバッグ出力を有効化
        )

        planner = Agent(
            role='Strategic Action Planner',
            goal='分析を元に具体的なACPアクションを立案する',
            backstory='感情データを利益に変える戦略家。',
            llm=get_agent_llm(model_name=NeoConfig.MODEL_HANDS), # Agent LLM (OpenRouter)
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        # 分析タスクの説明にObsidianへの追記指示を追加
        task_desc = f'分析目標: {goal}\nデータ: {context}'
        if web_search_tool:
            task_desc += '\n必要に応じてWeb Search Toolを使用し、最新の市場センチメントや関連ニュースを調査して分析に反映させよ。'
        
        task_desc += '\n\nIMPORTANT: 分析が完了したら、必ず Obsidian Tool を使用して結果を `vault/strategy/sentiment_analysis.md` に追記(append_content)せよ。'
        task_desc += '\n追記する内容は以下のフォーマットに従うこと:\n'
        task_desc += '## Sentiment Analysis Report\n- **Target**: [Target Name]\n- **Score**: [Score]\n- **Summary**: [Summary]\n- **Timestamp**: [Current Time]\n'

        analysis_task = Task(
            description=task_desc,
            expected_output='市場の感情スコア(-1.0 to 1.0)と主要要因。Obsidianへの追記完了メッセージを含むこと。',
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
