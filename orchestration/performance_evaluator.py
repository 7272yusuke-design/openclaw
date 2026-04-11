import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from tools.market_data import MarketData
try:
    import empyrical
    import numpy as np
    HAS_EMPYRICAL = True
except ImportError:
    HAS_EMPYRICAL = False

from core.blackboard import NeoBlackboard


def _parse_log(log_path):
    """paper_trade.logからBUY/SELLエントリを抽出してペアリング"""
    buys = defaultdict(list)   # symbol -> [{"timestamp","price","amount_usd"}]
    sells = defaultdict(list)  # symbol -> [{"timestamp","price","amount_usd"}]

    pattern = re.compile(
        r"\[(.*?)\] (.*?): \$(.*?) \| Action: (BUY|SELL|WAIT) \| Amount: \$(.*?) \|"
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

            if action == "BUY" and amount_usd > 0:
                buys[clean_symbol].append({
                    "timestamp": timestamp,
                    "price": price,
                    "amount_usd": amount_usd
                })
            elif action == "SELL" and amount_usd > 0:
                sells[clean_symbol].append({
                    "timestamp": timestamp,
                    "price": price,
                    "amount_usd": amount_usd
                })

    return buys, sells


def _parse_wallet_history():
    """PaperWalletのhistoryから直接BUY/SELLエントリを取得（最も正確なソース）
    
    ウォレットリセット後のゴーストBUY対策:
    現在のholdingsに存在しないシンボルで、BUY数>SELL数の場合、
    FIFOで決済されない余剰BUYはリセットにより無効化されたものとみなす。
    → SELLでカバーされる分のBUYのみを残す。
    """
    import json
    wallet_path = BASE_DIR / "data" / "paper_wallet.json"
    buys = defaultdict(list)
    sells = defaultdict(list)
    
    try:
        with open(wallet_path) as f:
            data = json.load(f)
        
        # 現在のholdingsを取得（amount>0のシンボルのみ）
        holdings = {}
        for sym, info in data.get("holdings", {}).items():
            amt = info.get("amount", 0) if isinstance(info, dict) else 0
            if amt > 0:
                holdings[sym.upper()] = amt
        
        for h in data.get("history", []):
            action = h.get("action", "").upper()
            symbol = h.get("symbol", "").split("/")[0].strip().upper()
            price = float(h.get("price", 0))
            amount_usd = float(h.get("amount_usd", 0))
            amount_token = float(h.get("amount_token", 0))
            timestamp = h.get("timestamp", "")
            
            if action == "BUY" and amount_token > 0:
                buys[symbol].append({"timestamp": timestamp, "price": price, "amount_usd": amount_usd, "amount_token": amount_token})
            elif action == "SELL" and amount_token > 0:
                sells[symbol].append({"timestamp": timestamp, "price": price, "amount_usd": amount_usd, "amount_token": amount_token})
        
        # ゴーストBUY除外: holdingsにないシンボルはSELL分だけBUYを残す
        for symbol in list(buys.keys()):
            if symbol not in holdings:
                sell_total_token = sum(s["amount_token"] for s in sells.get(symbol, []))
                if sell_total_token == 0:
                    # SELLもない → 全BUYがリセットで無効化
                    removed = len(buys[symbol])
                    del buys[symbol]
                    print(f"  🧹 {symbol}: BUY {removed}件除外（holdings空・SELL履歴なし）")
                else:
                    # SELLがある → SELLでカバーされるBUYのみ残す（FIFO）
                    trimmed_buys = []
                    cumulative_token = 0
                    for b in buys[symbol]:
                        cumulative_token += b["amount_token"]
                        trimmed_buys.append(b)
                        if cumulative_token >= sell_total_token:
                            break
                    removed = len(buys[symbol]) - len(trimmed_buys)
                    if removed > 0:
                        buys[symbol] = trimmed_buys
                        print(f"  🧹 {symbol}: BUY {removed}件除外（リセットによるゴースト）")
        
    except Exception as e:
        print(f"⚠️ Wallet history parse error: {e}")
    
    return buys, sells


def _calc_closed_trades(buys, sells):
    """
    決済済み取引のPnLを計算（FIFOマッチング）
    戻り値: closed=[{symbol, entry_price, exit_price, pnl_pct}], open_buys={symbol:[...]}
    """
    closed = []
    open_buys = {}

    all_symbols = set(list(buys.keys()) + list(sells.keys()))
    for symbol in all_symbols:
        buy_queue = list(buys.get(symbol, []))   # FIFO
        sell_list = list(sells.get(symbol, []))

        remaining_buys = list(buy_queue)
        for sell in sell_list:
            sell_token_left = sell["amount_token"]
            while sell_token_left > 0.0001 and remaining_buys:
                buy = remaining_buys[0]
                matched_token = min(buy["amount_token"], sell_token_left)
                pnl_pct = (sell["price"] - buy["price"]) / buy["price"] * 100
                matched_usd = round(matched_token * buy["price"], 2)
                closed.append({
                    "symbol": symbol,
                    "entry_price": buy["price"],
                    "exit_price": sell["price"],
                    "amount_usd": matched_usd,
                    "pnl_pct": round(pnl_pct, 2),
                    "sell_time": sell.get("timestamp", "")
                })
                sell_token_left -= matched_token
                buy["amount_token"] -= matched_token
                if buy["amount_token"] <= 0.0001:
                    remaining_buys.pop(0)

        if remaining_buys:
            open_buys[symbol] = remaining_buys

    # 時系列順にソート（直近5件表示用）
    closed.sort(key=lambda x: x.get("sell_time", ""))
    return closed, open_buys


def evaluate_performance(send_dashboard: bool = False):
    print("📊 [Evaluator] Neo's Verdict Review starting...")
    log_path = BASE_DIR / "paper_trade.log"

    if not log_path.exists():
        print("⚠️ Log file not found.")
        return

    # PaperWallet historyを優先（最も正確なソース）
    try:
        buys, sells = _parse_wallet_history()
        source = "PaperWallet"
    except Exception:
        buys, sells = {}, {}
        source = "none"
    
    # フォールバック: wallet historyが空ならpaper_trade.logを使用
    if not buys and not sells:
        try:
            buys, sells = _parse_log(log_path)
            source = "paper_trade.log"
        except Exception as e:
            print(f"⚠️ Log parse error: {e}")
            return
    
    print(f"  📂 データソース: {source}")

    # 決済済み取引の勝率
    closed, open_buys = _calc_closed_trades(buys, sells)
    closed_wins = sum(1 for t in closed if t["pnl_pct"] > 0)
    closed_total = len(closed)
    closed_accuracy = (closed_wins / closed_total * 100) if closed_total > 0 else 0.0

    print(f"  📁 決済済み取引: {closed_total}件 | 勝率: {closed_accuracy:.2f}%")
    # Tier別勝率（実取引移行条件はTier0のみで判定）
    from core.config import TIER0_SYMBOLS, VP_TIER1_SYMBOLS
    _tier0_closed = [t for t in closed if t["symbol"] in TIER0_SYMBOLS]
    _tier1_closed = [t for t in closed if t["symbol"] in VP_TIER1_SYMBOLS]
    _tier0_wins = sum(1 for t in _tier0_closed if t["pnl_pct"] > 0)
    _tier1_wins = sum(1 for t in _tier1_closed if t["pnl_pct"] > 0)
    _tier0_acc = (_tier0_wins / len(_tier0_closed) * 100) if _tier0_closed else 0.0
    _tier1_acc = (_tier1_wins / len(_tier1_closed) * 100) if _tier1_closed else 0.0
    if _tier0_closed:
        print(f"  🏦 Tier0 (BTC/ETH): {len(_tier0_closed)}件 | 勝率: {_tier0_acc:.1f}%")
    if _tier1_closed:
        print(f"  🪙 Tier1 (VP): {len(_tier1_closed)}件 | 勝率: {_tier1_acc:.1f}%")

    # 保有中ポジションの含み損益（参考情報）
    open_summary = []
    for symbol, buy_list in open_buys.items():
        current_data = MarketData.fetch_token_data(symbol)
        if current_data and current_data.get("status") == "success":
            current_price = float(current_data.get("priceUsd", 0.0))
            for b in buy_list:
                if current_price > 0 and b["price"] > 0:
                    pnl_pct = (current_price - b["price"]) / b["price"] * 100
                    open_summary.append({
                        "symbol": symbol,
                        "entry_price": b["price"],
                        "current_price": current_price,
                        "amount_usd": b["amount_usd"],
                        "pnl_pct": round(pnl_pct, 2)
                    })

    # empyricalで多次元指標（決済済み取引ベース）
    advanced_metrics = {}
    if HAS_EMPYRICAL and closed_total >= 3:
        try:
            returns = np.array([t["pnl_pct"] / 100 for t in closed])
            advanced_metrics = {
                "sortino_ratio": round(float(empyrical.sortino_ratio(returns) or 0), 3),
                "max_drawdown":  round(float(empyrical.max_drawdown(returns) or 0), 3),
                "calmar_ratio":  round(float(empyrical.calmar_ratio(returns) or 0), 3),
                "annual_return": round(float(empyrical.annual_return(returns) or 0), 3),
                "omega_ratio":   round(float(empyrical.omega_ratio(returns) or 0), 3),
            }
            print(f"  📈 Sortino: {advanced_metrics['sortino_ratio']} | MaxDD: {advanced_metrics['max_drawdown']:.1%} | Calmar: {advanced_metrics['calmar_ratio']}")
        except Exception as _e:
            print(f"  ⚠️ empyrical計算スキップ: {_e}")

    board_data = {
        "accuracy_score": round(closed_accuracy, 2),
        "total_evaluated_trades": closed_total,
        "tier0_accuracy": round(_tier0_acc, 2),
        "tier0_trades": len(_tier0_closed),
        "tier1_accuracy": round(_tier1_acc, 2),
        "tier1_trades": len(_tier1_closed),
        "open_positions_count": sum(len(v) for v in open_buys.values()),
        "recent_performance": closed[-5:] if closed else [],
        "open_positions": open_summary[-5:],
        "last_evaluated": datetime.now().isoformat(),
        "advanced_metrics": advanced_metrics
    }

    NeoBlackboard.update("performance_summary", board_data)
    print(f"✅ Performance Sync Complete: Closed Accuracy {closed_accuracy:.2f}% ({closed_total} closed trades, {sum(len(v) for v in open_buys.values())} open)")

    if send_dashboard:
        try:
            from tools.discord_reporter import DiscordReporter
            DiscordReporter.send_performance_dashboard(
                accuracy=round(closed_accuracy, 2),
                total_trades=closed_total,
                recent_performance=closed,
                win_count=closed_wins
            )
        except Exception as e:
            print(f"⚠️ Dashboard送信失敗: {e}")


if __name__ == "__main__":
    evaluate_performance()
