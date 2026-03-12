import os
import json
import time
import uuid
from datetime import datetime, timezone
import requests
from core.state_manager import NeoState # 追加

class SimulationExecutor:
    """
    物理的な資産を消費せず、リアルタイム市場データに基づいた仮想執行を行う。
    """
    def __init__(self, simulation_log_path="vault/simulation_logs.json"):
        self.log_path = simulation_log_path
        self.error_count = 0
        self._ensure_log_exists()

        # config/settings.json から設定を読み込む
        config_path = "config/settings.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                self.gas_correction_factor = config.get("GAS_CORRECTION_FACTOR", 1.1) # デフォルト値も維持
                self.discord_webhook_url = config.get("DISCORD_WEBHOOK_URL")
                self.scan_interval_seconds = config.get("SCAN_INTERVAL_SECONDS", 300)
                self.burst_cycle_limit = config.get("BURST_CYCLE_LIMIT", 5)
        else:
            # 設定ファイルがない場合のフォールバック
            self.gas_correction_factor = 1.1
            self.discord_webhook_url = None
            self.scan_interval_seconds = 300
            self.burst_cycle_limit = 5
        
        self.neo_state = NeoState() # NeoStateの初期化


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

    def execute_virtual_trade(self, symbol, side, quantity, price, expected_pnet=0.0):
        """
        仮想執行。物理的な署名をバイパスし、ログを記録する。
        Strict Real-time Protocol に基づき、重複を排除し一意な ID を付与する。
        """
        try:
            with open(self.log_path, "r") as f:
                logs = json.load(f)

            # [Wait & Observe] 価格の完全重複チェック
            if logs:
                last_log = logs[-1]
                if last_log.get("execution_price") == price and last_log.get("symbol") == symbol:
                    return {"status": "SKIPPED", "reason": "Identical price detected. Waiting for market movement."}

            gas_price_gwei = self.get_current_gas_price()
            # GAS_CORRECTION_FACTOR を config から適用
            adjusted_gas_gwei = gas_price_gwei * self.gas_correction_factor 
            virtual_gas_eth = (150000 * adjusted_gas_gwei * 10**9) / 10**18
            
            # [Unique Identity] UUID4 と 物理タイムスタンプ
            trade_record = {
                "uuid": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "execution_price": price,
                "expected_pnet_usd": expected_pnet,
                "virtual_gas_eth": virtual_gas_eth,
                "status": "COMPLETED"
            }

            # [Disk Consistency] 記録のたびに物理ディスクへ書き込み
            logs.append(trade_record)
            with open(self.log_path, "w") as f:
                json.dump(logs, f, indent=2)

            self.error_count = 0
            
            # 進捗の更新
            current_state = self.neo_state.load()
            self.neo_state.update(current_state["progress"] + 1)

            return trade_record

        except Exception as e:
            self.error_count += 1
            return {"status": "ERROR", "error": str(e)}

if __name__ == "__main__":
    # テスト仮想トレード: VIRTUAL を 1.50 で 1000枚 仮想購入
    sim = SimulationExecutor()
    res = sim.execute_virtual_trade("VIRTUAL", "BUY", 1000, 1.50)
    print(json.dumps(res, indent=2))
