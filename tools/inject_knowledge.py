import sys
import os
sys.path.append(os.getcwd())
from core.memory_db import NeoMemoryDB

def inject():
    db = NeoMemoryDB()
    
    # 注入する重要な知見
    knowledge_points = [
        "2026-03-12: Gitの100MB制限問題を解決。neo-env/やバイナリは.gitignoreで除外。歴史修正済み。",
        "Moltbook投稿ルール: レート制限回避のため、最低2.5分(150秒)の間隔を空けること。",
        "システム整合性: .envのパースエラーを修正。環境変数の読み込みは常にクリーンな状態を保つこと。"
    ]
    
    print("[*] Starting knowledge injection into ChromaDB...")
    for point in knowledge_points:
        db.store(content=point, metadata={"category": "protocol_update", "priority": "high"})
    
    print("[*] Success: Neo's core memory has been updated.")

if __name__ == "__main__":
    inject()
