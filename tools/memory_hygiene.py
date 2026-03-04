import json
import os
from datetime import datetime

LOG_FILE = "logs/execution_history.jsonl"
ARCHIVE_DIR = "logs/archive"
MEMORY_FILE = "MEMORY.md"

def maintain_memory():
    if not os.path.exists(LOG_FILE):
        print(f"No log file found at {LOG_FILE}")
        return

    print(f"Processing {LOG_FILE}...")
    
    entries = []
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except Exception as e:
        print(f"Error reading log file: {e}")
        return

    if not entries:
        print("Log file is empty.")
        return

    # Summarize entries
    summary_lines = []
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_lines.append(f"\n## Log Summary - {timestamp_str}")
    
    success_count = 0
    error_count = 0
    key_insights = []

    for entry in entries:
        crew_name = entry.get("crew_name", "Unknown")
        output = entry.get("final_output", "")
        
        # Simple heuristic for success/failure based on output content
        if "error" in str(output).lower() or "failed" in str(output).lower():
            error_count += 1
        else:
            success_count += 1
            
        # Extract key insights (if any structured data is present, e.g., 'insight': '...')
        # For now, just capture the first 100 chars of output as a snippet
        snippet = str(output)[:100].replace('\n', ' ')
        key_insights.append(f"- **{crew_name}**: {snippet}...")

    summary_lines.append(f"- **Total Entries**: {len(entries)}")
    summary_lines.append(f"- **Success**: {success_count}, **Errors**: {error_count}")
    summary_lines.append("### Key Activities:")
    summary_lines.extend(key_insights[:5]) # Limit to top 5 for brevity in MEMORY.md

    # Append to MEMORY.md
    with open(MEMORY_FILE, 'a') as f:
        f.write("\n".join(summary_lines) + "\n")
    
    print(f"Appended summary to {MEMORY_FILE}")

    # Archive the log file
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_filename = f"execution_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    os.rename(LOG_FILE, os.path.join(ARCHIVE_DIR, archive_filename))
    print(f"Archived log to {os.path.join(ARCHIVE_DIR, archive_filename)}")

    # Recreate empty log file
    with open(LOG_FILE, 'w') as f:
        pass
    print("Reset log file.")

if __name__ == "__main__":
    maintain_memory()
