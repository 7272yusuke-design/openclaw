from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import Field
from typing import Type, Dict, List, Any
import json
import os

from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="EcosystemScout")
        # Initialize performance metrics
        self.search_query_count = 0
        self.search_result_count = 0
        self.info_relevance_score = 0.0
        self.trend_detection_accuracy = 0.0
        self.new_info_count = 0
        self.last_run_results = None # To store results for post-run analysis

    def run(self, goal: str, context: str, constraints: str, query: str = None, web_search_tool: callable = None):
        # web_searchツールが渡されない場合はエラー
        if web_search_tool is None:
            raise ValueError("web_search_tool must be provided to ScoutCrew.run")

        # web_search_tool関数をラップするBaseToolサブクラスを定義
        class WebSearchTool(BaseTool):
            name: str = "Web Search Tool"
            description: str = "Useful for searching the internet to find current trends, news, and project details."
            parent_scout_crew: Any = None # Reference to the parent ScoutCrew instance
            
            def _run(self, query: str) -> str:
                self.parent_scout_crew.search_query_count += 1 # Increment query count

                # 渡された関数を呼び出す
                results = web_search_tool(query)

                # Increment result count if results are returned
                if results:
                    self.parent_scout_crew.search_result_count += len(results)
                
                # 結果を文字列に整形
                formatted_results = ""
                if results:
                    for res in results:
                        formatted_results += f"Title: {res.get('title', 'N/A')}\nSnippet: {res.get('snippet', 'N/A')}\nURL: {res.get('url', 'N/A')}\n\n"
                else:
                    formatted_results = "No relevant results found."
                
                # For performance metrics calculation, we need to return the raw results
                # or a structure that allows for post-processing.
                # Let's return the formatted string and also store raw results in parent for further analysis
                self.parent_scout_crew.last_run_results = results 
                return formatted_results

        # ツールのインスタンスを作成
        search_tool_instance = WebSearchTool()
        # Pass the parent ScoutCrew instance to the tool
        search_tool_instance.parent_scout_crew = self 

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

        # Execute crew and log performance metrics after completion
        execution_result = self.execute(crew)
        self._log_performance_metrics(research_task.expected_output) # Log metrics after execution
        return execution_result

    def _log_performance_metrics(self, expected_output: str):
        """Logs performance metrics for the Scout Crew."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "performance_metrics.jsonl")

        # Simple heuristics for relevance and accuracy based on available data
        # In a real scenario, these would be more sophisticated evaluations
        # For now, we'll use simple rules based on number of results and presence of keywords
        if self.last_run_results:
            # Ensure search_result_count is updated in WebSearchTool._run first
            if self.search_result_count > 0:
                self.info_relevance_score = 0.7 # Assume moderate relevance if results are found
                self.trend_detection_accuracy = 0.6 # Assume moderate accuracy
                self.new_info_count = min(self.search_result_count, 3) # Count up to 3 important pieces of info
                # Basic check for keywords like "opportunity", "action" in snippets
                for res in self.last_run_results:
                    snippet = res.get('snippet', '').lower()
                    if "opportunity" in snippet or "action" in snippet:
                        self.new_info_count += 1 # Count based on keywords found

            else: # No results found
                self.info_relevance_score = 0.1
                self.trend_detection_accuracy = 0.1
                self.new_info_count = 0
        else: # No results were even processed by the tool
            self.info_relevance_score = 0.05
            self.trend_detection_accuracy = 0.05
            self.new_info_count = 0


        # Ensure counts are integers
        self.search_query_count = int(self.search_query_count)
        self.search_result_count = int(self.search_result_count)
        self.new_info_count = int(self.new_info_count)

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "crew": self.name,
            "metrics": {
                "search_query_count": self.search_query_count,
                "search_result_count": self.search_result_count,
                "info_relevance_score": round(self.info_relevance_score, 2),
                "trend_detection_accuracy": round(self.trend_detection_accuracy, 2),
                "new_info_count": self.new_info_count
            }
        }

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
            print(f"Scout Crew performance metrics logged to {log_file}")
        except Exception as e:
            print(f"Error logging Scout Crew performance metrics: {e}")
