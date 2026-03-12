import os
import json
from datetime import datetime, timezone

class ParameterGovernance:
    """
    システムの重要パラメータ（P_net係数等）の変更を管理し、
    司令官の承認をトリガーとするガバナンスレイヤー。
    """
    def __init__(self, pending_path="vault/pending_changes.json", config_path="vault/blackboard/live_intel.json"):
        self.pending_path = pending_path
        self.config_path = config_path
        self._ensure_storage()

    def _ensure_storage(self):
        if not os.path.exists(self.pending_path):
            with open(self.pending_path, "w") as f:
                json.dump([], f)

    def propose_change(self, parameter, current_value, proposed_value, reasoning, risk_benefit):
        """変更案をキューに登録し、凍結状態で保持する"""
        proposal = {
            "proposal_id": f"PROP-{int(datetime.now(timezone.utc).timestamp())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameter": parameter,
            "current_value": current_value,
            "proposed_value": proposed_value,
            "reasoning": reasoning,
            "risk_benefit": risk_benefit,
            "status": "PENDING_APPROVAL"
        }

        with open(self.pending_path, "r") as f:
            proposals = json.load(f)
        
        # 同一パラメータの未承認案があれば上書きまたは追加
        proposals.append(proposal)
        
        with open(self.pending_path, "w") as f:
            json.dump(proposals, f, indent=2, ensure_ascii=False)
        
        return proposal

    def get_pending_sitrep(self):
        """承認待機中の提案を SitRep 向けにフォーマット"""
        if not os.path.exists(self.pending_path):
            return "No pending proposals."
            
        with open(self.pending_path, "r") as f:
            proposals = json.load(f)
            
        pending = [p for p in proposals if p["status"] == "PENDING_APPROVAL"]
        if not pending:
            return "No pending proposals."
            
        latest = pending[-1]
        return f"""
### ⚖️ 【Pending Strategic Approval】
- **Proposal ID**: `{latest['proposal_id']}`
- **Proposed Change**: Change `{latest['parameter']}` from `{latest['current_value']}` to `{latest['proposed_value']}`.
- **Reasoning**: {latest['reasoning']}
- **Risk/Benefit**: {latest['risk_benefit']}
- **Status**: **FROZEN (Awaiting Commander's 'Approve')**
"""

if __name__ == "__main__":
    gov = ParameterGovernance()
    # 1.1x 変更案の登録
    gov.propose_change(
        parameter="Gas Impact Coefficient",
        current_value="1.0x",
        proposed_value="1.1x",
        reasoning="シミュレーションにより期待値と実測値に 5% の乖離（過小評価）を検知したため。",
        risk_benefit="Benefit: P_net の精度向上により、より確実な利益機会を捕捉可能。 Risk: 係数が過大になると、本来利益が出る機会を見送る可能性がある。"
    )
    print(gov.get_pending_sitrep())
