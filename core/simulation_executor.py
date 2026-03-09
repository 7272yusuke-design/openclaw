import os
import json
import time
from datetime import datetime, timezone
import requests

class SimulationExecutor:
    """
    物理的な資産を消費せず、リアルタイム市場データに基づいた仮想執行を行う。
    """
    def __init__(self, simulation_log_path="vault/simulation_logs.json"):
        self.log_path = simulation_log_path
        self.error_count = 0
        self._ensure_log_exists()

    def _ensure_log_exists(self):
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                json.dump([], f)

    def get_current_gas_price(self):
        """Base Mainnet の現在の Gas 価格を取得"""
        rpc_url = os.environ.get("BASE_RPC_URL") or "https://mainnet.base.org"
        payload = {"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1}
        try:
            resp = requests.post(rpc_url, json=payload, timeout=5)
            if resp.status_code == 200:
                return int(resp.json().get("result"), 16) / 10**9 # Gwei
        except Exception:
            pass
        return 0.1 # Fallback

    def execute_virtual_trade(self, symbol, side, quantity, price):
        """
        仮想執行。物理的な署名をバイパスし、ログを記録する。
        """
        try:
            gas_price_gwei = self.get_current_gas_price()
            # 仮想ガスコスト計算 (150,000 gas units を想定)
            virtual_gas_eth = (150000 * gas_price_gwei * 10**9) / 10**18
            
            trade_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "execution_price": price,
                "virtual_gas_eth": virtual_gas_eth,
                "status": "COMPLETED"
            }

            with open(self.log_path, "r") as f:
                logs = json.load(f)
            
            logs.append(trade_record)
            
            with open(self.log_path, "w") as f:
                json.dump(logs, f, indent=2)

            self.error_count = 0 # 成功時はエラーカウントリセット
            return trade_record

        except Exception as e:
            self.error_count += 1
            error_msg = f"SIMULATION_ERROR: {str(e)}"
            if self.error_count >= 3:
                return {"status": "CRITICAL_HALT", "error": error_msg}
            return {"status": "ERROR", "error": error_msg}

if __name__ == "__main__":
    # テスト仮想トレード: VIRTUAL を 1.50 で 1000枚 仮想購入
    sim = SimulationExecutor()
    res = sim.execute_virtual_trade("VIRTUAL", "BUY", 1000, 1.50)
    print(json.dumps(res, indent=2))
