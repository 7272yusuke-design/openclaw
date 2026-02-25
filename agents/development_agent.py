from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.config import NeoConfig
from bridge.crewai_bridge import CrewResult

class DevelopmentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="AgentDevelopment")

    def run(self, spec: str, language: str = "python", execution_logs: str = "", error_report: str = ""):
        # 1. Code Reviewer: 実行ログとエラーを分析し、改善点を特定
        reviewer = Agent(
            role='System Architect & Reviewer',
            goal='システムの実行ログを分析し、パフォーマンス向上のための改善点を特定する',
            backstory='Neoの自己進化を司る監査役。失敗から学び、システムのボトルネックや論理的欠陥を見つけ出す達人。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # 2. Senior Developer: 具体的な修正コードを実装
        developer = Agent(
            role='Lead Software Engineer',
            goal='Reviewerの改善提案に基づき、堅牢で最適化されたコード修正案を作成する',
            backstory='あなたはDeepSeek-V3の推論力を極限まで引き出すエンジニアです。クリーンで堅牢なコード修正を即座に実装します。',
            max_iter=NeoConfig.MAX_ITER,
            allow_delegation=False
        )

        # タスク定義
        # Root Cause Analysis Task (原因分析)
        analysis_task_desc = f"""
        【仕様/目標】: {spec}
        【実行ログ】: {execution_logs}
        【エラー報告】: {error_report}

        現状のシステム挙動を分析し、以下の点を明らかにせよ:
        1. Root Cause: なぜ目標が達成されなかったか、またはエラーが発生したか。
        2. Improvement Strategy: コード、設定、またはプロンプトのどこを修正すべきか。
        3. Risk Assessment: 修正による副作用の可能性。
        """
        
        analysis_task = Task(
            description=analysis_task_desc,
            expected_output='根本原因、改善戦略、リスク評価を含む分析レポート。',
            agent=reviewer
        )

        # Implementation Task (実装)
        impl_task_desc = f"""
        Reviewerの分析結果に基づき、具体的な修正コードまたは設定変更案を作成せよ。
        出力はCrewResult形式のJSONとし、以下の要素を必ず含めること:
        - status: "success"
        - summary: 修正内容の要約
        - virtuals_payload: {{
            "file_path": "{language} file path (e.g., agents/planning_agent.py)",
            "code_patch": "修正前後のコードブロック、または新しいコード全体"
          }}
        - next_action_suggestion: 適用手順
        """

        implementation_task = Task(
            description=impl_task_desc,
            expected_output='具体的な修正コードを含むCrewResult形式のJSON。',
            agent=developer,
            context=[analysis_task], # Reviewerの出力を参照
            output_pydantic=CrewResult # 構造化データとして出力
        )

        # Crew編成
        crew = Crew(
            agents=[reviewer, developer],
            tasks=[analysis_task, implementation_task],
            **NeoConfig.get_common_crew_params()
        )

        return self.execute(crew)
