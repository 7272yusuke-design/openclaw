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
            market_lines.append(f"💲 **価格**: ${d['current_price']:.6f}")
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
            pos_lines.append(f"{pnl_emoji} **保有**: {d['holding_amount']:.2f} tokens @ ${d.get('avg_price', 0):.6f}")
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
        
        # --- フィールド組み立て ---
        fields = [
            {"name": "📊 市況データ", "value": cls._truncate(market_text, 500), "inline": False},
            {"name": "💼 ポジション", "value": cls._truncate(pos_text, 300), "inline": False},
            {"name": "🐂 強気派の意見", "value": cls._truncate(bull_text, 500), "inline": False},
            {"name": "🐻 弱気派の意見", "value": cls._truncate(bear_text, 500), "inline": False},
            {"name": "📈 バックテスト", "value": cls._truncate(d.get("backtest_summary", "N/A"), 400), "inline": False},
            {"name": "🤖 Neoの最終判断", "value": cls._truncate(d.get("verdict", "Pending"), 800), "inline": False},
        ]
        
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
        
        embed = {
            "title": title[:256],
            "color": color,
            "fields": fields,
            "footer": {"text": f"Mode: {os.getenv('NEO_MODE', 'PAPER')} | Neo Trinity Council v3"},
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
    def send_trade_alert(cls, symbol, action, amount_usd, price, status, balance_after):
        """取引実行の即時アラート（ログチャンネル）"""
        color_map = {"BUY": 0x2ecc71, "SELL": 0xe74c3c, "WAIT": 0x95a5a6}
        emoji_map = {"BUY": "🟢", "SELL": "🔴", "WAIT": "⏸️"}
        
        embed = {
            "title": f"{emoji_map.get(action, '❓')} Trade Alert: {action} {symbol}",
            "color": color_map.get(action, 0x3498db),
            "fields": [
                {"name": "Action", "value": action, "inline": True},
                {"name": "Amount", "value": f"${amount_usd:.2f}", "inline": True},
                {"name": "Price", "value": f"${price:.6f}", "inline": True},
                {"name": "Status", "value": status, "inline": True},
                {"name": "Balance After", "value": f"${balance_after:.2f} USDC", "inline": True},
            ],
            "footer": {"text": "Neo Paper Trading v2"}
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
                    f"{pnl_emoji} {pos['symbol']}: {pos['amount']:,.0f}枚"
                    f" @ ${pos['avg_price']:.6f} → ${pos['current_price']:.6f}"
                    f" ({pos['pnl_pct']:+.2f}%)"
                )
            lines_pf.append(f"💰 **総資産: ${summary['total_value_usd']:,.2f}** ({summary['total_pnl_usd']:+,.2f})")
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
        tp_sl_str = "TP1=+3% / TP2=+7% / SL=-3%" if LEARNING_MODE else "TP=+20% / SL=-10%"
        fields = [
            {"name": "🎯 決済済み勝率", "value": f"`{bar}` **{accuracy:.1f}%** ({total_trades}件)", "inline": False},
            {"name": "📊 平均P&L", "value": pnl_str, "inline": True},
            {"name": "🕐 更新時刻", "value": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"), "inline": True},
            {"name": f"{mode_str}", "value": f"`{progress_bar}` {progress} ({progress_pct:.0f}%)\n📐 閾値: {tp_sl_str}", "inline": False},
            {"name": "💼 ポートフォリオ", "value": portfolio_str, "inline": False},
            {"name": "📋 直近決済5件", "value": recent_str or "なし", "inline": False},
        ]
        embed = {
            "title": "📊 Neo Performance Dashboard",
            "color": color,
            "fields": fields,
            "footer": {"text": "Neo Trinity Council v3 | Paper Trading"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload = {"embeds": [embed]}
        success = cls._post(cls.DASHBOARD_WEBHOOK or cls.REPORT_WEBHOOK, payload)
        if success:
            logger.info("✅ Performance dashboard sent to Discord")
            print("✅ [Dashboard] Discord送信完了")
        return success
