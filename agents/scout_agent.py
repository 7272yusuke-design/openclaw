from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import Field
from typing import Type, Dict, List, Any
import json
import os
import datetime
import traceback
import importlib

from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class EventStackOverflowError(Exception):
    """Custom exception for event stack overflow."""
    pass

class CriticalDependencyError(Exception):
    """Custom exception for critical missing dependencies."""
    pass

class EventStackManager:
    def __init__(self, max_depth=50):
        self.max_depth = max_depth
        self.stack_trace = []
        self.safety_margin = 0.9  # 安全係数

    def execute_event(self, event, execute_fn: callable = None):
        if len(self.stack_trace) >= self.max_depth * self.safety_margin:
            self.log_stack_analysis()
            raise EventStackOverflowError(
                f"Safety threshold reached: {len(self.stack_trace)}/{self.max_depth}"
            )

        self.stack_trace.append({
            'event': event,
            'timestamp': self.get_precise_timestamp(),
            'context': self.get_current_context()
        })

        try:
            # execute_fn が提供されている場合はそれを使用
            if execute_fn:
                result = execute_fn(event)
            else:
                # デフォルトの実行ロジック (イベントオブジェクトに execute メソッドがあると仮定)
                result = event.execute() 
            self.stack_trace.clear()
            return result
        except Exception as e:
            self.log_error_with_context(e)
            self.stack_trace.clear()
            raise

    def get_precise_timestamp(self):
        try:
            from datetime import datetime
            return datetime.utcnow().isoformat() + 'Z'
        except ImportError:
            import time
            return f"unix:{time.time()}"
            
    def get_current_context(self):
        # 現在の実行コンテキストを返す（簡略化）
        return {"current_agent": "ScoutCrew"}

    def log_stack_analysis(self):
        # スタック分析ログ出力（詳細な実装は省略）
        print("Event Stack Analysis: Stack depth safety threshold reached.")
        for item in self.stack_trace:
            print(f"- Event: {item['event']}, Timestamp: {item['timestamp']}")

    def log_error_with_context(self, error):
        # エラーログ出力（詳細な実装は省略）
        print(f"Error in Event Stack: {error}")
        import traceback
        print(traceback.format_exc())


class QueryOptimizer:
    @staticmethod
    def build_dynamic_query(base_query, context):
        """
        コンテキストに基づく動的クエリ生成
        """
        time_filters = {
            'recent': 'AND (last_week OR last_month)',
            'historical': 'AND (year:2025 OR year:2026)'
        }

        sector_filters = {
            'tech': 'AND (technology OR AI OR blockchain)',
            'finance': 'AND (investment OR stocks OR market)'
        }

        query = f"{base_query} {time_filters.get(context.get('timeframe', 'recent'))}"
        query += f" {sector_filters.get(context.get('sector', 'tech'))}"
        query += " site:.edu OR site:.gov OR site:bloomberg.com"

        return query.strip()

# 必須モジュールの安全なロード
ESSENTIAL_MODULES = {
    'datetime': {'min_version': None}, # 標準ライブラリはNone
    'logging': {'min_version': None},
    'traceback': {'min_version': None},
    'numpy': {'optional': True}
}

def load_dependencies():
    missing = []
    for mod, config in ESSENTIAL_MODULES.items():
        try:
            imported = importlib.import_module(mod)
            if config.get('min_version'): # min_versionが設定されている場合のみチェック
                if not hasattr(imported, '__version__'):
                    raise ImportError(f"{mod} version check failed")
                else:
                    version = tuple(map(int, imported.__version__.split('.')[:2]))
                    if version < config['min_version']:
                        raise ImportError(f"{mod} version too old")
            globals()[mod] = imported # グローバルスコープにインポート
        except ImportError as e:
            if not config.get('optional', False):
                missing.append(mod)

    if missing:
        raise CriticalDependencyError(f"Missing required modules: {missing}")

# critical_error の簡易実装 (load_dependencies の後で定義)
def critical_error(message):
    print(f"CRITICAL ERROR: {message}")
    if 'logging' in globals():
        globals()['logging'].error(message)

# 初期ロードを実行
try:
    load_dependencies()
except CriticalDependencyError as e:
    print(f"System initialization failed: {e}")
    raise SystemExit(1)


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
        self.event_stack = EventStackManager() # EventStackManager のインスタンスを初期化

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
                # EventStack を使用して処理をラップ
                def execute_search_logic(q: str):
                    self.parent_scout_crew.search_query_count += 1 # Increment query count

                    # 渡された関数を呼び出す
                    results = web_search_tool(q)

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
                    
                    self.parent_scout_crew.last_run_results = results 
                    return formatted_results

                return self.parent_scout_crew.event_stack.execute_event(event=query, execute_fn=execute_search_logic)

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
            description=f"""
            目標: {goal}
            文脈: {context}
            
            web_searchツールを駆使し、以下の調査を遂行せよ:
            1. '{query}' に関する最新トレンドと機会を3つ特定。
            2. 主要なDEX (Virtuals DEX, Uniswap on Base) 間での特定トークンの価格差（アービトラージ機会）を調査。
            3. 発見した価格差について、手数料を考慮する前の単純な乖離率を報告せよ。
            """,
            expected_output='最新トレンド情報と、特定されたDEX間の価格乖離データ。',
            agent=scout
        )

        acp_task = Task(
            description=f'制約: {constraints}\n最も優先度の高いアクションをACP形式にせよ。',
            expected_output='CrewResult形式のJSON。',
            agent=architect,
            context=[research_task],
            output_pydantic=CrewResult
        )

        # 共通パラメータ（デフォルトは sequential）を使用
        params = NeoConfig.get_common_crew_params()

        crew = Crew(
            agents=[scout, architect],
            tasks=[research_task, acp_task],
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
            print(f"Error logging Scout Crew performance metrics: {e}\n{traceback.format_exc()}")
