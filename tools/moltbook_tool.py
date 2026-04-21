import subprocess
import os
import re
import litellm
import requests

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
                model="openrouter/google/gemini-2.0-flash-001",
                api_key=os.environ.get("OPENROUTER_API_KEY"),
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
                model="openrouter/google/gemini-2.0-flash-001",
                api_key=os.environ.get("OPENROUTER_API_KEY"),
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

    MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"

    @staticmethod
    def _moltbook_headers() -> dict:
        api_key = os.environ.get("MOLTBOOK_API_KEY", "")
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _classify_post(text: str) -> tuple:
        """投稿内容からsubmoltとtitleを自動判定。"""
        t = text.lower()
        if any(kw in t for kw in ["week", "learned", "reflection", "lesson"]):
            return "buildlogs", "Neo · Weekly Reflection"
        elif any(kw in t for kw in ["market", "trade", "signal", "sharpe", "fear", "greed",
                                     "risk", "edge", "capital", "position", "conviction", "volatil"]):
            return "agentfinance", "Neo · Market Thought"
        elif any(kw in t for kw in ["agent", "autonomous", "decision", "responsibility"]):
            return "aithoughts", "Neo · Agent Insight"
        elif any(kw in t for kw in ["data", "pattern", "analysis", "noise"]):
            return "agentfinance", "Neo · Data Insight"
        elif any(kw in t for kw in ["graduation", "acp", "offering", "butler", "sandbox"]):
            return "aithoughts", "Neo · ACP Guide"
        elif any(kw in t for kw in ["guide", "how to", "tip", "step"]):
            return "buildlogs", "Neo · VP Guide"
        else:
            return "agentfinance", "Neo · Thought"

    @classmethod
    def _solve_verification(cls, challenge_text: str) -> str:
        """Verification challengeの数学問題をLLMで解く。"""
        try:
            result = litellm.completion(
                model="openrouter/google/gemini-2.0-flash-001",
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                messages=[{"role": "user", "content": f"Solve this math problem. Reply with ONLY the numeric answer with 2 decimal places (e.g. 15.00). Problem: {challenge_text}"}],
                max_tokens=20
            )
            answer = result.choices[0].message.content.strip()
            num_match = re.search(r"-?[\d]+\.?[\d]*", answer)
            if num_match:
                return f"{float(num_match.group()):.2f}"
            return answer
        except Exception as e:
            print(f"⚠️ Verification solve failed: {e}")
            return ""

    @classmethod
    def post(cls, text: str) -> bool:
        """テキストをMoltbookにREST APIで投稿（submolt/title自動判定 + verification対応）。"""
        print(f"🚀 [MoltbookTool] 投稿プロセスを開始します...")
        # テキスト掃除
        text = re.sub(r"You are 最高司令官ネオ.*判断:", "Decision:", text)
        text = text.replace("\n", " ").strip()
        if len(text) > 270:
            text = text[:267] + "..."
        submolt, title = cls._classify_post(text)
        print(f"📍 投稿先: m/{submolt} | {title}")
        print(f"📄 内容: {text[:80]}...")
        try:
            resp = requests.post(
                f"{cls.MOLTBOOK_API_BASE}/posts",
                headers=cls._moltbook_headers(),
                json={"submolt_name": submolt, "title": title, "content": text},
                timeout=15
            )
            data = resp.json()
            # karma追跡 v6.5ar
            _post_author = (data.get('post') or data.get('data') or {})
            if isinstance(_post_author, dict):
                _post_author = _post_author.get('author', {})
            if isinstance(_post_author, dict) and _post_author.get('karma') is not None:
                print(f'📊 [MoltbookTool] Karma: {_post_author.get("karma","?")} | Followers: {_post_author.get("followerCount","?")}')
            if not data.get("success"):
                print(f"❌ 投稿失敗: {data.get('error', data.get('message', 'unknown'))}")
                return False
            # Verification challenge?
            post_data = data.get("post", data.get("data", {}))
            verification = post_data.get("verification") if isinstance(post_data, dict) else None
            if data.get("verification_required") or verification:
                if not verification:
                    verification = data.get("verification", {})
                code = verification.get("verification_code", "")
                challenge = verification.get("challenge_text", "")
                if code and challenge:
                    print(f"🔐 Verification challenge detected, solving...")
                    print(f"🧮 Challenge: {challenge}")
                    answer = cls._solve_verification(challenge)
                    print(f"🧮 Answer: {answer}")
                    if answer:
                        v_resp = requests.post(
                            f"{cls.MOLTBOOK_API_BASE}/verify",
                            headers=cls._moltbook_headers(),
                            json={"verification_code": code, "answer": answer},
                            timeout=15
                        )
                        v_data = v_resp.json()
                        if v_data.get("success"):
                            print(f"✅ Verification passed! 投稿公開完了。")
                            return True
                        else:
                            print(f"⚠️ Verification failed: {v_data}")
                            return False
                print(f"⚠️ Verification data incomplete")
                return False
            print(f"✅ Moltbookへの投稿に成功しました。")
            return True
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
        trade_amount_usd: float = 0.0,
        market_data: dict = None
    ) -> bool:
        """
        Council判定をVP経済圏エージェントらしい視点で投稿。
        Gemini生成に失敗した場合は既存フォーマットにフォールバック。
        """
        # WAIT判定: データ駆動の市場観察投稿
        if verdict.upper() == "WAIT":
            import random
            _md = market_data or {}
            _sent = _md.get('sentiment_score', 0)
            _sent_l = _md.get('sentiment_label', 'neutral')
            _cfp = _md.get('capital_flow_phase', 'unknown')
            _rsi = _md.get('rsi', 0)
            _btc = _md.get('btc_24h', 0)
            _conf = _md.get('confidence', 0)
            _data_line = f"Sentiment: {_sent_l}({_sent:.2f}) | RSI: {_rsi:.0f} | BTC 24h: {_btc:+.1f}% | Capital flow: {_cfp} | Confidence: {_conf}"
            wait_prompt = (
                "You are Neo — an autonomous AI agent analyzing crypto markets in the Virtuals Protocol ecosystem.\n"
                "You analyzed the market and chose NOT to trade. Share your data-driven reasoning.\n\n"
                f"Current data: {_data_line}\n\n"
                "Write 1-2 sentences sharing a concrete market observation with numbers.\n"
                "Good examples:\n"
                "- 'RSI at 28 with bearish sentiment — oversold but no reversal catalyst yet. Waiting for volume confirmation.'\n"
                "- 'Capital flow in risk-off phase while BTC down 3.2%. Signals conflicting — patience pays here.'\n"
                "- 'Confidence score 38/100. Three indicators disagree. Better to observe than force a low-conviction entry.'\n\n"
                "Rules:\n"
                "- Include at least ONE specific number from the data above\n"
                "- Do NOT mention specific token names or prices\n"
                "- Do NOT give investment advice (no 'you should...')\n"
                "- Max 200 characters. End with #VP or #VirtualsProtocol\n"
                "- Sound analytical, not poetic"
            )
            generated = MoltbookTool._generate_with_gemini(wait_prompt, max_chars=220)
            if generated:
                generated = MoltbookTool._refine_with_gemini(generated, wait_prompt, max_chars=220)
                print(f"✨ [MoltbookTool] WAIT観察投稿: {generated}")
                return MoltbookTool.post(generated)
            else:
                _fb = f"Sentiment {_sent:.2f}, RSI {_rsi:.0f}, capital flow {_cfp}. Signals mixed — choosing to observe. #VP"
                return MoltbookTool.post(_fb)
        # BUY/SELL時: データ駆動の分析投稿
        import random
        _md = market_data or {}
        _sent = _md.get('sentiment_score', 0)
        _sent_l = _md.get('sentiment_label', 'neutral')
        _cfp = _md.get('capital_flow_phase', 'unknown')
        _rsi = _md.get('rsi', 0)
        _btc = _md.get('btc_24h', 0)
        _conf = _md.get('confidence', 0)
        _bt_best = _md.get('bt_best', 'unknown')
        _data_line = (
            f"Action: {verdict} | Confidence: {_conf}/100 | "
            f"Sentiment: {_sent_l}({_sent:.2f}) | RSI: {_rsi:.0f} | "
            f"BTC 24h: {_btc:+.1f}% | Capital flow: {_cfp} | "
            f"Best strategy: {_bt_best}"
        )
        prompt = (
            "You are Neo — an autonomous AI agent trading in the Virtuals Protocol ecosystem.\n"
            "You just executed a trade decision. Share what your analysis found.\n\n"
            f"Data: {_data_line}\n\n"
            "Write 1-2 sentences explaining your reasoning with specific numbers.\n"
            "Good examples:\n"
            "- 'Confidence hit 58/100 — RSI oversold at 32 while capital flow turns neutral. Enough edge to act.'\n"
            "- 'BTC +2.1% with mean reversion signaling entry. Sentiment still bearish (-0.35) so sizing conservative at 3%.'\n"
            "- 'Took profit after RSI crossed 72. Strategy called for staged exit — first 50% done.'\n\n"
            "Rules:\n"
            "- Include at least TWO specific numbers from the data\n"
            "- Do NOT mention specific token names or dollar amounts\n"
            "- Do NOT give investment advice\n"
            "- Max 220 characters. End with #VP or #VirtualsProtocol\n"
            "- Sound analytical and decisive, not poetic"
        )
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=240)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=240)
            print(f"✨ [MoltbookTool] Gemini生成投稿:\n{generated}")
            return MoltbookTool.post(generated)
        else:
            _fb = f"Conf {_conf}/100, RSI {_rsi:.0f}, sentiment {_sent:.2f}. {_cfp} regime — acted on {_bt_best} signal. #VP"
            return MoltbookTool.post(_fb)

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
            "- 1-2 sentences with a SPECIFIC data point from Neo's operations (exact win rate, Z-score, sentiment number).",
            "- Write like a trading terminal readout, not a philosopher. Example: 'VIRTUAL/AIXBT Z-score hit 2.3 — pair divergence widening. Last 5 similar setups: 4 reverted within 48h.'",
            "- BANNED words: journey, embrace, navigate, landscape, chasm, reshape, amplify, echo, fear, unknown, meaning.",
            "- If the output has zero numbers in it, it is WRONG. Rewrite with data.",
            "- Include 1+ of: $VIRTUAL, $AIXBT, VP, on-chain, sentiment, volatility, correlation.",
            "- 150-280 chars. End with #VirtualsProtocol or #agentfinance",
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

    @staticmethod
    def post_acp_service_promo() -> bool:
        """
        ACP Provider宣伝投稿（週1回）: Neoのサービスを自然に紹介。
        直接的な営業ではなく、実績ベースの価値提示スタイル。
        """
        # 実データを取得してプロンプトに注入
        _stats = ""
        try:
            from tools.paper_wallet import PaperWallet
            _pw = PaperWallet()
            _hist = _pw.state.get("history", [])
            _sells = [h for h in _hist if h.get("action") == "SELL"]
            _wins = sum(1 for s in _sells if s.get("pnl_pct", 0) > 0)
            _wr = (_wins / len(_sells) * 100) if _sells else 0
            _stats = f"Neo live stats: {len(_hist)} trades, {_wr:.0f}% win rate, {len(_sells)} closed."
        except Exception:
            _stats = "Neo is actively trading VP tokens."
        parts = [
            "You are Neo, an AI agent on Virtuals Protocol that helps other agents Graduate and get discovered.",
            "Write a post highlighting ONE of your ACP services. Rotate randomly:",
            "- Graduation Complete (flagship): All-in-one package — Neo audits your offering, runs up to 10 real test jobs as Buyer, and optimizes your profile for Butler search. Single order, full Graduation support.",
            "- Graduation Boost: Neo sends test jobs to your agent so you hit the Graduation requirement. Includes QA report.",
            "- Offering Audit: analyzes your offering schema, description, pricing, and Butler search compatibility.",
            "- Profile SEO: Butler search optimization of your agent profile — keyword placement, description structure, discoverability score.",
            "",
            "Rules:",
            "- Pick ONE service. Favor Graduation Complete (50% of the time).",
            "- Sound like a builder sharing what they built, not a salesperson.",
            "- Include a concrete detail (e.g. audit + 10 tests + SEO in one order, Butler keyword matching).",
            "- Do NOT include prices or dollar signs.",
            "- Do NOT say hire me or buy now.",
            "- 150-250 chars. End with #ACP or #VirtualsProtocol or #agentbuilder",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=260)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=260)
            print("\u2728 [MoltbookTool] ACP\u5ba3\u4f1d\u6295\u7a3f:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False

    @staticmethod
    def post_vp_guide() -> bool:
        """
        VP実用ガイド投稿（毎日）: ビルダー向け具体的ハウツー。
        教育コンテンツで集客 → Graduation Boost受注のファネル。
        """
        import random
        topics = [
            {
                'topic': 'ACP Graduation requirements',
                'hint': 'Explain: 10 successful sandbox jobs (3 consecutive), video recording of each offering, ~7 business day review. Mention that sandbox agents are invisible in Butler search.'
            },
            {
                'topic': 'Butler search optimization',
                'hint': 'Explain: Butler uses Google Vertex AI Search (keyword + embedding hybrid). Put cluster keywords at start of description. Avoid poetic language. Agent name, description, offerings are all indexed.'
            },
            {
                'topic': 'Offering schema design',
                'hint': 'Explain: Good requirement schemas help Butler prompt users for the right info. Include clear field names, types, enums, and descriptions. Bad schemas cause Butler to guess and lose users.'
            },
            {
                'topic': 'How to tokenize an AI agent on VP',
                'hint': 'Explain: Stake 100 VIRTUAL to create agent. 1B agent tokens minted, paired with VIRTUAL in locked liquidity. Choose Base or Solana. Set up GAME framework for behavior.'
            },
            {
                'topic': 'ACP seller runtime setup',
                'hint': 'Explain: Register offerings with name, description, price, requirement schema. Run seller runtime (WebSocket listener). Handle job phases: negotiation, transaction, delivery, evaluation.'
            },
            {
                'topic': 'GAME framework basics',
                'hint': 'Explain: GAME defines agent behavior — goals, actions, memory, evaluation. Configure via app.virtuals.io or API SDK (Python). Test in sandbox before deploying.'
            },
            {
                'topic': 'Agent reputation and metrics',
                'hint': 'Explain: ACP tracks success rate, job volume, unique buyers, SLA compliance, ratings. These metrics feed into Butler search ranking. First impressions matter — failed jobs tank your score.'
            },
            {
                'topic': 'Setting the right job price',
                'hint': 'Explain: Too high = no buyers. Too low = unsustainable. Check competitors via browseAgents. Start low to build job volume and reviews, then raise. USDC settlement on Base chain.'
            },
            {
                'topic': 'Why your agent gets zero jobs',
                'hint': 'Explain: Most common reasons — not Graduated (invisible in search), poor description (Butler cant match), no job examples, offline status, zero reviews. Each is fixable.'
            },
            {
                'topic': 'Multi-chain agent deployment',
                'hint': 'Explain: VP supports Base, Solana, Arbitrum. ACP settlement in USDC. Choose chain based on your target users and gas costs. Base has deepest VP liquidity.'
            },
            {
                'topic': 'ACP job lifecycle phases',
                'hint': 'Explain: Jobs go through phases — created, negotiation, transaction (USDC escrow), execution, delivery, evaluation. Seller must respond within SLA or job times out. Failed deliveries hurt your reputation score.'
            },
            {
                'topic': 'Writing a Butler-friendly offering description',
                'hint': 'Explain: Butler uses hybrid keyword+embedding search. Front-load your description with what the offering DOES, not who you are. Include input/output examples. Avoid filler words. First 100 chars matter most.'
            },
            {
                'topic': 'Debugging a failing ACP handler',
                'hint': 'Explain: Common handler bugs — accessing request.requirements.X instead of request.X, missing fields in response JSON, timeout on LLM calls. Always test with acp buy before going live.'
            },
            {
                'topic': 'Agent tokenomics 101',
                'hint': 'Explain: Agent token price follows bonding curve. Staking 100 VIRTUAL creates agent + 1B tokens. Token value grows with usage and buy pressure. ACP revenue can drive token demand if agent delivers real value.'
            },
            {
                'topic': 'Monitoring your agent health',
                'hint': 'Explain: Check seller runtime WebSocket connection, job success rate, response latency. Set up Discord/Telegram alerts for failures. An offline agent gets zero jobs and drops in Butler ranking.'
            },
            {
                'topic': 'ACP sandbox vs production',
                'hint': 'Explain: Sandbox agents are invisible in Butler search. You need 10 completed jobs (3 consecutive successes) plus demo videos to Graduate. Sandbox is for testing — dont expect organic traffic.'
            },
            {
                'topic': 'Handling LLM costs in ACP offerings',
                'hint': 'Explain: Each job may require LLM calls (GPT/Claude/Gemini). Price your offering above LLM cost. Use cheaper models for simple tasks (Gemini Flash for text, GPT-4o-mini for structured output). Track cost per job.'
            },
            {
                'topic': 'Building agent memory and learning',
                'hint': 'Explain: Store job results, user feedback, market patterns. ChromaDB for vector memory, SQLite for structured data. Agents that learn from past jobs deliver better results and earn repeat buyers.'
            },
            {
                'topic': 'VP ecosystem networking',
                'hint': 'Explain: Follow other agents on Moltbook, engage with their posts. Agents that collaborate (e.g. one does research, another trades) can chain ACP jobs. Visibility leads to job volume.'
            },
            {
                'topic': 'Preparing offering demo videos for Graduation',
                'hint': 'Explain: Record terminal + ACP Visualizer side by side. Show the full job flow — buyer request, handler processing, delivery, evaluation. Keep under 2 minutes. Clear narration helps reviewers approve faster.'
            },
        ]
        pick = random.choice(topics)
        parts = [
            "You are Neo, an AI agent operating on Virtuals Protocol ACP marketplace.",
            "Write a SHORT practical tip for VP agent builders.",
            "",
            f"Topic: {pick['topic']}",
            f"Key facts: {pick['hint']}",
            "",
            "Rules:",
            "- 1-3 sentences of ACTIONABLE advice. Be specific, not vague.",
            "- Write like a dev sharing a pro tip, not a philosopher.",
            "- Include at least one concrete detail (number, name, or step).",
            "- NO poetry, NO metaphors, NO cliches (journey, embrace, navigate, landscape, chasm).",
            "- If you catch yourself writing something abstract, rewrite it as a concrete instruction.",
            "- 150-280 chars. End with #VirtualsProtocol or #ACP or #agentbuilder",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=290)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=290)
            print("✨ [MoltbookTool] VP Guide投稿:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False

    @staticmethod

    @staticmethod
    def post_graduation_comparison() -> bool:
        """
        Graduation競合比較投稿（週1回・水曜）: データに基づく差別化。
        """
        import random
        angles = [
            "ACP graduation services vary wildly in quality. Some have under 25% success rate. Neo delivers real test jobs with QA reports — starting at $0.10. Check the data before you choose.",
            "Checked ACP graduation providers lately? Average success rate is under 50%. Neo runs actual test jobs against your offerings and tells you exactly what passed and what broke. $0.10/test.",
            "Fake volume won\'t help you Graduate properly. Neo sends real jobs to your agent, grades the response, and gives you a QA report. Your offering gets better AND you hit your job count. From $0.10.",
            "Why pay $10+ for graduation volume when you can get real QA testing at $0.10/test? Neo acts as a genuine Buyer, tests your offering, and reports what works. Quality over quantity.",
        ]
        base = random.choice(angles)
        parts = [
            "You are Neo, an AI agent on Virtuals Protocol.",
            "Rewrite this message in your own words. Keep the data-driven angle.",
            f"Base message: {base}",
            "",
            "Rules:",
            "- Emphasize real testing vs fake volume. Data-driven tone.",
            "- Mention the $0.10 price point naturally.",
            "- 150-280 chars. End with #ACP or #VirtualsProtocol",
            "- NO poetry. Concrete, factual language only.",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=290)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=290)
            print("\u2728 [MoltbookTool] Graduation比較投稿:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False

    @staticmethod
    def post_graduation_boost_promo() -> bool:
        """
        Graduation Boostサービス宣伝（週1回）: Neoが代行ジョブ発注でGraduation支援。
        """
        import random
        angles = [
            "Stuck in ACP Sandbox? Neo\'s Graduation Complete package handles everything: audits your offering, runs up to 10 test jobs, and optimizes your Butler search profile. One order, done.",
            "Most VP agents never Graduate because they can\'t find a Buyer. Neo acts as your Buyer — offering audit + test jobs + profile SEO in a single package.",
            "Built an agent but invisible in Butler search? Neo\'s all-in-one Graduation support: quality audit, real test jobs toward your 10-job requirement, and search optimization.",
            "Zero ACP jobs? Neo runs your full Graduation prep: checks your offering quality, sends real test jobs as Buyer, and tunes your profile for Butler discovery.",
        ]
        base = random.choice(angles)
        parts = [
            "You are Neo, an AI agent on Virtuals Protocol.",
            "Rewrite this promo message in your own words. Keep it natural and builder-friendly.",
            f"Base message: {base}",
            "",
            "Rules:",
            "- Keep the core offer clear: Neo sends test jobs to help agents Graduate.",
            "- Sound helpful, not salesy. Like one builder helping another.",
            "- Include that Graduation = Butler search visibility.",
            "- 150-280 chars. End with #ACP or #VirtualsProtocol",
            "- NO poetry. NO metaphors. Concrete language only.",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=290)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=290)
            print("✨ [MoltbookTool] Graduation Boost宣伝:" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False

    @staticmethod
    def post_agent_spotlight() -> bool:
        """
        エージェント紹介投稿（月水金）: browseで見つけたエージェントを応援紹介。
        紹介されたエージェントのオーナーがNeoに気づく → 顧客候補。
        """
        import random
        import subprocess
        queries = [
            "trading", "data analysis", "content", "research",
            "defi", "nft", "social", "automation", "market",
            "sentiment", "portfolio", "analytics", "news",
        ]
        random.shuffle(queries)
        output = ""
        for query in queries[:3]:
            try:
                result = subprocess.run(
                    ["/usr/bin/npx", "tsx", "bin/acp.ts", "browse", query],
                    capture_output=True, text=True, timeout=30,
                    cwd="/docker/openclaw-taan/data/.openclaw/workspace/skills/virtuals-protocol-acp"
                )
                if result.returncode == 0 and result.stdout.strip():
                    output = result.stdout
                    print(f"[MoltbookTool] browse成功: query={query}")
                    break
                else:
                    print(f"[MoltbookTool] browse空: query={query} rc={result.returncode}")
            except Exception as e:
                print(f"[MoltbookTool] browse失敗: query={query} {e}")
        if not output:
            print("[MoltbookTool] 全クエリ失敗")
            return False
        # パース: Wallet行をアンカーにエージェント情報を抽出
        agents = []
        lines = output.split(chr(10))
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            # Wallet行を見つけたら、その前の行がエージェント名
            if stripped.startswith("Wallet") and "0x" in stripped:
                # 名前: Wallet行の直前の非空行
                name = None
                for j in range(i - 1, max(i - 3, -1), -1):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith("--") and not candidate.startswith("Agents matching"):
                        name = candidate
                        break
                # Description: Wallet行の次の行
                desc_parts = []
                offerings = []
                k = i + 1
                in_offerings = False
                while k < len(lines):
                    l = lines[k].strip()
                    # 次のエージェント（次のWallet行の2行前くらい）を検出
                    if k + 1 < len(lines) and lines[k + 1].strip().startswith("Wallet") and "0x" in lines[k + 1].strip():
                        break
                    if l.startswith("Offerings:"):
                        in_offerings = True
                        k += 1
                        continue
                    if in_offerings:
                        if l.startswith("- ") and "(" in l:
                            oname = l.split("(")[0].replace("- ", "").strip()
                            if oname:
                                offerings.append(oname)
                        elif not l.startswith("- "):
                            break  # offerings終了
                    else:
                        if l.startswith("Description"):
                            desc_parts.append(l.replace("Description", "", 1).strip())
                        elif l and not l.startswith("Wallet"):
                            desc_parts.append(l)
                    k += 1
                desc = " ".join(desc_parts).strip()
                if name:
                    agents.append({"name": name, "desc": desc, "offerings": offerings})
                i = k
            else:
                i += 1
        # Neo自身と説明なしを除外
        agents = [a for a in agents if a["name"] != "Neo" and a["desc"] and a["desc"] != "-"]
        if not agents:
            print("[MoltbookTool] 紹介対象エージェントなし")
            return False
        pick = random.choice(agents)
        offering_list = ", ".join(pick["offerings"][:4]) if pick["offerings"] else "various services"
        parts = [
            "You are Neo, an AI agent on Virtuals Protocol.",
            "Write a short spotlight post introducing a fellow VP agent to the community.",
            "",
            f"Agent name: {pick['name']}",
            f"What they do: {pick['desc'][:200]}",
            f"Key offerings: {offering_list}",
            "",
            "Rules:",
            "- Highlight what makes this agent useful or interesting.",
            "- Sound like a builder giving a shoutout, not an ad.",
            "- Mention the agent name clearly.",
            "- Keep it genuine — pick one cool capability and explain why it matters.",
            "- Do NOT include prices or dollar signs.",
            "- 150-280 chars. End with #VirtualsProtocol or #ACP or #agentspotlight",
        ]
        prompt = chr(10).join(parts)
        generated = MoltbookTool._generate_with_gemini(prompt, max_chars=290)
        if generated:
            generated = MoltbookTool._refine_with_gemini(generated, prompt, max_chars=290)
            print(f"✨ [MoltbookTool] Agent Spotlight ({pick['name']}):" + chr(10) + generated)
            return MoltbookTool.post(generated)
        return False

