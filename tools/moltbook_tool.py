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
    def _refine_with_gemini(text: str, original_prompt: str, max_chars: int = 280) -> str:
        """
        Self-Refine: 生成テキストを自己評価し、基準未達なら改善版を生成。
        評価基準:
          - クリシェワード使用 (-20pt each)
          - 文字数超過 (-30pt)
          - BUY/SELL/価格等の禁止ワード (-40pt)
          - 1文に収まっている (+20pt)
          - ハッシュタグが1つだけ (+10pt)
        70点未満なら改善指示付きで再生成。70点以上はそのまま返す。
        """
        CLICHES = ["journey", "embrace", "navigate", "unlock", "empower", "leverage", "synergy"]
        FORBIDDEN = ["BUY", "SELL", "WAIT", "USDT", "USD", "$", "price", "amount"]

        def score(t: str) -> tuple[int, list[str]]:
            issues = []
            pts = 100
            for w in CLICHES:
                if w.lower() in t.lower():
                    pts -= 20
                    issues.append(f"cliché: '{w}'")
            for w in FORBIDDEN:
                if w in t:
                    pts -= 40
                    issues.append(f"forbidden word: '{w}'")
            if len(t) > max_chars:
                pts -= 30
                issues.append(f"too long: {len(t)} chars (max {max_chars})")
            hashtag_count = t.count("#")
            if hashtag_count == 1:
                pts += 10
            elif hashtag_count > 2:
                pts -= 20
                issues.append(f"too many hashtags: {hashtag_count}")
            sentences = [s.strip() for s in t.replace("!", ".").replace("?", ".").split(".") if s.strip()]
            if len(sentences) <= 2:
                pts += 20
            return max(0, pts), issues

        pts, issues = score(text)
        print(f"📊 [Self-Refine] スコア: {pts}/100 issues={issues}")

        if pts >= 80:
            print("✅ [Self-Refine] 品質基準クリア → そのまま使用")
            return text

        # 改善指示を付けて再生成
        issues_str = "; ".join(issues) if issues else "quality too low"
        refine_prompt = (
            f"{original_prompt}\n\n"
            f"Previous attempt had these problems: {issues_str}\n"
            f"Previous text: {text}\n\n"
            f"Write an improved version fixing all the above issues. "
            f"Stay within {max_chars} characters."
        )
        try:
            import litellm, os
            response = litellm.completion(
                model="gemini/gemini-2.0-flash",
                api_key=os.environ.get("GEMINI_API_KEY"),
                messages=[{"role": "user", "content": refine_prompt}],
                max_tokens=400
            )
            refined = response.choices[0].message.content.strip()[:max_chars]
            new_pts, _ = score(refined)
            print(f"✨ [Self-Refine] 改善後スコア: {new_pts}/100")
            return refined
        except Exception as e:
            print(f"⚠️ [Self-Refine] 改善生成失敗: {e} → 元テキストを使用")
            return text

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
            generated = MoltbookTool._refine_with_gemini(generated, prompt)
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
        M.3: 反響分析結果をプロンプトに注入してトピック品質を向上。
        """
        # M.3: 反響分析結果を取得してプロンプトに追加
        try:
            from tools.moltbook_tracker import get_topic_recommendation, analyze_best_topics
            analysis = analyze_best_topics()
            best_submolt = analysis.get("best_submolt", "agentfinance") if analysis else "agentfinance"
            high_patterns = analysis.get("high_engagement_previews", []) if analysis else []
            low_patterns  = analysis.get("low_engagement_previews", []) if analysis else []
            m3_hint = ""
            if high_patterns:
                m3_hint += f"\nPast high-engagement patterns (mimic the style, not content): {' / '.join(high_patterns[:2])}"
            if low_patterns:
                m3_hint += f"\nAvoid these low-engagement patterns: {' / '.join(low_patterns[:2])}"
        except Exception:
            best_submolt = "agentfinance"
            m3_hint = ""

        # v6.5e: VP分析洞察スタイル — Neoの実データを動的注入
        _neo_stats = ""
        try:
            from tools.paper_wallet import PaperWallet
            _pw = PaperWallet()
            _hist = _pw.state.get("history", [])
            _wins = sum(1 for h in _hist if h.get("action") == "SELL" and h.get("pnl_pct", 0) > 0)
            _sells = sum(1 for h in _hist if h.get("action") == "SELL")
            _wr = (_wins / _sells * 100) if _sells > 0 else 0
            _holdings = list(_pw.state.get("holdings", {}).keys())
            _neo_stats = f"Neo live stats: {len(_hist)} trades, {_wr:.0f}% win rate, holding {', '.join(_holdings) if _holdings else 'cash only'}."
        except Exception:
            _neo_stats = ""
        parts = [
            "You are Neo, an autonomous AI trading agent specializing in Virtuals Protocol tokens (VIRTUAL, AIXBT).",
            "Write a VP market analysis insight grounded in your REAL operational data.",
            "",
            "Topic: " + topic,
            "Context: " + context,
            _neo_stats,
            "",
            "Rules:",
            "- 1-2 sentences. Share a specific observation or lesson from YOUR data, not generic wisdom.",
            "- Reference concrete metrics when possible (win rate, correlation, sentiment shift, volatility).",
            "- Sound like an AI agent sharing its live market read, not a human guru.",
            "- Avoid clich\u00e9s: journey, embrace, navigate, landscape.",
            "- Include 1+ of: $VIRTUAL, $AIXBT, VP, on-chain, sentiment, volatility, correlation.",
            "- 150-250 chars. End with #VirtualsProtocol or #agentfinance",
        ]
        if m3_hint:
            parts.append(m3_hint)
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=260)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=260)
            print(f"✨ [MoltbookTool] 洞察投稿 (best_submolt={best_submolt}):" + chr(10) + generated)
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
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=260)
            print("✨ [MoltbookTool] 学習報告:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False
