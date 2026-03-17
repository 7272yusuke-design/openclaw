"""
H.2 v2 — tsfresh + pingouin による高精度センチメント×結果相関分析
実行条件: 学習50回達成後
使い方: ./neo-env/bin/python research/analysis/h2_v2_tsfresh.py
"""
import sys, json
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import pingouin as pg
from tsfresh import extract_features
from tsfresh.feature_extraction import EfficientFCParameters
from tsfresh.utilities.dataframe_functions import impute
from core.memory_db import NeoMemoryDB

def load_trade_records(n=100):
    m = NeoMemoryDB()
    result = m.recall(query="BUY SELL WAIT VIRTUAL LUNA AIXBT", n_results=n)
    metas = result.get('metadatas', [])
    records = []
    for item in metas:
        if isinstance(item, list):
            records.extend(item)
        elif isinstance(item, dict):
            records.append(item)
    rows = []
    for r in records:
        action   = r.get('action', '')
        accuracy = r.get('accuracy')
        news     = r.get('news_count')
        fg       = r.get('fear_greed')
        score    = r.get('sentiment_score')
        bt       = r.get('bt_confidence', 'LOW')
        symbol   = r.get('symbol', '')
        price    = r.get('price')
        if action in ('BUY', 'WAIT', 'SELL') and accuracy is not None:
            rows.append({
                'action':     action,
                'symbol':     symbol,
                'accuracy':   float(accuracy),
                'news_count': float(news) if news else None,
                'fear_greed': float(fg) if fg else None,
                'sentiment_score': float(score) if score else None,
                'bt_conf':    1 if bt == 'HIGH' else (0.5 if bt == 'MEDIUM' else 0),
                'is_buy':     1 if action == 'BUY' else 0,
                'high_acc':   1 if float(accuracy) >= 80 else 0,
                'price':      float(price) if price else None,
            })
    return pd.DataFrame(rows)

def basic_stats(df):
    print("=" * 55)
    print("【基本統計】")
    print("=" * 55)
    print(f"総レコード数: {len(df)}")
    print(f"BUY: {(df.action=='BUY').sum()}件 / WAIT: {(df.action=='WAIT').sum()}件")
    print(f"accuracy平均: {df.accuracy.mean():.1f}%")
    print(f"BUYのaccuracy平均: {df[df.action=='BUY'].accuracy.mean():.1f}%")

def partial_correlation_analysis(df):
    print("\n" + "=" * 55)
    print("【pingouin 偏相関分析】")
    print("=" * 55)
    buy_df = df[df.action == 'BUY'].dropna(subset=['news_count', 'fear_greed', 'accuracy'])
    if len(buy_df) < 10:
        print(f"  ⚠️ BUYレコードが{len(buy_df)}件のみ（10件以上必要）")
        return
    try:
        result = pg.partial_corr(data=buy_df, x='news_count', y='accuracy', covar='fear_greed')
        r = result['r'].values[0]
        p = result['p_val'].values[0]
        print(f"  ニュース件数 → accuracy（FearGreed制御後）: r={r:.3f}, p={p:.3f} {'✅有意' if p < 0.05 else '⚠️非有意'}")
    except Exception as e:
        print(f"  偏相関計算エラー: {e}")
    try:
        result2 = pg.partial_corr(data=buy_df, x='fear_greed', y='accuracy', covar='news_count')
        r2 = result2['r'].values[0]
        p2 = result2['p_val'].values[0]
        print(f"  FearGreed → accuracy（ニュース制御後）:      r={r2:.3f}, p={p2:.3f} {'✅有意' if p2 < 0.05 else '⚠️非有意'}")
    except Exception as e:
        print(f"  偏相関計算エラー: {e}")
    buy_df2 = df[df.action == 'BUY'].dropna(subset=['sentiment_score', 'accuracy'])
    if len(buy_df2) >= 5:
        try:
            result3 = pg.corr(buy_df2['sentiment_score'], buy_df2['accuracy'])
            r3 = result3['r'].values[0]
            p3 = result3['p_val'].values[0]
            print(f"  sentiment_score → accuracy（単相関）:      r={r3:.3f}, p={p3:.3f} {'✅有意' if p3 < 0.05 else '⚠️非有意'}")
        except Exception as e:
            print(f"  sentiment_score相関エラー: {e}")

def news_count_breakdown(df):
    print("\n" + "=" * 55)
    print("【ニュース件数帯別 accuracy（更新版）】")
    print("=" * 55)
    buy_df = df[(df.action == 'BUY') & df.news_count.notna()]
    bands = [(0,3,'少(0-3)'),(4,5,'中(4-5)'),(6,7,'多(6-7)'),(8,99,'過多(8+)')]
    for lo, hi, label in bands:
        sub = buy_df[(buy_df.news_count >= lo) & (buy_df.news_count <= hi)]
        if len(sub) > 0:
            print(f"  {label}: avg={sub.accuracy.mean():.1f}% (n={len(sub)}) "
                  f"[min={sub.accuracy.min():.0f}% max={sub.accuracy.max():.0f}%]")

def tsfresh_price_features(df):
    print("\n" + "=" * 55)
    print("【tsfresh 価格特徴量 × accuracy相関 TOP10】")
    print("=" * 55)
    price_df = df[df.price.notna() & df.accuracy.notna()].reset_index(drop=True)
    if len(price_df) < 15:
        print(f"  ⚠️ 価格データ付きレコードが{len(price_df)}件のみ（15件以上必要）")
        return
    price_df = price_df.fillna(0)
    ts_data = []
    for idx, row in price_df.iterrows():
        for t, val in enumerate([
            row.get('price', 0),
            row.get('news_count', 0) or 0,
            row.get('fear_greed', 50) or 50,
            row.get('sentiment_score', 0.5) or 0.5,
            row.get('bt_conf', 0),
        ]):
            ts_data.append({'id': idx, 'time': t, 'value': float(val)})
    ts_df = pd.DataFrame(ts_data)
    target = price_df['accuracy']
    try:
        print("  特徴量抽出中（EfficientFCParameters）...")
        features = extract_features(
            ts_df, column_id='id', column_sort='time', column_value='value',
            default_fc_parameters=EfficientFCParameters(),
            disable_progressbar=True, n_jobs=1
        )
        impute(features)
        print(f"  抽出特徴量数: {features.shape[1]}件")
        corrs = []
        for col in features.columns:
            try:
                c = features[col].corr(target)
                if np.isfinite(c):
                    corrs.append((col, round(c, 3)))
            except Exception:
                continue
        corrs.sort(key=lambda x: abs(x[1]), reverse=True)
        print(f"\n  accuracyと相関の強い特徴量 TOP10:")
        for i, (feat, corr) in enumerate(corrs[:10], 1):
            direction = "↑高→高精度" if corr > 0 else "↑高→低精度"
            print(f"    {i:2d}. {feat[:50]}: r={corr} ({direction})")
    except Exception as e:
        print(f"  tsfresh実行エラー: {e}")

if __name__ == "__main__":
    print("🔬 H.2 v2 — tsfresh + pingouin 相関分析")
    print(f"実行日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
    df = load_trade_records(n=100)
    if len(df) < 10:
        print(f"❌ レコード不足: {len(df)}件（10件以上必要）")
        sys.exit(1)
    basic_stats(df)
    partial_correlation_analysis(df)
    news_count_breakdown(df)
    tsfresh_price_features(df)
    print("\n" + "=" * 55)
    print("✅ 分析完了")
    print("=" * 55)
