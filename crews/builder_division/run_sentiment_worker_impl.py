import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crews.builder_division.crew import BuilderDivisionEstimator

def run():
    print("## Starting SentimentWorker Skeleton Implementation Crew ##")
    
    # 入力データ
    inputs = {
        'project_description': 'Implementing Skeleton Code for SentimentWorker based on Technical Specification'
    }
    
    try:
        # Step 1: Design (Already done, but needed for context in sequential process if memory isn't persistent across runs in this script)
        # In a real scenario, we might skip the first task or mock its output, but for now we run the crew.
        # However, to be efficient, we can just run the crew. The Architect will likely re-generate the design, 
        # and then the Engineer will use it.
        # Ideally, we should pass the design as input if we want to skip step 1, but CrewAI sequential process usually runs all.
        # Let's run it.
        result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
        print("\n\n########################")
        print("## Crew Execution Result ##")
        print("########################\n")
        print(result)
        
        # 結果をファイルに保存
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, 'sentiment_worker_skeleton.py'), 'w') as f:
            f.write(str(result))
            
        print(f"\nResult saved to {os.path.join(output_dir, 'sentiment_worker_skeleton.py')}")
        
    except Exception as e:
        print(f"Error running crew: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
