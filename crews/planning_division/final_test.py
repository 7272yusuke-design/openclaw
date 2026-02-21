import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import PlanningDivisionCrew

def final_run():
    """部隊全員（3名）によるフル稼働テスト"""
    inputs = {
        'project_description': 'A decentralized service that provides liquidity for AI agents on Virtuals Protocol.',
        'customer_domain': 'Virtuals Protocol / AI Agent Economy',
        'current_year': '2026'
    }
    
    print("## Phase 3: Final Division Review (Analyst + Financial + Director) Start ##")
    
    # 3名全員によるシーケンシャルなフロー
    result = PlanningDivisionCrew().crew().kickoff(inputs=inputs)
    
    print("\n## Final Approved Planning Document ##\n")
    print(result)

if __name__ == "__main__":
    final_run()
