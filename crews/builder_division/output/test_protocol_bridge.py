import unittest
from protocol_bridge import ProtocolBridge

class TestProtocolBridge(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_key"
        self.bridge = ProtocolBridge(self.api_key)

    def test_initialization(self):
        """初期化テスト"""
        self.assertEqual(self.bridge.api_key, self.api_key)

    def test_connect(self):
        """接続テスト（モック）"""
        result = self.bridge.connect("TestAgent", "Goal", "Desc")
        self.assertTrue(result)

    def test_fetch_status(self):
        """ステータス取得テスト"""
        status = self.bridge.fetch_agent_status()
        self.assertIn("status", status)
        self.assertEqual(status["status"], "active")

    def test_send_log(self):
        """ログ送信テスト"""
        result = self.bridge.send_log("Testing bridge functionality.")
        self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
