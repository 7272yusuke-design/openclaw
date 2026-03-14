"""
DiscordReporter v2 — 取引結果フィールド追加、フィールド長制御
"""
import requests
import json
import os
import logging

logger = logging.getLogger("neo.discord")

class DiscordReporter:
    REPORT_WEBHOOK = "https://discord.com/api/webhooks/1479009905280028724/cX7C6pOTilIA4HeBzMwWOG_AhKMOcDH9KKU9_r955U0yr5z4hTsPRB0ISFfxjp3Otj64"
    LOG_WEBHOOK = "https://discord.com/api/webhooks/1478693375090622559/f0AwGgXAWkyGWOZVk5LLI9A1MKYQBvzmdSGoc3crPNMZ2mCaJEe-JIbF9ATuAsQp8Ioe"

    @classmethod
    def send_council_minutes(cls, title, discussion_data, color=0x3498db, image_path=None):
        """協議会レポート — 強気/弱気/統計/判定/取引結果の5フィールド"""
        
        fields = [
            {"name": "🐂 Bullish Opinion", "value": cls._truncate(discussion_data.get('bull', 'N/A'), 1024), "inline": False},
            {"name": "🐻 Bearish Opinion", "value": cls._truncate(discussion_data.get('bear', 'N/A'), 1024), "inline": False},
            {"name": "📊 Analysis & Backtest", "value": cls._truncate(discussion_data.get('stats', 'N/A'), 1024), "inline": False},
            {"name": "🤖 Neo's Verdict", "value": cls._truncate(discussion_data.get('verdict', 'Pending'), 1024), "inline": False},
        ]
        
        # 取引結果フィールド（存在する場合のみ追加）
        trade_info = discussion_data.get('trade')
        if trade_info:
            fields.append({
                "name": "💰 Trade Execution",
                "value": cls._truncate(trade_info, 1024),
                "inline": False
            })
        
        embed = {
            "title": title[:256],
            "color": color,
            "fields": fields,
            "footer": {"text": f"Mode: {os.getenv('NEO_MODE', 'PAPER')} | Neo Trinity Council v2"},
            "timestamp": None  # Discordが自動でタイムスタンプを付与
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
                if len(field["value"]) > 600:
                    field["value"] = field["value"][:597] + "..."
        
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
        return cls._post(cls.LOG_WEBHOOK, payload)

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
        """精度追跡ダッシュボード — 日次/評価後に自動送信"""
        from datetime import datetime

        # 勝率バー生成（10マス）
        filled = int(accuracy / 10) if accuracy > 0 else 0
        bar = "🟩" * filled + "⬜" * (10 - filled)

        # ステータス色
        if accuracy >= 60:
            color = 0x2ecc71   # 緑
        elif accuracy >= 40:
            color = 0xf39c12   # 橙
        else:
            color = 0xe74c3c   # 赤

        # 直近取引サマリー
        if recent_performance:
            lines = []
            for p in recent_performance[-5:]:
                pnl = p.get("pnl_pct", 0)
                emoji = "✅" if pnl > 0 else "❌"
                lines.append(f"{emoji} {p.get('symbol','?')} | 入: ${p.get('entry',0):.4f} 現: ${p.get('current',0):.4f} | {pnl:+.2f}%")
            recent_str = "\n".join(lines)
        else:
            recent_str = "取引履歴なし"

        # 累積P&L計算
        if recent_performance:
            avg_pnl = sum(p.get("pnl_pct", 0) for p in recent_performance) / len(recent_performance)
            pnl_str = f"{avg_pnl:+.2f}%"
        else:
            avg_pnl = 0.0
            pnl_str = "N/A"

        fields = [
            {"name": "🎯 勝率", "value": f"`{bar}` **{accuracy:.1f}%**", "inline": False},
            {"name": "📈 評価済み取引数", "value": str(total_trades), "inline": True},
            {"name": "📊 平均P&L", "value": pnl_str, "inline": True},
            {"name": "🕐 更新時刻", "value": datetime.now().strftime("%Y-%m-%d %H:%M JST"), "inline": True},
            {"name": "📋 直近5件", "value": recent_str or "なし", "inline": False},
        ]

        embed = {
            "title": "📊 Neo Performance Dashboard",
            "color": color,
            "fields": fields,
            "footer": {"text": "Neo Trinity Council v2 | Paper Trading"}
        }

        payload = {"embeds": [embed]}
        success = cls._post(cls.REPORT_WEBHOOK, payload)
        if success:
            logger.info("✅ Performance dashboard sent to Discord")
            print("✅ [Dashboard] Discord送信完了")
        return success
