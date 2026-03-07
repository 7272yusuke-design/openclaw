import unittest
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.memory_hygiene import ContextManager
from core.config import NeoConfig

class TestContextManagement(unittest.TestCase):
    def setUp(self):
        # 環境変数をロードする
        NeoConfig.setup_env()
        self.manager = ContextManager()
        # テスト用に一時的に閾値を低く設定
        self.manager.max_tokens = 50 

    def test_token_count(self):
        text = "This is a short test sentence."
        count = self.manager.count_tokens(text)
        print(f"Token count for '{text}': {count}")
        self.assertGreater(count, 0)

    def test_compression_trigger(self):
        # 閾値(50)を超える長いテキストを作成
        long_text = "Repeat this sentence many times to exceed the token limit. " * 20
        initial_tokens = self.manager.count_tokens(long_text)
        print(f"Initial tokens: {initial_tokens}")
        
        # 圧縮を実行
        compressed_text = self.manager.compress_context(long_text, max_tokens=50)
        final_tokens = self.manager.count_tokens(compressed_text)
        print(f"Compressed text: {compressed_text}")
        print(f"Final tokens: {final_tokens}")

        # 圧縮されたか確認 (元のテキストと異なること、トークン数が減っていること)
        self.assertNotEqual(long_text, compressed_text)
        self.assertLess(final_tokens, initial_tokens)
        self.assertTrue("[SUMMARY]" in compressed_text or "[TRUNCATED ERROR]" in compressed_text)

if __name__ == '__main__':
    unittest.main()
