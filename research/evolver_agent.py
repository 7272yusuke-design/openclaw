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

    # --- ルール1: 時間帯別勝率 — v6.5bcで生成停止 ---
    # 理由: Phase 4b の TZ_SCORE_* (固定値: Asia-10/EU+10/US-3) と二重計上になる
    # trinity_council.py L849 で `type=timezone` は適用側でも問答無用にスキップされていた
    # → 生成しても適用されない無駄パイプラインだったため生成側で停止
    # V2 EvolveR で「Phase 4b 固定テーブルそのものをEvolveRが自律調整」する方向に発展予定
    # 詳細: docs/v2_evolver_design.md

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

    # --- ルール4: 損大利小パターン — v6.5bcで生成停止 ---
    # 理由: Phase 4b でセンチメントは既に直接反映されており二重計上になる
    # trinity_council.py L852 で `type=sentiment_range` は適用側でも問答無用にスキップされていた
    # また condition の値 (-1.0〜-0.3) が「W/L比悪化」というトリガーと意味的に一致しておらず、
    # 「W/L比が悪いときに*全エントリー時*に-5点」という挙動になっていた（設計ミス）
    # V2 EvolveR で「出口戦略（SL/TP幅）の自律調整」として再実装予定
    # 詳細: docs/v2_evolver_design.md

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
