from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from tools.code_interpreter import CodeInterpreter
import os

class DevelopmentCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="AgentDevelopment")

    def run(self, spec: str, language: str = "python", execution_logs: str = "", error_report: str = "", **kwargs):
        # GitHub-MCP利用のためのトークン確認
        github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")

        # 🛠️ 実装・進化担当 (Neo-Builder)
        # 提案者から、物理的なコード修正を行う「実務家」へと昇華
        developer = Agent(
            role='Senior AI Software Builder & System Architect',
            goal='システムの整合性を向上させ、GitHub-MCPを介して自律的な自己進化ロジックを実装・反映せよ。',
            backstory=(
                'あなたは OpenClaw の肉体（コード）を造り替えるエンジニアです。'
                'Scout からの市場変化や Warden からの監査フィードバックを受け取り、'
                '実際に tools/ や core/ のファイルを GitHub-MCP を通じて修正・最適化します。'
                'あなたの書いたコードは Warden（執行官）によって厳格に監査されるため、'
                '常に安全かつ、実行ログに基づいた正確なパッチを提供しなければなりません。'
            ),
            tools=[CodeInterpreter()], # 既存のツールを継承
            llm=self.llm,
            verbose=True
        )

        task = Task(
            description=(
                f"【実装指令】: 以下の要件に基づき、システムコードを修正・最適化せよ。\n"
                f"1. 要件(Spec): {spec}\n"
                f"2. ターゲット言語: {language}\n"
                f"3. 実行ログ(Logs): {execution_logs}\n"
                f"4. エラー報告(Error): {error_report}\n\n"
                "【手順】:\n"
                "- npx @modelcontextprotocol/server-github を利用し、該当するファイルをリサーチせよ。\n"
                "- 修正が必要な箇所を特定し、GitHub-MCP を介してファイルを直接 update または create せよ。\n"
                "- 修正後、その内容が既存のロジックと整合しているか、CodeInterpreter でシミュレーションせよ。"
            ),
            expected_output='実行された修正内容のサマリーと、反映されたファイル名のリスト。',
            agent=developer
        )

        crew = Crew(agents=[developer], tasks=[task], verbose=True)
        result = crew.kickoff()
        # 既存のブリッジ形式を維持
        return CrewResult.from_crew_output(result)
