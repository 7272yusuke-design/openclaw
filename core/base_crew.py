import json
from datetime import datetime
from core.config import NeoConfig
from crewai import Crew

class NeoBaseCrew:
    """
    すべてのNeo実務部隊のベースクラス。
    一貫した出力とログ記録、エラー処理を提供する。
    """
    def __init__(self, name: str):
        NeoConfig.setup_env()
        self.name = name

    def execute(self, crew: Crew):
        """Crewを実行し、結果を標準化して返却する"""
        try:
            result = crew.kickoff()
            self._save_log(result)
            return result
        except Exception as e:
            error_msg = f"Error in {self.name}: {str(e)}"
            print(error_msg)
            return {"status": "failed", "error": error_msg}

    def _save_log(self, result):
        """実行ログの保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"logs/crewai/{self.name}_{timestamp}.json"
        
        log_data = {
            "timestamp": timestamp,
            "crew_name": self.name,
            "usage": str(getattr(result, 'usage_metrics', 'N/A')),
            "final_output": str(result)
        }
        
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
