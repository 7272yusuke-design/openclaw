import os
import sys

# パスの追加
sys.path.append('/docker/openclaw-taan/data/.openclaw/workspace')

from agents.trinity_council import TrinityCouncil
from tools.discord_reporter import DiscordReporter

def dry_run():
    print("🚀 [Dry Run] 新生ネオ・最終連結テストを開始します...")
    
    # 評議会の招集
    # sentiment_score=0.8 (強気), context="RSIの売られすぎからの反発"
    council = TrinityCouncil()
    try:
        result = council.run(sentiment_score=0.8, context="RSI Oversold Recovery Test", target_symbol="AIXBT")
        print(f"✅ テスト成功: {result}")
    except Exception as e:
        print(f"❌ テスト失敗: {e}")

if __name__ == "__main__":
    dry_run()
