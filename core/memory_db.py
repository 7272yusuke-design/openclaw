import chromadb
from chromadb.config import Settings
import datetime
import os

class NeoMemoryDB:
    def __init__(self, path="/docker/openclaw-taan/data/.openclaw/workspace/vault/chroma_db"):
        self.client = chromadb.PersistentClient(path=path)
        # 「neo_long_term_memory」という名前で記憶の保存場所を確保
        self.collection = self.client.get_or_create_collection(name="neo_memories")

    def store(self, content: str, metadata: dict = None):
        """記憶をベクトル化して保存する"""
        timestamp = datetime.datetime.now().isoformat()
        metadata = metadata or {}
        metadata["timestamp"] = timestamp
        
        # IDはタイムスタンプベースで一意に作成
        mem_id = f"mem_{datetime.datetime.now().timestamp()}"
        
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[mem_id]
        )
        print(f"[*] Memory stored: {content[:30]}...")

    def recall(self, query: str, n_results: int = 3):
        """現在の状況に似た過去の記憶を呼び出す (RAG)"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
