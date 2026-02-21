import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crews.builder_division.crew import BuilderDivisionEstimator

def run_test_generation():
    """エンジニアにテストコードを書かせる"""
    inputs = {
        'planning_document': 'Target: Unit testing for the Protocol Bridge module.'
    }
    
    print("## Builder Division: Test Code Generation Start ##")
    # 設計からテスト作成までをシーケンシャルに実行
    result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
    
    print("\n## Test Generation Result ##\n")
    print(result)

if __name__ == "__main__":
    run_test_generation()
