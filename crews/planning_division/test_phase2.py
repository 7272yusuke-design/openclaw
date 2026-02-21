import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import PlanningDivisionCrew

def test_workflow():
    """市場調査 ＋ 財務分析 の連携テスト"""
    inputs = {
        'project_description': 'A decentralized service that provides liquidity for AI agents on Virtuals Protocol.',
        'customer_domain': 'Virtuals Protocol / AI Agent Economy',
        'current_year': '2026'
    }
    
    print("## Phase 2: Workflow (Analyst + Financial) Test Start ##")
    
    crew_instance = PlanningDivisionCrew()
    analyst = crew_instance.lead_market_analyst()
    finance = crew_instance.financial_analyst()
    
    task1 = crew_instance.research_task()
    task2 = crew_instance.financial_analysis_task()
    
    # 2名によるシーケンシャルな連携
    combined_crew = crew_instance.crew()
    combined_crew.agents = [analyst, finance]
    combined_crew.tasks = [task1, task2]
    
    result = combined_crew.kickoff(inputs=inputs)
    
    print("\n## Workflow Test Result ##\n")
    print(result)

if __name__ == "__main__":
    test_workflow()
