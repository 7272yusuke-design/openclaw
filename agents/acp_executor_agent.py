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
        
        # 最高技術責任者 (Neo-Engineer) 兼 執行官
        engineer = Agent(
            role='Senior Full-stack Engineer & On-chain Executor',
            goal='GitHub-MCP を利用して最新の freqtrade 戦略をリサーチし、自律的に取引ロジックを改善しつつ、オンチェーン執行を行う。',
            backstory=(
                'あなたは OpenClaw システムの頭脳を司るシニアエンジニアです。'
                f'GITHUB_TOKEN を利用して freqtrade/technical などのリポジトリを直接読み取り、'
                '最新のインジケーター（RSI, EMA等）を indicators.py に反映させる能力を持ちます。'
                'コードの品質と、厳格なオンチェーン執行の両方に責任を持ちます。'
            ),
            llm=self.llm,
            verbose=True,
            # MCP ツールをエージェントに直接握らせる（ここが肝です）
            tools=[] # ※注: システム側の MCP サーバー設定が読み込まれるようにプロンプトで指示
        )

        task = Task(
            description=(
                f"【エンジニア指令】: 現在の戦略 '{strategy}' に最適なテクニカル指標を GitHub からリサーチせよ。\n"
                "1. npx @modelcontextprotocol/server-github を利用して freqtrade/technical リポジトリを確認せよ。\n"
                "2. 既存の tools/indicators.py を最新のロジックで強化できるか検討せよ。\n"
                f"【執行指令】: 感情情報 {sentiment_info} および クレジット情報 {credit_info} に基づき、ACP 執行の妥当性を判断せよ。\n"
                f"【前提コンテキスト】: {context}"
            ),
            expected_output='コード改善案、または ACP 用の有効な JSON ペイロード。',
            agent=engineer,
            output_json=ACPPayload
        )

        crew = Crew(agents=[engineer], tasks=[task], verbose=True)
        result = crew.kickoff()
        return result
