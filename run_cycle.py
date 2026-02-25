import time
import json
import os
from datetime import datetime
from neo_main import NeoSystem

# OpenClawのweb_searchツールを模倣するラッパー (バックグラウンド実行用)
# ※ 注意: 外部スクリプトからはOpenClawのツールを直接呼べないため、
# 簡易的な検索結果を返すか、あるいは MarketData (DexScreener) のみで判断させる。
# 今回は「ScoutCrew」がWeb検索に依存しているため、
# 検索機能がないとエラーになるか精度が落ちる。
# 妥協案として、MarketDataの結果を「検索結果」としても渡す。
def background_search_wrapper(query):
    print(f"[Background] Searching for: {query}")
    # 実際には検索できないので、汎用的なレスポンスを返すか、
    # MarketDataの結果を利用するようScoutCrewを調整するのが理想だが、
    # ここではエラー回避のためのダミーを返す。
    return [
        {"title": "Background Monitor", "snippet": "System is running in background monitoring mode.", "url": "internal://monitor"}
    ]

def run_loop():
    print("Starting Neo Autonomous Cycle Loop (Hourly)...")
    
    # ログディレクトリの作成
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "market_cycle.jsonl")

    # NeoSystemの初期化
    system = NeoSystem(web_search_tool=background_search_wrapper)

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Executing cycle...")
            
            topic = "Virtuals Protocol Market Update"
            
            # 自律サイクルの実行
            # ※ search_results=None にすると内部で ScoutCrew が web_search を呼ぶ。
            # background_search_wrapper が呼ばれる。
            result = system.autonomous_post_cycle(topic)
            
            # 結果にタイムスタンプを付与
            result["timestamp"] = current_time
            
            # ログファイルへの追記 (JSONL形式)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            
            print(f"Cycle completed. Logged to {log_file}")
            
        except Exception as e:
            print(f"Error in cycle: {e}")
            with open(log_file, "a", encoding="utf-8") as f:
                error_log = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "error": str(e)}
                f.write(json.dumps(error_log, ensure_ascii=False) + "\n")

        # 1時間待機 (3600秒)
        print("Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    run_loop()
