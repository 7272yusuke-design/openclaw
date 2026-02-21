import time
from protocol_bridge import ProtocolBridge
from liquidity_manager import LiquidityManager

class AgentRunner:
    """エージェントのメイン実行ループを制御するクラス"""
    def __init__(self, api_key: str):
        print("Initializing Agent Runner...")
        self.bridge = ProtocolBridge(api_key)
        self.manager = LiquidityManager()
        self.is_running = False

    def run_once(self):
        """1サイクルの実行プロセス"""
        print("\n--- NEW CYCLE STARTED ---")
        
        # 1. 市場データの取得
        print("[Step 1] Fetching market data via ProtocolBridge...")
        status = self.bridge.fetch_agent_status()
        print(f"Current Status: {status}")

        # 2. 戦略の策定
        print("[Step 2] Formulating strategy via LiquidityManager...")
        # ダミーデータを分析に渡す
        analysis = self.manager.analyze_pairs()
        print(f"Analysis Complete: {analysis}")
        
        # 最適な配分を計算
        allocation = self.manager.calculate_optimal_allocation(0.64)
        print(f"Decision: Optimal Allocation found. Strategy: {allocation}")

        # 3. ログの送信
        print("[Step 3] Logging decision to protocol...")
        self.bridge.send_log(f"Strategy executed: {allocation}")
        
        print("--- CYCLE COMPLETED ---\n")

    def start_loop(self, interval=5, iterations=2):
        """メインループの起動（テスト用に回数を制限）"""
        self.is_running = True
        print(f"Agent Loop started. Interval: {interval}s")
        for i in range(iterations):
            if not self.is_running: break
            self.run_once()
            time.sleep(interval)
        print("Agent Task Finished for testing.")

if __name__ == "__main__":
    # テスト起動
    runner = AgentRunner(api_key="OC-AGENT-BETA-001")
    runner.start_loop()
