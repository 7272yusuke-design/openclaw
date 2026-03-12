from core.memory_db import NeoMemoryDB

def read_recent():
    db = NeoMemoryDB()
    data = db.collection.get()
    docs = data.get('documents', [])
    metas = data.get('metadatas', [])

    print("=========================================")
    print("🌙 昨晩〜直近の評議会 記録")
    print("=========================================")

    # リストの後ろ（最新）から順番に確認
    found_count = 0
    recent_indices = list(range(len(docs)))
    recent_indices.reverse()

    for idx in recent_indices:
        meta = metas[idx] if metas[idx] else {}
        
        # 先ほど手動で入れた過去の記憶(legacy_md や commander_manual_injection)は除外
        if meta.get("source") in ["legacy_md", "commander_manual_injection"]:
            continue
            
        print(f"\n🔹 【対象銘柄】: {meta.get('symbol', '不明')}")
        print(f"🔹 【最終判断】: {meta.get('verdict', '不明')}")
        print(f"--- 議事録詳細 ---")
        print(docs[idx])
        print("-----------------------------------------")
        
        found_count += 1
        # 直近3回分くらい表示したらストップ
        if found_count >= 3:
            break

    if found_count == 0:
        print("直近の新しい記録は見つかりませんでした。")

if __name__ == "__main__":
    read_recent()
