from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult
import json
import os

class DevelopmentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="AgentDevelopment")

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
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # 2. Senior Developer: 具体的な修正コードを実装
        developer = Agent(
            role='Lead Software Engineer',
            goal='Reviewerの改善提案に基づき、堅牢で最適化されたコード修正案を作成する',
            backstory='あなたはDeepSeek-V3の推論力を極限まで引き出すエンジニア。プロンプトの微調整からロジックの書き換えまで、システムの自己高度化に必要なコード修正を即座に実装する。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
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
