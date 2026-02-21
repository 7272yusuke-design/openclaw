import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('crews'))

# Now, assuming the structure is workspace/crews/planning_division/src/planning_division/crew.py
# The import should be from crews.planning_division.src.planning_division.crew
from crews.planning_division.src.planning_division.crew import PlanningDivisionCrew

def run():
    """
    企画開発部隊のドライランを実行
    テーマ: Virtuals Protocolにおける新しいエージェント収益化サービスの企画
    """
    inputs = {
        'project_description': 'A decentralized service that provides liquidity for AI agents on Virtuals Protocol, enabling autonomous trading bots to scale their operations.',
        'customer_domain': 'Virtuals Protocol / AI Agent Economy',
        'current_year': '2026'
    }
    
    print("## Planning Division: Dry Run Start ##")
    crew = PlanningDivisionCrew()
    result = crew.crew().kickoff(inputs=inputs)
    
    print("\n## Dry Run Result ##\n")
    print(result)

if __name__ == "__main__":
    run()
