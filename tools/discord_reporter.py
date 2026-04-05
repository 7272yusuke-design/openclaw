"""
DiscordReporter v2 — 取引結果フィールド追加、フィールド長制御
"""
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()
import logging

logger = logging.getLogger("neo.discord")

class DiscordReporter:
    REPORT_WEBHOOK    = os.getenv("DISCORD_REPORT_WEBHOOK", "")
    LOG_WEBHOOK       = os.getenv("DISCORD_LOG_WEBHOOK", "")
    DASHBOARD_WEBHOOK = os.getenv("DISCORD_DASHBOARD_WEBHOOK", "")
    NIGHTLY_WEBHOOK   = os.getenv("DISCORD_NIGHTLY_WEBHOOK", "")

    @classmethod
    def send_council_minutes(cls, title, discussion_data, color=0x3498db, image_path=None):
        """協議会レポート v3 — 市況・意見・判定・取引を構造化表示"""
        d = discussion_data
        
        # --- 市況サマリー（1フィールドにコンパクトに） ---
        market_lines = []
        if d.get("current_price"):
            _sym = d.get("symbol", "")
            market_lines.append(f"💲 **価格**: {cls._fmt_price(d['current_price'], _sym)}")
        if d.get("btc_context"):
            market_lines.append(f"₿ {d['btc_context']}")
        if d.get("fear_greed") and d["fear_greed"] != "N/A":
            market_lines.append(f"😱 **Fear & Greed**: {d['fear_greed']}/100")
        if d.get("finbert_label"):
            fb_emoji = "📈" if d.get("finbert_score", 0) > 0.1 else ("📉" if d.get("finbert_score", 0) < -0.1 else "➡️")
            market_lines.append(f"{fb_emoji} **FinBERT**: {d['finbert_label']} ({d.get('finbert_score', 0):+.3f})")
        if d.get("whale_signal"):
            market_lines.append(f"🐋 **Whale**: {d['whale_signal']}")
        if d.get("news_count") is not None:
            market_lines.append(f"📰 **ニュース**: {d['news_count']}件")
        market_text = "\n".join(market_lines) if market_lines else "N/A"
        
        # --- ポジション情報 ---
        pos_lines = []
        if d.get("usdc_balance") is not None:
            pos_lines.append(f"💰 **USDC**: ${d['usdc_balance']:,.0f} ({d.get('usdc_ratio', 0):.0f}%)")
        if d.get("holding_amount") and d["holding_amount"] > 0:
            pnl_emoji = "📈" if d.get("unrealized_pnl_pct", 0) >= 0 else "📉"
            _pos_sym = d.get("symbol", "")
            pos_lines.append(f"{pnl_emoji} **保有**: {d['holding_amount']:.4f} tokens @ {cls._fmt_price(d.get('avg_price', 0), _pos_sym)}")
            pos_lines.append(f"   含み損益: {d.get('unrealized_pnl_pct', 0):+.2f}% (${d.get('unrealized_pnl_usd', 0):+.2f})")
        else:
            pos_lines.append("📦 **保有**: なし（新規エントリー）")
        pos_text = "\n".join(pos_lines)
        
        # --- Bull/Bear意見（クリーンアップ） ---
        def _clean_opinion(raw):
            """CrewAI出力からコードブロック・JSON・制御文字を除去"""
            text = str(raw) if raw else "N/A"
            import re
            text = re.sub(r'```[\s\S]*?```', '', text)
            text = re.sub(r'\{[\s\S]*?\}', '', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            if not text:
                return "N/A"
            return text
        
        bull_text = _clean_opinion(d.get("bull"))
        bear_text = _clean_opinion(d.get("bear"))
        
        # --- 戦略書セクション（Phase S対応） ---
        _strat = d.get("strategy")
        _strat_text = ""
        if _strat:
            _bull_s = _strat.get("bull_scenario", {})
            _bear_s = _strat.get("bear_scenario", {})
            _inv = _strat.get("invalidation", {})
            _tp_pct = _bull_s.get("target_pct", 0)
            _sl_pct = _bear_s.get("risk_pct", 0)
            _rr = abs(_tp_pct / _sl_pct) if _sl_pct != 0 else 0
            _strat_text = (
                f"📌 **{_strat.get('thesis', '?')}**\n"
                f"⏱️ TF: {_strat.get('thesis_timeframe', '?')} | 想定期間: {_bull_s.get('target_days', '?')}日\n"
                f"🎯 TP: ${_bull_s.get('target_price', 0):.4f} ({_tp_pct:+.1f}%)\n"
                f"🛡️ SL: ${_bear_s.get('stop_price', 0):.4f} ({_sl_pct:.1f}%)\n"
                f"📐 RR比: {_rr:.2f}\n"
                f"📈 利確戦略: {_bull_s.get('take_profit_plan', 'N/A')[:100]}\n"
                f"📉 ヘッジ戦略: {_bear_s.get('hedge_plan', 'N/A')[:100]}\n"
                f"⛔ 無効化条件: {', '.join(_inv.get('conditions', []))[:120]}"
            )

        # --- スコアリング内訳 ---
        _sb = d.get("scoring_breakdown", {})
        _score_text = "N/A"
        if _sb:
            _score_parts = []
            _score_parts.append(f"Base: {_sb.get('base', 50)}")
            if _sb.get('bt'): _score_parts.append(f"BT: {_sb['bt']}")
            if _sb.get('sent'): _score_parts.append(f"Sent: {_sb['sent']}")
            if _sb.get('acc'): _score_parts.append(f"Acc: {_sb['acc']}%")
            if _sb.get('bias'): _score_parts.append(f"Bias: +{_sb['bias']}")
            if _sb.get('tz') and _sb['tz'] != 'none': _score_parts.append(f"TZ: {_sb['tz']}")
            if _sb.get('nanpin') and _sb['nanpin'] != 'none': _score_parts.append(f"Nanpin: {_sb['nanpin']}")
            if _sb.get('streak') and _sb['streak'] != 'none': _score_parts.append(f"Streak: {_sb['streak']}")
            if _sb.get('pair_z') and _sb['pair_z'] != 'none': _score_parts.append(f"PairZ: {_sb['pair_z']}")
            if _sb.get('cfr') and _sb['cfr'] != 'none': _score_parts.append(f"CFR: {_sb['cfr']}")
            _score_text = f"**Confidence: {_sb.get('total', '?')}** | " + " | ".join(_score_parts)

        # --- フィールド組み立て ---
        fields = [
            {"name": "📊 市況データ", "value": cls._truncate(market_text, 500), "inline": False},
            {"name": "💼 ポジション", "value": cls._truncate(pos_text, 300), "inline": False},
        ]
        if _strat_text:
            fields.append({"name": "🎯 ポジション戦略書", "value": cls._truncate(_strat_text, 600), "inline": False})
        else:
            fields.append({"name": "🐂 強気派の意見", "value": cls._truncate(bull_text, 500), "inline": False})
            fields.append({"name": "🐻 弱気派の意見", "value": cls._truncate(bear_text, 500), "inline": False})
        fields.append({"name": "📐 スコアリング", "value": cls._truncate(_score_text, 400), "inline": False})
        fields.append({"name": "🤖 Neoの最終判断", "value": cls._truncate(d.get("verdict", "Pending"), 800), "inline": False})
        
        # N.1ペアトレードフィールド（存在する場合のみ追加）
        if d.get("pair_trade"):
            fields.append({
                "name": "📐 N.1 ペアトレード",
                "value": cls._truncate(d["pair_trade"], 400),
                "inline": False
            })

        # 取引結果フィールド（存在する場合のみ追加）
        trade_info = d.get("trade")
        if trade_info:
            fields.append({
                "name": "💰 取引執行",
                "value": cls._truncate(trade_info, 500),
                "inline": False
            })
        
        # Tier表記フィールド（存在する場合のみ追加）
        if d.get("tier"):
            fields.insert(0, {
                "name": "🏷️ Tier",
                "value": d["tier"],
                "inline": True
            })

        # 出口プロファイル（存在する場合のみ追加）
        if d.get("exit_profile"):
            fields.append({
                "name": "🚪 出口プロファイル",
                "value": cls._truncate(d["exit_profile"], 300),
                "inline": False
            })

        embed = {
            "title": title[:256],
            "color": color,
            "fields": fields,
            "footer": {"text": f"Mode: {os.getenv('NEO_MODE', 'PAPER')} | Neo Trinity Council v3 | 3-Asset Rotation"},
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        
        if image_path and os.path.exists(image_path):
            filename = os.path.basename(image_path)
            embed["image"] = {"url": f"attachment://{filename}"}
        
        payload = {"embeds": [embed]}
        
        # Embed合計長チェック (Discord制限: 6000文字)
        total_len = sum(len(f.get("value", "")) + len(f.get("name", "")) for f in fields) + len(title)
        if total_len > 5800:
            logger.warning(f"Embed total length {total_len} near limit. Truncating fields.")
            for field in fields:
                if len(field["value"]) > 400:
                    field["value"] = field["value"][:397] + "..."
        
        success = cls._post(cls.REPORT_WEBHOOK, payload, image_path)
        if success:
            logger.info(f"✅ Council minutes sent: {title}")
        return success

    @classmethod
    def send_trade_alert(cls, symbol, action, amount_usd, price, status, balance_after, exit_profile=""):
        """取引実行の即時アラート（ログチャンネル）"""
        color_map = {"BUY": 0x2ecc71, "SELL": 0xe74c3c, "WAIT": 0x95a5a6}
        emoji_map = {"BUY": "🟢", "SELL": "🔴", "WAIT": "⏸️"}
        # 銘柄名からシンボル抽出（"VIRTUAL (TP +5.2%)" → "VIRTUAL"）
        _clean_sym = symbol.split("(")[0].strip().split("/")[0].strip() if symbol else ""
        
        fields = [
            {"name": "Action", "value": action, "inline": True},
            {"name": "Amount", "value": f"${amount_usd:.2f}", "inline": True},
            {"name": "Price", "value": cls._fmt_price(price, _clean_sym), "inline": True},
            {"name": "Status", "value": status, "inline": True},
            {"name": "Balance After", "value": f"${balance_after:,.2f} USDC", "inline": True},
        ]
        if exit_profile:
            fields.append({"name": "Exit Profile", "value": exit_profile, "inline": True})
        
        embed = {
            "title": f"{emoji_map.get(action, '❓')} Trade Alert: {action} {symbol}",
            "color": color_map.get(action, 0x3498db),
            "fields": fields,
            "footer": {"text": "Neo Trinity Council v3 | Paper Trading | 3-Asset Rotation"}
        }
        
        payload = {"embeds": [embed]}
        return cls._post(cls.REPORT_WEBHOOK, payload)

    @classmethod
    def send_log(cls, title, message, color=0x3498db):
        """汎用ログメッセージ"""
        payload = {
            "embeds": [{
                "title": title[:256],
                "description": cls._truncate(message, 4096),
                "color": color
            }]
        }
        return cls._post(cls.LOG_WEBHOOK, payload)

    @classmethod
    def _truncate(cls, text, max_len):
        """安全なテキスト切り詰め"""
        text = str(text) if text else "N/A"
        if len(text) > max_len:
            return text[:max_len - 3] + "..."
        return text

    @staticmethod
    def _fmt_price(price, symbol=""):
        """銘柄に応じた価格フォーマット（BTC/ETH=カンマ区切り, VP銘柄=6桁小数）"""
        if price is None or price == 0:
            return "$0"
        if symbol in ("BTC", "ETH") or price >= 10:
            return f"${price:,.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        else:
            return f"${price:.6f}"

    @classmethod
    def _post(cls, url, payload, image_path=None):
        try:
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    filename = os.path.basename(image_path)
                    files = {'file': (filename, f, 'image/png')}
                    response = requests.post(url, data={'payload_json': json.dumps(payload)}, files=files, timeout=15)
            else:
                response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code in (200, 204):
                return True
            else:
                logger.error(f"Discord HTTP {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"❌ Discord送信失敗: {e}")
            return False


    @classmethod
    def send_moltbook_report(cls):
        """Moltbook活動レポート — 反響+エンゲージメント統合"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        fields = []
        # --- 反響データ（tracker） ---
        try:
            import json as _json, os as _os
            stats_path = "data/moltbook_stats.json"
            if _os.path.exists(stats_path):
                with open(stats_path) as f:
                    history = _json.load(f)
                if history:
                    latest = history[-1]
                    prev = history[-2] if len(history) >= 2 else latest
                    karma_diff = latest.get("karma", 0) - prev.get("karma", 0)
                    follower_diff = latest.get("follower_count", 0) - prev.get("follower_count", 0)
                    _kd = "+" + str(karma_diff) if karma_diff >= 0 else str(karma_diff)
                    _fd = "+" + str(follower_diff) if follower_diff >= 0 else str(follower_diff)
                    _karma = latest.get("karma", 0)
                    _followers = latest.get("follower_count", 0)
                    _posts = latest.get("posts_count", 0)
                    _avg_up = latest.get("avg_upvotes", 0)
                    ov_parts = []
                    ov_parts.append("karma: **" + str(_karma) + "** (" + _kd + ")")
                    ov_parts.append("followers: **" + str(_followers) + "** (" + _fd + ")")
                    ov_parts.append("posts: " + str(_posts) + " | avg upvotes: " + str(_avg_up))
                    overview = chr(10).join(ov_parts)
                    fields.append({"name": "📊 アカウント概要", "value": overview, "inline": False})
                    bp = latest.get("best_post", {})
                    if bp.get("upvotes", 0) > 0:
                        _bp_text = str(bp["upvotes"]) + "upvotes - " + bp.get("preview", "?")[:60]
                        fields.append({"name": "🏆 最高反響", "value": _bp_text, "inline": False})
        except Exception as e:
            logger.error("Moltbook tracker data error: " + str(e))
        # --- エンゲージメント活動（engager） ---
        try:
            from tools.moltbook_engager import MoltbookEngager
            stats = MoltbookEngager.get_engagement_stats()
            upvoted_ids = MoltbookEngager._load_json_set(MoltbookEngager.UPVOTED_FILE)
            _comments = stats.get("total_comments_received", 0)
            _commenters = len(stats.get("unique_commenters", []))
            _replied = stats.get("total_replied", 0)
            _unreplied = stats.get("total_unreplied", 0)
            _upvoted = len(upvoted_ids)
            eg_parts = []
            eg_parts.append("受信コメント: " + str(_comments) + "件 (" + str(_commenters) + "人)")
            eg_parts.append("返信済: " + str(_replied) + "件 / 未返信: " + str(_unreplied) + "件")
            eg_parts.append("Upvote実施: " + str(_upvoted) + "件（累計）")
            if _unreplied > 0:
                eg_parts.append("⚠️ 未返信" + str(_unreplied) + "件あり")
            fields.append({"name": "🤝 エンゲージメント", "value": chr(10).join(eg_parts), "inline": False})
            convos = stats.get("recent_conversations", [])
            if convos:
                convo_lines = []
                for c in convos[:3]:
                    mark = "✅" if c.get("replied") else "⏳"
                    convo_lines.append(mark + " [" + c.get("author", "?") + "] " + c.get("comment_preview", "")[:50])
                fields.append({"name": "💬 直近の会話", "value": chr(10).join(convo_lines), "inline": False})
        except Exception as e:
            logger.error("Moltbook engager data error: " + str(e))
        # --- submolt別分析 ---
        try:
            from tools.moltbook_tracker import analyze_best_topics
            analysis = analyze_best_topics()
            if analysis and analysis.get("submolt_ranking"):
                sm_lines = []
                for s in analysis["submolt_ranking"][:4]:
                    sm_lines.append(s["submolt"] + ": avg " + str(s["avg_upvotes"]) + "up (" + str(s["count"]) + "件)")
                fields.append({"name": "📈 submolt別パフォーマンス", "value": chr(10).join(sm_lines), "inline": False})
        except Exception:
            pass
        if not fields:
            fields.append({"name": "ℹ️ ステータス", "value": "データ蓄積中", "inline": False})
        embed = {
            "title": "📣 Moltbook活動レポート",
            "color": 0xe67e22,
            "fields": fields,
            "footer": {"text": "Neo Moltbook Analytics"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload = {"embeds": [embed]}
        _url = cls.NIGHTLY_WEBHOOK or cls.LOG_WEBHOOK
        success = cls._post(_url, payload)
        if success:
            logger.info("✅ Moltbook report sent to Discord")
        return success

    @classmethod
    def send_performance_dashboard(cls, accuracy, total_trades, recent_performance, win_count=None):
        """精度追跡ダッシュボード v3 — 学習進捗・TP/SL閾値・ポートフォリオ"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        # 学習モード情報取得
        try:
            from core.config import LEARNING_MODE, LEARNING_TARGET_TRADES
        except ImportError:
            LEARNING_MODE = True
            LEARNING_TARGET_TRADES = 100
        # 勝率バー生成（10マス）
        filled = int(accuracy / 10) if accuracy > 0 else 0
        bar = "🟩" * filled + "⬜" * (10 - filled)
        # ステータス色
        if accuracy >= 60:
            color = 0x2ecc71
        elif accuracy >= 40:
            color = 0xf39c12
        else:
            color = 0xe74c3c
        # 直近取引サマリー
        if recent_performance:
            lines = []
            for p in recent_performance[-5:]:
                pnl = p.get("pnl_pct", 0)
                emoji = "✅" if pnl > 0 else "❌"
                entry = p.get('entry_price', p.get('entry', 0))
                exit_ = p.get('exit_price', p.get('current', 0))
                lines.append(f"{emoji} {p.get('symbol','?')} | ${entry:.4f}→${exit_:.4f} | {pnl:+.2f}%")
            recent_str = "\n".join(lines)
        else:
            recent_str = "決済済み取引なし"
        # 累積P&L計算
        if recent_performance:
            avg_pnl = sum(p.get("pnl_pct", 0) for p in recent_performance) / len(recent_performance)
            pnl_str = f"{avg_pnl:+.2f}%"
        else:
            avg_pnl = 0.0
            pnl_str = "N/A"
        # ポートフォリオ内訳取得
        portfolio_str = "取得失敗"
        try:
            import sys as _sys
            _sys.path.insert(0, ".")
            from tools.paper_wallet import PaperWallet
            from tools.market_data import MarketData
            w = PaperWallet()
            prices = {}
            for symbol in w.state.get("holdings", {}).keys():
                data = MarketData.fetch_token_data(symbol)
                if data and data.get("priceUsd"):
                    prices[symbol] = float(data["priceUsd"])
            summary = w.get_portfolio_summary(prices)
            lines_pf = [f"💵 USDC: ${summary['usd_balance']:,.2f}"]
            for pos in summary.get("positions", []):
                pnl_emoji = "📈" if pos["pnl_pct"] >= 0 else "📉"
                lines_pf.append(
                    f"{pnl_emoji} **{pos['symbol']}**: {pos['amount']:,.0f}枚"
                    f" @ ${pos['avg_price']:.6f} → ${pos['current_price']:.6f}"
                    f" | {pos['pnl_pct']:+.2f}% (${pos.get('pnl_usd', 0):+,.2f})"
                )
                # 戦略書情報を追加（entry_contextから取得）
                _sym = pos.get("symbol", "")
                _hdata = w.state.get("holdings", {}).get(_sym, {})
                _ec = _hdata.get("entry_context", {}) if isinstance(_hdata, dict) else {}
                _strat = _ec.get("strategy")
                if _strat:
                    _bull_s = _strat.get("bull_scenario", {})
                    _bear_s = _strat.get("bear_scenario", {})
                    _tp = _bull_s.get("target_price", 0)
                    _sl = _bear_s.get("stop_price", 0)
                    _entry = float(_hdata.get("avg_price", 0))
                    _cur = pos.get("current_price", 0)
                    _bull_prog = ((_cur - _entry) / (_tp - _entry) * 100) if _tp > _entry > 0 else 0
                    _bear_prog = ((_entry - _cur) / (_entry - _sl) * 100) if _entry > _sl > 0 and _entry > 0 else 0
                    _days = _bull_s.get("target_days", "?")
                    lines_pf.append(
                        f"   📌 {_strat.get('thesis', '?')[:50]}"
                    )
                    lines_pf.append(
                        f"   🎯 TP: ${_tp:.4f} ({_bull_prog:.0f}%到達) | 🛡️ SL: ${_sl:.4f} ({_bear_prog:.0f}%接近) | ⏱️ {_days}日想定"
                    )
            lines_pf.append(f"💰 **総資産: ${summary['total_value_usd']:,.2f}** (${summary['total_pnl_usd']:+,.2f})")
            portfolio_str = "\n".join(lines_pf)
        except Exception as _pe:
            portfolio_str = f"取得失敗: {str(_pe)[:50]}"
        # 学習モード進捗
        history_count = 0
        try:
            from tools.paper_wallet import PaperWallet as _PW2
            _w2 = _PW2()
            history_count = len(_w2.state.get("history", []))
        except Exception:
            pass
        mode_str = "📚 学習モード" if LEARNING_MODE else "⚡ 通常モード"
        progress = f"{history_count}/{LEARNING_TARGET_TRADES}"
        progress_pct = min(history_count / LEARNING_TARGET_TRADES * 100, 100)
        progress_bar = "▓" * int(progress_pct / 10) + "░" * (10 - int(progress_pct / 10))
        # 出口プロファイル情報（v6.5aa: 戦略別出口）
        try:
            from core.config import EXIT_PROFILES
            _ep_lines = []
            for _ep_name, _ep in EXIT_PROFILES.items():
                _ep_lines.append(f"{_ep_name}: SL{_ep['sl_pct']}%/TP{_ep['hard_tp_pct']}%/Trail+{_ep['trailing_start_pct']}%")
            tp_sl_str = " | ".join(_ep_lines)
        except Exception:
            tp_sl_str = "戦略別出口プロファイル（config.py参照）"
        # Tier別勝率取得
        _tier0_str = "N/A"
        _tier1_str = "N/A"
        try:
            from core.blackboard import NeoBlackboard
            _bb = NeoBlackboard.load()
            _ps = _bb.get("performance_summary", {})
            _t0_acc = _ps.get("tier0_accuracy", 0)
            _t0_n = _ps.get("tier0_trades", 0)
            _t1_acc = _ps.get("tier1_accuracy", 0)
            _t1_n = _ps.get("tier1_trades", 0)
            if _t0_n > 0:
                _tier0_str = f"{_t0_acc:.1f}% ({_t0_n}件)"
            if _t1_n > 0:
                _tier1_str = f"{_t1_acc:.1f}% ({_t1_n}件)"
        except Exception:
            pass

        fields = [
            {"name": "🎯 総合勝率", "value": f"`{bar}` **{accuracy:.1f}%** ({total_trades}件)", "inline": False},
            {"name": "🏦 Tier0 (BTC/ETH)", "value": _tier0_str, "inline": True},
            {"name": "🪙 Tier1 (VP銘柄)", "value": _tier1_str, "inline": True},
            {"name": "📊 平均P&L", "value": pnl_str, "inline": True},
            {"name": "🕐 更新時刻", "value": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"), "inline": True},
            {"name": f"{mode_str}", "value": f"`{progress_bar}` {progress} ({progress_pct:.0f}%)\n📐 出口: {tp_sl_str}", "inline": False},
            {"name": "💼 ポートフォリオ", "value": portfolio_str, "inline": False},
            {"name": "📋 直近決済5件", "value": recent_str or "なし", "inline": False},
        ]
        embed = {
            "title": "📊 Neo Performance Dashboard",
            "color": color,
            "fields": fields,
            "footer": {"text": "Neo Trinity Council v3 | Paper Trading | Tier0+Tier1 3-Asset Rotation"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload = {"embeds": [embed]}
        success = cls._post(cls.DASHBOARD_WEBHOOK or cls.REPORT_WEBHOOK, payload)
        if success:
            logger.info("✅ Performance dashboard sent to Discord")
            print("✅ [Dashboard] Discord送信完了")
        return success
