import sys
from pathlib import Path
import logging

# 既存のツール群を読み込めるようにパスを追加
sys.path.append(str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from tools.deepwiki_tool import DeepWikiTool
from tools.code_interpreter import CodeInterpreter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("neo.quant.discovery")

# 🛠️ 修正: 生のクラスをCrewAIが握れる「ツール」に変換（ラップ）する
@tool("Local File Reader / Code Executor")
def code_executor_tool(code: str) -> str:
    """
    Executes Python code. Useful for reading local files (e.g., reading .py or .md files in the repository) 
    and returning their contents.
    """
    return CodeInterpreter.run_code(code)

def run_local_alpha_extraction():
    logger.info("=== 🧠 Starting Local DeepWiki Alpha Extraction Mission ===")
    
    # ツールを初期化（ラップ済みのcode_executor_toolを使用）
    wiki_tool = DeepWikiTool()
    
    quant_researcher = Agent(
        role="Senior Quant Alpha Researcher",
        goal="Extract practical Funding Rate Arbitrage mathematical formulas and Pandas implementations from our existing DeepWiki knowledge base and local repositories.",
        backstory="You are a veteran quant developer who relies solely on verified internal knowledge (DeepWiki) and existing repository code. You extract strict formulas, not vague advice.",
        verbose=True,
        allow_delegation=False,
        tools=[wiki_tool, code_executor_tool] # 👈 ここを修正
    )

    extraction_prompt = """
    【GSD マイクロタスク指令: ローカルナレッジからの抽出】
    あなたは外部のインターネット検索を禁止されています。
    必ず `DeepWikiTool` または `Local File Reader / Code Executor` を使用して、「Funding Rate Arbitrage」「Z-Score strategy」に関する社内（ローカル）の叡智を検索・抽出してください。

    Phase 1: DeepWikiとローカルコードからの知識抽出
    - DeepWikiToolを使って、資金調達率（Funding Rate）を用いた統計的アービトラージに関するドキュメントを検索せよ。
    - 必要であれば Code Executor Tool を使って `cat feature_engineering/*.py` のように既存のローカルファイルを参照せよ。
    
    Phase 2: 数式とロジックの定式化
    - 抽出した知識から、Pandas等で実装可能な具体的な計算式を組み立てよ。

    Phase 3: レポート出力
    以下のMarkdownフォーマットに厳密に従って出力せよ。
    
    # Alpha Name: [抽出したアルファの名前]
    ## 1. Mathematical Logic (数学的根拠)
    [抽出された知識に基づくロジック]
    ## 2. Calculation Formula (計算式)
    [Z-score等の計算式]
    ## 3. Pseudo-Code / Pandas Logic (実装イメージ)
    [Python/Pandasでの実装例]
    ## 4. Source (参照元)
    [DeepWikiやローカルのどのファイルから抽出したか]
    """

    extraction_task = Task(
        description=extraction_prompt,
        expected_output="A structured Markdown report containing mathematical formulas and Pandas pseudo-code extracted from DeepWiki and local files.",
        agent=quant_researcher
    )

    crew = Crew(
        agents=[quant_researcher],
        tasks=[extraction_task],
        process=Process.sequential
    )

    result = crew.kickoff()
    
    output_path = "research/funding_rate_alpha_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.raw if hasattr(result, 'raw') else str(result))
        
    logger.info(f"=== ✅ Extraction Complete. Report saved to {output_path} ===")

if __name__ == "__main__":
    run_local_alpha_extraction()
