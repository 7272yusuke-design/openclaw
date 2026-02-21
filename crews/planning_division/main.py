import sys
import os

# 自身のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import PlanningDivisionCrew

def run():
    inputs = {
        'project_description': 'A decentralized service that provides liquidity for AI agents on Virtuals Protocol.',
        'customer_domain': 'Virtuals Protocol / AI Agent Economy',
        'current_year': '2026'
    }
    print("## Planning Division: Dry Run Start ##")
    result = PlanningDivisionCrew().crew().kickoff(inputs=inputs)
    print("\n## Result ##\n")
    print(result)

if __name__ == "__main__":
    run()
