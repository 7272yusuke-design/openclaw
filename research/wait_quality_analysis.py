"""
WAIT品質検証スクリプト
- ChromaDBのwait_recordを取得
- WAIT判定時の価格から、もしBUYしていたらどうなったかをシミュレーション
- 4h/12h/24h/48h後の価格変動 + TP(+7%)/SL(-3%)ヒット判定
"""
import sys; sys.path.insert(0, '.')
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from core.memory_db import NeoMemoryDB

# === 設定 ===
TP_PCT = 0.07   # +7%
SL_PCT = -0.03  # -3%
TIME_LIMIT_H = 96  # 時間制約
EVAL_WINDOWS = [4, 12, 24, 48]  # 評価時間窓(hours)
TARGET_SYMBOLS = ['VIRTUAL', 'ETH', 'BTC']  # Council対象銘柄に合わせる  # Tier1のみ

def iso_to_epoch_ms(iso_str):
    """ISO文字列→ミリ秒エポック"""
    dt = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def get_prices_after(conn, symbol, start_ms, hours):
    """start_msからhours時間分の価格データを取得"""
    end_ms = start_ms + int(hours * 3600 * 1000)
    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, close FROM prices WHERE symbol=? AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
        (symbol, start_ms, end_ms)
    )
    return cur.fetchall()

def simulate_trade(prices, entry_price):
    """
    仮想BUYした場合のシミュレーション
    Returns: {
        'max_up': 最大上昇率,
        'max_down': 最大下落率,
        'tp_hit': TP到達したか,
        'sl_hit': SL到達したか,
        'tp_first': TPがSLより先にヒットしたか,
        'final_pct': 最終的な損益率,
        'outcome': 'TP' / 'SL' / 'TIME_EXIT' / 'HOLD'
    }
    """
    if not prices:
        return None
    
    max_up = 0.0
    max_down = 0.0
    tp_hit_ts = None
    sl_hit_ts = None
    
    for ts, close in prices:
        pct = (close - entry_price) / entry_price
        max_up = max(max_up, pct)
        max_down = min(max_down, pct)
        
        if pct >= TP_PCT and tp_hit_ts is None:
            tp_hit_ts = ts
        if pct <= SL_PCT and sl_hit_ts is None:
            sl_hit_ts = ts
    
    # 最終価格
    final_pct = (prices[-1][1] - entry_price) / entry_price
    
    # アウトカム判定
    if tp_hit_ts and sl_hit_ts:
        outcome = 'TP' if tp_hit_ts < sl_hit_ts else 'SL'
    elif tp_hit_ts:
        outcome = 'TP'
    elif sl_hit_ts:
        outcome = 'SL'
    else:
        outcome = 'HOLD'
    
    return {
        'max_up': max_up,
        'max_down': max_down,
        'tp_hit': tp_hit_ts is not None,
        'sl_hit': sl_hit_ts is not None,
        'tp_first': tp_hit_ts is not None and (sl_hit_ts is None or tp_hit_ts < sl_hit_ts),
        'final_pct': final_pct,
        'outcome': outcome
    }

def main():
    # ChromaDBからWAIT記録取得
    db = NeoMemoryDB()
    col = db.collection
    results = col.get(where={"category": "wait_record"}, limit=500)
    
    # Tier1のみフィルタ
    waits = []
    for i in range(len(results['ids'])):
        meta = results['metadatas'][i]
        if meta.get('symbol') in TARGET_SYMBOLS:
            waits.append({
                'id': results['ids'][i],
                'symbol': meta['symbol'],
                'price': float(meta['price']),
                'timestamp': meta['timestamp'],
                'sentiment': meta.get('sentiment', '?'),
                'sentiment_score': float(meta.get('sentiment_score', 0)),
                'finbert_score': float(meta.get('finbert_score', 0)),
                'fear_greed': int(meta.get('fear_greed', 0)),
                'bt_confidence': meta.get('bt_confidence', '?'),
                'wait_reason': meta.get('wait_reason', '')[:100]
            })
    
    print(f"=== WAIT品質検証レポート ===")
    print(f"対象: {len(waits)}件（Tier1: {TARGET_SYMBOLS}）")
    print(f"TP閾値: +{TP_PCT*100}% / SL閾値: {SL_PCT*100}%")
    print(f"評価窓: {EVAL_WINDOWS}h")
    print()
    
    # SQLite接続
    conn = sqlite3.connect('vault/market_db/prices.sqlite')
    
    # === 各WAIT記録を検証 ===
    all_results = []
    for w in sorted(waits, key=lambda x: x['timestamp']):
        start_ms = iso_to_epoch_ms(w['timestamp'])
        # 96h分の価格取得
        prices = get_prices_after(conn, w['symbol'], start_ms, TIME_LIMIT_H)
        
        if len(prices) < 10:
            # データ不足
            all_results.append({**w, 'sim': None, 'data_points': len(prices)})
            continue
        
        sim = simulate_trade(prices, w['price'])
        
        # 各時間窓の変動も計算
        window_pcts = {}
        for wh in EVAL_WINDOWS:
            window_prices = get_prices_after(conn, w['symbol'], start_ms, wh)
            if window_prices:
                final_p = window_prices[-1][1]
                window_pcts[f'{wh}h'] = (final_p - w['price']) / w['price']
            else:
                window_pcts[f'{wh}h'] = None
        
        all_results.append({**w, 'sim': sim, 'windows': window_pcts, 'data_points': len(prices)})
    
    conn.close()
    
    # === サマリー出力 ===
    valid = [r for r in all_results if r.get('sim')]
    insufficient = [r for r in all_results if not r.get('sim')]
    
    print(f"検証可能: {len(valid)}件 / データ不足: {len(insufficient)}件")
    print()
    
    if not valid:
        print("検証可能なデータがありません。SQLiteにもう少しデータが蓄積されるのを待ってください。")
        return
    
    # アウトカム集計
    outcomes = {}
    for r in valid:
        o = r['sim']['outcome']
        outcomes[o] = outcomes.get(o, 0) + 1
    
    print("=== アウトカム集計（もしBUYしていたら）===")
    for o, c in sorted(outcomes.items()):
        pct = c / len(valid) * 100
        print(f"  {o}: {c}件 ({pct:.1f}%)")
    
    # WAITが正しかった = SLヒット or 最終的にマイナス
    correct_waits = [r for r in valid if r['sim']['outcome'] == 'SL' or r['sim']['final_pct'] < 0]
    missed_opps = [r for r in valid if r['sim']['outcome'] == 'TP']
    
    print(f"\n  ✅ WAIT正解（SLヒット or 最終マイナス）: {len(correct_waits)}件 ({len(correct_waits)/len(valid)*100:.1f}%)")
    print(f"  ❌ チャンス見逃し（TPヒット）: {len(missed_opps)}件 ({len(missed_opps)/len(valid)*100:.1f}%)")
    
    # 銘柄別集計
    print("\n=== 銘柄別サマリー ===")
    for sym in TARGET_SYMBOLS:
        sym_results = [r for r in valid if r['symbol'] == sym]
        if not sym_results:
            continue
        
        avg_max_up = sum(r['sim']['max_up'] for r in sym_results) / len(sym_results)
        avg_max_down = sum(r['sim']['max_down'] for r in sym_results) / len(sym_results)
        avg_final = sum(r['sim']['final_pct'] for r in sym_results) / len(sym_results)
        tp_count = sum(1 for r in sym_results if r['sim']['outcome'] == 'TP')
        sl_count = sum(1 for r in sym_results if r['sim']['outcome'] == 'SL')
        
        print(f"\n  {sym} ({len(sym_results)}件):")
        print(f"    平均最大上昇: {avg_max_up*100:+.2f}%")
        print(f"    平均最大下落: {avg_max_down*100:+.2f}%")
        print(f"    平均最終損益: {avg_final*100:+.2f}%")
        print(f"    TPヒット: {tp_count}件 / SLヒット: {sl_count}件")
    
    # 時間窓別の平均変動
    print("\n=== 時間窓別の平均変動（WAIT後にBUYしていたら）===")
    for wh_label in [f'{w}h' for w in EVAL_WINDOWS]:
        vals = [r['windows'][wh_label] for r in valid if r.get('windows') and r['windows'].get(wh_label) is not None]
        if vals:
            avg = sum(vals) / len(vals)
            positive = sum(1 for v in vals if v > 0)
            print(f"  {wh_label}: 平均 {avg*100:+.3f}% (上昇{positive}/{len(vals)}件)")
    
    # === 詳細テーブル ===
    print("\n=== 個別WAIT詳細 ===")
    print(f"{'時刻':>20} {'銘柄':>8} {'WAIT価格':>10} {'4h後':>8} {'24h後':>8} {'結果':>6} {'最大↑':>8} {'最大↓':>8}")
    print("-" * 95)
    for r in sorted(valid, key=lambda x: x['timestamp']):
        ts_short = r['timestamp'][5:16]  # MM-DDThh:mm
        w4 = r.get('windows', {}).get('4h')
        w24 = r.get('windows', {}).get('24h')
        w4s = f"{w4*100:+.2f}%" if w4 is not None else "N/A"
        w24s = f"{w24*100:+.2f}%" if w24 is not None else "N/A"
        print(f"  {ts_short:>18} {r['symbol']:>8} ${r['price']:.4f} {w4s:>8} {w24s:>8} {r['sim']['outcome']:>6} {r['sim']['max_up']*100:+.2f}% {r['sim']['max_down']*100:-.2f}%")
    
    # === センチメント別分析 ===
    print("\n=== センチメント別のWAIT品質 ===")
    bearish_waits = [r for r in valid if r['sentiment'] == 'bearish']
    neutral_waits = [r for r in valid if r['sentiment'] == 'neutral']
    
    for label, group in [('bearish', bearish_waits), ('neutral', neutral_waits)]:
        if not group:
            continue
        sl_in_group = sum(1 for r in group if r['sim']['outcome'] == 'SL')
        tp_in_group = sum(1 for r in group if r['sim']['outcome'] == 'TP')
        avg_final = sum(r['sim']['final_pct'] for r in group) / len(group)
        print(f"  {label} ({len(group)}件): SL={sl_in_group} TP={tp_in_group} 平均最終損益={avg_final*100:+.2f}%")
    
    print("\n✅ 分析完了")

if __name__ == '__main__':
    main()


def run_nightly_summary():
    """
    Nightly Batch用の軽量版。サマリーdictを返す。
    Discord報告用のテキストも生成する。
    """
    import sqlite3
    from core.memory_db import NeoMemoryDB

    TARGET_SYMBOLS = ['VIRTUAL', 'ETH', 'BTC']  # Council対象銘柄に合わせる

    db = NeoMemoryDB()
    col = db.collection
    results = col.get(where={"category": "wait_record"}, limit=500)

    waits = []
    for i in range(len(results['ids'])):
        meta = results['metadatas'][i]
        if meta.get('symbol') in TARGET_SYMBOLS:
            waits.append({
                'symbol': meta['symbol'],
                'price': float(meta['price']),
                'timestamp': meta['timestamp'],
                'sentiment': meta.get('sentiment', '?'),
            })

    if len(waits) < 5:
        return {
            'total': len(waits),
            'status': 'insufficient_data',
            'discord_text': f"📊 WAIT品質: データ不足（{len(waits)}件・5件未満）"
        }

    conn = sqlite3.connect('vault/market_db/prices.sqlite')

    symbol_stats = {}
    total_correct = 0
    total_missed = 0
    total_valid = 0

    for sym in TARGET_SYMBOLS:
        sym_waits = [w for w in waits if w['symbol'] == sym]
        if not sym_waits:
            continue

        tp_count = 0
        sl_count = 0
        hold_count = 0
        valid_count = 0
        correct_count = 0

        for w in sym_waits:
            start_ms = iso_to_epoch_ms(w['timestamp'])
            prices = get_prices_after(conn, w['symbol'], start_ms, 96)

            if len(prices) < 10:
                continue

            sim = simulate_trade(prices, w['price'])
            if not sim:
                continue

            valid_count += 1
            if sim['outcome'] == 'TP':
                tp_count += 1
            elif sim['outcome'] == 'SL':
                sl_count += 1
                correct_count += 1
            else:
                hold_count += 1
                if sim['final_pct'] < 0:
                    correct_count += 1

        if valid_count > 0:
            correct = correct_count  # SLヒット or 最終マイナス = WAITが正しかった
            missed = tp_count        # TPヒット = チャンス見逃し
            correct_rate = correct / valid_count * 100

            symbol_stats[sym] = {
                'total': len(sym_waits),
                'valid': valid_count,
                'tp': tp_count,
                'sl': sl_count,
                'hold': hold_count,
                'correct_rate': correct_rate,
            }
            total_correct += correct
            total_missed += missed
            total_valid += valid_count

    conn.close()

    # 全体正解率
    overall_correct_rate = (total_correct / total_valid * 100) if total_valid > 0 else 0.0

    # Discord報告テキスト生成
    lines = [f"📊 **WAIT品質検証** ({len(waits)}件分析)"]
    lines.append(f"全体WAIT正解率: **{overall_correct_rate:.1f}%** (SL={total_correct} / TP見逃し={total_missed})")

    for sym, st in symbol_stats.items():
        emoji = "✅" if st['correct_rate'] >= 50 else "⚠️"
        lines.append(f"{emoji} {sym}: 正解率{st['correct_rate']:.0f}% (TP={st['tp']} SL={st['sl']} HOLD={st['hold']})")

    # 自動調整の示唆（50件以上で表示）
    if total_valid >= 50:
        for sym, st in symbol_stats.items():
            if st['correct_rate'] < 40 and st['valid'] >= 10:
                lines.append(f"💡 {sym}: WAIT条件が厳しすぎる可能性（正解率{st['correct_rate']:.0f}%）")

    discord_text = "\n".join(lines)

    return {
        'total': len(waits),
        'valid': total_valid,
        'overall_correct_rate': overall_correct_rate,
        'total_correct': total_correct,
        'total_missed': total_missed,
        'symbol_stats': symbol_stats,
        'status': 'ok',
        'discord_text': discord_text,
    }
