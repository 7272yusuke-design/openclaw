import json
import os
import logging
from datetime import datetime, timezone
from tools.discord_reporter import DiscordReporter

def load_blackboard():
    path = "vault/blackboard/live_intel.json"
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

class NeoPublisher:
    """
    Neo-CCO の出力を外部へ配信する物理接続レイヤー。
    """
    
    @classmethod
    def publish_to_discord(cls, message: str):
        """Discordへ直接メッセージを送る"""
        return DiscordReporter.send_report(message)

    @classmethod
    def generate_daily_sitrep(cls, auto_publish=True) -> str:
        """
        Blackboardから状況報告書を生成し、Discordへ送信する。
        """
        intel = load_blackboard()
        m_intel = intel.get("market_intel", {})
        s_intel = intel.get("strategic_intel", {})
        
        # 報告書の組み立て（既存の優秀なフォーマットを継承）
        pnet_val = s_intel.get('expected_pnet', 0.0)
        
        sitrep = f"""# 📊 Neo SitRep - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

## 💰 【Financials】
- **Portfolio**: ACTIVE (VIRTUAL Monitoring)
- **Expected Pnet**: {pnet_val:.4f}
- **Risk Mitigation**: {s_intel.get('risk_mitigation_plan', 'Active')}

## 🔍 【Intelligence】
- **VIRTUAL Price**: ${m_intel.get('VIRTUAL', {}).get('price', 0.0):.4f}
- **Whale Alert**: {m_intel.get('VIRTUAL', {}).get('whale_alert', 'None')}

## 🛡️ 【System Status】
- **Global Status**: {intel.get('system_status', 'ONLINE')}
- **Version**: {intel.get('version', '5.1')}
"""
        # ファイル保存
        os.makedirs("reports", exist_ok=True)
        with open("reports/daily_sitrep.md", "w") as f:
            f.write(sitrep)
            
        # 📡 Discordへ送信
        if auto_publish:
            DiscordReporter.send_report(sitrep)
            
        return sitrep

if __name__ == "__main__":
    # テスト実行
    print("--- Sending Test SitRep to Discord ---")
    NeoPublisher.generate_daily_sitrep()
