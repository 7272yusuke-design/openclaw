import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.logger import ExecutionLogger
from agents.development_agent import DevelopmentCrew
from core.config import NeoConfig

class BatchOptimizer:
    """
    Nightly optimization routine.
    Analyzes the execution logs of the previous day and proposes targeted fixes.
    """
    
    def __init__(self):
        self.logger = ExecutionLogger()
        self.dev_crew = DevelopmentCrew()
        self.patch_dir = "patches/"
        os.makedirs(self.patch_dir, exist_ok=True)

    def run_daily_analysis(self, target_date_str: str = None):
        """
        Runs the daily optimization logic.
        """
        if target_date_str is None:
            # Default to yesterday
            target_date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"[Batch] Starting analysis for: {target_date_str}")
        logs = self.logger.get_logs_for_date(target_date_str)
        
        if not logs:
            print(f"[Batch] No logs found for {target_date_str}. Skipping.")
            return

        # 1. Identify problematic executions
        bad_logs = [
            l for l in logs 
            if (l.get("turns", 0) >= 3) or (l.get("status") == "error")
        ]
        
        if not bad_logs:
            print(f"[Batch] No critical issues found in {len(logs)} executions. System is healthy.")
            # Optional: Report healthy status to Discord
            return

        print(f"[Batch] Found {len(bad_logs)} problematic executions. Initiating Deep Analysis...")
        
        # 2. Analyze with Development Crew (Batch Mode)
        # We aggregate the logs to save tokens
        analysis_context = json.dumps(bad_logs[:5], indent=2, ensure_ascii=False) # Analyze top 5 worst cases
        
        patch_proposal = self.dev_crew.run(
            spec="Analyze these failed/inefficient execution logs and generate a specific prompt fix or code patch to prevent recurrence.",
            language="python", # Request structured patch format
            execution_logs=analysis_context,
            error_report="Batch Analysis Request",
            performance_log_path=None,
            market_cycle_log_path=None
        )
        
        # 3. Save Patch Proposal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patch_file = os.path.join(self.patch_dir, f"patch_proposal_{timestamp}.json")
        
        with open(patch_file, 'w', encoding='utf-8') as f:
            # Check if patch_proposal is Pydantic or dict or str
            content = patch_proposal
            if hasattr(patch_proposal, 'pydantic') and patch_proposal.pydantic:
                content = patch_proposal.pydantic.model_dump()
            elif hasattr(patch_proposal, 'dict'):
                content = patch_proposal.dict()
            elif hasattr(patch_proposal, 'json'):
                 content = patch_proposal.json()
            else:
                 content = str(patch_proposal)

            # If content is string, try to parse as JSON if possible, otherwise wrap
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    content = {"raw_output": content}

            json.dump(content, f, indent=2, ensure_ascii=False)
            
        print(f"[Batch] Analysis complete. Patch proposal saved to: {patch_file}")

        # 4. Report to Discord (NEW)
        self._report_to_discord(target_date_str, len(bad_logs), content)
        
        return patch_file

    def _report_to_discord(self, date_str: str, issue_count: int, patch_content: Any):
        webhook_url = "https://discord.com/api/webhooks/1479009905280028724/cX7C6pOTilIA4HeBzMwWOG_AhKMOcDH9KKU9_r955U0yr5z4hTsPRB0ISFfxjp3Otj64"
        
        # Format the patch content for readability
        try:
            summary = patch_content.get("summary", "No summary provided.")
            next_action = patch_content.get("next_action_suggestion", "Check the patch file.")
            
            # Extract code patch (truncate if too long)
            payload = patch_content.get("virtuals_payload", {})
            file_path = payload.get("file_path", "N/A")
            code_patch = payload.get("code_patch", "N/A")
            if len(code_patch) > 500:
                code_patch = code_patch[:500] + "... (truncated)"
        except AttributeError:
             # Fallback for raw string or unexpected format
             summary = "Raw analysis output available."
             next_action = "Review raw output."
             file_path = "N/A"
             code_patch = str(patch_content)[:500]

        message = {
            "embeds": [{
                "title": f"🛠️ Neo Self-Optimization Report ({date_str})",
                "color": 0xFFAA00, # Orange
                "fields": [
                    {"name": "📉 Issues Detected", "value": f"{issue_count} critical incidents found.", "inline": True},
                    {"name": "🧐 Diagnosis", "value": summary, "inline": False},
                    {"name": "🩹 Proposed Fix", "value": f"**File**: `{file_path}`\n```python\n{code_patch}\n```", "inline": False},
                    {"name": "🚀 Expected Improvement", "value": next_action, "inline": False}
                ],
                "footer": {"text": "Run 'python3 batch/daily_optimize.py --apply' to execute fix."}
            }]
        }
        
        try:
            import requests
            requests.post(webhook_url, json=message)
            print("[Batch] Report sent to Discord.")
        except Exception as e:
            print(f"[Batch] Failed to send Discord report: {e}")


if __name__ == "__main__":
    # Test run
    optimizer = BatchOptimizer()
    optimizer.run_daily_analysis()
