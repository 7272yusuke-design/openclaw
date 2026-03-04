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
        """Crewを実行し、安定化された結果を標準化して返却する (Retry logic含む)"""
        import time
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 共通の制限パラメータを適用
                for task in crew.tasks:
                    if not hasattr(task, 'max_execution_time') or task.max_execution_time is None:
                        task.max_execution_time = NeoConfig.MAX_EXEC_TIME
                
                result = crew.kickoff()
                self._save_log(result)
                return result
            except Exception as e:
                error_msg = f"Attempt {attempt + 1} Failed in {self.name}: {str(e)}"
                print(error_msg)
                if attempt < max_retries - 1:
                    time.sleep(2) # レート制限や一時的な接続エラー対策で待機
                    continue
                return {"status": "failed", "error": error_msg}

    def _save_log(self, result):
        """実行ログの保存。ファイル競合を避けるため追記モード(JSONL)での保存も検討"""
        import os
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("logs/crewai", exist_ok=True)
        
        # 個別ログ
        log_path = f"logs/crewai/{self.name}_{timestamp}.json"
        
        # 統合JSONLログ (追記専用・競合に強い)
        history_path = "logs/execution_history.jsonl"
        
        log_data = {
            "timestamp": timestamp,
            "crew_name": self.name,
            "usage": str(getattr(result, 'usage_metrics', 'N/A')),
            "final_output": str(result)
        }
        
        # 個別ファイル書き出し
        try:
            with open(log_path, "w") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            # JSONLへの追記 (Atomic append)
            with open(history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Failed to save log: {e}")
