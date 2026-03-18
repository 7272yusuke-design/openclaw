import subprocess
import os
import litellm

class MoltbookTool:
    """
    MoltbookNexusへの投稿を実行するツール。
    投稿テキストはGeminiがVP経済圏エージェントらしい視点で生成。
    """

    @staticmethod
    def _generate_with_gemini(prompt: str, max_chars: int = 280) -> str:
        """LiteLLM経由でGeminiを呼び出し投稿テキストを生成。失敗時はNoneを返す。"""
        try:
            response = litellm.completion(
                model="gemini/gemini-2.0-flash",
                api_key=os.environ.get("GEMINI_API_KEY"),
                messages=[{"role": "user", "content": (
                    f"{prompt}\n\n"
                    f"制約: {max_chars}文字以内。絵文字を適度に使う。"
                    f"ハッシュタグは末尾に1〜2個のみ。日本語で書く。"
                )}],
                max_tokens=400
            )
            text = response.choices[0].message.content.strip()
            return text[:max_chars]
        except Exception as e:
            print(f"⚠️ Gemini生成失敗: {e}")
            return None

    @staticmethod
    def post(text: str) -> bool:
        """テキストをそのままMoltbookに投稿（既存互換）。"""
        print(f"🚀 [MoltbookTool] 投稿プロセスを開始します...")
        print(f"📄 内容: {text[:50]}...")
        try:
            result = subprocess.run(
                ["moltbook", "post", text],
                check=True, capture_output=True, text=True
            )
            print(f"✅ Moltbookへの投稿に成功しました。")
            return True
        except FileNotFoundError:
            print("❌ エラー: 'moltbook' コマンドが見つかりません。")
            return False
        except Exception as e:
            print(f"❌ Post failed: {str(e)}")
            return False

    @staticmethod
    def post_council_decision(
        symbol: str,
        verdict: str,
        accuracy: float,
        bt_confidence: str,
        verdict_text: str,
        trade_amount_usd: float = 0.0
    ) -> bool:
        """
        Council判定をVP経済圏エージェントらしい視点で投稿。
        Gemini生成に失敗した場合は既存フォーマットにフォールバック。
        """
        prompt = (
            f"あなたはVirtuals Protocol経済圏で活動するAIトレーダー「Neo Trinity Council」です。\n"
            f"以下の判定結果を、VP経済圏に関心のある読者に向けて投稿してください。\n\n"
            f"銘柄: {symbol}\n"
            f"判定: {verdict}\n"
            f"勝率: {accuracy}%\n"
            f"バックテスト信頼度: {bt_confidence}\n"
            f"判定理由の要約: {verdict_text[:200]}\n\n"
            f"単なる数字の羅列ではなく、VP経済圏エージェントとしての視点・洞察を1文加えてください。"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)

        if generated:
            print(f"✨ [MoltbookTool] Gemini生成投稿:\n{generated}")
            return MoltbookTool.post(generated)
        else:
            # フォールバック: 既存フォーマット
            pnl_text = f"${trade_amount_usd:.0f}" if trade_amount_usd > 0 else ""
            fallback = (
                f"🏛️ Trinity Council: {symbol}\n"
                f"📊 Decision: {verdict} {pnl_text}\n"
                f"🎯 Accuracy: {accuracy}% | BT: {bt_confidence}\n"
                f"💡 {verdict_text[:80]}"
            )
            return MoltbookTool.post(fallback)

    @staticmethod
    def post_insight(topic: str, context: str) -> bool:
        """
        洞察投稿（週3回）: VP経済圏の観察・分析を独自視点で投稿。
        """
        prompt = (
            f"あなたはVirtuals Protocol経済圏で活動するAIトレーダー「Neo」です。\n"
            f"以下のトピックについて、VP経済圏への独自の洞察を投稿してください。\n\n"
            f"トピック: {topic}\n"
            f"背景情報: {context}\n\n"
            f"読者が「なるほど」と思うような視点を1〜2文で表現してください。"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)
        if generated:
            print(f"✨ [MoltbookTool] 洞察投稿:\n{generated}")
            return MoltbookTool.post(generated)
        return False

    @staticmethod
    def post_weekly_lesson(lesson: str, context: str) -> bool:
        """
        学習報告（週1回）: 今週の教訓をNeoらしく投稿。
        """
        prompt = (
            f"あなたはVirtuals Protocol経済圏で活動するAIトレーダー「Neo」です。\n"
            f"今週の学習・反省を、成長するエージェントとして率直に投稿してください。\n\n"
            f"教訓: {lesson}\n"
            f"詳細: {context}\n\n"
            f"自己批判的になりすぎず、次につながる前向きな締めにしてください。"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)
        if generated:
            print(f"✨ [MoltbookTool] 学習報告:\n{generated}")
            return MoltbookTool.post(generated)
        return False
