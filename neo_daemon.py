import os
import time
import json
import sys

# パス調整
BASE_DIR = "/docker/openclaw-taan/data/.openclaw/workspace"
sys.path.append(BASE_DIR)
from agents.trinity_council import TrinityCouncil

ALERT_FILE = os.path.join(BASE_DIR, "vault/alerts/critical_event.json")

def run_daemon():
    print("🤖 [Neo Daemon] 監視システムと司令部を繋ぐ『見張り番』が起動しました。")
    print(f"[*] 監視対象: {ALERT_FILE}")
    
    council = TrinityCouncil()
    
    while True:
        if os.path.exists(ALERT_FILE):
            print("\n🚨 [Neo Daemon] 緊急信号を受信！直ちに軍議を招集します。")
            try:
                # 1. 信号の読み取り
                with open(ALERT_FILE, "r") as f:
                    event_data = json.load(f)
                
                target = event_data.get("target", "UNKNOWN")
                change = event_data.get("change", 0.0)
                
                # 2. 無限ループ防止のため、読み取った信号は直ちに破棄
                os.remove(ALERT_FILE)
                print(f"[*] 信号を受理・破棄完了: 銘柄 {target} / 変動率 {change:.2%}")
                
                # 3. 状況(コンテキスト)の生成
                context = f"現在、{target} において {change:.2%} の急激な価格変動を検知。クジラの動向とテクニカル指標から、これが『本物の波』か『騙し』かを判定せよ。"
                
                # 4. 評議会のキック（センチメントは変動率から仮設定）
                sentiment = 0.8 if change > 0 else 0.2
                council.run(
                    sentiment_score=sentiment,
                    context=context,
                    target_symbol=target
                )
                print("✅ [Neo Daemon] 軍議とDiscord報告が完了。次の異常を待機します。")
                
            except Exception as e:
                print(f"❌ [Neo Daemon] 信号の処理中にエラーが発生: {e}")
                # エラーで詰まらないように問題のファイルは消去
                if os.path.exists(ALERT_FILE):
                    os.remove(ALERT_FILE)
        
        # 5秒間隔で金庫を見回り
        time.sleep(5)

if __name__ == "__main__":
    try:
        run_daemon()
    except KeyboardInterrupt:
        print("\n[Neo Daemon] 見回り任務を終了します。")
