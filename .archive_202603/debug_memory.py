from core.memory_db import NeoMemoryDB
import json

def debug():
    memory = NeoMemoryDB()
    # 最新の記憶を5件呼び出し
    print("--- Recent Memories in ChromaDB ---")
    results = memory.recall(query="Update", n_results=5)
    
    if not results['documents'][0]:
        print("[!] No memories found yet. Wait for a radar trigger.")
        return

    for i, doc in enumerate(results['documents'][0]):
        metadata = results['metadatas'][0][i]
        print(f"\n[{i+1}] Timestamp: {metadata.get('timestamp')}")
        print(f"    Category: {metadata.get('section')}")
        print(f"    Content: {doc[:100]}...")

if __name__ == "__main__":
    debug()
