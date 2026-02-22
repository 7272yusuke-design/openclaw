import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crews.builder_division.crew import BuilderDivisionEstimator

def run():
    print("## Starting Real DataFetcher Design Crew ##")
    
    inputs = {
        'project_description': 'Design of the Real DataFetcher for SentimentWorker.'
    }
    
    try:
        result = BuilderDivisionEstimator().crew().kickoff(inputs=inputs)
        print("\n\n########################")
        print("## Crew Execution Result ##")
        print("########################\n")
        print(result)
        
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, 'real_data_fetcher_design.md'), 'w') as f:
            f.write(str(result))
            
        print(f"\nResult saved to {os.path.join(output_dir, 'real_data_fetcher_design.md')}")
        
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
