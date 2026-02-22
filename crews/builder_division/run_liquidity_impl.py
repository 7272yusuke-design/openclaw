import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))\

from crews.builder_division.crew import BuilderDivisionEstimator

def run():
    print("## Starting LiquidityWorker Implementation Crew ##")
    
    inputs = {
        'project_description': 'Implementation of the LiquidityWorker based on the Technical Specification.'
    }
    
    try:
        result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
        print("\n\n########################")
        print("## Crew Execution Result ##")
        print("########################\n")
        print(result)
        
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, 'liquidity_worker_implementation.py'), 'w') as f:
            f.write(str(result))
            
        print(f"\nResult saved to {os.path.join(output_dir, 'liquidity_worker_implementation.py')}")
        
    except Exception as e:
        print(f"Error running crew: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
