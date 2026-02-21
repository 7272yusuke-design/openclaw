import os
import sys

# SDKパスの解決
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../libs/virtuals-sdk/src')))

try:
    from virtuals_sdk.game.agent import Agent
    from virtuals_sdk.game.worker import Worker
except ImportError:
    # テスト時やライブラリ未導入時のためのフォールバック
    Agent = object
    Worker = object

class ProtocolBridge:
    """Virtuals Protocolと通信するためのブリッジクラス"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.agent = None

    def connect(self, name: str, goal: str, description: str):
        """プロトコルへの接続とエージェント初期化"""
        try:
            # 本来はSDKのAgentクラスを初期化
            print(f"Connecting to Virtuals Protocol as {name}...")
            return True
        except Exception as e:
            print(f"Connection error: {str(e)}")
            return False

    def fetch_agent_status(self):
        """エージェントの現在のステータスを取得"""
        # モックデータを返す
        return {"status": "active", "balance": "100 VIRTUAL"}

    def send_log(self, message: str):
        """プロトコルへログを送信"""
        print(f"[BRIDGE LOG]: {message}")
        return True
