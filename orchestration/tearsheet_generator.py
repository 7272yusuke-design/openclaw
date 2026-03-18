"""
M.2: quantstatsによるHTMLティアシート生成
Nightly Batch実行時に paper_trade.log からリターン系列を生成し
HTMLレポートを出力する
"""
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
OUTPUT_DIR = BASE_DIR / "data" / "tearsheets"

def _parse_closed_trades(log_path: Path) -> list:
    """paper_trade.logから決済済み取引のPnL系列を生成（FIFOマッチング）"""
    buys = defaultdict(list)
    sells = defaultdict(list)
    pattern = re.compile(
        r"\[(.*?)\] (.*?): \$(.*?) \| Action: (BUY|SELL) \| Amount: \$([\d.]+) \|"
    )
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if not m:
                continue
            timestamp, symbol, price_str, action, amount_str = m.groups()
            clean_symbol = symbol.split('/')[0].strip()
            try:
                price = float(price_str)
                amount_usd = float(amount_str)
            except ValueError:
                continue
            if amount_usd <= 0:
                continue
            entry = {"timestamp": timestamp, "price": price, "amount_usd": amount_usd}
            if action == "BUY":
                buys[clean_symbol].append(entry)
            else:
                sells[clean_symbol].append(entry)

    # FIFOマッチング
    closed = []
    for symbol in set(list(buys.keys()) + list(sells.keys())):
        remaining = list(buys.get(symbol, []))
        for sell in sells.get(symbol, []):
            sell_left = sell["amount_usd"]
            while sell_left > 0 and remaining:
                buy = remaining[0]
                matched = min(buy["amount_usd"], sell_left)
                pnl_pct = (sell["price"] - buy["price"]) / buy["price"]
                closed.append({
                    "timestamp": sell["timestamp"],
                    "symbol": symbol,
                    "pnl_pct": pnl_pct,
                    "amount_usd": matched
                })
                sell_left -= matched
                buy["amount_usd"] -= matched
                if buy["amount_usd"] <= 0:
                    remaining.pop(0)
    closed.sort(key=lambda x: x["timestamp"])
    return closed


def generate_tearsheet() -> str | None:
    """
    HTMLティアシートを生成してファイルパスを返す。
    決済済み取引が3件未満の場合はスキップ。
    """
    try:
        import quantstats as qs
        import pandas as pd
    except ImportError as e:
        print(f"⚠️ [Tearsheet] quantstats未インストール: {e}")
        return None

    log_path = BASE_DIR / "paper_trade.log"
    if not log_path.exists():
        print("⚠️ [Tearsheet] paper_trade.log が見つかりません")
        return None

    closed = _parse_closed_trades(log_path)
    if len(closed) < 3:
        print(f"⚠️ [Tearsheet] 決済済み取引が{len(closed)}件（最低3件必要）。スキップ。")
        return None

    # pandas Seriesに変換（日次リターン）
    df = pd.DataFrame(closed)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    returns = df["pnl_pct"].rename("Neo")

    # 出力先
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    output_path = OUTPUT_DIR / f"tearsheet_{today}.html"

    try:
        qs.reports.html(
            returns,
            output=str(output_path),
            title=f"Neo Trading Report ({today})",
            download_filename=str(output_path)
        )
        print(f"✅ [Tearsheet] HTMLレポート生成完了: {output_path}")
        return str(output_path)
    except Exception as e:
        print(f"⚠️ [Tearsheet] HTML生成失敗: {e}")
        # フォールバック: テキストサマリーのみ
        try:
            print("\n📊 [Tearsheet] テキストサマリー:")
            qs.reports.basic(returns)
        except Exception:
            pass
        return None


if __name__ == "__main__":
    result = generate_tearsheet()
    if result:
        print(f"出力先: {result}")
