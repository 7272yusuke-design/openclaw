import os
import json
import logging

logger = logging.getLogger(__name__)

class PortfolioManager:
    """ネオの軍資金とリスク許容度を管理するツール（ペーパーテスト対応版）"""
    
    def __init__(self, mode=None):
        # 環境変数 NEO_MODE が 'PAPER' なら仮想残高を使用
        self.mode = mode or os.getenv("NEO_MODE", "PAPER")
        self.wallet_address = os.getenv("SOLANA_WALLET_ADDRESS")
        self.paper_balance_file = "/docker/openclaw-taan/data/.openclaw/workspace/vault/portfolio/paper_balance.json"
        
        # フォルダがない場合は作成
        os.makedirs(os.path.dirname(self.paper_balance_file), exist_ok=True)
        
        # ペーパー残高の初期化（1,000 USDC）
        if self.mode == "PAPER" and not os.path.exists(self.paper_balance_file):
            self.update_paper_balance({"USDC": 1000.0, "SOL": 10.0, "VIRTUAL": 0.0})

    def get_balance(self):
        """現在のモードに応じた残高を取得"""
        if self.mode == "PAPER":
            with open(self.paper_balance_file, "r") as f:
                return json.load(f)
        else:
            # TODO: ここに実弾用のRPC通信（solana-py等）を記述
            # 現状は安全のためダミーの実残高を返すようにしておきます
            return {"USDC": 0.0, "SOL": 0.0, "VIRTUAL": 0.0, "note": "Mainnet RPC not connected"}

    def update_paper_balance(self, new_balance):
        """ペーパーテスト用の残高を更新（トレード後のシミュレーション用）"""
        with open(self.paper_balance_file, "w") as f:
            json.dump(new_balance, f, indent=4)
        logger.info(f"[*] Paper balance updated: {new_balance}")

    def calculate_position_size(self, confidence_score: float):
        """自信度に基づき、投入額を決定（リスク管理）"""
        balances = self.get_balance()
        available_usdc = balances.get("USDC", 0.0)
        
        # 1トレードあたりの最大許容損失（例：残高の10%）
        max_risk_ratio = 0.1 
        suggested_amount = available_usdc * max_risk_ratio * confidence_score
        
        return round(suggested_amount, 2)
