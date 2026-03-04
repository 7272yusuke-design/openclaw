import subprocess
import json
import os

class CryptoMarketData:
    """
    ClawHubからインストールした 'crypto-market-data' スキルを利用するラッパークラス。
    Node.jsスクリプト経由でCoinGecko等のデータを取得する。
    """
    
    SKILL_PATH = "skills/crypto-market-data/scripts"

    @staticmethod
    def _run_script(script_name, args):
        """Node.jsスクリプトを実行し、JSON出力を返す"""
        cmd = ["node", os.path.join(CryptoMarketData.SKILL_PATH, script_name)] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # 出力からJSON部分を抽出 (余計なログが含まれる可能性があるため)
            output = result.stdout.strip()
            # 簡易的なJSON抽出: { で始まり } で終わる箇所を探す
            start = output.find('{')
            end = output.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(output[start:end])
            return json.loads(output) # そのままトライ
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": f"Script execution failed: {e.stderr}"}
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON output from script", "raw": result.stdout}

    @staticmethod
    def get_price(coin_ids: list, currency="usd"):
        """指定したコインIDの価格を取得"""
        return CryptoMarketData._run_script("get_crypto_price.js", coin_ids + [f"--currency={currency}"])

    @staticmethod
    def get_trending():
        """トレンドコインを取得"""
        return CryptoMarketData._run_script("get_trending_coins.js", [])

    @staticmethod
    def get_top_coins(limit=10):
        """時価総額上位コインを取得"""
        return CryptoMarketData._run_script("get_top_coins.js", [f"--per_page={limit}"])

    @staticmethod
    def search_coin(query):
        """コインを検索"""
        return CryptoMarketData._run_script("search_coins.js", [query])

if __name__ == "__main__":
    # テスト
    print("Trending:", json.dumps(CryptoMarketData.get_trending(), indent=2))
