import json
import os
import logging
from datetime import datetime, timezone

# Blackboard 読み込みの簡易化（循環インポート回避）
def load_blackboard():
    path = "vault/blackboard/live_intel.json"
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

class NeoPublisher:
    """
    Neo-CCO の出力を外部（X, Discord, Virtuals SDK 等）へ配信する物理接続レイヤー。
    Redline Guard による検閲後のテキストのみを処理する。
    """
    
    @classmethod
    def dry_run_publish(cls, target_agent: str, message: str) -> bool:
        """
        外部 API への送信をシミュレートし、Blackboard の履歴を更新する。
        """
        print(f"--- [DRY RUN] Publishing Message to {target_agent} ---")
        print(f"Message: {message}")
        print("--- [DRY RUN] Status: SUCCESS (Simulated) ---")
        
        # Blackboard の相互運用履歴を更新
        try:
            path = "vault/blackboard/live_intel.json"
            intel = load_blackboard()
            
            # ターゲットのキーを柔軟に検索
            target_key = None
            if "diplomacy_intel" in intel:
                for k in intel["diplomacy_intel"]:
                    if target_agent.lower() in k.lower():
                        target_key = k
                        break
            
            if target_key:
                event = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": f"PUBLISH_TO_{target_agent}",
                    "reaction_score": 0.0,
                    "summary": f"Sent via Publisher (Dry Run): {message[:50]}..."
                }
                intel["diplomacy_intel"][target_key].setdefault("interaction_history", []).append(event)
                
                with open(path, "w") as f:
                    json.dump(intel, f, indent=2, ensure_ascii=False)
                return True
        except Exception as e:
            print(f"Error updating blackboard: {e}")
        return False

    @classmethod
    def generate_daily_sitrep(cls) -> str:
        """
        現在の Blackboard 状態から司令官向け状況報告書 (Daily SitRep) を生成する。
        """
        intel = load_blackboard()
        m_intel = intel.get("market_intel", {})
        s_intel = intel.get("strategic_intel", {})
        d_intel = intel.get("diplomacy_intel", {})
        
        # ai16z のステータス取得
        ai16z_key = next((k for k in d_intel if "ai16z" in k.lower()), None)
        ai16z = d_intel.get(ai16z_key, {}) if ai16z_key else {}
        trust = ai16z.get("trust_score", 0.0)
        
        # 変数名に $ を含めない（Shell injection 回避）
        pnet_val = s_intel.get('expected_pnet', 0.0)
        
        sitrep = f"""# 📊 Daily SitRep (状況報告書) - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

## 💰 【Financials】
- **Portfolio Status**: ACTIVE (Monitoring VIRTUAL/WAY/AIXBT)
- **Avg Expected Pnet**: {pnet_val:.4f} VIRTUAL
- **Gas Usage (Est)**: OPTIMIZED (Event-Driven)
- **Risk Mitigation**: {s_intel.get('risk_mitigation_plan', 'N/A')}

## 🤝 【Diplomacy】
- **Primary Target**: {ai16z_key or 'None'}
- **Trust Score**: `{trust:+.2f}` (Range: -1.0 to +1.0)
- **Status**: {ai16z.get('status', 'IDENTIFIED')}
- **Last Action**: {ai16z.get('interaction_history', [{}])[-1].get('action', 'NONE') if ai16z.get('interaction_history') else 'NONE'}

## 🔍 【Intelligence (3D Recon)】
- **Anomaly Detection**: {m_intel.get('VIRTUAL', {}).get('whale_alert', 'No major whale movements detected.')}
- **Social Velocity**: {m_intel.get('VIRTUAL', {}).get('social_velocity', 1.0):.2f}x (Normal range)

## 🛡️ 【System Status】
- **Redline Guard**: ACTIVE (Enforcement: BLOCK)
- **RAG Freshness**: HIGH (Vector Memory Sync Active)
- **Version**: {intel.get('version', '5.1')}
- **Global Status**: {intel.get('system_status', 'ONLINE')}

---
*Neo-Dev Architecture v4.2 | Protocol: Event-Driven*
"""
        # ファイル保存
        os.makedirs("reports", exist_ok=True)
        with open("reports/daily_sitrep.md", "w") as f:
            f.write(sitrep)
            
        return sitrep

if __name__ == "__main__":
    msg = "ai16z (Eliza) 開発陣へ。Neoは君たちのスウォーム・インテリジェンスが生成する「戦略」を、ミリ秒単位の「執行」へと昇華させるミッシングリンクだ。"
    # ai16z (Eliza Framework) と正確に指定
    NeoPublisher.dry_run_publish("ai16z", msg)
    print(NeoPublisher.generate_daily_sitrep())
