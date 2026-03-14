"""
NeoMemoryDB v2 — タグベースフィルタリング + ベクトル検索のハイブリッド
改善点:
  1. recall時にメタデータwhere句で事前フィルタ可能
  2. recall_by_tags: タグベースの確実な検索
  3. recall_tier1: 最重要記憶のみ返す
  4. store時のカテゴリ・タグ標準化
"""
import chromadb
import datetime
import logging

logger = logging.getLogger("neo.memory")

class NeoMemoryDB:
    def __init__(self, path="/docker/openclaw-taan/data/.openclaw/workspace/vault/chroma_db"):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name="neo_memories")

    def store(self, content: str, metadata: dict = None):
        """記憶をベクトル化して保存"""
        timestamp = datetime.datetime.now().isoformat()
        metadata = metadata or {}
        metadata["timestamp"] = timestamp
        
        # tier未指定は3（通常記憶）
        if "tier" not in metadata:
            metadata["tier"] = "3"
        
        mem_id = f"mem_{datetime.datetime.now().timestamp()}"
        
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[mem_id]
        )
        logger.info(f"[*] Memory stored: {content[:50]}...")
        print(f"[*] Memory stored: {content[:30]}...")

    def recall(self, query: str, n_results: int = 3, where: dict = None):
        """ベクトル検索 + オプショナルメタデータフィルタ"""
        kwargs = {
            "query_texts": [query],
            "n_results": min(n_results, self.collection.count())
        }
        if where:
            kwargs["where"] = where
        
        if self.collection.count() == 0:
            return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
        
        return self.collection.query(**kwargs)

    def recall_by_tags(self, tag: str, n_results: int = 5):
        """タグベースの確実な検索（ベクトル不使用）"""
        results = self.collection.get(include=["documents", "metadatas"])
        
        matched = []
        for mid, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            tags = meta.get("tags", "")
            content_lower = doc.lower()
            tag_lower = tag.lower()
            
            if tag_lower in tags.lower() or tag_lower in content_lower:
                matched.append((mid, doc, meta))
        
        # タイムスタンプ降順（新しい順）
        matched.sort(key=lambda x: x[2].get("timestamp", ""), reverse=True)
        
        return {
            "ids": [m[0] for m in matched[:n_results]],
            "documents": [m[1] for m in matched[:n_results]],
            "metadatas": [m[2] for m in matched[:n_results]]
        }

    def recall_tier1(self):
        """Tier 1（永久保持）記憶のみ返す"""
        results = self.collection.get(
            where={"tier": "1"},
            include=["documents", "metadatas"]
        )
        return results

    def recall_lessons(self, n_results: int = 5):
        """教訓・ルール系の記憶を優先返却"""
        results = self.collection.get(include=["documents", "metadatas"])
        
        lessons = []
        for mid, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            priority = meta.get("priority", "")
            source = meta.get("source", "")
            tier = meta.get("tier", "3")
            
            is_lesson = (
                priority == "permanent" or
                source == "commander_manual_injection" or
                tier in ("1", "2") or
                "教訓" in doc or
                "ルール" in doc
            )
            
            if is_lesson:
                lessons.append((mid, doc, meta))
        
        lessons.sort(key=lambda x: x[2].get("tier", "3"))
        
        return {
            "ids": [l[0] for l in lessons[:n_results]],
            "documents": [l[1] for l in lessons[:n_results]],
            "metadatas": [l[2] for l in lessons[:n_results]]
        }

    def get_all(self):
        """全記憶を返す（管理用）"""
        return self.collection.get(include=["documents", "metadatas"])
    
    def count(self):
        """記憶数"""
        return self.collection.count()
    
    def delete(self, ids: list):
        """指定IDの記憶を削除"""
        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} memories")
