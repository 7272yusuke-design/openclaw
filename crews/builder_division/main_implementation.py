import sys
import os

# パス調整
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crews.builder_division.crew import BuilderDivisionEstimator

def run_implementation():
    """設計に基づき、最初のモジュールを実装"""
    # 出力先を確保
    os.makedirs('crews/builder_division/output', exist_ok=True)
    
    inputs = {
        'planning_document': """
        Target: Decentralized Liquidity Service for AI Agents on Virtuals Protocol.
        Structure: 
        1. Protocol Bridge (Connects to Virtuals SDK)
        2. Liquidity Manager (Logic)
        3. Fraud Guard (Security)
        """
    }
    
    print("## Builder Division: Implementation Task (Step 1) Start ##")
    # 設計から実装までをシーケンシャルに実行
    result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
    
    print("\n## Implementation Result ##\n")
    print(result)

if __name__ == "__main__":
    run_implementation()
