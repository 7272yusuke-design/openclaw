"""
H.2 v2 — BUY→SELL完結サイクル分析
tsfresh + pingouin による統計分析

前提条件:
  - v6.3以降のクリーンデータ（CLEAN_START以降・Tier1のみ）
  - 完結ペア20件以上で統計分析を実行
  - 20件未満の場合は進捗レポートのみ返却
"""
import sys; sys.path.insert(0, '.')
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict
from tools.paper_wallet import PaperWallet

# === 設定 ===
CLEAN_START = "2026-03-21T00:00"  # v6.3稼働開始日
VALID_SYMBOLS = ['VIRTUAL', 'AIXBT']
MIN_PAIRS_FOR_ANALYSIS = 20


def get_clean_pairs():
    """v6.3以降のクリーンなBUY→SELLペアを組み立て"""
    w = PaperWallet()
    history = w.state.get('history', [])
    
    # フィルタ: v6.3以降 + Tier1のみ
    clean = [h for h in history 
             if h['timestamp'] >= CLEAN_START 
             and h['symbol'] in VALID_SYMBOLS]
    
    # FIFO方式でペア組み立て
    buys = defaultdict(list)
    pairs = []
    unpaired_buys = 0
    
    for h in clean:
        sym = h['symbol']
        if h['action'] == 'BUY':
            buys[sym].append(h)
        elif h['action'] == 'SELL' and buys[sym]:
            buy = buys[sym].pop(0)
            pnl_pct = (h['price'] - buy['price']) / buy['price'] * 100
            
            # 手数料考慮後の損益（BUY時-0.5%, SELL時-0.5%）
            pnl_pct_after_fee = pnl_pct - 1.0  # 概算: 往復1%
            
            pairs.append({
                'symbol': sym,
                'buy_ts': buy['timestamp'],
                'sell_ts': h['timestamp'],
                'buy_price': buy['price'],
                'sell_price': h['price'],
                'amount_usd': buy['amount_usd'],
                'pnl_pct': pnl_pct,
                'pnl_pct_after_fee': pnl_pct_after_fee,
                'result': 'win' if pnl_pct_after_fee > 0 else 'loss',
                'buy_reason': buy.get('reason', ''),
                'sell_reason': h.get('reason', ''),
                'hold_hours': _calc_hold_hours(buy['timestamp'], h['timestamp']),
            })
    
    unpaired_buys = sum(len(v) for v in buys.values())
    return pairs, unpaired_buys, len(clean)


def _calc_hold_hours(buy_ts, sell_ts):
    """保有時間を計算"""
    try:
        buy_dt = datetime.fromisoformat(buy_ts)
        sell_dt = datetime.fromisoformat(sell_ts)
        return (sell_dt - buy_dt).total_seconds() / 3600
    except:
        return 0.0


def get_progress_report():
    """
    進捗レポート（Nightly用）
    完結ペア数と分析可能までの残り件数を返す
    """
    pairs, unpaired, total_clean = get_clean_pairs()
    
    completed = len(pairs)
    remaining = max(0, MIN_PAIRS_FOR_ANALYSIS - completed)
    
    # 銘柄別
    sym_counts = {}
    sym_wins = {}
    for sym in VALID_SYMBOLS:
        sp = [p for p in pairs if p['symbol'] == sym]
        sw = [p for p in sp if p['result'] == 'win']
        sym_counts[sym] = len(sp)
        sym_wins[sym] = len(sw)
    
    lines = [f"📈 **取引分析進捗** (v6.3以降)"]
    lines.append(f"完結ペア: **{completed}/{MIN_PAIRS_FOR_ANALYSIS}件** (H.2分析まであと{remaining}件)")
    lines.append(f"未決済BUY: {unpaired}件 / クリーン履歴: {total_clean}件")
    
    if completed > 0:
        total_wins = sum(1 for p in pairs if p['result'] == 'win')
        win_rate = total_wins / completed * 100
        avg_pnl = sum(p['pnl_pct_after_fee'] for p in pairs) / completed
        lines.append(f"勝率: {win_rate:.1f}% / 平均損益: {avg_pnl:+.2f}% (手数料後)")
        
        for sym in VALID_SYMBOLS:
            if sym_counts[sym] > 0:
                sr = sym_wins[sym] / sym_counts[sym] * 100
                lines.append(f"  {sym}: {sym_counts[sym]}件 勝率{sr:.0f}%")
    
    return {
        'completed': completed,
        'remaining': remaining,
        'ready': completed >= MIN_PAIRS_FOR_ANALYSIS,
        'discord_text': "\n".join(lines),
    }


def run_full_analysis():
    """
    完全分析（20件以上で実行）
    tsfresh + pingouin による統計分析
    """
    pairs, _, _ = get_clean_pairs()
    
    if len(pairs) < MIN_PAIRS_FOR_ANALYSIS:
        print(f"❌ 完結ペアが{len(pairs)}件（{MIN_PAIRS_FOR_ANALYSIS}件必要）。データ蓄積を待ってください。")
        return get_progress_report()
    
    print(f"=== H.2 v2 完全分析 ({len(pairs)}件) ===")
    
    df = pd.DataFrame(pairs)
    
    # --- 基本統計 ---
    print("\n--- 基本統計 ---")
    print(f"全体勝率: {(df['result']=='win').mean()*100:.1f}%")
    print(f"平均損益(手数料後): {df['pnl_pct_after_fee'].mean():+.2f}%")
    print(f"平均保有時間: {df['hold_hours'].mean():.1f}h")
    
    for sym in VALID_SYMBOLS:
        sd = df[df['symbol'] == sym]
        if len(sd) > 0:
            print(f"\n  {sym} ({len(sd)}件):")
            print(f"    勝率: {(sd['result']=='win').mean()*100:.1f}%")
            print(f"    平均損益: {sd['pnl_pct_after_fee'].mean():+.2f}%")
            print(f"    平均保有時間: {sd['hold_hours'].mean():.1f}h")
    
    # --- pingouin: win/loss群の統計的差異検定 ---
    print("\n--- pingouin 統計検定 ---")
    try:
        import pingouin as pg
        
        win_df = df[df['result'] == 'win']
        loss_df = df[df['result'] == 'loss']
        
        if len(win_df) >= 3 and len(loss_df) >= 3:
            # 保有時間の差
            result = pg.ttest(win_df['hold_hours'], loss_df['hold_hours'])
            print(f"保有時間 win vs loss: p={result['p-val'].values[0]:.4f} (Cohen's d={result['cohen-d'].values[0]:.3f})")
            
            # 取引額の差
            result2 = pg.ttest(win_df['amount_usd'], loss_df['amount_usd'])
            print(f"取引額 win vs loss: p={result2['p-val'].values[0]:.4f}")
        else:
            print("サンプル不足（各群3件以上必要）")
    except Exception as e:
        print(f"pingouin分析エラー: {e}")
    
    # --- SELL理由別の勝率 ---
    print("\n--- SELL理由別 ---")
    for reason_key in ['Stop Loss', 'Take Profit', 'RSI', 'Time']:
        matched = df[df['sell_reason'].str.contains(reason_key, case=False, na=False)]
        if len(matched) > 0:
            wr = (matched['result'] == 'win').mean() * 100
            print(f"  {reason_key}: {len(matched)}件 勝率{wr:.0f}% 平均損益{matched['pnl_pct_after_fee'].mean():+.2f}%")
    
    return {'status': 'complete', 'pairs': len(pairs)}


if __name__ == '__main__':
    report = get_progress_report()
    print(report['discord_text'])
    print()
    
    if report['ready']:
        run_full_analysis()
    else:
        print(f"\n💡 {report['remaining']}件の完結ペア蓄積後に `run_full_analysis()` を実行してください")
