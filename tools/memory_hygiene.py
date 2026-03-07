import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from core.config import NeoConfig

LOG_FILE = "logs/execution_history.jsonl"
ARCHIVE_DIR = "logs/archive"
MEMORY_FILE = "MEMORY.md"

class ContextManager:
    """
    動的なコンテキスト圧縮とメモリ管理を行うクラス。
    """
    def __init__(self):
        self.max_tokens = NeoConfig.MAX_CONTEXT_TOKENS
        # Use Neo LLM (Google API) for summarization
        self.summary_model = NeoConfig.get_neo_llm(model_name=NeoConfig.SUMMARY_MODEL)

    def count_tokens(self, text: str) -> int:
        """
        簡易的なトークン数見積もり。
        厳密なtiktoken等は使わず、文字数ベースで概算する（日本語含むため安全側に倒す）。
        英語: 1token ≒ 4chars, 日本語: 1token ≒ 0.5~1chars
        """
        if not text:
            return 0
        # 安全を見て、文字数 * 0.7 をトークン数とする（日本語多めの想定）
        return int(len(text) * 0.7)

    def compress_context(self, text: str, max_tokens: int = None) -> str:
        """
        指定されたトークン数を超えている場合、LLMを使用して要約する。
        """
        limit = max_tokens or self.max_tokens
        current_tokens = self.count_tokens(text)

        if current_tokens <= limit:
            return text

        print(f"⚠️ Context too large ({current_tokens} tokens > {limit}). Compressing...")
        
        try:
            prompt = (
                "以下のテキストは、AIエージェント間の通信ログまたはタスク結果です。\n"
                "重要な「事実」「決定事項」「数値」「エラー内容」を漏らさず、"
                f"かつ {int(limit * 0.5)} トークン程度に圧縮・要約してください。\n"
                "装飾は省き、情報の密度を高めてください。\n\n"
                f"--- TEXT START ---\n{text}\n--- TEXT END ---"
            )
            
            print(f"DEBUG: Invoking summary model: {NeoConfig.SUMMARY_MODEL}")
            response = self.summary_model.invoke([
                SystemMessage(content="You are a professional summarizer optimized for AI context compression."),
                HumanMessage(content=prompt)
            ])
            print(f"DEBUG: Summary model response received.")
            
            summary = response.content
            new_tokens = self.count_tokens(summary)
            print(f"✅ Context compressed: {current_tokens} -> {new_tokens} tokens.")
            return f"[SUMMARY]\n{summary}"
            
        except Exception as e:
            print(f"❌ Error compressing context: {e}")
            # エラー時は元のテキストの末尾だけ返す（緊急避難）
            return f"[TRUNCATED ERROR] ... {text[-2000:]}"

def maintain_memory():
    """
    既存のログアーカイブ機能（後方互換性のため維持）
    """
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
        
        # Simple heuristic for success/failure
        if "error" in str(output).lower() or "failed" in str(output).lower():
            error_count += 1
        else:
            success_count += 1
            
        snippet = str(output)[:100].replace('\n', ' ')
        key_insights.append(f"- **{crew_name}**: {snippet}...")

    summary_lines.append(f"- **Total Entries**: {len(entries)}")
    summary_lines.append(f"- **Success**: {success_count}, **Errors**: {error_count}")
    summary_lines.append("### Key Activities:")
    summary_lines.extend(key_insights[:5]) 

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
