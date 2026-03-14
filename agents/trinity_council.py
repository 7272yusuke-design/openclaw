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
        price_data = MarketData.fetch_token_data(clean_symbol)
        current_price = 0.0
        if price_data and price_data.get("status") == "success":
            current_price = float(price_data.get("priceUsd", 0.0))
        
        print(f"  💰 USDC残高: ${current_usdc:.2f}")
        print(f"  📊 精度: {accuracy}% ({total_past_trades}件)")
        print(f"  💲 現在価格: ${current_price:.6f}")
        
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

        # 1c-2. センチメント分析
        sentiment_label = "neutral"
        sentiment_risk_factors = []
        try:
            from agents.sentiment_agent import SentimentCrew
            print(f"\n[Phase 1-S] センチメント分析中...")
            sentiment_crew = SentimentCrew()
            s_result = sentiment_crew.run(
                goal=f"{target_symbol} の市場センチメントを評価せよ",
                context=f"価格: ${current_price:.6f}, クジラ動向: {whale_sig}, 外部コンテキスト: {context}",
                constraints="score=-1.0〜1.0, label=bullish/neutral/bearish"
            )
            import json as _json
            s_data = _json.loads(str(s_result)) if isinstance(s_result, str) else (s_result.__dict__ if hasattr(s_result, "__dict__") else {})
            sentiment_score = float(s_data.get("market_sentiment_score", sentiment_score))
            sentiment_label = s_data.get("sentiment_label", "neutral")
            sentiment_risk_factors = s_data.get("risk_factors", [])
            print(f"  🧠 センチメント: {sentiment_label} (score={sentiment_score:.2f})")
        except Exception as se:
            print(f"  ⚠️ SentimentCrew失敗（フォールバック）: {str(se)[:60]}")
            sentiment_label = "neutral"
            sentiment_risk_factors = []

        # 1d. 過去の記憶
        # 教訓を優先的にrecall
        lessons = self.memory.recall_lessons(n_results=3)
        tag_memories = self.memory.recall_by_tags(clean_symbol, n_results=2)
        
        lesson_texts = lessons.get("documents", [])
        tag_texts = tag_memories.get("documents", [])
        all_precedents = lesson_texts + tag_texts
        # 重複排除
        seen = set()
        unique_precedents = []
        for p in all_precedents:
            key = p[:50]
            if key not in seen:
                seen.add(key)
                unique_precedents.append(p)
        formatted_precedents = "\n---\n".join(unique_precedents[:5]) if unique_precedents else "過去の記録なし。"

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

        caution_note = ""
        if total_past_trades < 5:
            caution_note = "⚠️ 評価可能な取引数が少ないため、予測精度は未確定。特に慎重に判断せよ。"
        elif accuracy < 50:
            caution_note = f"⚠️ 現在の勝率は{accuracy}%と低迷中。リスク回避を最優先とせよ。"

        # ポートフォリオ状況をコンテキストに
        portfolio_context = (
            f"現在のポートフォリオ: USDC=${current_usdc:.2f}, "
            f"現在価格: ${current_price:.6f}, "
            f"バックテスト結果: {backtest_report}"
        )

        agent_bull = Agent(
            role='強気派アナリスト',
            goal=f'{target_symbol} の上昇ポテンシャルを数値根拠とともに主張せよ',
            backstory=f'市場の熱量を肯定的に捉える専門家。スカウト報告「{whale_sig}」を重視。センチメント: {sentiment_label}(score={sentiment_score:.2f})。{portfolio_context}',
            tools=[wiki_tool],
            llm=self.flash_model
        )
        agent_bear = Agent(
            role='リスク管理者',
            goal=f'{target_symbol} のリスクをバックテスト結果から厳密に指摘せよ',
            backstory=f'データ不足やドローダウンを厳しく評価する。バックテスト信頼度: {bt_confidence}。センチメントリスク: {sentiment_risk_factors}。{portfolio_context}',
            llm=self.flash_model
        )
        agent_neo = Agent(
            role='最高司令官ネオ',
            goal='全意見を総合し、明確にBUY/SELL/WAITのいずれか一語で判断を開始せよ',
            backstory=(
                f'最終決定権者。予測精度: {accuracy}%（{total_past_trades}件）。{caution_note}\n市場センチメント: {sentiment_label}(score={sentiment_score:.2f}), リスク要因: {sentiment_risk_factors}\n'
                f'過去の教訓: {formatted_precedents}\n'
                f'必ず回答の最初に「BUY」「SELL」「WAIT」のいずれかを明記し、その後に根拠を日本語で述べよ。'
            ),
            llm=self.pro_model
        )

        t1 = Task(description=f"{target_symbol} の強気レポート作成。数値データを含めること。", agent=agent_bull, expected_output="強気分析レポート")
        t2 = Task(description=f"{target_symbol} の弱気レポート作成。リスク要因を列挙すること。", agent=agent_bear, expected_output="リスク評価書")
        t3 = Task(description=f"{target_symbol} への最終投資判断。必ずBUY/SELL/WAITで始めよ。", agent=agent_neo, expected_output="最終判断と根拠")

        crew = Crew(agents=[agent_bull, agent_bear, agent_neo], tasks=[t1, t2, t3], process=Process.sequential)
        import threading
        verdict_container = [None]
        def _kickoff():
            verdict_container[0] = crew.kickoff()
        t = threading.Thread(target=_kickoff, daemon=True)
        t.start()
        t.join(timeout=90)  # 90秒でタイムアウト
        if verdict_container[0] is None:
            logger.warning("[Council] crew.kickoff() timed out (90s). Defaulting to WAIT.")
            final_verdict = "WAIT: タイムアウトのため判断を保留"
        else:
            final_verdict = verdict_container[0]
        verdict_text = str(final_verdict)
        
        print(f"\n[Phase 4] 判定: {verdict_text[:100]}...")

        # ============================================================
        # Phase 3: 取引実行
        # ============================================================
        trade_result = None
        trade_action = "WAIT"
        trade_amount_usd = 0.0
        
        if "BUY" in verdict_text.upper() and current_price > 0:
            trade_action = "BUY"
            trade_amount_usd = round(current_usdc * 0.10, 2)  # 残高の10%
            
            if trade_amount_usd >= 10.0:
                print(f"\n[Phase 5] 🟢 BUY実行: ${trade_amount_usd:.2f} USDC → {clean_symbol}")
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
        
        elif "SELL" in verdict_text.upper() and current_price > 0:
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
        
        discussion_data = {
            "bull": str(t1.output)[:1024] if t1.output else "N/A",
            "bear": str(t2.output)[:1024] if t2.output else "N/A",
            "stats": (
                f"**🐳 Whale Signal:** `{whale_sig}`\n"
                f"**🎯 Accuracy:** `{accuracy}% ({total_past_trades} trades)`\n"
                f"**📈 Backtest ({bt_confidence}):**\n```\n{backtest_report[:500]}\n```"
            ),
            "verdict": f"**{trade_action}**\n\n{verdict_text[:800]}",
            "trade": trade_text
        }
        
        DiscordReporter.send_council_minutes(
            title=f"🏛️ 評議会決定: {target_symbol} → **{trade_action}**",
            discussion_data=discussion_data,
            color=status_color
        )

        # ============================================================
        # Phase 6: Moltbook投稿
        # ============================================================
        try:
            pnl_text = f"${trade_amount_usd:.0f}" if trade_amount_usd > 0 else ""
            molt_text = (
                f"🏛️ Trinity Council: {target_symbol}\n"
                f"📊 Decision: {trade_action} {pnl_text}\n"
                f"🎯 Accuracy: {accuracy}% | BT: {bt_confidence}\n"
                f"💡 {verdict_text[:80]}"
            )
            MoltbookTool.post(molt_text)
        except Exception as e:
            print(f"⚠️ Moltbook投稿スキップ: {e}")

        # ============================================================
        # Phase 7: メモリ保存
        # ============================================================
        memory_entry = (
            f"{target_symbol} @ ${current_price:.6f}: {trade_action} "
            f"(accuracy={accuracy}%, bt={bt_confidence}, amount=${trade_amount_usd:.2f})"
        )
        self.memory.store(memory_entry)

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
