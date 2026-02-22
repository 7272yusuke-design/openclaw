import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crews.builder_division.crew import BuilderDivisionEstimator

def run():
    print("## Starting Integration Pipeline Crew ##")
    
    inputs = {
        'project_description': 'Integrate SentimentWorker and LiquidityWorker for end-to-end autonomous trading simulation.'
    }
    
    try:
        result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
        print("\n\n########################")
        print("## Crew Execution Result ##")
        print("########################\n")
        print(result)
        
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, 'integrated_pipeline_simulation.py'), 'w') as f:
            f.write(str(result))
            
        print(f"\nResult saved to {os.path.join(output_dir, 'integrated_pipeline_simulation.py')}")
        
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
