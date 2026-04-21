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
from datetime import datetime, timezone
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
from core.model_factory import ModelFactory

logger = logging.getLogger("neo.trinity_council")

class TrinityCouncil(NeoBaseCrew):
    def __init__(self):
        super().__init__(name="TrinityCouncil")
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("❌ APIキーが見つかりません。")
        # v6.5bd: CrewAI LLM with Gemini→OpenRouter fallback on 429
        self.pro_model = ModelFactory.get_crewai_llm("critical")
        self.flash_model = ModelFactory.get_crewai_llm("standard")
        self.memory = NeoMemoryDB()
        self.portfolio = PortfolioManager()

    def run(self, sentiment_score: float, context: str, target_symbol: str = "VIRTUAL", analysis_only: bool = False):
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
        # Tier0（BTC/ETH）: ローカルDB優先（Binance蓄積・API節約）
        # VP銘柄: GeckoTerminal優先
        current_price = 0.0
        if clean_symbol in ("BTC", "ETH"):
            from orchestration.data_collector import get_latest_price_from_db
            _db_price = get_latest_price_from_db(clean_symbol)
            if _db_price and _db_price > 0:
                current_price = _db_price
            else:
                price_data = MarketData.fetch_token_data(clean_symbol)
                if price_data and price_data.get("status") == "success":
                    current_price = float(price_data.get("priceUsd", 0.0))
        elif clean_symbol in ("VIRTUAL", "AIXBT"):
            price_data = MarketData._fetch_price_from_geckoterminal(clean_symbol)
            if not price_data:
                price_data = MarketData.fetch_token_data(clean_symbol)
            if price_data and price_data.get("status") == "success":
                current_price = float(price_data.get("priceUsd", 0.0))
        else:
            price_data = MarketData.fetch_token_data(clean_symbol)
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
                # v6.5ay: ハードコードTP/SL削除 → EXIT_PROFILES参照に統一
                from core.config import EXIT_PROFILES, STRATEGY_TO_EXIT_PROFILE, EXIT_PROFILE_DEFAULT
                _h = self.portfolio.wallet.state.get("holdings", {}).get(clean_symbol, {})
                _tag = _h.get("strategy_tag", "") if isinstance(_h, dict) else ""
                _ep_name = STRATEGY_TO_EXIT_PROFILE.get(_tag, EXIT_PROFILE_DEFAULT)
                _ep = EXIT_PROFILES.get(_ep_name, {})
                full_tp_pct = _ep.get("hard_tp_pct", 14.0)
                sl_pct = _ep.get("sl_pct", 3.0)
                if pnl['pnl_pct'] >= full_tp_pct:
                    print(f"  ⚠️ TP圏内（+{pnl['pnl_pct']:.1f}% / {_ep_name}: TP+{full_tp_pct}%） → 次サイクルでSELL予定")
                elif pnl['pnl_pct'] <= -sl_pct:
                    print(f"  ⚠️ SL圏内（{pnl['pnl_pct']:.1f}% / {_ep_name}: SL-{sl_pct}%） → 次サイクルでSELL予定")
                else:
                    pass  # TP/SLは30秒サイクルで自動チェック

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
        sentiment_risk_factors = "特になし"
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

                    # BTC市場フェーズ判定（v6.5ak: 事実提示のみ・判断指示なし）
                    if _btc_180d < -20 and _btc_30d < -5:
                        btc_warning = f"\n📊 [BTC下落継続] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 戦略調整: SL引き締め・短期シナリオ推奨。長期底値圏での仕込み水準。"
                    elif _btc_180d < -20 and _btc_30d < 0 and _btc_24h < -3:
                        btc_warning = f"\n📊 [BTC短期急落] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 戦略調整: 最小サイズ・タイトSL。急落後リバウンドシナリオ検討。"
                    elif _btc_180d < -20 and _btc_30d < 0:
                        btc_warning = f"\n📊 [BTC底値圏] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 戦略調整: SL引き締め・控えめTP。割安仕込み水準。"
                    elif _btc_180d < -20 and _btc_30d >= 0:
                        btc_warning = f"\n📊 [BTC底打ち兆候] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 戦略調整: 転換初期のため段階的エントリー推奨。"
                    elif _btc_180d >= 0 and _btc_30d >= 0 and _btc_24h >= 3:
                        btc_warning = f"\n📈 [BTC強気] 180d:{_btc_180d:+.1f}% / 30d:{_btc_30d:+.1f}% / 24h:{_btc_24h:+.1f}% — 戦略調整: トレーリングTP活用・上昇トレンド継続前提。"
                    elif _btc_24h <= -7:
                        btc_warning = f"\n📊 [BTC急落] 24h:{_btc_24h:+.1f}% — 戦略調整: 最小サイズ・タイトSL・短期リバウンドシナリオ。"
                    elif _btc_24h <= -3:
                        btc_warning = f"\n📊 [BTC下落] 24h:{_btc_24h:+.1f}% — 戦略調整: SL引き締め・押し目エントリーシナリオ。"

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
            # H.2: ニュース過多警戒（v6.5ai: 閾値10件に引き上げ。6件は常態で常時発火していた）
            news_noise_warning = ""
            if vp_count >= 10:
                news_noise_warning = f"\n⚠️ [H.2警告] ニュース件数={vp_count}件（10件以上は市場ノイズが非常に多い状態。シグナルの信頼性を慎重に評価せよ）"
                print(f"  ⚠️ [H.2] ニュース過多警戒: {vp_count}件 → ノイズ注意")
            elif vp_count >= 7:
                news_noise_warning = f"\n📰 [H.2] ニュース件数={vp_count}件（やや多い。個別ニュースの重要度を精査すること）"
                print(f"  📰 [H.2] ニュース件数: {vp_count}件（通常範囲）")
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
            _raw_risk_factors = s_data.get("risk_factors", [])
            sentiment_risk_factors = " / ".join(_raw_risk_factors) if _raw_risk_factors else "特になし"
            print(f"  🧠 センチメント: {sentiment_label} (score={sentiment_score:.2f})")
        except Exception as se:
            print(f"  ⚠️ SentimentCrew失敗（フォールバック）: {str(se)[:60]}")
            sentiment_label = "neutral"
            sentiment_risk_factors = "特になし"
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

        # E2.2: failure_category集計（Reflexion入力用）
        _failure_summary = "失敗パターンデータなし"
        _failure_counts = {}
        try:
            _fc_results = self.memory.recall(
                query=f"{clean_symbol} trade_result failure",
                n_results=50,
                where={"category": "trade_result"}
            )
            _fc_metas = _fc_results.get("metadatas", [[]])[0]
            for _fm in _fc_metas:
                _fc = _fm.get("failure_category", "")
                if _fc and _fc != "unknown":
                    _failure_counts[_fc] = _failure_counts.get(_fc, 0) + 1
            if _failure_counts:
                _failure_summary = "\n".join(
                    f"- {cat}: {cnt}回"
                    for cat, cnt in sorted(_failure_counts.items(), key=lambda x: -x[1])
                )
                print(f"  📊 [E2] failure分布: {_failure_counts}")
        except Exception as _fce:
            print(f"  ⚠️ [E2] failure集計失敗: {_fce}")

        # E2.4: 前回のReflexion指示を取得（閉ループ検証用）
        _last_reflexion_instruction = ""
        try:
            _lr = self.memory.recall(
                query=f"{clean_symbol} reflexion instruction_for_next",
                n_results=1,
                where={"category": "reflexion_result"}
            )
            _lr_docs = _lr.get("documents", [[]])[0]
            if _lr_docs:
                _last_reflexion_instruction = _lr_docs[0][:200] if isinstance(_lr_docs[0], str) else str(_lr_docs[0])[:200]
                print(f"  📝 [E2] 前回Reflexion指示: {_last_reflexion_instruction[:60]}...")
        except Exception:
            pass

        # 1d-R. Reflexion: 過去判断の自己評価を動的生成（E2.1高度化）
        reflexion_insight = ""
        _reflexion_adj = 0
        if unique_precedents:
            try:
                _ref_model = ModelFactory.get_genai_model("fast")
                _compliance_note = ""
                if _last_reflexion_instruction:
                    _compliance_note = f"\n\n【前回のReflexion指示】\n{_last_reflexion_instruction}\n→ この指示に今回従えているか評価せよ。"
                _ref_prompt = (
                    f"あなたはNeoの思考パターン分析官だ。市場リスクの列挙は不要。\n"
                    f"Neoの過去の**判断プロセスの癖・偏り**を特定し、今回それが再発しうるか診断せよ。\n\n"
                    f"【分析手順】\n"
                    f"Step 1: 過去の取引記録から「事実の間違い」ではなく「思考パターンの間違い」を抽出せよ\n"
                    f"  例: 過信傾向、トレンド無視、BTC相関軽視、ナンピン固執、時間帯無視\n"
                    f"Step 2: 今回の状況({clean_symbol} sent={sentiment_score:.2f})に同じパターンが当てはまるか検査\n"
                    f"Step 3: 当てはまる場合は確率を下げ、過去に学びが活かせている場合は上げよ\n\n"
                    f"【今回の判断対象】\n{clean_symbol} @ ${current_price:.6f} | sent={sentiment_label}({sentiment_score:.2f})\n\n"
                    f"【過去の取引記録・教訓】\n{formatted_precedents}\n\n"
                    f"【失敗カテゴリ分布（E1）】\n{_failure_summary}"
                    f"{_compliance_note}\n\n"
                    f"以下のJSON形式のみで回答（余計なテキスト厳禁）:\n"
                    f'{{\"thinking_biases\": [\"Neoが繰り返している思考の癖（最大3つ・各25字以内・市場状況ではなくNeoの判断傾向を書け）\"],'
                    f'\"current_pattern_match\": \"今回の状況が過去の思考バイアスに該当するか（true/false+根拠20字）\",'
                    f'\"confidence_adjustment\": -10から+10の整数（バイアス該当なら下げ、学習改善あれば上げ）,'
                    f'\"adjustment_reason\": \"修正値の根拠（30字以内・Neoの思考傾向に言及）\",'
                    f'\"instruction_for_next\": \"次回Councilで意識すべき思考の罠（50字以内・市場予測ではなく判断プロセスの注意点）\",'
                    f'\"strategy_constraint_violated\": \"戦略制約違反があればその内容（なければnull）\",'
                    f'\"evidence_reliability_score\": 1から5の整数,'
                    f'\"evidence_weakness\": \"根拠の最大弱点（25字以内）\",'
                    f'\"previous_instruction_followed\": true/false/null}}'
                )
                _ref_resp = _ref_model.generate_content(_ref_prompt)
                _ref_raw = _ref_resp.text.strip()
                # JSON抽出を試行
                import json as _json_ref
                _ref_clean = _ref_raw
                if "```" in _ref_clean:
                    _ref_clean = _ref_clean.split("```")[1].replace("json", "", 1).strip()
                if "{" in _ref_clean:
                    _ref_clean = _ref_clean[_ref_clean.index("{"):_ref_clean.rindex("}")+1]
                _ref_parsed = _json_ref.loads(_ref_clean)
                _reflexion_adj = int(_ref_parsed.get("confidence_adjustment", 0))
                _reflexion_adj = max(-10, min(10, _reflexion_adj))
                _ref_biases = _ref_parsed.get("thinking_biases", _ref_parsed.get("active_risks", []))
                _ref_pattern = _ref_parsed.get("current_pattern_match", "")
                _ref_reason = _ref_parsed.get("adjustment_reason", "")
                _ref_next = _ref_parsed.get("instruction_for_next", "")
                _ref_followed = _ref_parsed.get("previous_instruction_followed", None)
                _ref_strat_violated = _ref_parsed.get("strategy_constraint_violated")
                _ref_ev_score = _ref_parsed.get("evidence_reliability_score", 3)
                _ref_ev_weakness = _ref_parsed.get("evidence_weakness", "")
                reflexion_insight = (
                    f"思考バイアス: {', '.join(_ref_biases[:3])}\n"
                    f"今回該当: {_ref_pattern}\n"
                    f"confidence調整: {_reflexion_adj:+d} ({_ref_reason})\n"
                    f"次回注意: {_ref_next}"
                    f"戦略制約違反: {_ref_strat_violated or 'なし'}\n"
                    f"根拠信頼性: {_ref_ev_score}/5 ({_ref_ev_weakness})\n"
                )
                # E2.4: Reflexion結果をChromaDBに保存（閉ループ用）
                try:
                    self.memory.store(
                        f"{clean_symbol} Reflexion: adj={_reflexion_adj:+d}, biases={_ref_biases}, pattern={_ref_pattern}, next={_ref_next}",
                        metadata={
                            "category": "reflexion_result",
                            "symbol": clean_symbol,
                            "confidence_adjustment": str(_reflexion_adj),
                            "instruction_for_next": _ref_next[:200],
                            "previous_followed": str(_ref_followed),
                            "tier": "4",
                        }
                    )
                except Exception:
                    pass
                print(f"  🔄 [E2 Reflexion] adj={_reflexion_adj:+d}, biases={_ref_biases}, pattern={_ref_pattern}, followed={_ref_followed}")
            except (_json_ref.JSONDecodeError if '_json_ref' in dir() else ValueError):
                # JSONパース失敗 → フォールバック（従来の自由文Reflexion）
                reflexion_insight = _ref_raw[:300] if '_ref_raw' in dir() else ""
                _reflexion_adj = 0
                print(f"  ⚠️ [E2 Reflexion] JSONパース失敗、フォールバック: {reflexion_insight[:60]}")
            except Exception as _re:
                print(f"  ⚠️ [E2 Reflexion] 失敗: {str(_re)[:60]}")
                reflexion_insight = ""
                _reflexion_adj = 0

        # 1-P. N.1 removed (v6.5as)
        pair_trade_context = ""
        _pt_z = 0
        _pt_z_label = "z0"

        # 1e. PlanningCrew 戦略リスク評価
        _planning_result = {}
        _capital_flow_phase = "RISK_ON_RIDE"
        try:
            from agents.planning_agent import run_strategic_assessment
            print(f"\n[Phase 1e] 戦略リスク評価中...")
            _planning_result = run_strategic_assessment(
                symbol=clean_symbol,
                current_price=current_price,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                bt_confidence=bt_confidence if 'bt_confidence' in dir() else "NONE",
                formatted_precedents=formatted_precedents,
                failure_summary=_failure_summary,
                btc_context=btc_context,
            )
            _capital_flow_phase = _planning_result.get("capital_flow_phase", "RISK_ON_RIDE")
        except Exception as _pe:
            print(f"  ⚠️ [Phase 1e] PlanningCrew失敗: {str(_pe)[:60]}")

        # Planning結果を三者協議用テキストに変換
        _planning_context = ""
        if _planning_result.get("risk_level"):
            _pr = _planning_result
            _planning_context = (
                f"{_pr.get('risk_level','?')}, "
                f"リスク: {', '.join(_pr.get('risk_factors',[])[:3])}, "
                f"機会: {', '.join(_pr.get('opportunity_factors',[])[:3])}, "
                f"最悪: {_pr.get('worst_case','')}, "
                f"マクロ: {_pr.get('macro_summary','')}, "
                f"資本フロー: {_capital_flow_phase}"
            )

        # 1f. 実データバックテスト (v2)
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
        bt_best_strategy = bt_result.get("best_strategy", "none") if isinstance(bt_result, dict) else "none"
        
        print(f"  📈 バックテスト: {bt_confidence} confidence (best: {bt_best_strategy})")

        # ============================================================
        # Phase 2: 三者協議
        # ============================================================
        print(f"\n[Phase 3] 三者協議開始...")
        
        wiki_tool = DeepWikiTool()

        # v6.5ay: LEARNING_MODE削除、通常モード用の注意文言のみ残す
        caution_note = ""
        if total_past_trades < 5:
            caution_note = "📊 取引データ蓄積中（{total_past_trades}件）。経験を増やすためシナリオを策定しBUYせよ。SL/サイズで調整。".format(total_past_trades=total_past_trades)
        elif accuracy < 50:
            caution_note = f"📊 現在の勝率{accuracy}%。SL引き締め・小さめサイズで戦略精度を改善せよ。WAITでは学べない。"

        # WAIT品質データ（銘柄別）をCouncilに注入
        _wait_quality_note = ""
        try:
            _wait_records = self.memory.recall(query=f"{clean_symbol} wait_record", n_results=30)
            _wait_metas = _wait_records.get("metadatas", [[]])[0] if _wait_records else []
            _wait_prices = [(float(m.get("price", 0)), m.get("symbol", "")) for m in _wait_metas 
                           if m.get("category") == "wait_record" and m.get("symbol") == clean_symbol and float(m.get("price", 0)) > 0]
            if len(_wait_prices) >= 5 and current_price > 0:
                _correct = sum(1 for p, _ in _wait_prices if current_price < p)
                _total = len(_wait_prices)
                _wait_acc = _correct / _total * 100
                if _wait_acc < 30:
                    _wait_quality_note = f"\n⚠️ 【WAIT品質警告】{clean_symbol}の過去WAIT判定は正解率{_wait_acc:.0f}%（{_correct}/{_total}件）。大半がチャンス見逃し。この銘柄では積極的にBUYすべき。"
                elif _wait_acc > 80:
                    _wait_quality_note = f"\n✅ 【WAIT品質良好】{clean_symbol}の過去WAIT判定は正解率{_wait_acc:.0f}%（{_correct}/{_total}件）。WAITの判断は概ね正しい。"
        except Exception as _wq_err:
            pass  # WAIT品質計算失敗は無視

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
        # v6.5ay: LEARNING_MODE削除、通常モード用bear設定のみ残す
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
            goal='BullとBearの主張から楽観シナリオと悲観シナリオの両方を策定せよ。BTC下落・マクロ悪化は買わない理由ではなく、SL引き締め・期間短縮・サイズ縮小で対応する材料である。両シナリオが策定できればBUY（出口はS2/S3モニタリングで動的管理される）。WAITは市場閉鎖級の異常事態のみ。回答の1行目にJSON {"verdict": "BUYかWAIT", "confidence": 戦略の質20-95, "key_factor": "戦略の核テーゼ1語"} で1回のみ出力し、2行目以降に楽観/悲観シナリオと出口条件を述べよ。',
            backstory=(
                f'最終決定権者。予測精度: {accuracy}%（{total_past_trades}件）。{caution_note}{_wait_quality_note}\n'
                f'市場センチメント: {sentiment_label}(score={sentiment_score:.2f}), リスク要因: {sentiment_risk_factors}\n'
                f'過去の教訓: {formatted_precedents}\n\n{"【Reflexion自己評価】\n" + reflexion_insight + "\n\n" if reflexion_insight else ""}{"【戦略リスク評価】risk=" + _planning_context + "\n\n" if _planning_context else ""}'
                # v6.5ay: LEARNING_MODE削除、通常モード（SOUL原則）のみ残す
                + (
                    f'【判断の拒否権（SOUL原則）】\n'
                    f'BullがBUYを推奨していても、以下のいずれかに該当する場合は迷わずWAITを主張せよ。これは義務であり、最終決定権者としての責任だ。\n'
                    f'1. センチメントスコアが-0.2以下かつニュース件数が10件以上（ノイズ過多）\n'
                    f'2. バックテスト信頼度がNONEまたはLOWかつ過去教訓に同銘柄の損切記録がある\n'
                    f'3. クジラ動向が「Accumulating（買い集め中）」と報告されている（ダマシの可能性）\n'
                    f'4. 直近の損切内省に「同じパターン」への言及がある（同じ罠に2度落ちるな）\n'
                    f'5. BTC短期トレンドが急落中かつ当銘柄との相関が高い\n\n'
                    f'逆に、以下の条件が揃えばBullの意見を支持し積極的にBUYを主張せよ。\n'
                    f'- センチメントスコアが+0.2以上\n'
                    f'- バックテスト信頼度がMED以上\n'
                    f'- 過去教訓に同銘柄のBUY成功記録がある\n\n'
                    f'必ず回答の1行目に以下のJSON形式で判断を出力せよ（厳守・1回のみ出力・繰り返すな）:\n'
                    f'{{"verdict": "BUYまたはWAIT", "confidence": 実際の確信度0-100, "key_factor": "実際の判断根拠1語"}}\n'
                    f'2行目以降に根拠を日本語で述べよ。例文の値をコピーせず、実際のデータに基づいた値を入れること。\n'
                    f'【confidenceスケール（厳守）】20-35=非常に弱い（指標の大半が反対方向）, 40-55=弱い/混在（指標が割れている）, 60-70=中程度（過半数の指標が一致）, 75-85=強い（大半の指標が強く一致）, 90+=非常に強い（全指標が一致、稀）。65をデフォルトにするな。実際のデータを見て上記スケールから正直に選べ。key_factorは最も重視した要因1語（例: RSI反転, BTC下落, クジラ買集, Sharpe高, 出来高急増 等）。'
                )
            ),
            llm=self.pro_model
        )

        t1 = Task(description=f"{target_symbol} の強気レポート作成。数値データを含めること。", agent=agent_bull, expected_output="強気分析レポート")
        # v6.5ay: LEARNING_MODE削除、通常モード用Bearタスクのみ残す
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


        # v6.5a-fix: verdict_textから残存JSON行・jsonプレフィックス行を全除去（Discord表示クリーンアップ）
        _clean_lines = []
        for _cl in verdict_text.split('\n'):
            _cls = _cl.strip()
            if _cls.startswith('{') and 'verdict' in _cls.lower():
                continue
            if _cls.lower().startswith('json'):
                continue
            if _cls.startswith('```'):
                continue
            _clean_lines.append(_cl)
        verdict_text = '\n'.join(_clean_lines).strip()

        
        # ============================================================
        # Phase 4b: ルールベースconfidence算出（v6.5h）
        # LLMのconfidenceは参考値のみ。信号データから常に独立算出し上書き
        # ============================================================
        _llm_confidence = _structured_confidence  # LLM出力を保存（ログ用）
        _calc_conf = 50  # ニュートラル起点
        # バックテスト信頼度
        if bt_confidence == "HIGH":
            _calc_conf += 15
        elif bt_confidence in ("MEDIUM", "MED"):
            _calc_conf += 5
        elif bt_confidence == "LOW":
            _calc_conf -= 5
        elif bt_confidence == "NONE":
            _calc_conf -= 10
        # センチメント — v6.5ax無効化（慢性ネガティブで一方的にconf低下、情報価値なし）
        # if sentiment_score > 0.6:
        #     _calc_conf += 10
        # elif sentiment_score > 0.3:
        #     _calc_conf += 5
        # elif sentiment_score < -0.3:
        #     _calc_conf -= 10
        # elif sentiment_score < 0:
        #     _calc_conf -= 5
        # 過去精度
        if accuracy > 70:
            _calc_conf += 10
        elif accuracy > 50:
            _calc_conf += 5
        elif accuracy < 40:
            _calc_conf -= 5
        # BUY判定自体のバイアス（v6.5ag: 相関分析で高conf=低勝率 → バイアス0に）
        # if first_word == "BUY":
        #     _calc_conf += 5  # 旧: +5 → データ: 逆相関のため無効化
        # === v6.5i H.2ベース スコアリングテーブル拡張 ===
        # 時間帯スコア（H.2分析: 欧州82%勝率 vs アジア40%）
        from core.config import TZ_SCORE_ASIA, TZ_SCORE_EU, TZ_SCORE_US
        _utc_hour = datetime.now(timezone.utc).hour
        if 8 <= _utc_hour < 16:   # 欧州時間(17-01 JST)
            _calc_conf += TZ_SCORE_EU
            _tz_label = f"EU{TZ_SCORE_EU:+d}"
        elif 0 <= _utc_hour < 8:  # アジア時間(09-17 JST)
            _calc_conf += TZ_SCORE_ASIA
            _tz_label = f"Asia{TZ_SCORE_ASIA:+d}"
        else:                      # 米国時間
            _calc_conf += TZ_SCORE_US
            _tz_label = f"US{TZ_SCORE_US:+d}"
        # ナンピン数ペナルティ（H.2分析: 20回ナンピン集中問題）
        _npin_count = 0
        _hist = self.portfolio.get_full_state().get("history", [])
        for _h in reversed(_hist):
            if _h.get("symbol") == clean_symbol:
                if _h.get("action") == "BUY":
                    _npin_count += 1
                elif _h.get("action") == "SELL":
                    break
        if _npin_count >= 2:
            _calc_conf -= 5   # v6.5an: -10→-5 戦略書ありなら戦略的ナンピン許容
            _npin_label = f"npin{_npin_count}:-5"
        else:
            _npin_label = f"npin{_npin_count}:0"
        # 直近連敗ペナルティ（H.2分析: 6連敗あり）+ 時間減衰（v6.5q）
        _recent_sells = [h for h in _hist if h.get("action") == "SELL"][-3:]
        _recent_losses = sum(1 for _rs in _recent_sells if "Stop Loss" in _rs.get("reason", ""))
        # 時間減衰: 最後のSLから48h以上経過でペナルティ半減（デッドロック防止）
        _streak_decay = 1.0
        if _recent_losses >= 2 and _recent_sells:
            try:
                _last_sl_time = None
                for _rs in reversed(_recent_sells):
                    if "Stop Loss" in _rs.get("reason", ""):
                        _last_sl_ts = _rs.get("timestamp", "")
                        if _last_sl_ts:
                            from datetime import datetime as _dt
                            _last_sl_time = _dt.fromisoformat(_last_sl_ts.replace("Z", "+00:00")) if isinstance(_last_sl_ts, str) else None
                        break
                if _last_sl_time:
                    _hours_since = (datetime.now(timezone.utc) - _last_sl_time.replace(tzinfo=timezone.utc if _last_sl_time.tzinfo is None else _last_sl_time.tzinfo)).total_seconds() / 3600
                    if _hours_since > 48:
                        _streak_decay = 0.0  # 48h経過: 完全解除（デッドロック防止 v6.5r）
                    elif _hours_since > 24:
                        _streak_decay = 0.5  # 24h経過: 半減
            except Exception:
                pass
        if _recent_losses >= 3:
            _penalty = int(10 * _streak_decay)
            _calc_conf -= _penalty
            _streak_label = f"streak-{_penalty}"
        elif _recent_losses >= 2:
            _penalty = int(5 * _streak_decay)
            _calc_conf -= _penalty
            _streak_label = f"streak-{_penalty}"
        else:
            _streak_label = "streak0"
        # N.1 scoring removed (v6.5as)
        # Capital Flow Radar マクロスコア（v6.5z Task2.3）
        _cfr_label = 'cfr0'
        try:
            import json as _json
            _cfr_path = "vault/blackboard/macro_flow.json"
            import os as _os
            if _os.path.exists(_cfr_path):
                with open(_cfr_path) as _cf:
                    _cfr = _json.load(_cf)
                _cfr_score = _cfr.get("score", 0)
                _cfr_regime = _cfr.get("regime", "Neutral")
                if _cfr_score >= 50:
                    _calc_conf += 5
                    _cfr_label = f"cfr{_cfr_score:+.0f}:+5({_cfr_regime})"
                elif _cfr_score <= -50:
                    _calc_conf -= 10
                    _cfr_label = f"cfr{_cfr_score:+.0f}:-10({_cfr_regime})"
                elif _cfr_score >= 20:
                    _calc_conf += 2
                    _cfr_label = f"cfr{_cfr_score:+.0f}:+2({_cfr_regime})"
                elif _cfr_score <= -20:
                    _calc_conf -= 5
                    _cfr_label = f"cfr{_cfr_score:+.0f}:-5({_cfr_regime})"
                else:
                    _cfr_label = f"cfr{_cfr_score:+.0f}:0({_cfr_regime})"
        except Exception:
            pass
        # === F5: capital_flow_phase スコアリング注入 ===
        _macro_adj_map = {
            "RISK_OFF_ACCUMULATE": 5,
            "RISK_ON_RIDE": 0,
            "RISK_ON_DISTRIBUTE": -2,  # v6.5an: -5→-2 リスクは戦略SL/出口で管理
            "RISK_OFF_EXIT": -3,       # v6.5an: -10→-3 同上（二重減点排除）
        }
        _macro_adj = _macro_adj_map.get(_capital_flow_phase, 0)
        _calc_conf += _macro_adj
        _planning_label = f"macro{_macro_adj:+d}({_capital_flow_phase})"
        if _macro_adj != 0:
            print(f"[Phase 4b] F5マクロ調整: {_macro_adj:+d} (phase={_capital_flow_phase})")
        # === Task 6: 戦略信頼度スコア（strategy_scores.json参照） ===
        _strat_label = "strat0"
        try:
            import json as _json_strat
            _ss_path = "vault/strategy_scores.json"
            if os.path.exists(_ss_path):
                with open(_ss_path) as _sf:
                    _ss_data = _json_strat.load(_sf)
                _ss_entry = _ss_data.get("scores", {}).get(bt_best_strategy, {})
                _ss_tier = _ss_entry.get("tier", "mid")
                if _ss_tier == "high":
                    _calc_conf += 5
                    _strat_label = f"strat+5({bt_best_strategy}:{_ss_entry.get('win_rate',0)}%)"
                elif _ss_tier == "low":
                    _calc_conf -= 5
                    _strat_label = f"strat-5({bt_best_strategy}:{_ss_entry.get('win_rate',0)}%)"
                else:
                    _strat_label = f"strat0({bt_best_strategy}:{_ss_entry.get('win_rate','?')}%)"
        except Exception:
            pass
        # === E3: EvolveR動的ルール適用 ===
        _evolver_total = 0
        _evolver_labels = []
        try:
            import json as _json_evol
            _adj_path = "vault/evolver/scoring_adjustments.json"
            if os.path.exists(_adj_path):
                with open(_adj_path, encoding='utf-8') as _af:
                    _adj_data = _json_evol.load(_af)
                _now_iso = datetime.now(timezone.utc).isoformat()
                for _adj in _adj_data.get("adjustments", []):
                    # 有効期限チェック
                    if _adj.get("expires_at", "") < _now_iso:
                        continue
                    # サンプルサイズチェック
                    if _adj.get("actual_sample_size", 0) < _adj.get("min_sample_size", 3):
                        continue
                    # 条件マッチング
                    _cond = _adj.get("condition", {})
                    _ctype = _cond.get("type", "")
                    _matched = False
                    # v6.5bc整理: 生成停止済みのタイプ(timezone/sentiment_range)の分岐を除去
                    # 理由: Phase 4b の固定値(TZ_SCORE_*) / 直接センチメント反映 と二重計上になるため
                    #       evolver_agent.py 側で生成停止済み（docs/v2_evolver_design.md参照）
                    # 到達可能なタイプ: symbol / bt_confidence / capital_flow_phase
                    if _ctype == "symbol":
                        _matched = (_cond.get("match", "").upper() == clean_symbol.upper())
                    elif _ctype == "bt_confidence":
                        _matched = (_cond.get("match") == bt_confidence)
                    elif _ctype == "capital_flow_phase":
                        _matched = (_cond.get("match") == _capital_flow_phase)
                    if _matched:
                        _val = max(-15, min(15, _adj["adjustment"]))
                        _evolver_total += _val
                        _evolver_labels.append(f"{_adj['rule_id']}:{_val:+d}")
                # 全ルール合計の安全制限 ±30
                if abs(_evolver_total) > 30:
                    _evolver_total = 30 if _evolver_total > 0 else -30
                _calc_conf += _evolver_total
        except Exception as _ee:
            print(f"  ⚠️ [E3] EvolveR動的ルール読み込み失敗: {_ee}")
        _evolver_label = f"evol{_evolver_total:+d}({','.join(_evolver_labels)})" if _evolver_labels else "evol0"
        if _evolver_total != 0:
            print(f"[Phase 4b] E3 EvolveR調整: {_evolver_total:+d} ({_evolver_labels})")
        # === E2.3: Reflexion — Phase 4b 直接反映は意図的に無効 ===
        # 設計意図（v6.5bc 検査で確認）:
        # - ChromaDB に蓄積された416件の confidence_adjustment は 78.4% がマイナス(平均-3.94)
        # - LLM の内省は構造的にマイナス偏重し、直接加算すると「慢性抑制ループ」に陥る
        #   （v6.5ax で発生した過剰BUY抑制問題の根本原因）
        # - Reflexion の知見は【別ルート】で反映されている:
        #     L336-347 で前回Reflexion指示を ChromaDB から読み出し
        #     L555 で次回 Council の LLM プロンプトに注入
        # - これにより LLM が文脈判断して confidence を自律調整（案5: エージェント委任）
        # - スコアリング値として直接加算する形は固定バイアスになるため採用しない
        _reflexion_label = "refl0(via_prompt)"  # LLMプロンプト経由で反映中（数値加算は意図的に無効）
        # === スコアリングテーブル拡張ここまで ===
        _calc_conf = max(20, min(95, _calc_conf))
        print(f"[Phase 4b] ルールベース再計算: {_calc_conf} (LLM={_llm_confidence}, bt={bt_confidence}, sent={sentiment_score:.2f}, acc={accuracy}%, {_tz_label}, {_npin_label}, {_streak_label}, {_cfr_label}, {_reflexion_label}, {_evolver_label}, {_planning_label}, {_strat_label})")
        _structured_confidence = _calc_conf

        # ============================================================
        # Phase 3b: 戦略書生成（Phase S1 — verdict=BUY時のみ）
        # LLMを「戦略家」として活用し、ポジションごとの戦略書を生成
        # ============================================================
        _position_strategy = None
        if first_word == "BUY" and current_price > 0:
            try:
                print(f"\n[Phase 3b] 戦略書生成中...")
                _strategy_model = ModelFactory.get_genai_model("critical")

                # BTC情報取得
                _strat_btc = {}
                try:
                    _strat_btc = MarketData.fetch_btc_trend() or {}
                except Exception:
                    pass

                # マクロ情報取得
                _strat_macro = {}
                try:
                    import json as _json_sm
                    _macro_path = "vault/blackboard/macro_flow.json"
                    if os.path.exists(_macro_path):
                        with open(_macro_path) as _mf:
                            _strat_macro = _json_sm.load(_mf).get("macro_data", {})
                except Exception:
                    pass

                # テクニカル指標（ATR取得後にdf使用して計算）
                _strat_rsi = 0
                _strat_macd = "unknown"

                # Voyagerパターンマッチ
                _voyager_matches = []
                try:
                    _vm = self.memory.recall(query=f"{clean_symbol} voyager_skill pattern", n_results=3, where={"category": "voyager_skill"})
                    _vm_docs = _vm.get("documents", [[]])[0] if _vm else []
                    _voyager_matches = [d[:80] for d in _vm_docs if isinstance(d, str)]
                except Exception:
                    pass

                _macro_line = "マクロデータなし"
                if _strat_macro:
                    _macro_line = f"SPY30d: {_strat_macro.get('spy_30d', 'N/A')}%, DXY30d: {_strat_macro.get('dxy_30d', 'N/A')}%, Gold30d: {_strat_macro.get('gold_30d', 'N/A')}%, US10Y30d: {_strat_macro.get('us10y_30d', 'N/A')}%"

                # ATR計算（ボラティリティベースSL/TP算出用）
                _strat_atr = 0.0
                _strat_atr_pct = 0.0
                try:
                    _atr_df = MarketData.fetch_ohlcv_custom(target_symbol, days=7)
                    if _atr_df is not None and len(_atr_df) >= 15:
                        df = _atr_df
                        _highs = df["high"].astype(float).iloc[-14:]
                        _lows = df["low"].astype(float).iloc[-14:]
                        _closes = df["close"].astype(float).iloc[-15:-1]
                        _tr = []
                        for _i in range(len(_highs)):
                            _tr.append(max(_highs.iloc[_i] - _lows.iloc[_i],
                                          abs(_highs.iloc[_i] - _closes.iloc[_i]),
                                          abs(_lows.iloc[_i] - _closes.iloc[_i])))
                        _strat_atr = sum(_tr) / len(_tr) if _tr else 0
                        _strat_atr_pct = (_strat_atr / current_price * 100) if current_price > 0 else 0
                except Exception:
                    pass
                # テクニカル指標（ATR取得後のdfを使用）
                try:
                    if df is not None and len(df) > 0:
                        if 'rsi_14' in df.columns:
                            _strat_rsi = float(df.iloc[-1]['rsi_14'])
                        else:
                            _close = df['close'].astype(float)
                            _delta = _close.diff()
                            _gain = _delta.where(_delta > 0, 0).rolling(14).mean()
                            _loss = (-_delta.where(_delta < 0, 0)).rolling(14).mean()
                            _rs = _gain.iloc[-1] / _loss.iloc[-1] if _loss.iloc[-1] > 0 else 100
                            _strat_rsi = round(100 - (100 / (1 + _rs)), 1)
                        if 'macd' in df.columns and 'macd_signal' in df.columns:
                            _macd_val = float(df.iloc[-1]['macd'])
                            _macd_sig = float(df.iloc[-1]['macd_signal'])
                            _strat_macd = 'bullish' if _macd_val > _macd_sig else 'bearish'
                except Exception:
                    pass

                # ポートフォリオリスク制約計算
                _strat_total_assets = current_usdc
                try:
                    for _ps, _pa in self.portfolio.get_balance().items():
                        if _ps == "USDC":
                            continue
                        _pd = MarketData.fetch_token_data(_ps)
                        if _pd and _pd.get("status") == "success":
                            _strat_total_assets += float(_pa) * float(_pd.get("priceUsd", 0)) if not isinstance(_pa, dict) else float(_pa.get("amount", 0)) * float(_pd.get("priceUsd", 0))
                except Exception:
                    pass
                _strat_max_loss_usd = _strat_total_assets * 0.03  # 3%ルール

                _strategy_prompt = f"""あなたは自律取引AIエージェントNeoの戦略立案者だ。
BUY判断が下された。このポジションの戦略書を作成せよ。

【判断基準】
「上がるか下がるか」の予測ではなく、「根拠ある楽観シナリオ+利確戦略」と「根拠ある悲観シナリオ+ヘッジ戦略」を設計せよ。
【シナリオ具体性ルール（違反=却下）】
- narrative内に必ず具体的な数値（価格帯・%・時間）を2つ以上含めよ
- 「底値圏で反発」「上昇トレンド継続」等の抽象表現は禁止。代わりに「RSI28の売られすぎ+BTC24h-3%からの反転パターン」のように書け
- bull/bearのevidenceは最低3つ、全て異なるデータソース（テクニカル/センチメント/マクロ/オンチェーン/バックテスト）から1つずつ
- evidenceは「データソース名:具体的数値→解釈」の形式必須（例: "RSI(14):28→売られすぎ反転圏"）
- bull narrativeとbear narrativeは対立する具体的条件で書け（片方が成立すればもう片方は不成立になる関係）

【ハードリスク制約（違反不可）】
- 最大ポジション損失: ${_strat_max_loss_usd:,.0f}（総資産${_strat_total_assets:,.0f}の3%）
- stop_priceは上記損失制約内に収めよ。risk_pctが-6%を超えるSL設定は却下
- ATR(14): ${_strat_atr:.6f} ({_strat_atr_pct:.2f}%) — SL/TPはATRを基準に設計せよ
  - 推奨SL: 1.5〜2.5×ATR = {_strat_atr_pct*1.5:.1f}%〜{_strat_atr_pct*2.5:.1f}%
  - 推奨TP: 2〜4×ATR = {_strat_atr_pct*2:.1f}%〜{_strat_atr_pct*4:.1f}%
- リスク/リワード比: 最低1.5以上（TP%÷SL%≧1.5）
【exit_stagesルール】
- bull_scenario.exit_stages: 段階的利確。trigger_pctはentry価格からの変動%、sell_pctは残ポジションの何%を売るか
  - 例: [{{"trigger_pct": 2.0, "sell_pct": 50, "note": "半利確"}}, {{"trigger_pct": 4.0, "sell_pct": 100, "note": "全利確"}}]
  - 最低2段階、最大4段階。最終stageはsell_pct=100必須
- bear_scenario.exit_stages: 損切り。通常1段階（trigger_pctは負数、sell_pct=100）
【position_size_pctルール（v6.5as: AI推奨ポジションサイズ）】
- 総資産に対する推奨BUY比率（%）を1〜15の数値で指定
- 判断基準: 確信度、ボラティリティ、相場環境、リスクリワード比
- 高確信+低ボラ+良RR: 8〜15%
- 中確信+通常ボラ: 4〜7%
- 低確信+高ボラ: 1〜3%
- ハードキャップ15%は超えられない（安全装置）

【exit_paramsルール（v6.5as: AI動的出口パラメータ）】
- rsi_exit: RSI出口閾値。ボラが高い相場なら80-85、低ボラなら70-75。nullでRSI出口無効
- trailing_start: トレーリング開始%。target_pctの60-80%が目安。nullでデフォルト使用
- trailing_drop: HWMからの下落%で利確。ボラに応じて2-5%。nullでデフォルト使用
- 相場ボラティリティ（ATR%）と戦略timeframeを考慮して設定すること
- invalidation条件とstop_priceは具体的な数値・条件で明記必須（曖昧なら却下）

【銘柄・価格】
{clean_symbol} @ ${current_price:.6f}

【バックテスト結果】
{backtest_report[:800]}

【テクニカル】
RSI(14): {_strat_rsi:.1f} | MACD: {_strat_macd}

【センチメント】
{sentiment_label} (score={sentiment_score:.2f})

【マクロ環境】
資本フローフェーズ: {_capital_flow_phase}
{_macro_line}

【BTC市場】
価格: ${_strat_btc.get('price', 0):,.0f} | 24h: {_strat_btc.get('change_24h', 0):+.1f}% | 30d: {_strat_btc.get('change_30d', 0):+.1f}%

【オンチェーン】
{onchain_context[:300] if onchain_context else "データなし"}

【Voyagerパターン】
{chr(10).join(_voyager_matches) if _voyager_matches else "マッチなし"}

【EvolveRルール適用中】
{', '.join(_evolver_labels) if _evolver_labels else "なし"}

【Reflexion】
{reflexion_insight[:200] if reflexion_insight else "なし"}

【戦略リスク評価】
{_planning_context[:200] if _planning_context else "なし"}

以下のJSON形式のみで回答（余計なテキスト厳禁）:
{{"thesis": "核心テーゼ（50字以内、具体的数値を含む）",
"thesis_timeframe": "short or mid or long",
"position_size_pct": 数値,
"bull_scenario": {{
  "narrative": "楽観シナリオ展開（80字以内）",
  "evidence": ["根拠1（データソース:値）", "根拠2（データソース:値）", "根拠3以上"],
  "target_price": 数値,
  "target_pct": 数値,
  "target_days": 整数,
  "exit_stages": [
    {{"trigger_pct": 数値, "sell_pct": 50, "note": "理由"}},
    {{"trigger_pct": 数値, "sell_pct": 100, "note": "理由"}}
  ],
  "take_profit_plan": "利確戦略の要約（30字以内）"
}},
"bear_scenario": {{
  "narrative": "悲観シナリオ展開（80字以内）",
  "evidence": ["根拠1（データソース:値）", "根拠2（データソース:値）", "根拠3以上"],
  "stop_price": 数値,
  "risk_pct": 数値,
  "exit_stages": [
    {{"trigger_pct": 数値, "sell_pct": 100, "note": "損切り理由"}}
  ],
  "hedge_plan": "ヘッジ戦略の要約（30字以内）"
}},
"exit_params": {{
  "rsi_exit": 数値or null,
  "trailing_start": 数値or null,
  "trailing_drop": 数値or null
}},
"invalidation": {{
  "conditions": ["戦略前提崩壊条件1", "条件2"],
  "action": "無効化時のアクション"
}}}}"""

                _strat_resp = _strategy_model.generate_content(_strategy_prompt)
                _strat_raw = _strat_resp.text.strip()

                # JSONパース
                import json as _json_sp
                _strat_clean = _strat_raw
                if "```" in _strat_clean:
                    _parts = _strat_clean.split("```")
                    if len(_parts) >= 3:
                        _strat_clean = _parts[1].replace("json", "", 1).strip()
                if "{" in _strat_clean:
                    _strat_clean = _strat_clean[_strat_clean.index("{"):_strat_clean.rindex("}") + 1]
                _strat_parsed = _json_sp.loads(_strat_clean)

                # 根拠品質チェック
                _bull_ev = _strat_parsed.get("bull_scenario", {}).get("evidence", [])
                _bear_ev = _strat_parsed.get("bear_scenario", {}).get("evidence", [])
                _has_num = lambda evs: any(any(c.isdigit() for c in str(e)) for e in evs)

                _target_pct = abs(float(_strat_parsed.get("bull_scenario", {}).get("target_pct", 0)))
                _risk_pct = abs(float(_strat_parsed.get("bear_scenario", {}).get("risk_pct", 0)))
                # exit_stagesバリデーション・フォールバック
                _bull_stages = _strat_parsed.get("bull_scenario", {}).get("exit_stages", [])
                _bear_stages = _strat_parsed.get("bear_scenario", {}).get("exit_stages", [])
                # bull_stagesが無いか不正な場合はデフォルト生成
                if not _bull_stages or not isinstance(_bull_stages, list) or len(_bull_stages) < 2:
                    _half_tp = round(_target_pct * 0.5, 1) if _target_pct > 0 else 1.5
                    _bull_stages = [
                        {"trigger_pct": _half_tp, "sell_pct": 50, "note": "auto: half TP"},
                        {"trigger_pct": round(_target_pct, 1) if _target_pct > 0 else 3.0, "sell_pct": 100, "note": "auto: full TP"}
                    ]
                    _strat_parsed.setdefault("bull_scenario", {})["exit_stages"] = _bull_stages
                # bear_stagesが無い場合はデフォルト生成
                if not _bear_stages or not isinstance(_bear_stages, list):
                    _bear_stages = [{"trigger_pct": -round(_risk_pct, 1) if _risk_pct > 0 else -3.0, "sell_pct": 100, "note": "auto: SL"}]
                    _strat_parsed.setdefault("bear_scenario", {})["exit_stages"] = _bear_stages
                _rr_ratio = (_target_pct / _risk_pct) if _risk_pct > 0 else 0
                _risk_ok = _risk_pct <= 6.0  # ハード制約: -6%超は却下
                _rr_ok = _rr_ratio >= 1.5  # ハード制約: RR比1.5未満は却下
                if len(_bull_ev) >= 3 and len(_bear_ev) >= 3 and _has_num(_bull_ev) and _has_num(_bear_ev) and _risk_ok and _rr_ok:
                    # evidence_snapshot自動付加
                    _strat_parsed["evidence_snapshot"] = {
                        "bt_confidence": bt_confidence,
                        "bt_best_strategy": bt_best_strategy,
                        "sentiment": {"score": round(sentiment_score, 3), "label": sentiment_label},
                        "macro": {"capital_flow_phase": _capital_flow_phase},
                        "btc": {"price": _strat_btc.get("price", 0), "change_24h": _strat_btc.get("change_24h", 0), "change_30d": _strat_btc.get("change_30d", 0)},
                        "technicals": {"rsi_14": round(_strat_rsi, 1), "macd_signal": _strat_macd},
                        "voyager_matches": _voyager_matches[:3],
                        "evolver_adjustments": _evolver_labels[:5] if _evolver_labels else [],
                        "reflexion_instruction": reflexion_insight[:200] if reflexion_insight else "",
                    }
                    if _strat_macro:
                        _strat_parsed["evidence_snapshot"]["macro"].update({k: v for k, v in _strat_macro.items() if isinstance(v, (int, float, str))})
                    _position_strategy = _strat_parsed
                    _s_thesis = _strat_parsed.get("thesis", "")[:60]
                    _s_tp = _strat_parsed.get("bull_scenario", {}).get("target_pct", 0)
                    _s_sl = _strat_parsed.get("bear_scenario", {}).get("risk_pct", 0)
                    print(f"[Phase 3b] ✅ 戦略書生成完了: {_s_thesis} (target:{_s_tp:+.1f}% / stop:{_s_sl:.1f}% / RR={_rr_ratio:.2f} / ATR={_strat_atr_pct:.1f}%)")
                else:
                    _rej_reason = []
                    if len(_bull_ev) < 3: _rej_reason.append(f"bull_ev={len(_bull_ev)}<3")
                    if len(_bear_ev) < 3: _rej_reason.append(f"bear_ev={len(_bear_ev)}<3")
                    if not _risk_ok: _rej_reason.append(f"risk={_risk_pct:.1f}%>6%")
                    if not _rr_ok: _rej_reason.append(f"RR={_rr_ratio:.2f}<1.5")
                    if not _has_num(_bull_ev): _rej_reason.append("bull定量データなし")
                    if not _has_num(_bear_ev): _rej_reason.append("bear定量データなし")
                    print(f"[Phase 3b] ⚠️ 品質不足: {', '.join(_rej_reason)} (RR={_rr_ratio:.2f}) → 戦略書なしで続行")

            except Exception as _se:
                print(f"[Phase 3b] ⚠️ 戦略書生成失敗: {str(_se)[:80]} → 既存フローで続行")

        # ============================================================
        # analysis_only モード: レポート生成のみ（ACP Market Intelligence用）
        # Phase 5〜8（取引・Discord・Moltbook・メモリ）をスキップ
        # ============================================================
        if analysis_only:
            from core.config import EXIT_PROFILES, STRATEGY_TO_EXIT_PROFILE, EXIT_PROFILE_DEFAULT
            # v6.5as: AIのthesis_timeframeを優先、戦略名マッピングはフォールバック
            _ai_timeframe = _strat_parsed.get("thesis_timeframe") if isinstance(locals().get("_strat_parsed"), dict) else None
            if _ai_timeframe in ("short", "mid", "long"):
                _exit_name = _ai_timeframe
            else:
                _exit_name = STRATEGY_TO_EXIT_PROFILE.get(bt_best_strategy, EXIT_PROFILE_DEFAULT)
            _exit_data = EXIT_PROFILES.get(_exit_name, {})
            _fb_s = finbert_score if "finbert_score" in dir() else 0.0
            _fb_l = finbert_label if "finbert_label" in dir() else "neutral"
            try:
                _fng_val = market_context.split("Fear & Greed Index:")[1].split("/")[0].strip() if market_context and "Fear & Greed" in market_context else "N/A"
            except Exception:
                _fng_val = "N/A"
            _ai_exit = _strat_parsed.get("exit_params", {}) if isinstance(locals().get("_strat_parsed"), dict) else {}
            return {
                "verdict": first_word,
                "confidence": _calc_conf,
                "key_factor": _structured_key_factor,
                "price": current_price,
                "scoring_breakdown": {
                    "base": 50,
                    "bt_confidence": bt_confidence,
                    "sentiment_score": round(sentiment_score, 3),
                    "accuracy": accuracy,
                    "verdict_bias": 5 if first_word == "BUY" else 0,
                    "timezone": _tz_label,
                    "nanpin": _npin_label,
                    "streak": _streak_label,
                    
                    "cfr": _cfr_label,
                    "total": _calc_conf,
                },
                "bull_case": str(t1.output)[:500] if t1.output else "N/A",
                "bear_case": str(t2.output)[:500] if t2.output else "N/A",
                "neo_synthesis": str(t3.output)[:500] if t3.output else "N/A",
                "sentiment_detail": {
                    "score": round(sentiment_score, 3),
                    "label": sentiment_label,
                    "finbert_score": round(_fb_s, 3),
                    "finbert_label": _fb_l,
                    "fear_greed": _fng_val,
                },
                "backtest_summary": {
                    "best_strategy": bt_best_strategy,
                    "confidence": bt_confidence,
                    "report": backtest_report[:300] if isinstance(backtest_report, str) else "N/A",
                },
                "exit_profile": {
                    "category": _exit_name,
                    "sl_pct": _exit_data.get("sl_pct", 5.0),
                    "trailing_start": _ai_exit.get("trailing_start") or _exit_data.get("trailing_start", 5.0),
                    "trailing_drop": _ai_exit.get("trailing_drop") or _exit_data.get("trailing_drop", 2.5),
                    "rsi_exit": _ai_exit.get("rsi_exit") if _ai_exit.get("rsi_exit") is not None else _exit_data.get("rsi_exit"),
                    "hard_tp_pct": _exit_data.get("hard_tp_pct", 14.0),
                    "time_limit_hours": _exit_data.get("time_limit_hours", 96),
                },
                "best_strategy": bt_best_strategy,
                "reflexion_insight": reflexion_insight if reflexion_insight else "N/A",
                "planning_assessment": _planning_context if _planning_context else "N/A",
            }

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
                    # ②b 相関リスクガード: Tier1同時ポジション合計が総資産の50%超ならBUY禁止
                    _tier1_exposure = 0.0
                    for _t1sym in ["VIRTUAL", "AIXBT"]:
                        _t1amount = balances.get(_t1sym, 0.0)
                        if _t1amount > 0:
                            _t1data = MarketData.fetch_token_data(_t1sym)
                            _t1price = float(_t1data.get("priceUsd", 0.0)) if _t1data else 0.0
                            _tier1_exposure += _t1amount * _t1price
                    _tier1_ratio = _tier1_exposure / total_assets if total_assets > 0 else 0
                    if _tier1_ratio > 0.50:
                        trade_action = "WAIT"
                        trade_result = {"status": "skipped", "reason": f"Tier1合計エクスポージャー上限超過 ({_tier1_ratio:.1%} > 50%) — 相関リスクガード"}
                        print(f"\n[Phase 5] 🛑 BUY禁止: Tier1合計保有{_tier1_ratio:.1%}が上限50%超 (相関係数≈0.72)")
                    else:
                        # ②c confidence閾値ガード: 確信度40未満ならBUY禁止
                        MIN_CONFIDENCE_FOR_BUY = 30  # v6.5an: 50→30 BUYゲートではなくサイズで制御（出口防御で管理）
                        if _structured_confidence > 0 and _structured_confidence < MIN_CONFIDENCE_FOR_BUY:
                            trade_action = "WAIT"
                            trade_result = {"status": "skipped", "reason": f"confidence不足 ({_structured_confidence} < {MIN_CONFIDENCE_FOR_BUY}) — 低確信度ガード"}
                            print(f"\n[Phase 5] 🛑 BUY禁止: confidence={_structured_confidence}が閾値{MIN_CONFIDENCE_FOR_BUY}未満")
                        else:
                            # ③d ナンピン回数制限: 同一銘柄の未決済BUY回数がMAXを超えたらBUY禁止
                            # ⚠️ 安全装置（天井）— エージェントに判断を委ねる調整値ではなく、絶対超えてはいけない物理上限
                            # v6.5bc: 3→2 に引き下げ。根拠: ラウンドトリップ25件中、3BUY/1SELLパターン16件の
                            # うち負け13件（勝率0/13）。「3回目のBUY」が構造的に機能しておらず、
                            # 全てSL発火で平均-3.27%の損失を組織的に生産していた。
                            # 2回目BUY（=1回のナンピン）までは戦略的ナンピンとして許容する余地があるが、
                            # 3回目は実測データ上「ほぼ必ず負ける」パターンのため物理的に禁止する。
                            # この値は能動的調整を意図しない（エージェントの裁量外）。
                            MAX_OPEN_BUYS_PER_SYMBOL = 2
                            _open_buy_count = 0
                            _history = self.portfolio.get_full_state().get("history", [])
                            for _h in reversed(_history):
                                if _h.get("symbol") == clean_symbol:
                                    if _h.get("action") == "BUY":
                                        _open_buy_count += 1
                                    elif _h.get("action") == "SELL":
                                        break
                            if _open_buy_count >= MAX_OPEN_BUYS_PER_SYMBOL:
                                trade_action = "WAIT"
                                trade_result = {"status": "skipped", "reason": f"ナンピン上限到達 ({_open_buy_count}/{MAX_OPEN_BUYS_PER_SYMBOL}回)"}
                                print(f"\n[Phase 5] 🛑 BUY禁止: {clean_symbol}ナンピン{_open_buy_count}回（上限{MAX_OPEN_BUYS_PER_SYMBOL}回）")
                            else:
                                # ③ BUY額: ポジションサイズ（v6.5ag データ駆動型）
                                # v6.5as: AIポジションサイズ優先、ハードキャップ15%
                                _ai_size = None
                                try:
                                    _ai_size = _position_strategy.get("position_size_pct") if isinstance(_position_strategy, dict) else None
                                    if _ai_size is not None:
                                        _ai_size = float(_ai_size)
                                except Exception:
                                    _ai_size = None
                                if _ai_size is not None and 1.0 <= _ai_size <= 15.0:
                                    _size_pct = min(_ai_size / 100.0, 0.15)  # AI推奨（キャップ15%）
                                    print(f"  📐 AI推奨サイズ: {_ai_size:.1f}% → {_size_pct:.0%}")
                                elif _structured_confidence >= 85:
                                    _size_pct = 0.10
                                elif _structured_confidence >= 70:
                                    _size_pct = 0.07
                                elif _structured_confidence >= 55:
                                    _size_pct = 0.05
                                elif _structured_confidence >= 40:
                                    _size_pct = 0.03
                                else:
                                    _size_pct = 0.02
                                trade_amount_usd = round(min(total_assets * _size_pct, current_usdc * 0.10), 2)
                                if trade_amount_usd >= 10.0:
                                    print(f"\n[Phase 5] 🟢 BUY実行: ${trade_amount_usd:.2f} USDC → {clean_symbol} (conf={_structured_confidence} → {_size_pct:.0%} / USDC比率:{usdc_ratio:.1%} / {clean_symbol}比率:{holding_ratio:.1%})")
                                    trade_result = self.portfolio.execute_trade(
                                        symbol=clean_symbol,
                                        action="BUY",
                                        amount_usd=trade_amount_usd,
                                        price=current_price,
                                        reason=f"Trinity Council BUY verdict (accuracy: {accuracy}%, confidence: {bt_confidence})"
                                    )
                                    logger.info(f"Trade executed: BUY {clean_symbol} ${trade_amount_usd} @ ${current_price}")
                                    # 戦略タグをholdingsに保存（出口プロファイル用）
                                    from core.config import STRATEGY_TO_EXIT_PROFILE, EXIT_PROFILE_DEFAULT
                                    # v6.5as: AIのthesis_timeframeを優先
                                    _ai_tf = _position_strategy.get("thesis_timeframe") if isinstance(_position_strategy, dict) else None
                                    if _ai_tf in ("short", "mid", "long"):
                                        _exit_cat = _ai_tf
                                    else:
                                        _exit_cat = STRATEGY_TO_EXIT_PROFILE.get(bt_best_strategy, EXIT_PROFILE_DEFAULT)
                                    _pw_state = self.portfolio.get_full_state()
                                    if clean_symbol in _pw_state.get("holdings", {}):
                                        _pw_state["holdings"][clean_symbol]["strategy_tag"] = bt_best_strategy
                                        _pw_state["holdings"][clean_symbol]["exit_profile"] = _exit_cat
                                        self.portfolio.wallet._save_wallet()
                                        logger.info(f"Strategy tag: {bt_best_strategy} → exit_profile: {_exit_cat}")
                                        # BUY historyにもstrategy_tag保存（H.2分析用）
                                        if _pw_state.get("history"):
                                            _pw_state["history"][-1]["strategy_tag"] = bt_best_strategy
                                            self.portfolio.wallet._save_wallet()
                                        # E1.3: エントリー時コンテキスト保存（自己進化用）
                                        _entry_ctx = {
                                            "rsi_14": float(df.iloc[-1].get("rsi_14", 0)) if "df" in dir() and len(df) > 0 else 0,
                                            "sentiment_score": round(sentiment_score, 3),
                                            "sentiment_label": sentiment_label,
                                            "bt_confidence": bt_confidence,
                                            "confidence": _calc_conf,
                                            "key_factor": _structured_key_factor,
                                            "scoring_breakdown": {
                                                "base": 50,
                                                "bt": bt_confidence,
                                                "sent": round(sentiment_score, 3),
                                                "acc": accuracy,
                                                "tz": _tz_label,
                                                "npin": _npin_label,
                                                "streak": _streak_label,
                                                "cfr": _cfr_label,
                                                "macro": _planning_label,
                                                "total": _calc_conf,
                                            },
                                            "capital_flow_phase": _capital_flow_phase,
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        }
                                        try:
                                            _btc_ctx = MarketData.fetch_btc_trend()
                                            _entry_ctx["btc_24h"] = _btc_ctx.get("change_24h", 0) if _btc_ctx else 0
                                            _entry_ctx["btc_trend"] = _btc_ctx.get("trend", "unknown") if _btc_ctx else "unknown"
                                        except Exception:
                                            _entry_ctx["btc_24h"] = 0
                                            _entry_ctx["btc_trend"] = "unknown"
                                        # Phase S1: 戦略書をentry_contextに保存
                                        if _position_strategy:
                                            _entry_ctx["strategy"] = _position_strategy
                                        _pw_state["holdings"][clean_symbol]["entry_context"] = _entry_ctx
                                        self.portfolio.wallet._save_wallet()
                                        logger.info(f"Entry context saved for {clean_symbol}: conf={_calc_conf}, bt={bt_confidence}, strategy={'yes' if _position_strategy else 'no'}")
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
            _strategy_line = ""
            if _position_strategy:
                _s_thesis = _position_strategy.get("thesis", "")[:60]
                _s_tf = _position_strategy.get("thesis_timeframe", "?")
                _s_tp = _position_strategy.get("bull_scenario", {}).get("target_pct", 0)
                _s_sl = _position_strategy.get("bear_scenario", {}).get("risk_pct", 0)
                _strategy_line = f"\n🎯 戦略: {_s_thesis}\n📐 TF={_s_tf} | TP={_s_tp:+.1f}% | SL={_s_sl:.1f}%"
            trade_text = (
                f"✅ **BUY EXECUTED**\n"
                f"💰 Amount: ${trade_amount_usd:.2f} USDC\n"
                f"📊 Price: ${current_price:.6f}\n"
                f"🪙 Tokens: {tx.get('amount_token', 0):.4f} {clean_symbol}\n"
                f"📁 New Balance: ${self.portfolio.get_balance().get('USDC', 0):.2f} USDC"
                f"{_strategy_line}"
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

        # v6.5ay: EXIT_PROFILESダイジェスト生成（協議会レポート用）
        _eps_summary = ""
        try:
            from core.config import EXIT_PROFILES
            _eps_lines = []
            for _epn, _epd in EXIT_PROFILES.items():
                _eps_lines.append(
                    f"**{_epn}**: SL -{_epd['sl_pct']}% / HardTP +{_epd['hard_tp_pct']}% / "
                    f"Trail +{_epd['trailing_start']}%開始-{_epd['trailing_drop']}%利確 / "
                    f"上限 {_epd['time_limit_hours']}h"
                )
            _eps_summary = "⚡ 通常モード稼働中\n" + "\n".join(_eps_lines)
        except Exception:
            _eps_summary = ""

        discussion_data = {
            "bull": str(t1.output)[:1024] if t1.output else "N/A",
            "bear": str(t2.output)[:1024] if t2.output else "N/A",
            "exit_profiles_summary": _eps_summary,
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
            
            "symbol": clean_symbol,
            "tier": "Tier0 (BTC/ETH)" if clean_symbol in ("BTC", "ETH") else "Tier1 (VP銘柄)",
            "exit_profile": "",
            "strategy": _position_strategy,
            "scoring_breakdown": {
                "base": 50,
                "bt": bt_confidence,
                "sent": round(sentiment_score, 3),
                "acc": accuracy,
                "bias": 5 if trade_action == "BUY" else 0,
                "tz": _tz_label,
                "nanpin": _npin_label,
                "streak": _streak_label,
                
                "cfr": _cfr_label,
                "total": _structured_confidence,
            },
        }
        # exit_profile情報をBUY時に追加
        if trade_action == "BUY" and trade_result and trade_result.get("status") == "success":
            try:
                from core.config import EXIT_PROFILES, STRATEGY_TO_EXIT_PROFILE, EXIT_PROFILE_DEFAULT
                _ep_name = EXIT_PROFILE_DEFAULT
                _st = trade_result.get("tx", {}).get("strategy_tag", "")
                if _st:
                    _ep_name = STRATEGY_TO_EXIT_PROFILE.get(_st, EXIT_PROFILE_DEFAULT)
                _ep = EXIT_PROFILES.get(_ep_name, {})
                discussion_data["exit_profile"] = (
                    f"📋 **{_ep_name}** (strategy: {_st})\n"
                    f"SL: {_ep.get('sl_pct', 'N/A')}% | Trail: +{_ep.get('trailing_start', 'N/A')}%開始/-{abs(_ep.get('trailing_drop', 0))}%利確\n"
                    f"Hard TP: +{_ep.get('hard_tp_pct', 'N/A')}% | 時間上限: {_ep.get('time_limit_hours', 'N/A')}h"
                )
            except Exception:
                pass
        
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
                trade_amount_usd=trade_amount_usd,
                market_data={
                    'sentiment_score': round(sentiment_score, 2),
                    'sentiment_label': sentiment_label,
                    'capital_flow_phase': _capital_flow_phase if '_capital_flow_phase' in dir() else 'unknown',
                    'rsi': round(_strat_rsi, 1) if '_strat_rsi' in dir() and _strat_rsi else 0,
                    'confidence': _calc_conf if '_calc_conf' in dir() else 0,
                    'bt_best': bt_best_strategy if 'bt_best_strategy' in dir() else 'unknown',
                    'btc_24h': _strat_btc.get('change_24h', 0) if '_strat_btc' in dir() else 0,
                }
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
