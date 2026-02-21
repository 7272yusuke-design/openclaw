import sys
import os

# 自身のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import PlanningDivisionCrew

def test_analyst():
    """市場調査員単体での動作テスト"""
    inputs = {
        'project_description': 'A decentralized service that provides liquidity for AI agents on Virtuals Protocol.',
        'customer_domain': 'Virtuals Protocol / AI Agent Economy',
        'current_year': '2026'
    }
    
    print("## Phase 1: Analyst Single Test Start ##")
    
    # 全タスクではなく、最初のタスク（research_task）のみを実行
    crew_instance = PlanningDivisionCrew()
    analyst_agent = crew_instance.lead_market_analyst()
    research_task = crew_instance.research_task()
    
    # 単体テスト用のCrewを臨時編成
    single_crew = crew_instance.crew()
    single_crew.tasks = [research_task]
    single_crew.agents = [analyst_agent]
    
    result = single_crew.kickoff(inputs=inputs)
    
    print("\n## Analyst Test Result ##\n")
    print(result)

if __name__ == "__main__":
    test_analyst()
