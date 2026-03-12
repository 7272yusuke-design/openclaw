import os
from core.memory_db import NeoMemoryDB

def ingest_legacy_memories():
    print("🧠 過去の記憶（Markdown）の統合を開始します...")
    memory_dir = "/docker/openclaw-taan/data/.openclaw/workspace/memory"
    db = NeoMemoryDB()
    
    count = 0
    for filename in sorted(os.listdir(memory_dir)):
        if filename.endswith(".md"):
            filepath = os.path.join(memory_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # ファイル名をメタデータにしてChromaDBへ保存
            db.store(
                content=content,
                metadata={"source": "legacy_md", "date": filename.replace(".md", "")}
            )
            print(f"✅ {filename} をベクトル化し、記憶領域に統合しました。")
            count += 1
            
    print(f"🎉 完了: 合計 {count} 件の過去の記憶をネオの脳にインストールしました。")

if __name__ == "__main__":
    ingest_legacy_memories()
