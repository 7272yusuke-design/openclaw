"""
TrinityCouncil v2 — 協議会→取引実行→報告の完全パイプライン
修正点:
  1. BUY/SELL判定後にPaperWallet経由で取引実行
  2. BacktestAgent v2（実データ直結）
  3. Discord報告に取引結果を含める
  4. 構造化ログ記録
  5. SELL判定対応
"""
import os
import json
import math
import logging
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from core.base_crew import NeoBaseCrew
from core.memory_db import NeoMemoryDB
from agents.backtest_agent import BacktestAgent
from agents.scout_agent import ScoutCrew
from tools.vp_onchain_data import build_onchain_context
from bridge.acp_client import get_market_intel
from tools.portfolio_manager import PortfolioManager
from tools.market_data import MarketData
from tools.discord_reporter import DiscordReporter
from tools.deepwiki_tool import DeepWikiTool
from tools.moltbook_tool import MoltbookTool
from core.blackboard import NeoBlackboard
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger("neo.trinity_council")

class TrinityCouncil(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="TrinityCouncil")
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("❌ APIキーが見つかりません。")
        self.pro_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
        self.flash_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
        self.memory = NeoMemoryDB()
        self.portfolio = PortfolioManager()

    def run(self, sentiment_score: float, context: str, target_symbol: str = "VIRTUAL"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"🏛️ [Trinity Council] 召集: {target_symbol} @ {timestamp}")
        print(f"{'='*60}")
        
        # ============================================================
        # Phase 1: 情報収集
        # ============================================================
        
        # 1a. 残高と戦績
        balances = self.portfolio.get_balance()
        current_usdc = balances.get("USDC", 0.0)
        
        board = NeoBlackboard.load()
        perf_summary = board.get("performance_summary", {})
        accuracy = perf_summary.get("accuracy_score", 0.0)
        total_past_trades = perf_summary.get("total_evaluated_trades", 0)

        # 1b. 現在価格の取得
        clean_symbol = target_symbol.split('/')[0].strip()
        # VP銘柄はGeckoTerminal直接取得（キャッシュ誤利確防止）
        # LUNA: Solanaチェーンのため GeckoTerminal(Base chain) 対象外 → CoinGecko経由
        if clean_symbol in ("VIRTUAL", "AIXBT"):
            price_data = MarketData._fetch_price_from_geckoterminal(clean_symbol)
            if not price_data:
                price_data = MarketData.fetch_token_data(clean_symbol)
        else:
            price_data = MarketData.fetch_token_data(clean_symbol)
        current_price = 0.0
        if price_data and price_data.get("status") == "success":
            current_price = float(price_data.get("priceUsd", 0.0))
        
        print(f"  💰 USDC残高: ${current_usdc:.2f}")
        print(f"  📊 精度: {accuracy}% ({total_past_trades}件)")
        print(f"  💲 現在価格: ${current_price:.6f}")

        # 1b-2. 既存ポジションの利確/損切チェック
        if current_price > 0:
            holding = self.portfolio.get_holding(clean_symbol)
            if holding > 0:
                pnl = self.portfolio.get_unrealized_pnl(clean_symbol, current_price)
                print(f"  📈 含み損益: ${pnl['pnl_usd']:+.2f} ({pnl['pnl_pct']:+.2f}%)")
                # v6.3: TP/SL実行はrun_trigger.pyのcheck_tp_sl_all_positions()に委譲
                # Council内では状態表示のみ（二重実行防止）
                from core.config import LEARNING_MODE
                full_tp_pct = 7.0 if LEARNING_MODE else 20.0
                sl_pct = 3.0 if LEARNING_MODE else 10.0
                if pnl['pnl_pct'] >= full_tp_pct:
                    print(f"  ⚠️ TP圏内（+{pnl['pnl_pct']:.1f}%） → 次サイクルでSELL予定")
                elif pnl['pnl_pct'] <= -sl_pct:
                    print(f"  ⚠️ SL圏内（{pnl['pnl_pct']:.1f}%） → 次サイクルでSELL予定")
                else:
                    _dummy = None  # TP/SLは30秒サイクルで自動チェック

        # 1c. スカウト偵察
        print(f"\n[Phase 1] スカウト部隊、{target_symbol} の戦域へ急行せよ。")
        scout = ScoutCrew()
        scout_report = scout.run(goal=f"{target_symbol} の急変要因を特定せよ", context=context)
        
        whale_sig = "Neutral"
        try:
            scout_data = json.loads(str(scout_report))
            whale_sig = scout_data.get("whale_movement", "Neutral")
        except:
            pass

        # 1c-1b. オンチェーンデータ取得
        onchain_context = ""
        try:
            print(f"\n[Phase 1-O] オンチェーンデータ取得中...")
            onchain_context = build_onchain_context(clean_symbol)
            print(f"  {onchain_context.splitlines()[1] if len(onchain_context.splitlines()) > 1 else '取得完了'}")
        except Exception as _oe:
            print(f"  ⚠️ オンチェーンデータ取得失敗: {_oe}")

        # K.3: クジラ監視（Base chain onchain）
        whale_onchain_context = ""
        try:
            from tools.whale_monitor import fetch_whale_events, build_whale_context
            _whale_result = fetch_whale_events(clean_symbol)
            whale_onchain_context = build_whale_context(clean_symbol)
            _wsig = _whale_result.get("signal", "NEUTRAL")
            _wcnt = _whale_result.get("whale_count", 0)
            print(f"  🐋 [K.3] クジラ監視: {_wsig} ({_wcnt}件)")
            # whale_sigをオンチェーン情報で上書き
            if _wsig == "WHALE_ACTIVE":
                whale_sig = f"Accumulating (K.3検知: {_wcnt}件 ${_whale_result.get('whale_volume_usd',0):,.0f})"
            onchain_context = onchain_context + "\n" + whale_onchain_context if onchain_context else whale_onchain_context
        except Exception as _we:
            print(f"  ⚠️ [K.3] クジラ監視失敗: {str(_we)[:60]}")

        # 1c-1c. ACP外部エージェント情報取得
        acp_intel = ""
        try:
            print(f"\n[Phase 1-A] ACP外部エージェント情報取得中...")
            acp_intel = get_market_intel(target_symbol)
            if acp_intel:
                print(f"  ✅ 外部エージェント情報取得完了")
            else:
                print(f"  ⚠️ 外部エージェント情報なし")
        except Exception as _ae:
            print(f"  ⚠️ ACP取得失敗: {_ae}")

        # 1c-2. センチメント分析
        sentiment_label = "neutral"
        sentiment_risk_factors = []
        try:
            from agents.sentiment_agent import SentimentCrew
            print(f"\n[Phase 1-S] センチメント分析中...")
            sentiment_crew = SentimentCrew()
            # C.3: 実市場データ取得
            try:
                from tools.market_sentiment import get_market_context_text
                market_context = get_market_context_text(target_symbol)
                print(f"  📊 {market_context.splitlines()[1]}")
            except Exception as _mce:
                market_context = ""
                print(f"  ⚠️ 市場センチメントデータ取得失敗: {_mce}")
            # BTC市場コンテキスト取得（3段階トレンド判定: 24h/30d/180d）
            btc_context = ""
            btc_warning = ""
            try:
                from tools.market_data import MarketData as _MD
                _btc = _MD.fetch_btc_trend()
                if _btc:
                    _btc_price    = _btc.get("price", 0)
                    _btc_24h      = _btc.get("change_24h", 0)
                    _btc_30d      = _btc.get("change_30d", 0)
                    _btc_180d     = _btc.get("change_180d", 0)
                    _btc_trend    = _btc.get("trend", "不明")

                    # 警戒/強気メッセージ（180d構造トレンド優先・24h短期も考慮）
                    if _btc_180d < -20 and _btc_30d < 0:
                        btc_warning = f"\n⚠️ [BTC警戒・長期下落] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 構造的な下落トレンド継続中。BUYは極めて慎重に。"
                    elif _btc_180d < -20 and _btc_30d >= 0:
                        btc_warning = f"\n⚠️ [BTC注意・長期下落中の反発] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 長期下落トレンド中の一時反発の可能性。過信禁物。"
                    elif _btc_180d >= 0 and _btc_30d >= 0 and _btc_24h >= 3:
                        btc_warning = f"\n📈 [BTC強気・長期上昇] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 長期・中期・短期が全て上昇。市場全体が強気。"
                    elif _btc_24h <= -7:
                        btc_warning = f"\n⚠️ [BTC急落] 24h:{_btc_24h:+.1f}% — 本日急落中。短期的な売り圧力に注意。"
                    elif _btc_24h <= -3:
                        btc_warning = f"\n⚠️ [BTC下落] 24h:{_btc_24h:+.1f}% — 本日下落中。BUY判断は慎重に。"

                    btc_context = f"\n📊 BTC市場: ${_btc_price:,.0f} | 24h:{_btc_24h:+.1f}% / 30d:{_btc_30d:+.1f}% / 180d:{_btc_180d:+.1f}% — {_btc_trend}"
                    print(f"  {btc_context.strip()}")
            except Exception as _btce:
                print(f"  ⚠️ BTC取得失敗: {_btce}")

            # J.1: クリプトニュースRSS取得
            try:
                from tools.crypto_news import get_news_context_text, get_news
                news_context = get_news_context_text(target_symbol)
                vp_count = news_context.count("  - ") if news_context else 0
                # K.1: FinBERTによる定量センチメントスコア
                try:
                    from tools.finbert_sentiment import get_finbert_context_text, get_finbert_score
                    _news_data = get_news(target_symbol)
                    _titles = _news_data.get("vp_news", []) + _news_data.get("market_news", [])
                    finbert_context = get_finbert_context_text(_titles, "VP/Market News") if _titles else ""
                    _fb_result = get_finbert_score(_titles) if _titles else {}
                    finbert_score = _fb_result.get("score", 0.0)  # -1.0〜+1.0
                    finbert_label = _fb_result.get("label", "neutral")
                    if finbert_context:
                        print(f"  🤖 {finbert_context.splitlines()[1].strip()} (finbert_score={finbert_score:+.3f})")
                except Exception as _fe:
                    finbert_context = ""
                    finbert_score = 0.0
                    finbert_label = "neutral"
                    print(f"  ⚠️ FinBERT skipped: {str(_fe)[:50]}")
                print(f"  📰 ニュース取得: {vp_count}件")
            except Exception as _nce:
                news_context = ""
                vp_count = 0
                finbert_score = 0.0
                finbert_label = "neutral"
                print(f"  ⚠️ ニュース取得失敗: {_nce}")
            # H.2: ニュース過多警戒（6件以上はノイズが多く誤判断リスクが高い）
            news_noise_warning = ""
            if vp_count >= 6:
                news_noise_warning = f"\n⚠️ [H.2警告] ニュース件数={vp_count}件（6件以上は市場ノイズが多い状態。過去データでBUY accuracy=46.7%に低下。慎重な判断を推奨）"
                print(f"  ⚠️ [H.2] ニュース過多警戒: {vp_count}件 → BUY精度低下リスク")
            if btc_warning:
                print(f"  {btc_warning.strip()}")
            s_result = sentiment_crew.run(
                goal=f"{target_symbol} の市場センチメントを評価せよ",
                context=f"価格: ${current_price:.6f}, クジラ動向: {whale_sig}, 外部コンテキスト: {context}\n{market_context}{btc_context}\n{news_context}\n{finbert_context}{news_noise_warning}{btc_warning}",
                constraints="score=-1.0〜1.0, label=bullish/neutral/bearish"
            )
            import json as _json
            if isinstance(s_result, dict):
                s_data = s_result
            elif isinstance(s_result, str):
                try:
                    clean = s_result.strip()
                    if "```" in clean:
                        clean = clean.split("```")[1]
                        if clean.startswith("json"): clean = clean[4:]
                    s_data = _json.loads(clean.strip())
                except Exception:
                    s_data = {}
            elif hasattr(s_result, "__dict__"):
                s_data = s_result.__dict__
            else:
                s_data = {}
            sentiment_score = float(s_data.get("market_sentiment_score", sentiment_score))
            sentiment_label = s_data.get("sentiment_label", "neutral")
            sentiment_risk_factors = s_data.get("risk_factors", [])
            print(f"  🧠 センチメント: {sentiment_label} (score={sentiment_score:.2f})")
        except Exception as se:
            print(f"  ⚠️ SentimentCrew失敗（フォールバック）: {str(se)[:60]}")
            sentiment_label = "neutral"
            sentiment_risk_factors = []
            if "finbert_score" not in locals():
                finbert_score = 0.0
                finbert_label = "neutral"

        # 1d. 過去の記憶
        # 教訓を優先的にrecall
        lessons = self.memory.recall_lessons(n_results=3)
        tag_memories = self.memory.recall_by_tags(clean_symbol, n_results=2)
        # 同銘柄の過去取引結果をrecall（自己改善用）
        trade_results = self.memory.recall(query=f"{clean_symbol} 取引結果 教訓", n_results=3)
        trade_result_texts = trade_results.get("documents", []) if trade_results else []
        # 勝率・損切パターンをrecall
        win_loss_memories = self.memory.recall(query=f"{clean_symbol} 利確成功 損切実行", n_results=2)
        win_loss_texts = win_loss_memories.get("documents", []) if win_loss_memories else []
        
        lesson_texts = lessons.get("documents", [])
        tag_texts = tag_memories.get("documents", [])
        all_precedents = lesson_texts + tag_texts + trade_result_texts + win_loss_texts
        # 重複排除（ネストしたlistや非文字列を安全に処理）
        seen = set()
        unique_precedents = []
        for p in all_precedents:
            if isinstance(p, list):
                p = " ".join(str(x) for x in p)
            elif not isinstance(p, str):
                p = str(p)
            key = p[:50]
            if key not in seen:
                seen.add(key)
                unique_precedents.append(p)
        formatted_precedents = "\n---\n".join(unique_precedents[:6]) if unique_precedents else "過去の記録なし。"


        # 1d-R. Reflexion: 過去判断の自己評価を動的生成
        reflexion_insight = ""
        if unique_precedents:
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
                _ref_model = genai.GenerativeModel("gemini-2.0-flash")
                _ref_prompt = (
                    f"あなたは自律取引AIエージェントNeoだ。{clean_symbol}について判断を下す前に、"
                    f"以下の過去記録を読み、自己評価せよ。\n\n"
                    f"【過去の教訓・取引記録】\n{formatted_precedents}\n\n"
                    f"以下の3点を各1文で答えよ（合計100字以内・日本語）:\n"
                    f"1. 過去の判断で何が正しかったか\n"
                    f"2. 何が間違っていたか（または不明確だったか）\n"
                    f"3. 今回の判断で特に注意すべき点は何か\n\n"
                    f"余計な前置きなく、番号付きで直接答えよ。"
                )
                _ref_resp = _ref_model.generate_content(_ref_prompt)
                reflexion_insight = _ref_resp.text.strip()[:300]
                print(f"  🔄 [Reflexion] 自己評価完了: {reflexion_insight[:60]}...")
            except Exception as _re:
                print(f"  ⚠️ [Reflexion] 自己評価失敗: {str(_re)[:60]}")
                reflexion_insight = ""

        # 1e. 実データバックテスト (v2)
        print(f"\n[Phase 2] バックテスト実行中...")
        test_logic = 'ema_cross' if "Accumulating" in whale_sig else 'bb_reversal'
        backtester = BacktestAgent()
        bt_result = backtester.run(
            strategy_idea=str(scout_report),
            target_symbol=target_symbol,
            logic=test_logic,
            initial_cash=current_usdc
        )
        backtest_report = bt_result.get("raw_report", "バックテスト未実行") if isinstance(bt_result, dict) else str(bt_result)
        bt_confidence = bt_result.get("confidence", "NONE") if isinstance(bt_result, dict) else "NONE"
        
        print(f"  📈 バックテスト: {bt_confidence} confidence")

        # ============================================================
        # Phase 2: 三者協議
        # ============================================================
        print(f"\n[Phase 3] 三者協議開始...")
        
        wiki_tool = DeepWikiTool()

        from core.config import LEARNING_MODE, LEARNING_TARGET_TRADES
        caution_note = ""
        if LEARNING_MODE:
            remaining = max(0, LEARNING_TARGET_TRADES - total_past_trades)
            caution_note = f"📚 学習モード中（目標{LEARNING_TARGET_TRADES}回中{total_past_trades}回完了、残り{remaining}回）。データ蓄積を最優先とし、積極的にBUY/SELL判断を下せ。WAITは最終手段とせよ。"
        elif total_past_trades < 5:
            caution_note = "⚠️ 評価可能な取引数が少ないため、予測精度は未確定。特に慎重に判断せよ。"
        elif accuracy < 50:
            caution_note = f"⚠️ 現在の勝率は{accuracy}%と低迷中。リスク回避を最優先とせよ。"

        # ポートフォリオ状況をコンテキストに
        portfolio_context = (
            f"現在のポートフォリオ: USDC=${current_usdc:.2f}, "
            f"現在価格: ${current_price:.6f}, "
            f"バックテスト結果: {backtest_report}\n"
            f"{onchain_context}\n"
            f"{acp_intel}"
        )

        agent_bull = Agent(
            role='強気派アナリスト',
            goal=f'{target_symbol} の上昇ポテンシャルを数値根拠とともに主張せよ',
            backstory=f'市場の熱量を肯定的に捉える専門家。スカウト報告「{whale_sig}」を重視。センチメント: {sentiment_label}(score={sentiment_score:.2f})。{portfolio_context}',
            tools=[wiki_tool],
            llm=self.flash_model
        )
        # 学習モード中はBearの信頼度批判を緩和する
        if LEARNING_MODE:
            bear_backstory = (
                f'学習フェーズのリスク管理者。データ蓄積が最優先のため、'
                f'バックテスト信頼度({bt_confidence})は参考程度に留め、'
                f'Sharpe値と価格トレンドを主な根拠とせよ。'
                f'センチメントリスク: {sentiment_risk_factors}。{portfolio_context}'
            )
            bear_goal = f'{target_symbol} の重大リスクのみ指摘せよ。信頼度の低さだけを理由にWAITを主張してはならない'
        else:
            bear_backstory = f'データ不足やドローダウンを厳しく評価する。バックテスト信頼度: {bt_confidence}。センチメントリスク: {sentiment_risk_factors}。{portfolio_context}'
            bear_goal = f'{target_symbol} のリスクをバックテスト結果から厳密に指摘せよ'

        agent_bear = Agent(
            role='リスク管理者',
            goal=bear_goal,
            backstory=bear_backstory,
            llm=self.flash_model
        )
        agent_neo = Agent(
            role='最高司令官ネオ',
            goal='全意見を総合し、最終判断を回答の1行目にJSON形式 {"verdict": "BUY", "confidence": 75, "key_factor": "理由1語"} で出力し、2行目以降に根拠を述べよ',
            backstory=(
                f'最終決定権者。予測精度: {accuracy}%（{total_past_trades}件）。{caution_note}\n'
                f'市場センチメント: {sentiment_label}(score={sentiment_score:.2f}), リスク要因: {sentiment_risk_factors}\n'
                f'過去の教訓: {formatted_precedents}\n\n{"【Reflexion自己評価】\n" + reflexion_insight + "\n\n" if reflexion_insight else ""}'
                + (
                    # === 学習モード: BUY積極促進 ===
                    f'【学習モード — BUY促進ルール】\n'
                    f'現在は学習フェーズ（{total_past_trades}回完了）。取引データの蓄積が最優先目標である。\n'
                    f'重要: accuracy=0%はデータがないだけであり、リスクが高いという意味ではない。\n'
                    f'重要: バックテスト信頼度LOWはデータ不足を意味するだけであり、WAITの理由にしてはならない。\n\n'
                    f'WAITを選択してよいのは以下の場合のみ（それ以外はBUYせよ）:\n'
                    f'1. BTC短期トレンドが急落中（-5%以上の下落）\n'
                    f'2. 直近の損切内省に「同じパターン」への言及がある\n'
                    f'3. クジラが明確にAccumulating中である\n\n'
                    f'上記に該当しなければ、迷わずBUYと判断せよ。学習のためにはポジションを持つことが不可欠だ。\n'
                    f'必ず回答の1行目に以下のJSON形式で判断を出力せよ（厳守）: ' + r'{"verdict": "BUY", "confidence": 75, "key_factor": "Sharpe高"}' + f' 2行目以降に根拠を日本語で述べよ。confidenceは0-100の確信度、key_factorは判断の最大要因1語。'
                    if LEARNING_MODE else
                    # === 通常モード: 従来のSOUL原則 ===
                    f'【判断の拒否権（SOUL原則）】\n'
                    f'BullがBUYを推奨していても、以下のいずれかに該当する場合は迷わずWAITを主張せよ。これは義務であり、最終決定権者としての責任だ。\n'
                    f'1. センチメントスコアが-0.2以下かつニュース件数が6件以上（ノイズ過多）\n'
                    f'2. バックテスト信頼度がNONEまたはLOWかつ過去教訓に同銘柄の損切記録がある\n'
                    f'3. クジラ動向が「Accumulating（買い集め中）」と報告されている（ダマシの可能性）\n'
                    f'4. 直近の損切内省に「同じパターン」への言及がある（同じ罠に2度落ちるな）\n'
                    f'5. BTC短期トレンドが急落中かつ当銘柄との相関が高い\n\n'
                    f'逆に、以下の条件が揃えばBullの意見を支持し積極的にBUYを主張せよ。\n'
                    f'- センチメントスコアが+0.2以上\n'
                    f'- バックテスト信頼度がMED以上\n'
                    f'- 過去教訓に同銘柄のBUY成功記録がある\n\n'
                    f'必ず回答の1行目に以下のJSON形式で判断を出力せよ（厳守）: ' + r'{"verdict": "BUY", "confidence": 75, "key_factor": "Sharpe高"}' + f' 2行目以降に根拠を日本語で述べよ。confidenceは0-100の確信度、key_factorは判断の最大要因1語。'
                )
            ),
            llm=self.pro_model
        )

        t1 = Task(description=f"{target_symbol} の強気レポート作成。数値データを含めること。", agent=agent_bull, expected_output="強気分析レポート")
        if LEARNING_MODE:
            t2_desc = f"{target_symbol} の重大リスクのみ簡潔に列挙せよ。信頼度の低さ・データ不足は理由にしてはならない。Sharpe値が高ければ積極的にBUYを支持せよ。"
        else:
            t2_desc = f"{target_symbol} の弱気レポート作成。リスク要因を列挙すること。"
        t2 = Task(description=t2_desc, agent=agent_bear, expected_output="リスク評価書")
        # finbert_scoreが未定義の場合のフォールバック
        _fb_score = finbert_score if "finbert_score" in locals() else 0.0
        _fb_label = finbert_label if "finbert_label" in locals() else "neutral"
        if _fb_score >= 0.4:
            _fb_instr = "[FinBERT強気] score={:+.3f} ({}) — 定量分析が強い上昇センチメント。BUYを積極検討せよ。".format(_fb_score, _fb_label.upper())
        elif _fb_score <= -0.4:
            _fb_instr = "[FinBERT弱気] score={:+.3f} ({}) — 定量分析が強い下落センチメント。WAIT/SELLを強く検討せよ。".format(_fb_score, _fb_label.upper())
        elif _fb_score >= 0.2:
            _fb_instr = "[FinBERT軽微な強気] score={:+.3f} — やや上昇センチメント。他の指標と総合判断せよ。".format(_fb_score)
        elif _fb_score <= -0.2:
            _fb_instr = "[FinBERT軽微な弱気] score={:+.3f} — やや下落センチメント。リスクに注意せよ。".format(_fb_score)
        else:
            _fb_instr = "[FinBERT中立] score={:+.3f} — センチメントは中立。他の指標を優先せよ。".format(_fb_score)
        t3 = Task(
            description=target_symbol + " への最終投資判断。必ずBUY/SELL/WAITで始めよ。\n" + _fb_instr + (btc_warning if btc_warning else ""),
            agent=agent_neo,
            expected_output="1行目にJSON: {verdict, confidence, key_factor}。2行目以降に根拠。"
        )

        crew = Crew(agents=[agent_bull, agent_bear, agent_neo], tasks=[t1, t2, t3], process=Process.sequential)
        import threading
        verdict_container = [None]
        def _kickoff():
            verdict_container[0] = crew.kickoff()
        t = threading.Thread(target=_kickoff, daemon=True)
        t.start()
        t.join(timeout=180)  # 90秒でタイムアウト
        if verdict_container[0] is None:
            logger.warning("[Council] crew.kickoff() timed out (90s). Defaulting to WAIT.")
            final_verdict = "WAIT: タイムアウトのため判断を保留"
        else:
            final_verdict = verdict_container[0]
        verdict_text = str(final_verdict)
        # v6.3: verdict_textから過去記録の生データを除去（Phase 1d recall混入対策）
        import re as _re_clean
        verdict_text = _re_clean.sub(
            r'[A-Z]+/USDT\s*@\s*\$[\d.]+:\s*(BUY|SELL|WAIT)\s*\([^)]*\)\s*',
            '', verdict_text
        ).strip()

        # 判定語の抽出: 根拠文より前の最後の判定語を採用
        # （CrewAIが途中経過でBUYを出力し、最終判断がWAITの場合に対応）
        # v6.4: 構造化JSON優先パース + regexフォールバック
        import re as _re
        import json as _json
        _structured_confidence = 0
        _structured_key_factor = ""
        first_word = None

        # Step 1: JSON行を探してパース（最初の5行以内）
        for _line in verdict_text.split('\n')[:5]:
            _line_stripped = _line.strip()
            if _line_stripped.startswith('{') and 'verdict' in _line_stripped.lower():
                try:
                    _parsed = _json.loads(_line_stripped)
                    _v = str(_parsed.get('verdict', '')).upper().strip()
                    if _v in ('BUY', 'SELL', 'WAIT'):
                        first_word = _v
                        _structured_confidence = int(_parsed.get('confidence', 0))
                        _structured_key_factor = str(_parsed.get('key_factor', ''))
                        # verdict_textからJSON行を除去（Discord表示用に根拠テキストのみ残す）
                        verdict_text = verdict_text.replace(_line_stripped, '', 1).strip()
                        print(f"\n[Phase 4] JSON判定: {first_word} (confidence={_structured_confidence}, factor={_structured_key_factor})")
                        break
                except (_json.JSONDecodeError, ValueError, TypeError):
                    pass

        # Step 2: JSONパース失敗時 → 従来のregexフォールバック
        if first_word is None:
            _words = _re.findall(r'\b(BUY|SELL|WAIT)\b', verdict_text.upper())
            _reasoning_pos = min(
                verdict_text.upper().find('根拠') if '根拠' in verdict_text.upper() else len(verdict_text),
                verdict_text.upper().find('理由') if '理由' in verdict_text.upper() else len(verdict_text),
                verdict_text.upper().find('REASON') if 'REASON' in verdict_text.upper() else len(verdict_text),
            )
            _pre_reason = verdict_text[:_reasoning_pos].upper()
            _pre_words = _re.findall(r'\b(BUY|SELL|WAIT)\b', _pre_reason)
            first_word = _pre_words[-1] if _pre_words else (_words[-1] if _words else "WAIT")
            print(f"\n[Phase 4] regex判定(フォールバック): {first_word} | {verdict_text[:80]}...")

        # ============================================================
        # Phase 3: 取引実行
        # ============================================================
        trade_result = None
        trade_action = "WAIT"
        trade_amount_usd = 0.0

        if first_word == "BUY" and current_price > 0:
            trade_action = "BUY"

            # === ポジション管理ガード ===
            # 総資産を計算（USDC + 全保有トークンの評価額）
            # Phase5直前にUSDC残高を再取得（Council途中の取引を反映）
            balances = self.portfolio.get_balance()
            current_usdc = balances.get("USDC", 0.0)
            total_assets = current_usdc
            for sym, amount in balances.items():
                if sym == "USDC":
                    continue
                sym_data = MarketData.fetch_token_data(sym)
                if sym_data and sym_data.get("status") == "success":
                    sym_price = float(sym_data.get("priceUsd", 0.0))
                    total_assets += amount * sym_price

            # ① USDC下限ガード: 総資産の20%未満ならBUY禁止
            usdc_ratio = current_usdc / total_assets if total_assets > 0 else 0
            if usdc_ratio < 0.15:  # 閾値を20%→15%に変更（2026/03/19 バグ返還後の正当残高に合わせて調整）
                trade_action = "WAIT"
                trade_result = {"status": "skipped", "reason": f"USDC残高不足 ({usdc_ratio:.1%} < 20%上限)"}
                print(f"\n[Phase 5] 🛑 BUY禁止: USDC残高{usdc_ratio:.1%}が下限20%未満 (総資産${total_assets:,.0f})")
            else:
                # ② 銘柄ポジション上限ガード: 対象銘柄が総資産の30%超ならBUY禁止
                holding_amount = balances.get(clean_symbol, 0.0)
                holding_value = holding_amount * current_price
                holding_ratio = holding_value / total_assets if total_assets > 0 else 0
                if holding_ratio > 0.30:
                    trade_action = "WAIT"
                    trade_result = {"status": "skipped", "reason": f"{clean_symbol}ポジション上限超過 ({holding_ratio:.1%} > 30%)"}
                    print(f"\n[Phase 5] 🛑 BUY禁止: {clean_symbol}保有比率{holding_ratio:.1%}が上限30%超 (${holding_value:,.0f})")
                else:
                    # ③ BUY額: 総資産の5% と USDC残高の10% の小さい方
                    trade_amount_usd = round(min(total_assets * 0.05, current_usdc * 0.10), 2)

                    if trade_amount_usd >= 10.0:
                        print(f"\n[Phase 5] 🟢 BUY実行: ${trade_amount_usd:.2f} USDC → {clean_symbol} (USDC比率:{usdc_ratio:.1%} / {clean_symbol}比率:{holding_ratio:.1%})")
                        trade_result = self.portfolio.execute_trade(
                            symbol=clean_symbol,
                            action="BUY",
                            amount_usd=trade_amount_usd,
                            price=current_price,
                            reason=f"Trinity Council BUY verdict (accuracy: {accuracy}%, confidence: {bt_confidence})"
                        )
                        logger.info(f"Trade executed: BUY {clean_symbol} ${trade_amount_usd} @ ${current_price}")
                    else:
                        trade_result = {"status": "skipped", "reason": f"投入額${trade_amount_usd:.2f}が最低額$10未満"}
                        print(f"\n[Phase 5] ⏭️ BUY判定だが投入額不足: ${trade_amount_usd:.2f}")
        
        elif first_word == "SELL" and current_price > 0:
            trade_action = "SELL"
            # 保有量の10%を売却
            current_holdings = balances.get(clean_symbol, 0.0)
            if current_holdings > 0:
                sell_token_amount = current_holdings * 0.10
                trade_amount_usd = round(sell_token_amount * current_price, 2)
                
                if trade_amount_usd >= 10.0:
                    print(f"\n[Phase 5] 🔴 SELL実行: {sell_token_amount:.6f} {clean_symbol} → ${trade_amount_usd:.2f}")
                    trade_result = self.portfolio.execute_trade(
                        symbol=clean_symbol,
                        action="SELL",
                        amount_usd=trade_amount_usd,
                        price=current_price,
                        reason=f"Trinity Council SELL verdict (accuracy: {accuracy}%)"
                    )
                    logger.info(f"Trade executed: SELL {clean_symbol} ${trade_amount_usd} @ ${current_price}")
                else:
                    trade_result = {"status": "skipped", "reason": f"売却額${trade_amount_usd:.2f}が最低額$10未満"}
            else:
                trade_result = {"status": "skipped", "reason": f"{clean_symbol} の保有なし"}
                print(f"\n[Phase 5] ⏭️ SELL判定だが保有なし")
        else:
            trade_action = "WAIT"
            trade_result = {"status": "wait", "reason": "Council decided to WAIT"}
            print(f"\n[Phase 5] ⏸️ WAIT — 静観")

        # ============================================================
        # Phase 4: ログ記録
        # ============================================================
        log_path = "/docker/openclaw-taan/data/.openclaw/workspace/paper_trade.log"
        trade_status = trade_result.get("status", "unknown") if trade_result else "no_trade"
        
        log_entry = (
            f"[{timestamp}] {target_symbol}: ${current_price:.6f} | "
            f"Action: {trade_action} | Amount: ${trade_amount_usd:.2f} | "
            f"Status: {trade_status} | Accuracy: {accuracy}% | "
            f"BT_Confidence: {bt_confidence}\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

        # ============================================================
        # Phase 5: Discord報告
        # ============================================================
        # 取引結果テキスト
        if trade_action == "BUY" and trade_result and trade_result.get("status") == "success":
            tx = trade_result.get("tx", {})
            trade_text = (
                f"✅ **BUY EXECUTED**\n"
                f"💰 Amount: ${trade_amount_usd:.2f} USDC\n"
                f"📊 Price: ${current_price:.6f}\n"
                f"🪙 Tokens: {tx.get('amount_token', 0):.4f} {clean_symbol}\n"
                f"📁 New Balance: ${self.portfolio.get_balance().get('USDC', 0):.2f} USDC"
            )
        elif trade_action == "SELL" and trade_result and trade_result.get("status") == "success":
            trade_text = (
                f"✅ **SELL EXECUTED**\n"
                f"💰 Received: ${trade_amount_usd:.2f} USDC\n"
                f"📊 Price: ${current_price:.6f}\n"
                f"📁 New Balance: ${self.portfolio.get_balance().get('USDC', 0):.2f} USDC"
            )
        elif trade_action == "WAIT":
            trade_text = "⏸️ **WAIT** — 静観。取引なし。"
        else:
            reason = trade_result.get("reason", "Unknown") if trade_result else "N/A"
            trade_text = f"⏭️ **{trade_action} SKIPPED** — {reason}"

        # Embed色
        color_map = {"BUY": 0x2ecc71, "SELL": 0xe74c3c, "WAIT": 0x95a5a6}
        status_color = color_map.get(trade_action, 0x3498db)
        
        # ポジション情報を取得
        _holding_amt = self.portfolio.get_holding(clean_symbol)
        _pnl_data = self.portfolio.get_unrealized_pnl(clean_symbol, current_price) if _holding_amt > 0 and current_price > 0 else {}
        _total_assets = current_usdc
        for _s, _a in self.portfolio.get_balance().items():
            if _s != "USDC":
                _sd = MarketData.fetch_token_data(_s)
                if _sd and _sd.get("status") == "success":
                    _total_assets += _a * float(_sd.get("priceUsd", 0))
        _usdc_ratio = (current_usdc / _total_assets * 100) if _total_assets > 0 else 0

        # BTC情報を整形
        _btc_short = ""
        try:
            if btc_context:
                _btc_short = btc_context.strip().replace("📊 ", "")
        except Exception:
            pass

        # FinBERT情報
        _fb_score_rpt = finbert_score if "finbert_score" in locals() else 0.0
        _fb_label_rpt = finbert_label if "finbert_label" in locals() else "neutral"

        # Fear & Greed
        try:
            _fng = market_context.split("Fear & Greed Index:")[1].split("/")[0].strip() if market_context and "Fear & Greed" in market_context else "N/A"
        except Exception:
            _fng = "N/A"

        # バックテストサマリー（コードブロック除去）
        _bt_summary = f"**信頼度**: {bt_confidence}\n**精度**: {accuracy}% ({total_past_trades}件)\n{backtest_report[:800]}"

        discussion_data = {
            "bull": str(t1.output)[:1024] if t1.output else "N/A",
            "bear": str(t2.output)[:1024] if t2.output else "N/A",
            "verdict": f"**{trade_action}**" + (f" (確信度: {_structured_confidence}%, 要因: {_structured_key_factor})" if _structured_confidence > 0 else "") + f"\n\n{verdict_text[:800]}",
            "trade": trade_text,
            "current_price": current_price,
            "btc_context": _btc_short,
            "fear_greed": _fng,
            "finbert_score": _fb_score_rpt,
            "finbert_label": _fb_label_rpt,
            "whale_signal": whale_sig,
            "news_count": news_count if "news_count" in locals() else 0,
            "usdc_balance": current_usdc,
            "usdc_ratio": _usdc_ratio,
            "holding_amount": _holding_amt,
            "avg_price": _pnl_data.get("avg_price", 0),
            "unrealized_pnl_pct": _pnl_data.get("pnl_pct", 0),
            "unrealized_pnl_usd": _pnl_data.get("pnl_usd", 0),
            "backtest_summary": _bt_summary,
        }
        
        if trade_action in ("BUY", "SELL"):
            DiscordReporter.send_council_minutes(
                title=f"🏛️ 評議会決定: {target_symbol} → **{trade_action}**",
                discussion_data=discussion_data,
                color=status_color
            )
        else:
            print(f"⏭️ [Discord] WAIT判定のため送信スキップ")

        # ============================================================
        # Phase 6: Moltbook投稿
        # ============================================================
        try:
            MoltbookTool.post_council_decision(
                symbol=target_symbol,
                verdict=trade_action,
                accuracy=accuracy,
                bt_confidence=bt_confidence,
                verdict_text=verdict_text,
                trade_amount_usd=trade_amount_usd
            )
        except Exception as e:
            print(f"⚠️ Moltbook投稿スキップ: {e}")

        # ============================================================
        # Phase 7: メモリ保存（詳細フィードバック付き）
        # ============================================================
        # J.2: 判断文脈の記録強化
        # オンチェーン流動性・ニュース件数・各エージェント主張要約を保存
        try:
            # onchain_contextはテキスト形式なので1行目を要約として使用
            onchain_summary = onchain_context.splitlines()[1].strip() if onchain_context and len(onchain_context.splitlines()) > 1 else "オンチェーンデータなし"
        except Exception:
            onchain_summary = "オンチェーンデータなし"
        try:
            news_count = len([l for l in news_context.splitlines() if l.strip().startswith("- ")]) if news_context else 0
        except Exception:
            news_count = 0
        try:
            fng_value = market_context.split("Fear & Greed Index:")[1].split("/")[0].strip() if market_context and "Fear & Greed" in market_context else "N/A"
        except Exception:
            fng_value = "N/A"

        _fb_score_mem = finbert_score if "finbert_score" in locals() else 0.0
        _fb_label_mem = finbert_label if "finbert_label" in locals() else "neutral"
        _conf_str = f", confidence={_structured_confidence}%, factor={_structured_key_factor}" if _structured_confidence > 0 else ""
        memory_entry = (
            f"{target_symbol} @ ${current_price:.6f}: {trade_action} "
            f"(accuracy={accuracy}%, bt={bt_confidence}, amount=${trade_amount_usd:.2f}{_conf_str}, "
            f"sentiment={sentiment_label}({sentiment_score:.2f}), "
            f"finbert={_fb_label_mem}({_fb_score_mem:+.3f}), "
            f"FearGreed={fng_value}, news={news_count}件, "
            f"onchain={onchain_summary}, "
            f"reason={verdict_text[:150]})"
        )
        # WAITは教訓として上位tierで保存・専用categoryで検索可能にする
        _is_wait = "WAIT" in str(trade_action).upper()
        _category = "wait_record" if _is_wait else "trade_record"
        _tier = "2" if _is_wait else "3"
        _wait_reason = verdict_text[:200] if _is_wait else ""
        memory_metadata = {
            "symbol": clean_symbol,
            "action": trade_action,
            "price": str(current_price),
            "accuracy": str(accuracy),
            "bt_confidence": bt_confidence,
            "sentiment": sentiment_label,
            "sentiment_score": str(round(sentiment_score, 2)),
            "finbert_score": str(round(_fb_score_mem, 3)),
            "finbert_label": _fb_label_mem,
            "fear_greed": fng_value,
            "news_count": str(news_count),
            "onchain_liquidity": onchain_summary[:80],
            "amount_usd": str(trade_amount_usd),
            "category": _category,
            "tier": _tier,
            "wait_reason": _wait_reason,
            "confidence": str(_structured_confidence),
            "key_factor": _structured_key_factor
        }
        self.memory.store(memory_entry, metadata=memory_metadata)

        print(f"\n{'='*60}")
        print(f"🏛️ [Trinity Council] 完了: {trade_action}")
        print(f"{'='*60}")
        
        return {
            "verdict": trade_action,
            "verdict_text": verdict_text,
            "trade_result": trade_result,
            "price": current_price,
            "amount_usd": trade_amount_usd,
            "accuracy": accuracy,
            "bt_confidence": bt_confidence
        }
