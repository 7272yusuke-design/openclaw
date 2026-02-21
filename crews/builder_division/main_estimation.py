import sys
import os

# パス調整
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crews.builder_division.crew import BuilderDivisionEstimator

def run_estimation(planning_document: str):
    """企画書を受け取り、技術設計とコスト見積もりを実行"""
    inputs = {
        'planning_document': planning_document
    }
    print("## Builder Division: Estimation Run Start ##")
    result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
    print("\n## Technical Design & Cost Report ##\n")
    print(result)

if __name__ == "__main__":
    # 前回の企画結果（流動性提供サービス）を模した入力
    sample_plan = """
    Target: Decentralized Liquidity Service for AI Agents on Virtuals Protocol.
    Features: Automated liquidity provision, staking rewards optimization, fraud detection.
    ROI: 146.15%. Annual Revenue: $1,000,000.
    """
    run_estimation(sample_plan)
