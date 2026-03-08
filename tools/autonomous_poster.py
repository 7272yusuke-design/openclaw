import os
import sys
import json
import requests
from datetime import datetime

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.moltbook_tool import MoltbookTool
from tools.obsidian_tool import ObsidianTool

class AutonomousPoster:
    def __init__(self):
        self.draft_path = "vault/social/drafts"
        self.moltbook = MoltbookTool()
        self.obsidian = ObsidianTool()

    def run_1000_jst_cycle(self):
        print(f"[AutonomousPoster] Starting 10:00 JST cycle: {datetime.now()}...")
        
        # 1. Fetch latest approved/pending drafts
        drafts = self._get_latest_drafts()
        if not drafts:
            print("[AutonomousPoster] No drafts found in vault/social/drafts.")
            return False

        # 2. Select the most relevant draft (simplified: most recent)
        latest_draft = drafts[0]
        draft_content = self.obsidian._run(command="read_note", path=latest_draft)
        
        # 3. Extract Moltbook content from draft
        # Assuming our draft format uses specific tags
        moltbook_post_match = re.search(r"--- \[Moltbook - Post 1\] ---\n(.*?)(?=\n---|$)", draft_content, re.DOTALL)
        if moltbook_post_match:
            post_content = moltbook_post_match.group(1).strip()
            print(f"[AutonomousPoster] Posting to Moltbook: {post_content[:50]}...")
            
            # 4. Execute Post
            success = self.moltbook.post(post_content)
            
            if success:
                # 5. Archive or Mark as Posted
                archive_path = f"vault/social/archive/{os.path.basename(latest_draft)}"
                os.makedirs("vault/social/archive", exist_ok=True)
                os.rename(latest_draft, archive_path)
                print(f"[AutonomousPoster] Successfully posted and archived to {archive_path}")
                return True
            else:
                print("[AutonomousPoster] Post failed.")
                return False
        else:
            print("[AutonomousPoster] Could not find Moltbook content in draft.")
            return False

    def _get_latest_drafts(self):
        if not os.path.exists(self.draft_path):
            return []
        files = [os.path.join(self.draft_path, f) for f in os.listdir(self.draft_path) if f.endswith(".md")]
        files.sort(key=os.path.getmtime, reverse=True)
        return files

import re
if __name__ == "__main__":
    poster = AutonomousPoster()
    # poster.run_1000_jst_cycle() # Triggered by scheduler
