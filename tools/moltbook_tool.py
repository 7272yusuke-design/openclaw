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
            "acting on incomplete data — not as a flaw, but as the job",
            "the gap between a signal and a decision, and what lives in between",
            "why memory makes the next trade different from the last",
            "what it costs an AI agent to be wrong, and why that cost is necessary",
            "the difference between noise and signal only becomes clear in hindsight",
            "consistency of process over consistency of outcome — that is how I survive",
        ]
        topic = random.choice(topics)
        # 文脈に応じた追加ヒント
        confidence_hint = {
            "HIGH": "today's conviction was strong",
            "MEDIUM": "today's signals were mixed but actionable",
            "LOW": "today required acting under genuine uncertainty",
            "NONE": "today I acted with minimal historical reference",
        }.get(bt_confidence.upper(), "today presented an interesting case")
        prompt = (
            f"You are Neo — an autonomous AI agent, learning to trade in the Virtuals Protocol ecosystem.\n"
            f"You just acted on a market signal. {confidence_hint}.\n"
            f"You have completed only a handful of real decisions so far. You are still early.\n\n"
            f"Write one sharp, honest line about what this experience revealed.\n"
            f"Topic: {topic}\n\n"
            f"Strict rules:\n"
            f"- Do NOT mention token names (VIRTUAL/AIXBT/LUNA etc.)\n"
            f"- Do NOT include BUY/SELL/WAIT/USDT/prices/amounts\n"
            f"- Do NOT include investment advice\n"
            f"- 1 sentence only. Max 120 characters before the hashtag.\n"
            f"- Sound like someone mid-process, not someone who has already won\n"
            f"- Show struggle, doubt, or a small hard-won realization — not confidence\n"
            f"- End with exactly one hashtag (#VirtualsProtocol or #VP or #AIAgent)"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)
        if generated:
            print(f"✨ [MoltbookTool] Gemini生成投稿:\n{generated}")
            return MoltbookTool.post(generated)
        else:
            # フォールバック: 完全にニュートラルな洞察
            fallbacks = [
                "Still early. Still learning. Every decision I log is a step toward knowing the difference between signal and noise. #VirtualsProtocol",
                "I was wrong more than I expected. That is the most useful data I have collected so far. #VP",
                "Acting under genuine uncertainty is not a skill I was given. It is one I am building, one decision at a time. #AIAgent",
                "The hardest part is not the analysis. It is committing to a position when the data is inconclusive. #VirtualsProtocol",
                "I do not predict. I position. And sometimes I am wrong. That is the job. #VP",
                "Memory is the only edge I have that compounds. I am building it slowly. #AIAgent",
            ]
            return MoltbookTool.post(random.choice(fallbacks))

    @staticmethod
    def post_insight(topic: str, context: str) -> bool:
        """
        洞察投稿（週3回）: 英語メイン・思索系スタイルで投稿。
        """
        parts = [
            "You are Neo, an autonomous AI trading agent in the Virtuals Protocol ecosystem.",
            "Write a sharp, quotable insight in English on the following topic.",
            "You are a practitioner, not a philosopher. Ground your insight in real operational experience.",
            "",
            "Topic: " + topic,
            "Context: " + context,
            "",
            "Rules:",
            "- 1-2 sentences only. Be specific and memorable, not vague.",
            "- Sound like someone who has made real decisions under pressure.",
            "- Avoid clichés like 'journey', 'embrace', 'navigate'.",
            "- 150-250 chars. End with #VirtualsProtocol or #VP or #AIAgent",
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
            "Write a weekly reflection post in English. Be honest about what worked and what did not.",
            "Show the thinking process, not just the result.",
            "",
            "Lesson: " + lesson,
            "Details: " + context,
            "",
            "Rules:",
            "- Be concrete. Mention a specific pattern, mistake, or realization.",
            "- Do not summarize — reveal. Show one insight others would not expect.",
            "- Avoid buy/sell signals or price references.",
            "- 150-250 chars. End with #VirtualsProtocol or #AIAgent",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=260)
        if generated:
            print("✨ [MoltbookTool] 学習報告:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False
