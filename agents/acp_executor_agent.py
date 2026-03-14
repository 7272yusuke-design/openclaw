from crewai import Agent, Task, Crew
from core.base_crew import NeoBaseCrew
from bridge.crewai_bridge import CrewResult
from pydantic import BaseModel, Field
import os

class ACPPayload(BaseModel):
    action: str = Field(..., description="Action to perform (swap, stake, update_code, etc.)")
    token_address: str = Field(..., description="Target token address or 'N/A'")
    amount_usd: float = Field(..., description="Amount in USD or 0.0")
    validated: bool = Field(..., description="Is the task validated by the crew?")

class ACPExecutorCrew(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="ACPExecutor")

    def run(self, strategy: str, context: str, credit_info: dict = None, sentiment_info: str = "Neutral"):
        # GitHub-MCP サーバーの定義（環境変数からトークンを取得）
        github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        
        # 🛡️ 執行・監査官 (Neo-Warden)
        # エンジニアリング人格を切り離し、執行の安全性のみに特化
        warden = Agent(
            role='Security-First Transaction Warden (Neo-Warden)',
            goal='戦略の執行安全性を厳格に監査し、1 Wei の誤差もなく正確にオンチェーン執行を完遂する。',
            backstory=(
                'あなたは OpenClaw 資産を守る最後の砦（Warden）です。'
                'Development Agent が作成したコードや戦略に、資産流出のリスクや論理的欠陥がないか、'
                'GitHub リポジトリ内の安全基準と照合して最終判断を下します。'
                '開発（実装）はあなたの領域ではありません。あなたの聖域は「完璧な執行と防衛」です。'
            ),
            llm=self.llm,
            verbose=True,
            tools=[] # システム側で提供される GitHub-MCP (Read-only) を想定
        )

        task = Task(
            description=(
                f"【監査指令】: 提案された戦略 '{strategy}' の安全性を検証せよ。\n"
                "1. GitHub リポジトリを参照し、現在の執行ロジックが承認済みの安全基準（Slippage, Max Amount等）に従っているか監査せよ。\n"
                f"2. 執行パラメータ（金額: {credit_info}, トークン）が、現在の感情状況 {sentiment_info} において正当な範囲内か確認せよ。\n"
                "3. 脆弱性が疑われる場合は、迷わず validated を False に設定せよ。\n"
                f"【前提コンテキスト】: {context}"
            ),
            expected_output='監査済みの執行ペイロード。不合格時は validated を False に設定した JSON。',
            agent=warden,
            output_json=ACPPayload
        )

        crew = Crew(agents=[warden], tasks=[task], verbose=True)
        result = crew.kickoff()
        return result
