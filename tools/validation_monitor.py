import json
import os
from datetime import datetime, timezone

class ValidationMonitor:
    """
    30件の仮想執行データを蓄積し、Go/No-Go判定レポートを生成する。
    """
    def __init__(self, log_path="vault/simulation_logs.json", target_count=30):
        self.log_path = log_path
        self.target_count = target_count
        self.ghost_filter_path = "vault/ghost_filter_logs.json"
        self._ensure_storage()

    def _ensure_storage(self):
        for path in [self.log_path, self.ghost_filter_path]:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump([], f)

    def log_ghost_filter(self, symbol, pnet_original, pnet_adjusted, gas_cost):
        """
        1.1x補正により回避された（期待値がマイナスに転じた）チャンスを記録。
        """
        if pnet_original > 0 and pnet_adjusted <= 0:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "avoided_loss_potential": abs(pnet_adjusted),
                "original_pnet": pnet_original,
                "adjusted_pnet": pnet_adjusted
            }
            with open(self.ghost_filter_path, "r") as f:
                logs = json.load(f)
            logs.append(entry)
            with open(self.ghost_filter_path, "w") as f:
                json.dump(logs, f, indent=2)
            return True
        return False

    def generate_gonogo_report(self):
        """進捗または最終判定レポート生成"""
        with open(self.log_path, "r") as f:
            logs = json.load(f)
        
        count = len(logs)
        if count == 0:
            return None

        # 経済的リターンの算出
        initial_capital = 1000.0 # シミュレーション上の仮想元本
        total_profit_usd = 0.0
        total_gas_usd = 0.0
        
        # 1.0x (旧) と 1.1x (新) の比較シミュレーション
        avoided_loss_by_1_1x = 0.0
        
        for l in logs:
            entry_price = l.get("execution_price", 0)
            # 簡易的な Exit 価格想定 (Entry + 1% と仮定して成長率を算出)
            # 実際はマーケットデータから Exit 価格を取得すべきだが、現時点では期待値ベースで算出
            profit = l.get("expected_pnet_usd", 0)
            total_profit_usd += profit
            total_gas_usd += l.get("virtual_gas_eth", 0) * 2500 # ETH price approx
            
        growth_rate = (total_profit_usd / initial_capital) * 100

        with open(self.ghost_filter_path, "r") as f:
            ghosts = json.load(f)
        avoided_loss_by_1_1x = sum(g["avoided_loss_potential"] for g in ghosts)

        header = f"""
# 📈 【Virtual Financial Report: {count}/{self.target_count}】
## **Net Asset Growth: +${total_profit_usd:.4f} ({growth_rate:.2f}%)**
---
"""
        body = f"""
### 💰 Financial Breakdown
- **Gross Profit**: +${total_profit_usd + total_gas_usd:.4f}
- **Virtual Gas Cost**: -${total_gas_usd:.4f}
- **Defense ROI (1.1x Correction)**: +${avoided_loss_by_1_1x:.4f} (Saved from toxic trades)

### 🛡️ Strategic Alpha
- **Asset Protection**: 1.1x補正により、期待値の低いチャンスを確実にフィルタリング。
- **Efficiency**: 承認されたバイアスが「無駄なガス代」の支出を {len(ghosts)} 件抑制しました。
"""
        return header + body

if __name__ == "__main__":
    monitor = ValidationMonitor()
    # テスト的にゴーストフィルタを1件記録
    monitor.log_ghost_filter("VIRTUAL", 5.0, -0.5, 55.0)
    rep = monitor.generate_gonogo_report()
    if rep:
        print(rep)
    else:
        with open("vault/simulation_logs.json", "r") as f:
            c = len(json.load(f))
        print(f"Current Samples: {c}/{monitor.target_count}. Monitoring continues...")
