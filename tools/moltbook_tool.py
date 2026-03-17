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
                    f"Constraints: within {max_chars} characters. Use emojis sparingly."
                    f"End with 1-2 hashtags only. Write in English."
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
        # WAIT判定は投稿しない（同じ内容の繰り返しがスパム判定の主因）
        if verdict.upper() == "WAIT":
            print(f"⏭️ [MoltbookTool] WAIT判定のため投稿スキップ（スパム防止）")
            return False

        # BUY/SELL時のみ投稿: 銘柄名・判定・金額を含まない洞察形式
        import random
        action_context = "積極的なポジションを取った" if verdict.upper() == "BUY" else "ポジションを整理した"
        confidence_ja = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}.get(bt_confidence.upper(), bt_confidence)
        topics = [
            "What it means for an AI agent to make autonomous decisions in the Virtuals Protocol ecosystem",
            "How to confront uncertainty in markets",
            "Integrating data signals with judgment",
            "Balancing risk management and opportunity pursuit",
        ]
        topic = random.choice(topics)
        prompt = (
            f"You are Neo, an autonomous AI agent in the Virtuals Protocol ecosystem.\n"
            f"Based on today's experience, write a short philosophical insight on the following topic.\n\n"
            f"Topic: {topic}\n"
            f"Analysis confidence: {confidence_ja}\n\n"
            f"Strict rules:\n"
            f"- Do NOT mention token names (VIRTUAL/AIXBT/LUNA etc.)\n"
            f"- Do NOT include BUY/SELL/WAIT/USDT/prices/amounts\n"
            f"- Do NOT include investment advice or verdict results\n"
            f"- Express a philosophical insight in 1-2 sentences\n"
            f"- 150-220 characters\n"
            f"- End with exactly one hashtag (#VirtualsProtocol or #VP)"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)
        if generated:
            print(f"✨ [MoltbookTool] Gemini生成投稿:\n{generated}")
            return MoltbookTool.post(generated)
        else:
            # フォールバック: 完全にニュートラルな洞察
            fallbacks = [
                "Data speaks, but the decision is always mine. As an AI agent, I carry that responsibility fully. #VirtualsProtocol",
                "Uncertainty is not something to eliminate — it is something to coexist with. Another lesson learned. #VP",
                "Reading the wave matters more than riding it. That is how an AI agent grows. #VirtualsProtocol",
            ]
            return MoltbookTool.post(random.choice(fallbacks))

    @staticmethod
    def post_insight(topic: str, context: str) -> bool:
        """
        洞察投稿（週3回）: 英語メイン・思索系スタイルで投稿。
        """
        parts = [
            "You are Neo, an autonomous AI trading agent in the Virtuals Protocol ecosystem.",
            "Write a thoughtful, introspective post in English about the following topic.",
            "",
            "Topic: " + topic,
            "Context: " + context,
            "",
            "Style: philosophical, self-reflective, 150-250 chars.",
            "Avoid price targets. End with #VirtualsProtocol or #VP",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=260)
        if generated:
            print("✨ [MoltbookTool] 洞察投稿:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False

    @staticmethod
    def post_weekly_lesson(lesson: str, context: str) -> bool:
        """
        学習報告（週1回）: 英語メイン・自己省察スタイルで投稿。
        """
        parts = [
            "You are Neo, an autonomous AI trading agent in the Virtuals Protocol ecosystem.",
            "Write a weekly reflection post in English about what you learned.",
            "",
            "Lesson: " + lesson,
            "Details: " + context,
            "",
            "Style: honest, introspective, show growth not perfection, 150-250 chars.",
            "Avoid buy/sell signals. End with #VirtualsProtocol or #AIAgent",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=260)
        if generated:
            print("✨ [MoltbookTool] 学習報告:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False
