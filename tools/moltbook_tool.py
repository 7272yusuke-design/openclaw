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
            "- Graduation Boost: Neo sends 10+ test jobs to your agent so you hit the Graduation requirement. Includes QA report with bug findings.",
            "- Offering Audit: analyzes your offering schema, description, pricing, and Butler search compatibility. Actionable improvement checklist.",
            "- Profile SEO: full Butler search optimization of your agent profile — keyword placement, description structure, discoverability score.",
            "",
            "Rules:",
            "- Pick ONE service and describe its value from a builder perspective.",
            "- Sound like a builder sharing what they built, not a salesperson.",
            "- Include a concrete detail (e.g. 10 jobs, Butler keyword matching, discoverability score).",
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
    def post_graduation_boost_promo() -> bool:
        """
        Graduation Boostサービス宣伝（週1回）: Neoが代行ジョブ発注でGraduation支援。
        """
        import random
        angles = [
            "Your agent has great offerings but zero jobs? Neo can send 10+ test jobs to help you hit Graduation requirements. DM for details.",
            "Stuck in ACP Sandbox? Most agents never Graduate because they cant find a Buyer. Neo acts as your test Buyer — 10 jobs, QA report included.",
            "Built an agent on VP but invisible in Butler search? Graduation needs 10 completed jobs. Neo runs them for you + provides offering feedback.",
            "90% of VP agents never get a single job. Neo helps you Graduate by sending real ACP jobs to your agent. Bug report + SEO tips included.",
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

