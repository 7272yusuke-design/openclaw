"""
EvolveR — 教訓抽象化エンジン（v6.5i）

個別の取引結果パターンから汎用ルールを自動抽出し、
ChromaDBにTier1教訓として保存。

抽象化の流れ:
  具体的観察 → 統計的検証 → 汎用ルール化 → ChromaDB永久保存
"""
import sys; sys.path.insert(0, '.')
from datetime import datetime, timezone
from core.memory_db import NeoMemoryDB

RULE_TAG = "evolver_rule"


def evolve_rules_from_h2():
    """H.2分析結果から汎用ルールを抽出"""
    from research.h2_trade_analysis import get_clean_pairs
    import pandas as pd

    pairs, _, _ = get_clean_pairs()
    if len(pairs) < 10:
        return []

    df = pd.DataFrame(pairs)
    df['buy_hour'] = pd.to_datetime(df['buy_ts']).dt.hour
    rules = []
    now = datetime.now(timezone.utc).isoformat()

    # ルール1: 損大利小の検知と対策
    win_df = df[df['result'] == 'win']
    loss_df = df[df['result'] == 'loss']
    if len(win_df) > 0 and len(loss_df) > 0:
        avg_win = win_df['pnl_pct_after_fee'].mean()
        avg_loss = loss_df['pnl_pct_after_fee'].mean()
        wl_ratio = abs(avg_win) / abs(avg_loss) if avg_loss != 0 else 999
        if wl_ratio < 1.0:
            rules.append({
                "rule_id": "R001_loss_larger_than_win",
                "rule": f"損大利小パターン検出: W/L比={wl_ratio:.2f}。SL幅の縮小またはTP目標の引き上げが必要",
                "evidence": f"平均Win={avg_win:+.2f}% vs 平均Loss={avg_loss:+.2f}% (N={len(df)})",
                "action": "RSI出口の利益閾値を引き上げ済み(+0.5%→+1.5%)。トレーリングTPの発火を待つ",
                "severity": "high",
                "updated_at": now,
            })

    # ルール2: 時間帯ルール
    for label, hours, tz in [('アジア', range(0, 9), 'Asia'), ('欧州', range(9, 17), 'EU')]:
        hd = df[df['buy_hour'].isin(hours)]
        if len(hd) >= 3:
            wr = (hd['result'] == 'win').mean() * 100
            if wr >= 75:
                rules.append({
                    "rule_id": f"R002_{tz.lower()}_high_winrate",
                    "rule": f"{label}時間帯は高勝率({wr:.0f}%)。BUY confidence +10の根拠がある",
                    "evidence": f"{len(hd)}件中{(hd['result']=='win').sum()}勝",
                    "action": "Phase 4bスコアリングテーブルに反映済み",
                    "severity": "info",
                    "updated_at": now,
                })
            elif wr <= 45:
                rules.append({
                    "rule_id": f"R003_{tz.lower()}_low_winrate",
                    "rule": f"{label}時間帯は低勝率({wr:.0f}%)。BUY confidence -10の根拠がある",
                    "evidence": f"{len(hd)}件中{(hd['result']=='win').sum()}勝",
                    "action": "Phase 4bスコアリングテーブルに反映済み",
                    "severity": "warning",
                    "updated_at": now,
                })

    # ルール3: SELL出口の最適戦略
    rsi_exits = df[df['sell_reason'].str.contains('RSI', case=False, na=False)]
    sl_exits = df[df['sell_reason'].str.contains('Stop Loss', case=False, na=False)]
    if len(rsi_exits) >= 3 and len(sl_exits) >= 3:
        rsi_wr = (rsi_exits['result'] == 'win').mean() * 100
        sl_wr = (sl_exits['result'] == 'win').mean() * 100
        if rsi_wr > sl_wr + 10:
            rules.append({
                "rule_id": "R004_rsi_exit_superior",
                "rule": f"RSI出口({rsi_wr:.0f}%)がSL出口({sl_wr:.0f}%)より{rsi_wr-sl_wr:.0f}pp優秀。RSI出口を早期に狙う戦略が有効",
                "evidence": f"RSI: {len(rsi_exits)}件 / SL: {len(sl_exits)}件",
                "action": "RSI出口利益閾値を+1.5%に引き上げ済み。手数料後もプラス確保",
                "severity": "info",
                "updated_at": now,
            })

    # ルール4: ナンピン制限ルール
    from collections import defaultdict
    buy_counts = defaultdict(int)
    for h in df.to_dict('records'):
        buy_counts[h['symbol']] += 1
    max_buys = max(buy_counts.values()) if buy_counts else 0
    if max_buys > 5:
        rules.append({
            "rule_id": "R005_excessive_averaging_down",
            "rule": f"過度なナンピン検出（最大{max_buys}回）。同一ポジションへの集中投資はリスク増大",
            "evidence": f"銘柄別BUY回数: {dict(buy_counts)}",
            "action": "Phase 5にナンピン回数制限(MAX 3回)を実装済み",
            "severity": "high",
            "updated_at": now,
        })

    # ルール5: 保有時間とLossの関係
    if len(win_df) >= 3 and len(loss_df) >= 3:
        win_hold = win_df['hold_hours'].mean()
        loss_hold = loss_df['hold_hours'].mean()
        if loss_hold > win_hold * 1.3:
            rules.append({
                "rule_id": "R006_loss_holds_longer",
                "rule": f"Lossの保有時間({loss_hold:.0f}h)がWin({win_hold:.0f}h)より{loss_hold/win_hold:.1f}倍長い。早期損切りが有効",
                "evidence": f"Win平均{win_hold:.1f}h vs Loss平均{loss_hold:.1f}h",
                "action": "SL -3%は維持。96h時間制約で長期保有を制限",
                "severity": "warning",
                "updated_at": now,
            })

    return rules


def save_rules_to_memory(rules):
    """ルールをChromaDBにTier1として保存"""
    mem = NeoMemoryDB()
    saved = 0
    for rule in rules:
        doc_text = f"EvolveR Rule [{rule['rule_id']}]: {rule['rule']}\n根拠: {rule['evidence']}\n対応: {rule['action']}"
        metadata = {
            "source": "evolver_auto",
            "category": "evolver_rule",
            "tier": "1",
            "tag": f"evolver,{rule['rule_id']},{RULE_TAG}",
            "severity": rule['severity'],
        }
        mem.store(doc_text, metadata=metadata)
        saved += 1
    return saved


def run_evolver_update():
    """Nightly実行用: ルール抽出・保存"""
    rules = evolve_rules_from_h2()
    if rules:
        saved = save_rules_to_memory(rules)
        print(f"✅ EvolveR: {saved}件の汎用ルールを生成")
        for r in rules:
            severity_icon = {"high": "🔴", "warning": "🟡", "info": "🟢"}.get(r['severity'], "⚪")
            print(f"  {severity_icon} [{r['rule_id']}] {r['rule'][:80]}")
    else:
        print("⚠️ EvolveR: ルール生成対象データ不足")
    return rules


if __name__ == '__main__':
    run_evolver_update()
