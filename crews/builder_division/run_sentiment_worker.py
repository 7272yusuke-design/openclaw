import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crews.builder_division.crew import BuilderDivisionEstimator

def run():
    print("## Starting SentimentWorker Design & Implementation Crew ##")
    
    # 入力データ（今回は設計タスクなので入力は最小限ですが、コンテキストとして渡す）
    inputs = {
        'project_description': 'Sentiment Analysis Module for Virtuals Protocol Agent'
    }
    
    try:
        result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
        print("\n\n########################")
        print("## Crew Execution Result ##")
        print("########################\n")
        print(result)
        
        # 結果をファイルに保存
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, 'sentiment_worker_design.md'), 'w') as f:
            f.write(str(result))
            
        print(f"\nResult saved to {os.path.join(output_dir, 'sentiment_worker_design.md')}")
        
    except Exception as e:
        print(f"Error running crew: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
