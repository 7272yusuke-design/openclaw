from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult
import json
import os
from tools.gsd_tool import get_gsd_tools

class DevelopmentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="AgentDevelopment")
        self.gsd_tools = get_gsd_tools()

    def run(self, spec: str, language: str = "python", execution_logs: str = "", error_report: str = "", performance_log_path: str = None, market_cycle_log_path: str = None):
        # 1. パフォーマンスログと市場サイクルログの読み込み
        additional_context = ""
        
        if performance_log_path and os.path.exists(performance_log_path):
            try:
                with open(performance_log_path, 'r', encoding='utf-8') as f:
                    perf_data = [json.loads(line) for line in f if line.strip()][-10:] # 直近10件
                    additional_context += f"\n【Scout Crew パフォーマンスメトリクス】:\n{json.dumps(perf_data, indent=2, ensure_ascii=False)}\n"
            except Exception as e:
                print(f"Warning: Failed to load performance logs: {e}")

        if market_cycle_log_path and os.path.exists(market_cycle_log_path):
            try:
                with open(market_cycle_log_path, 'r', encoding='utf-8') as f:
                    cycle_data = [json.loads(line) for line in f if line.strip()][-5:] # 直近5件
                    additional_context += f"\n【直近の市場サイクル実行結果】:\n{json.dumps(cycle_data, indent=2, ensure_ascii=False)}\n"
            except Exception as e:
                print(f"Warning: Failed to load market cycle logs: {e}")

        # 1. Code Reviewer: 実行ログとパフォーマンスデータを分析し、改善点を特定
        reviewer = Agent(
            role='System Architect & Reviewer',
            goal='システムの実行ログとパフォーマンス指標を分析し、自律的な進化のための改善点を特定する',
            backstory='Neoの自己進化を司る監査役。単なるエラー修正だけでなく、Scout Crewの検索精度向上や戦略の洗練など、システムの「質」を高めるためのボトルネックを見つけ出す達人。',
            llm=NeoConfig.get_agent_llm(NeoConfig.MODEL_BRAIN), # Agent LLM (OpenRouter)
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # 2. Senior Developer: 具体的な修正コードを実装
        developer = Agent(
            role='Lead Software Engineer',
            goal='Reviewerの改善提案に基づき、堅牢で最適化されたコード修正案を作成する。大規模な改修が必要な場合はGSD (Get-Shit-Done) フレームワークを用いて計画的に進める。',
            backstory='あなたはClaude 3.5 Sonnetの推論力を極限まで引き出すエンジニア。プロンプトの微調整からロジックの書き換えまで、システムの自己高度化に必要なコード修正を即座に実装する。',
            llm=NeoConfig.get_agent_llm(NeoConfig.MODEL_BRAIN), # Agent LLM (OpenRouter)
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            tools=self.gsd_tools  # GSDツールを追加
        )

        # タスク定義
        analysis_task_desc = f"""
        【改善目標】: {spec}
        【基本実行ログ】: {execution_logs}
        【エラー報告】: {error_report}
        {additional_context}

        現状のシステム挙動とパフォーマンス指標を詳細に分析し、以下の点を明らかにせよ:
        1. Performance Evaluation: Scout Crewの検索クエリ数、結果数、関連性スコアは適切か？
        2. Bottleneck Discovery: 情報収集の質を下げている原因、または戦略立案の精度を下げている要因は何か？
        3. Optimization Strategy: コード、検索クエリ、プロンプト、またはパラメータのどこを修正して「自己高度化」すべきか。
        4. Risk Assessment: 修正による副作用（コスト増、処理遅延など）の可能性。
        """
        
        analysis_task = Task(
            description=analysis_task_desc,
            expected_output='パフォーマンス評価、根本原因、具体的な最適化戦略を含む分析レポート。',
            agent=reviewer
        )

        # Implementation Task (実装)
        impl_task_desc = f"""
        Reviewerの分析結果に基づき、Scout CrewやPlanning Crewの能力を向上させるための具体的な修正コード（Python）またはプロンプト調整案を作成せよ。
        
        出力はCrewResult形式のJSONとし、以下の要素を必ず含めること:
        - status: \"success\"
        - summary: 自己高度化のための修正内容の要約
        - virtuals_payload: {{
            \"file_path\": \"修正対象のファイルパス (例: agents/scout_agent.py)\",
            \"code_patch\": \"修正後のコード全体、または重要な変更箇所。プロンプト修正の場合はその内容。\"
          }}
        - next_action_suggestion: この修正を適用することで期待されるパフォーマンス向上
        """

        implementation_task = Task(
            description=impl_task_desc,
            expected_output='具体的な自己高度化コードを含むCrewResult形式のJSON。',
            agent=developer,
            context=[analysis_task],
            output_pydantic=CrewResult
        )

        # Crew編成
        crew = Crew(
            agents=[reviewer, developer],
            tasks=[analysis_task, implementation_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)

    def run_parallel_roadmap(self, roadmap_path: str = "ROADMAP.md"):
        """
        ROADMAP.md を読み込み、依存関係のないタスクを並列実行する動的ループ。
        """
        from tools.gsd_tool import GSDTool
        
        print(f"--- Starting Parallel Execution Loop for {roadmap_path} ---")
        gsd_tool = GSDTool()
        
        # Define Worker Agent (Generic executor for GSD tasks)
        worker = Agent(
            role='GSD Task Executor',
            goal='ROADMAP.md に定義されたタスクを迅速かつ正確に実行する',
            backstory='GSDフレームワークの忠実な実行者。並列処理に対応し、独立したタスクを同時にこなす能力を持つ。',
            llm=NeoConfig.get_agent_llm(NeoConfig.MODEL_HANDS),
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False,
            tools=self.gsd_tools
        )

        while True:
            # Step A: Get Parallel Tasks
            executable_tasks = gsd_tool.get_parallel_tasks(roadmap_path)
            
            # Step B: Termination Check
            if not executable_tasks:
                print("✅ All tasks completed or no executable tasks found.")
                break
            
            print(f"🚀 Dispatching {len(executable_tasks)} tasks in parallel: {[t['id'] for t in executable_tasks]}")
            
            # Step C: Create CrewAI Tasks (Async)
            crew_tasks = []
            for task_info in executable_tasks:
                # 実際のタスク内容（ファイル作成など）を指示に含める
                task_desc = f"""
                Execute the following GSD Task:
                {task_info['desc']}
                
                If the task involves creating a file, use the 'write' tool (via Python or GSD tools).
                If the task is just analysis, provide the report.
                
                Original definition: {task_info['original_line']}
                """
                
                crew_task = Task(
                    description=task_desc,
                    expected_output="Detailed execution result and confirmation of completion.",
                    agent=worker,
                    async_execution=True # Key for Parallelism
                )
                crew_tasks.append(crew_task)
            
            # Step D: Aggregation Task (Sync) - Required for async batch to complete
            aggregator_task = Task(
                description="Wait for all parallel tasks to complete and summarize their results.",
                expected_output="Summary of all completed tasks.",
                agent=worker,
                context=crew_tasks # Depends on async tasks -> Forces wait
            )
            
            # Execute Batch
            crew = Crew(
                agents=[worker],
                tasks=crew_tasks + [aggregator_task],
                verbose=True,
                process=Process.sequential # Async tasks run in background, aggregator waits
            )
            
            result = crew.kickoff()
            
            # Step E: Update Status
            self._mark_tasks_complete(roadmap_path, executable_tasks)
            
        print("--- Parallel Execution Loop Completed ---")

    def _mark_tasks_complete(self, roadmap_path, tasks):
        """Helper to update ROADMAP.md status from [ ] to [x]"""
        if not os.path.exists(roadmap_path):
             return

        with open(roadmap_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated_count = 0
        for t in tasks:
            # Replace "- [ ] Task..." with "- [x] Task..."
            # Using original_line which contains the exact line from the file.
            original = t['original_line']
            # Only replace the first occurrence of "- [ ]" in that specific line context
            # A safer way is to replace the whole line.
            
            if original in content:
                # Assuming standard format "- [ ] ..."
                completed_line = original.replace("- [ ]", "- [x]", 1)
                content = content.replace(original, completed_line, 1) # Replace only one occurrence to be safe
                updated_count += 1
            else:
                print(f"Warning: Could not find original line in ROADMAP.md: '{original}'")
        
        with open(roadmap_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated ROADMAP.md: Marked {updated_count} tasks as complete.")
