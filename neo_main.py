import json
import sys
from agents.sentiment_agent import SentimentCrew
from agents.scout_agent import ScoutCrew
from agents.content_creator_agent import ContentCreatorCrew
from agents.planning_agent import PlanningCrew
from agents.development_agent import DevelopmentCrew
from tools.data_fetcher import DataFetcher
from tools.moltbook_tool import MoltbookTool

class NeoSystem:
    """
    Neoの全実務部隊を統合管理するメインインターフェース。
    """
    def __init__(self):
        self.sentiment_crew = SentimentCrew()
        self.scout_crew = ScoutCrew()
        self.creator_crew = ContentCreatorCrew()
        self.planning_crew = PlanningCrew()
        self.development_crew = DevelopmentCrew()

    def analyze_sentiment(self, goal: str, market_data: str, raw_sns_data: list):
        """感情分析部隊を派遣する"""
        formatted_sns = DataFetcher.format_for_crew(raw_sns_data)
        inputs = DataFetcher.create_sentiment_input(goal, market_data, formatted_sns)
        print(f"派遣中: SentimentAnalysisCrew...")
        return self.sentiment_crew.run(
            goal=inputs["goal"],
            context=inputs["context"],
            constraints=inputs["constraints"]
        )

    def scout_ecosystem(self, goal: str, context: str, constraints: str):
        """エコシステム調査部隊を派遣する"""
        print(f"派遣中: EcosystemScoutCrew...")
        return self.scout_crew.run(goal, context, constraints)

    def plan_project(self, goal: str, context: str):
        """企画部隊を派遣する"""
        print(f"派遣中: StrategicPlanningCrew...")
        return self.planning_crew.run(goal, context)

    def develop_skill(self, spec: str, language: str = "python"):
        """開発部隊を派遣する"""
        print(f"派遣中: AgentDevelopmentCrew...")
        return self.development_crew.run(spec, language)

    def autonomous_post_cycle(self, topic: str):
        """
        リサーチ -> 分析 -> 投稿生成 -> 実行 の本番用自律サイクル
        """
        try:
            raw_data = [{"title": "aGDP Growth", "snippet": "Virtuals aGDP $470M, high growth.", "url": "N/A"}]
            analysis = self.analyze_sentiment(f"{topic}の分析", "Price: $0.62", raw_data)
            
            summary = str(getattr(analysis, 'raw', analysis))
            print(f"派遣中: ContentCreatorCrew...")
            creation = self.creator_crew.run(summary, topic)
            
            post_content = ""
            if hasattr(creation, 'pydantic') and creation.pydantic:
                post_content = creation.pydantic.content
            elif hasattr(creation, 'raw'):
                post_content = creation.raw
            else:
                post_content = str(creation)

            if post_content:
                clean_content = post_content.strip().strip('"').strip("'")
                success = MoltbookTool.post(clean_content)
                return {"status": "success" if success else "failed", "content": clean_content}
            
            return {"status": "error", "message": "Failed to extract content"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    system = NeoSystem()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""
        if cmd == "post":
            print(json.dumps(system.autonomous_post_cycle(arg), indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(system.plan_project(arg, "Neo 2.0 Ecosystem"))
