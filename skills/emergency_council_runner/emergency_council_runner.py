import os
import json
import shutil
from datetime import datetime

# Import default_api for tool access - this will now work in a skill context
import default_api

# Assuming trinity_council can be imported like this, relative to the workspace root
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..')) # Adjust path for skill
from agents.trinity_council import TrinityCouncil

# Configuration
ALERTS_DIR = "vault/alerts"
CRITICAL_EVENT_FILE = os.path.join(ALERTS_DIR, "critical_event.json")
ARCHIVE_DIR = os.path.join(ALERTS_DIR, "archive")

# Ensure alerts and archive directories exist
os.makedirs(ALERTS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def run():
    if os.path.exists(CRITICAL_EVENT_FILE):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Critical event detected!")
        try:
            with open(CRITICAL_EVENT_FILE, 'r') as f:
                event_data = json.load(f)
            
            # Prepare context for Trinity Council
            context_message = f"Emergency: A critical market event has been detected.\n"
            context_message += f"Event Type: {event_data.get('type', 'N/A')}\n"
            context_message += f"Asset: {event_data.get('asset', 'N/A')}\n"
            context_message += f"Details: {json.dumps(event_data, indent=2)}\n"
            context_message += f"The council must convene immediately to assess the situation and make a GO/NO-GO decision within 3 minutes.\n"
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Convening Trinity Council in Emergency Mode...")
            council = TrinityCouncil()
            # Pass the emergency context and asset to the council
            council_result = council.run(
                sentiment_score=0.5, # Default or derive if possible, or make council adapt
                context=context_message,
                target_symbol=event_data.get('asset', 'AIXBT') # Use detected asset as target
            )
            
            # Format report for Discord
            report_title = "🚨 緊急評議会報告"
            report_content = f"**日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_content += f"**緊急事態**: {event_data.get('type', '不明な事象')}\n"
            report_content += f"**対象銘柄**: {event_data.get('asset', 'N/A')}\n"
            report_content += f"\n{council_result}"
            
            # ACTUAL Discord message sending using default_api.message
            print(default_api.message(action="send", message=f"**{report_title}**\n{report_content}"))

            # Archive the event file
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"critical_event_{timestamp_str}.json"
            shutil.move(CRITICAL_EVENT_FILE, os.path.join(ARCHIVE_DIR, archive_filename))
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Critical event archived to {archive_filename}")

        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing critical event: {e}")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No critical event detected. Standing by.")

# For testing: create a dummy critical_event.json if it doesn't exist outside the skill execution
# This logic should be handled by a separate test runner or during initial setup
# or in the run_market_watcher.py script itself when it detects an anomaly.
# When this skill is called by HEARTBEAT.md, critical_event.json should already exist if an anomaly was detected.

# In a real OpenClaw skill, the primary function (often `run`) is called directly by the framework.
# The `if __name__ == "__main__":` block is typically not used in skills unless for internal testing.
