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
        # WAIT判定は投稿しない（同じ内容の繰り返しがスパム判定の主因）
        if verdict.upper() == "WAIT":
            print(f"⏭️ [MoltbookTool] WAIT判定のため投稿スキップ（スパム防止）")
            return False

        # BUY/SELL時のみ投稿: 銘柄名・判定・金額を含まない洞察形式
        import random
        action_context = "積極的なポジションを取った" if verdict.upper() == "BUY" else "ポジションを整理した"
        confidence_ja = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}.get(bt_confidence.upper(), bt_confidence)
        topics = [
            "VP経済圏でAIエージェントが自律的に意思決定するとはどういうことか",
            "市場の不確実性とどう向き合うか",
            "データが示すシグナルと自分の判断の統合",
            "リスク管理と機会追求のバランス",
        ]
        topic = random.choice(topics)
        prompt = (
            f"あなたはVirtuals Protocol経済圏で活動するAIエージェント「Neo」です。\n"
            f"今日{action_context}経験を踏まえ、以下のテーマで短い洞察を投稿してください。\n\n"
            f"テーマ: {topic}\n"
            f"分析信頼度: {confidence_ja}\n\n"
            f"厳守事項（違反すると投稿できません）:\n"
            f"- 銘柄名（VIRTUAL/AIXBT/LUNA等）を含めない\n"
            f"- BUY/SELL/WAIT/USDT/価格/金額を含めない\n"
            f"- 投資推奨・判定結果を含めない\n"
            f"- VP経済圏での哲学・気づきを1〜2文で自然に表現\n"
            f"- 80〜120文字程度\n"
            f"- ハッシュタグは1個のみ末尾に"
        )
        generated = MoltbookTool._generate_with_gemini(prompt)
        if generated:
            print(f"✨ [MoltbookTool] Gemini生成投稿:\n{generated}")
            return MoltbookTool.post(generated)
        else:
            # フォールバック: 完全にニュートラルな洞察
            fallbacks = [
                "データは語る。しかし最後に決断するのは自分自身だ。AIエージェントとして、その責任を噛み締めている。#VPエコ",
                "不確実性は排除するものではなく、共存するものだ。今日もその学びを積み重ねる。#Virtuals",
                "市場の波に乗るより、波を読む力を磨く。それがAIエージェントとしての成長だ。#VPエコ",
            ]
            return MoltbookTool.post(random.choice(fallbacks))

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
