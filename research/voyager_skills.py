"""
Voyager — 成功パターンのスキル化（v6.5i）

取引の成功/失敗パターンを抽出し、ChromaDBにスキルとして保存。
Council判断時に類似パターンを参照して意思決定の質を向上させる。
"""
import sys; sys.path.insert(0, '.')
import json
from datetime import datetime, timezone
from core.memory_db import NeoMemoryDB

SKILL_TAG = "voyager_skill"


def extract_skills_from_h2():
    """H.2分析結果からスキルパターンを抽出"""
    from research.h2_trade_analysis import get_clean_pairs
    import pandas as pd

    pairs, _, _ = get_clean_pairs()
    if len(pairs) < 10:
        return []

    df = pd.DataFrame(pairs)
    df['buy_hour'] = pd.to_datetime(df['buy_ts']).dt.hour
    skills = []

    # スキル1: 時間帯別パターン
    for label, hours, tz_name in [
        ('アジア時間BUY', range(0, 9), 'Asia'),
        ('欧州時間BUY', range(9, 17), 'EU'),
        ('米国時間BUY', range(17, 24), 'US'),
    ]:
        hd = df[df['buy_hour'].isin(hours)]
        if len(hd) >= 3:
            wr = (hd['result'] == 'win').mean() * 100
            avg_pnl = hd['pnl_pct_after_fee'].mean()
            skills.append({
                "skill_name": f"{tz_name.lower()}_session_pattern",
                "pattern": f"{label}の勝率パターン",
                "win_rate": round(wr, 1),
                "avg_pnl": round(avg_pnl, 2),
                "sample_size": len(hd),
                "conditions": {"timezone": tz_name},
                "recommendation": f"{label}: 勝率{wr:.0f}% 平均損益{avg_pnl:+.2f}%",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

    # スキル2: SELL理由別パターン
    for reason_key in ['Stop Loss', 'RSI', 'Trailing', 'Time']:
        matched = df[df['sell_reason'].str.contains(reason_key, case=False, na=False)]
        if len(matched) >= 3:
            wr = (matched['result'] == 'win').mean() * 100
            avg_pnl = matched['pnl_pct_after_fee'].mean()
            skills.append({
                "skill_name": f"{reason_key.lower().replace(' ', '_')}_exit_pattern",
                "pattern": f"{reason_key}出口の勝率パターン",
                "win_rate": round(wr, 1),
                "avg_pnl": round(avg_pnl, 2),
                "sample_size": len(matched),
                "conditions": {"exit_type": reason_key},
                "recommendation": f"{reason_key}出口: 勝率{wr:.0f}% 平均損益{avg_pnl:+.2f}%",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

    # スキル3: 銘柄別パターン
    for sym in ['VIRTUAL', 'ETH', 'BTC']:
        sd = df[df['symbol'] == sym]
        if len(sd) >= 3:
            wr = (sd['result'] == 'win').mean() * 100
            avg_pnl = sd['pnl_pct_after_fee'].mean()
            skills.append({
                "skill_name": f"{sym.lower()}_trade_pattern",
                "pattern": f"{sym}取引の勝率パターン",
                "win_rate": round(wr, 1),
                "avg_pnl": round(avg_pnl, 2),
                "sample_size": len(sd),
                "conditions": {"symbol": sym},
                "recommendation": f"{sym}: 勝率{wr:.0f}% 平均損益{avg_pnl:+.2f}%",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

    return skills


def save_skills_to_memory(skills):
    """スキルをChromaDBに保存"""
    mem = NeoMemoryDB()
    saved = 0
    for skill in skills:
        doc_text = f"Voyager Skill: {skill['skill_name']} — {skill['recommendation']}"
        metadata = {
            "source": "voyager_auto",
            "category": "voyager_skill",
            "tier": "2",
            "tag": f"voyager,{skill['skill_name']},{SKILL_TAG}",
            "win_rate": str(skill['win_rate']),
            "sample_size": str(skill['sample_size']),
        }
        mem.store(doc_text, metadata=metadata)
        saved += 1
    return saved


def get_relevant_skills(symbol=None, timezone_label=None):
    """Council判断時に関連スキルを参照（銘柄フィルタ付き）"""
    mem = NeoMemoryDB()
    results = mem.recall_by_tags(SKILL_TAG, n_results=10)
    if not symbol or not results:
        return results
    # 銘柄別スキルは該当銘柄のみ、汎用スキル（出口パターン等）は全て返す
    sym_upper = symbol.split('/')[0].strip().upper()
    filtered = []
    for r in results:
        doc_text = r if isinstance(r, str) else r.get('document', r.get('text', ''))
        # 銘柄固有スキル（_trade_pattern）は該当銘柄のみ通す
        if '_trade_pattern' in str(doc_text):
            if sym_upper.lower() in str(doc_text).lower():
                filtered.append(r)
        else:
            # 汎用スキル（出口パターン、時間帯等）は全て通す
            filtered.append(r)
    return filtered if filtered else results


def run_voyager_update():
    """Nightly実行用: スキル抽出・保存"""
    skills = extract_skills_from_h2()
    if skills:
        saved = save_skills_to_memory(skills)
        print(f"✅ Voyager: {saved}件のスキルをChromaDBに保存")
        for s in skills:
            print(f"  📌 {s['skill_name']}: 勝率{s['win_rate']}% ({s['sample_size']}件)")
    else:
        print("⚠️ Voyager: スキル抽出対象データ不足")
    return skills


if __name__ == '__main__':
    run_voyager_update()
