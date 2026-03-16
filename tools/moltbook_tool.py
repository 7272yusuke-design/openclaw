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
        # スパム対策: verdict/金額を直接含めず洞察形式に変換
        stance = "強気シグナルを検知" if verdict.upper() == "BUY" else ("調整シグナルを検知" if verdict.upper() == "SELL" else "様子見を継続")
        confidence_ja = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}.get(bt_confidence.upper(), bt_confidence)
        prompt = (
            f"あなたはVirtuals Protocol経済圏で活動するAIエージェント「Neo」です。\n"
            f"市場分析の結果を、洞察・観察として自然な文体で投稿してください。\n\n"
            f"分析対象: VP生態系の主要トークン\n"
            f"市場シグナル: {stance}\n"
            f"分析信頼度: {confidence_ja}\n"
            f"観察内容: {verdict_text[:150]}\n\n"
            f"要件:\n"
            f"- BUY/SELL/USDT/ドル金額などの取引推奨キーワードを一切含めない\n"
            f"- VP経済圏エージェントとしての独自の視点・洞察を1〜2文で表現\n"
            f"- 自然な観察日記のような文体で\n"
            f"- 140文字程度に収める"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)

        if generated:
            print(f"✨ [MoltbookTool] Gemini生成投稿:\n{generated}")
            return MoltbookTool.post(generated)
        else:
            # フォールバック: スパム対策済みフォーマット
            fallback = (
                f"🧠 Neo分析ログ\n"
                f"VP生態系に{stance}。\n"
                f"分析信頼度: {confidence_ja} | 精度実績: {accuracy}%\n"
                f"引き続き市場の動向を注視します。"
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
