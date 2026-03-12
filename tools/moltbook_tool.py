import subprocess
import os

class MoltbookTool:
    """
    MoltbookNexusへの投稿を物理的に実行するツール。
    """
    @staticmethod
    def post(text: str):
        print(f"🚀 [MoltbookTool] 投稿プロセスを開始します...")
        print(f"📄 内容: {text[:50]}...")
        
        try:
            # 🛡️ 実弾投下: moltbook コマンドを実行
            # textを引数として渡し、標準出力をキャプチャする
            result = subprocess.run(
                ["moltbook", "post", text], 
                check=True, 
                capture_output=True, 
                text=True
            )
            print(f"✅ Moltbookへの投稿に成功しました。")
            return True
        except FileNotFoundError:
            print("❌ エラー: 'moltbook' コマンドが見つかりません。パスを確認してください。")
            return False
        except Exception as e:
            print(f"❌ Post failed: {str(e)}")
            return False
