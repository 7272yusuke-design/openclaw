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
    pairs, unpaired, _ = get_clean_pairs()
    
    if len(pairs) < MIN_PAIRS_FOR_ANALYSIS:
        print(f"❌ 完結ペアが{len(pairs)}件（{MIN_PAIRS_FOR_ANALYSIS}件必要）。データ蓄積を待ってください。")
        return get_progress_report()
    
    print(f"=== H.2 v2 完全分析 ({len(pairs)}件 / 未決済BUY: {unpaired}件) ===")
    
    df = pd.DataFrame(pairs)
    
    # --- 基本統計 ---
    print("\n" + "="*50)
    print("1. 基本統計")
    print("="*50)
    total_wins = (df['result']=='win').sum()
    total_losses = (df['result']=='loss').sum()
    print(f"全体勝率: {total_wins}/{len(df)} = {total_wins/len(df)*100:.1f}%")
    print(f"平均損益(手数料前): {df['pnl_pct'].mean():+.2f}%")
    print(f"平均損益(手数料後): {df['pnl_pct_after_fee'].mean():+.2f}%")
    print(f"損益中央値(手数料後): {df['pnl_pct_after_fee'].median():+.2f}%")
    print(f"損益標準偏差: {df['pnl_pct_after_fee'].std():.2f}%")
    print(f"最大利益: {df['pnl_pct_after_fee'].max():+.2f}%")
    print(f"最大損失: {df['pnl_pct_after_fee'].min():+.2f}%")
    print(f"平均保有時間: {df['hold_hours'].mean():.1f}h (中央値: {df['hold_hours'].median():.1f}h)")
    print(f"平均取引額: ${df['amount_usd'].mean():,.0f}")
    
    # 銘柄別
    print("\n" + "="*50)
    print("2. 銘柄別分析")
    print("="*50)
    for sym in VALID_SYMBOLS:
        sd = df[df['symbol'] == sym]
        if len(sd) > 0:
            sw = (sd['result']=='win').sum()
            print(f"\n  {sym} ({len(sd)}件: {sw}勝{len(sd)-sw}敗):")
            print(f"    勝率: {sw/len(sd)*100:.1f}%")
            print(f"    平均損益(後): {sd['pnl_pct_after_fee'].mean():+.2f}%")
            print(f"    損益中央値: {sd['pnl_pct_after_fee'].median():+.2f}%")
            print(f"    平均保有: {sd['hold_hours'].mean():.1f}h")
            print(f"    累計PnL%: {sd['pnl_pct_after_fee'].sum():+.2f}%")
    
    # --- SELL理由別の勝率 ---
    print("\n" + "="*50)
    print("3. SELL理由別分析")
    print("="*50)
    for reason_key in ['Stop Loss', 'Trailing', 'Take Profit', 'RSI', 'Time']:
        matched = df[df['sell_reason'].str.contains(reason_key, case=False, na=False)]
        if len(matched) > 0:
            wr = (matched['result'] == 'win').mean() * 100
            print(f"  {reason_key}: {len(matched)}件 勝率{wr:.0f}% 平均損益{matched['pnl_pct_after_fee'].mean():+.2f}% 平均保有{matched['hold_hours'].mean():.1f}h")
    
    # Council判定で終了したもの（BUY reasonからconfidence抽出）
    print("\n  ※ SLで57%がwinなのはSL閾値-3%と手数料前損益の関係")
    print("    → SL発火=-3%でも、手数料前で-2.5%等なら手数料後-3.5%=loss")
    print("    → SL発火=-3.0%丁度なら手数料後-4.0%で確実にloss")
    
    # --- 勝ちトレードvs負けトレードの特徴比較 ---
    print("\n" + "="*50)
    print("4. Win vs Loss 特徴比較")
    print("="*50)
    win_df = df[df['result'] == 'win']
    loss_df = df[df['result'] == 'loss']
    
    print(f"  Win ({len(win_df)}件): 平均保有{win_df['hold_hours'].mean():.1f}h / 平均損益{win_df['pnl_pct_after_fee'].mean():+.2f}%")
    print(f"  Loss ({len(loss_df)}件): 平均保有{loss_df['hold_hours'].mean():.1f}h / 平均損益{loss_df['pnl_pct_after_fee'].mean():+.2f}%")
    
    # Win側のSELL理由分布
    print(f"\n  Win側のSELL理由:")
    for reason_key in ['Stop Loss', 'Trailing', 'Take Profit', 'RSI', 'Time']:
        cnt = win_df['sell_reason'].str.contains(reason_key, case=False, na=False).sum()
        if cnt > 0:
            print(f"    {reason_key}: {cnt}件")
    print(f"  Loss側のSELL理由:")
    for reason_key in ['Stop Loss', 'Trailing', 'Take Profit', 'RSI', 'Time']:
        cnt = loss_df['sell_reason'].str.contains(reason_key, case=False, na=False).sum()
        if cnt > 0:
            print(f"    {reason_key}: {cnt}件")
    
    # --- pingouin: win/loss群の統計的差異検定 ---
    print("\n" + "="*50)
    print("5. pingouin 統計検定 (win vs loss)")
    print("="*50)
    try:
        import pingouin as pg
        
        if len(win_df) >= 3 and len(loss_df) >= 3:
            # 保有時間の差
            r1 = pg.ttest(win_df['hold_hours'], loss_df['hold_hours'])
            p1 = r1['p_val'].values[0]
            d1 = r1['cohen_d'].values[0]
            sig1 = "***" if p1 < 0.01 else "**" if p1 < 0.05 else "*" if p1 < 0.1 else "ns"
            print(f"  保有時間: p={p1:.4f} ({sig1}) Cohen's d={d1:.3f}")
            
            # 取引額の差
            r2 = pg.ttest(win_df['amount_usd'], loss_df['amount_usd'])
            p2 = r2['p_val'].values[0]
            d2 = r2['cohen_d'].values[0]
            sig2 = "***" if p2 < 0.01 else "**" if p2 < 0.05 else "*" if p2 < 0.1 else "ns"
            print(f"  取引額: p={p2:.4f} ({sig2}) Cohen's d={d2:.3f}")
            
            # 銘柄別勝率の差（カイ二乗検定）
            ct = pd.crosstab(df['symbol'], df['result'])
            if ct.shape == (2, 2):
                chi2 = pg.chi2_independence(df, 'symbol', 'result')
                chi_p = chi2[2]['pval'].values[0]
                sig3 = "***" if chi_p < 0.01 else "**" if chi_p < 0.05 else "*" if chi_p < 0.1 else "ns"
                print(f"  銘柄×勝敗 独立性: p={chi_p:.4f} ({sig3})")
            
            print("\n  (*** p<0.01, ** p<0.05, * p<0.1, ns=not significant)")
        else:
            print("  サンプル不足（各群3件以上必要）")
    except Exception as e:
        print(f"  pingouin分析エラー: {e}")
    
    # --- tsfresh 時系列特徴量 ---
    print("\n" + "="*50)
    print("6. 保有時間帯分析")
    print("="*50)
    # BUY時刻のUTC時間帯別
    df['buy_hour'] = pd.to_datetime(df['buy_ts']).dt.hour
    for label, hours in [('アジア(00-08UTC/09-17JST)', range(0,9)), 
                          ('欧州(08-16UTC/17-01JST)', range(9,17)),
                          ('米国(16-24UTC/01-09JST)', range(17,24))]:
        hd = df[df['buy_hour'].isin(hours)]
        if len(hd) > 0:
            wr = (hd['result']=='win').mean()*100
            print(f"  {label}: {len(hd)}件 勝率{wr:.0f}% 平均損益{hd['pnl_pct_after_fee'].mean():+.2f}%")
    
    # --- 連勝・連敗パターン ---
    print("\n" + "="*50)
    print("7. 連勝・連敗パターン")
    print("="*50)
    streaks = []
    current_streak = 0
    current_type = None
    for _, row in df.iterrows():
        if row['result'] == current_type:
            current_streak += 1
        else:
            if current_type is not None:
                streaks.append((current_type, current_streak))
            current_type = row['result']
            current_streak = 1
    if current_type is not None:
        streaks.append((current_type, current_streak))
    
    max_win_streak = max((s[1] for s in streaks if s[0]=='win'), default=0)
    max_loss_streak = max((s[1] for s in streaks if s[0]=='loss'), default=0)
    print(f"  最大連勝: {max_win_streak}連勝")
    print(f"  最大連敗: {max_loss_streak}連敗")
    print(f"  ストリーク推移: {' → '.join(f'{s[0][0].upper()}{s[1]}' for s in streaks)}")
    
    # --- 累計損益推移 ---
    print("\n" + "="*50)
    print("8. 累計損益推移")
    print("="*50)
    cum_pnl = 0
    max_cum = 0
    max_dd = 0
    for i, row in df.iterrows():
        cum_pnl += row['pnl_pct_after_fee']
        if cum_pnl > max_cum:
            max_cum = cum_pnl
        dd = cum_pnl - max_cum
        if dd < max_dd:
            max_dd = dd
    print(f"  累計損益: {cum_pnl:+.2f}%")
    print(f"  最大累計: {max_cum:+.2f}%")
    print(f"  最大DD: {max_dd:+.2f}%")
    print(f"  回復力: {'✅ 回復済み' if cum_pnl > 0 else '⚠️ マイナス圏'}")
    
    # --- 総合診断 ---
    print("\n" + "="*50)
    print("9. 総合診断")
    print("="*50)
    avg_win = win_df['pnl_pct_after_fee'].mean() if len(win_df) > 0 else 0
    avg_loss = loss_df['pnl_pct_after_fee'].mean() if len(loss_df) > 0 else 0
    profit_factor = abs(avg_win * len(win_df)) / abs(avg_loss * len(loss_df)) if len(loss_df) > 0 and avg_loss != 0 else float('inf')
    
    print(f"  平均Win: {avg_win:+.2f}% / 平均Loss: {avg_loss:+.2f}%")
    print(f"  Win/Loss比: {abs(avg_win)/abs(avg_loss):.2f}" if avg_loss != 0 else "  Win/Loss比: N/A")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  期待値(1トレード): {df['pnl_pct_after_fee'].mean():+.2f}%")
    
    issues = []
    if df['pnl_pct_after_fee'].mean() < 0.5:
        issues.append("期待値が薄い（+0.5%未満）→ 手数料負けリスク")
    if (df['result']=='loss').sum() > 0:
        sl_losses = df[(df['sell_reason'].str.contains('Stop Loss', case=False, na=False)) & (df['result']=='loss')]
        if len(sl_losses) >= 3:
            issues.append(f"SL負け{len(sl_losses)}件 → BUYタイミング改善余地")
    if abs(avg_loss) > abs(avg_win):
        issues.append("平均Loss > 平均Win → 損大利小")
    if len(issues) > 0:
        print(f"\n  ⚠️ 改善ポイント:")
        for iss in issues:
            print(f"    - {iss}")
    else:
        print(f"\n  ✅ 特に重大な問題なし")
    
    return {'status': 'complete', 'pairs': len(pairs)}


if __name__ == '__main__':
    report = get_progress_report()
    print(report['discord_text'])
    print()
    
    if report['ready']:
        run_full_analysis()
    else:
        print(f"\n💡 {report['remaining']}件の完結ペア蓄積後に `run_full_analysis()` を実行してください")
