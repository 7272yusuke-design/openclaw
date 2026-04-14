"""
EvolveR Agent — 自律ルール発見・適用エンジン (E3)

既存のevolver_rules.pyの統計ルールをscoring_adjustments.jsonに変換し、
Phase 4bが起動時に動的読み込みして自動適用する。

安全装置:
- 1ルール最大 ±15
- 全ルール合計 ±30
- 最小サンプルサイズ未満は無視
- 有効期限切れルールは無視
"""
import sys; sys.path.insert(0, '.')
import json
import os
from datetime import datetime, timezone, timedelta

OUTPUT_PATH = "vault/evolver/scoring_adjustments.json"
DEFAULT_EXPIRY_DAYS = 30
MIN_SAMPLE_SIZE = 3


def _get_fifo_closed_trades():
    """EvaluatorのFIFOロット方式で決済済み取引を取得（最も正確）"""
    import pandas as pd
    from orchestration.performance_evaluator import _parse_wallet_history, _calc_closed_trades
    from tools.paper_wallet import PaperWallet
    buys, sells = _parse_wallet_history()
    closed, _ = _calc_closed_trades(buys, sells)
    if not closed:
        return pd.DataFrame()
    # historyからbuy_hourを復元するためtimestamp情報を付加
    pw = PaperWallet()
    hist = pw.state.get("history", [])
    buy_ts_map = {}  # symbol -> [timestamps] (FIFO順)
    sell_ts_map = {}
    sell_reason_map = {}
    for h in hist:
        sym = h.get("symbol", "").split("/")[0].strip().upper()
        if h["action"] == "BUY":
            buy_ts_map.setdefault(sym, []).append(h.get("timestamp", ""))
        elif h["action"] == "SELL":
            sell_ts_map.setdefault(sym, []).append(h.get("timestamp", ""))
            sell_reason_map.setdefault(sym, []).append(h.get("reason", ""))
    # closedにbuy_ts/sell_reason付加
    sym_buy_idx = {}
    sym_sell_idx = {}
    for c in closed:
        sym = c["symbol"]
        bi = sym_buy_idx.get(sym, 0)
        si = sym_sell_idx.get(sym, 0)
        c["buy_ts"] = buy_ts_map.get(sym, [""])[min(bi, len(buy_ts_map.get(sym, []))-1)] if buy_ts_map.get(sym) else ""
        c["sell_reason"] = sell_reason_map.get(sym, [""])[min(si, len(sell_reason_map.get(sym, []))-1)] if sell_reason_map.get(sym) else ""
        c["result"] = "win" if c["pnl_pct"] > 0 else "loss"
        sym_buy_idx[sym] = bi + 1
        # sell_timeが変わったらsellインデックスも進める
        if si < len(sell_ts_map.get(sym, [])) - 1:
            if c.get("sell_time", "") != sell_ts_map.get(sym, [""])[si]:
                sym_sell_idx[sym] = si + 1
    df = pd.DataFrame(closed)
    if "buy_ts" in df.columns and len(df) > 0:
        df["buy_hour"] = pd.to_datetime(df["buy_ts"], errors="coerce").dt.hour.fillna(0).astype(int)
    else:
        df["buy_hour"] = 0
    return df


def generate_scoring_adjustments():
    """EvolveRルール + FIFOロット統計からscoring_adjustments.jsonを自動生成"""
    import pandas as pd

    df = _get_fifo_closed_trades()
    if len(df) < 10:
        print("⚠️ [E3] データ不足（10ペア未満）: scoring_adjustments生成スキップ")
        return []
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=DEFAULT_EXPIRY_DAYS)).isoformat()
    adjustments = []

    # --- ルール1: 時間帯別勝率 ---
    for label, hours, tz_match in [
        ('Asia', range(0, 9), 'Asia'),
        ('EU', range(9, 17), 'EU'),
        ('US', range(17, 24), 'US'),
    ]:
        hd = df[df['buy_hour'].isin(hours)]
        if len(hd) >= MIN_SAMPLE_SIZE:
            wr = (hd['result'] == 'win').mean() * 100
            if wr >= 70:
                adj = min(10, int((wr - 60) / 2))
                adjustments.append({
                    "rule_id": f"R_tz_{tz_match.lower()}_high",
                    "condition": {"type": "timezone", "match": tz_match},
                    "adjustment": adj,
                    "evidence": f"{len(hd)}件中{(hd['result']=='win').sum()}勝({wr:.0f}%)",
                    "min_sample_size": MIN_SAMPLE_SIZE,
                    "actual_sample_size": len(hd),
                    "expires_at": expires,
                })
            elif wr <= 40:
                adj = max(-10, -int((50 - wr) / 2))
                adjustments.append({
                    "rule_id": f"R_tz_{tz_match.lower()}_low",
                    "condition": {"type": "timezone", "match": tz_match},
                    "adjustment": adj,
                    "evidence": f"{len(hd)}件中{(hd['result']=='win').sum()}勝({wr:.0f}%)",
                    "min_sample_size": MIN_SAMPLE_SIZE,
                    "actual_sample_size": len(hd),
                    "expires_at": expires,
                })

    # --- ルール2: 銘柄別勝率 ---
    for sym in df['symbol'].unique():
        sd = df[df['symbol'] == sym]
        if len(sd) >= MIN_SAMPLE_SIZE:
            wr = (sd['result'] == 'win').mean() * 100
            if wr >= 65:
                adj = min(10, int((wr - 60) / 2))
                adjustments.append({
                    "rule_id": f"R_sym_{sym.lower()}_high",
                    "condition": {"type": "symbol", "match": sym},
                    "adjustment": adj,
                    "evidence": f"{len(sd)}件中{(sd['result']=='win').sum()}勝({wr:.0f}%)",
                    "min_sample_size": MIN_SAMPLE_SIZE,
                    "actual_sample_size": len(sd),
                    "expires_at": expires,
                })
            elif wr <= 45:
                adj = max(-10, -int((50 - wr) / 2))
                adjustments.append({
                    "rule_id": f"R_sym_{sym.lower()}_low",
                    "condition": {"type": "symbol", "match": sym},
                    "adjustment": adj,
                    "evidence": f"{len(sd)}件中{(sd['result']=='win').sum()}勝({wr:.0f}%)",
                    "min_sample_size": MIN_SAMPLE_SIZE,
                    "actual_sample_size": len(sd),
                    "expires_at": expires,
                })

    # --- ルール3: BT confidence別 ---
    for bt_val in ["HIGH", "LOW", "NONE"]:
        bd = df[df.get('bt_confidence', pd.Series(dtype=str)) == bt_val] if 'bt_confidence' in df.columns else pd.DataFrame()
        if len(bd) >= MIN_SAMPLE_SIZE:
            wr = (bd['result'] == 'win').mean() * 100
            if bt_val == "NONE" and wr <= 40:
                adjustments.append({
                    "rule_id": "R_bt_none_low",
                    "condition": {"type": "bt_confidence", "match": "NONE"},
                    "adjustment": max(-10, -int((50 - wr) / 2)),
                    "evidence": f"BT=NONE: {len(bd)}件中{(bd['result']=='win').sum()}勝({wr:.0f}%)",
                    "min_sample_size": MIN_SAMPLE_SIZE,
                    "actual_sample_size": len(bd),
                    "expires_at": expires,
                })

    # --- ルール4: 損大利小パターン ---
    win_df = df[df['result'] == 'win']
    loss_df = df[df['result'] == 'loss']
    if len(win_df) >= 3 and len(loss_df) >= 3:
        avg_win = win_df['pnl_pct'].mean()
        avg_loss = loss_df['pnl_pct'].mean()
        wl_ratio = abs(avg_win) / abs(avg_loss) if avg_loss != 0 else 999
        if wl_ratio < 0.8:
            adjustments.append({
                "rule_id": "R_wl_ratio_bad",
                "condition": {"type": "sentiment_range", "min": -1.0, "max": -0.3},
                "adjustment": -5,
                "evidence": f"W/L比={wl_ratio:.2f} (Win{avg_win:+.2f}% / Loss{avg_loss:+.2f}%)",
                "min_sample_size": MIN_SAMPLE_SIZE,
                "actual_sample_size": len(df),
                "expires_at": expires,
            })

    # --- 保存 ---
    output = {
        "adjustments": adjustments,
        "generated_at": now.isoformat(),
        "total_adjustments": len(adjustments),
        "source_pairs": len(df),
    }
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ [E3] scoring_adjustments.json生成: {len(adjustments)}ルール (from {len(df)} pairs)")
    for a in adjustments:
        print(f"  {'🟢' if a['adjustment']>0 else '🔴'} [{a['rule_id']}] {a['adjustment']:+d} — {a['evidence']}")

    return adjustments


if __name__ == '__main__':
    generate_scoring_adjustments()
