"""
N.1 統計的アービトラージ — VIRTUAL/AIXBTペアトレード（v6.5i 設計）

== 概要 ==
VIRTUAL/AIXBTの高相関(0.72-0.79)を利用した統計的ペアトレード。
価格比(スプレッド)が平均から乖離した時にmean reversionを狙う。

== 戦略 ==
  - スプレッド = VIRTUAL価格 / AIXBT価格
  - Zスコア = (現在スプレッド - 平均) / 標準偏差
  - ENTRY: |Z| > 2.0 → 割高側をSELL、割安側をBUY
  - EXIT:  |Z| < 0.5 → ポジションクローズ
  - STOP:  |Z| > 3.0 → 損切り（相関崩壊の可能性）

== 実装ステータス ==
  基盤スクリプト: ✅ 作成済み（シグナル計算のみ）
  Council統合: 未着手（Phase 1-Pとして注入予定）
  実取引: 未着手（通常のBUY/SELL実行との整合性確認が必要）

== 前提条件 ==
  - 相関リスクガード(Phase 5 ②b)との整合性
  - 片側ポジションだけにならない（ペアで同時エントリー）
  - 既存のTrinityCouncil判断と競合しないこと
"""
import sys; sys.path.insert(0, '.')
import numpy as np
import pandas as pd
from tools.market_data import MarketData


def calc_pair_signal(lookback_days=30, z_entry=2.0, z_exit=0.5, z_stop=3.0):
    """
    VIRTUAL/AIXBTペアトレードシグナルを計算
    
    Returns:
        dict with signal, z_score, spread, recommendation
    """
    v_df = MarketData.fetch_ohlcv_custom('VIRTUAL', days=lookback_days)
    a_df = MarketData.fetch_ohlcv_custom('AIXBT', days=lookback_days)
    
    if v_df is None or a_df is None or len(v_df) < 20 or len(a_df) < 20:
        return {"signal": "NO_DATA", "z_score": 0, "error": "OHLCV取得不足"}
    
    v_close = v_df.set_index('datetime')['close'].rename('VIRTUAL')
    a_close = a_df.set_index('datetime')['close'].rename('AIXBT')
    merged = pd.concat([v_close, a_close], axis=1).dropna()
    
    if len(merged) < 20:
        return {"signal": "NO_DATA", "z_score": 0, "error": "共通データ不足"}
    
    # スプレッド計算
    spread = merged['VIRTUAL'] / merged['AIXBT']
    spread_mean = spread.rolling(window=min(100, len(spread))).mean().iloc[-1]
    spread_std = spread.rolling(window=min(100, len(spread))).std().iloc[-1]
    current_spread = spread.iloc[-1]
    
    if spread_std == 0 or np.isnan(spread_std):
        return {"signal": "NO_DATA", "z_score": 0, "error": "標準偏差ゼロ"}
    
    z_score = (current_spread - spread_mean) / spread_std
    
    # 相関チェック（直近の相関が低下していないか）
    log_ret = np.log(merged / merged.shift(1)).dropna()
    recent_corr = log_ret.tail(50)['VIRTUAL'].corr(log_ret.tail(50)['AIXBT'])
    
    # シグナル判定
    signal = "NEUTRAL"
    recommendation = ""
    
    if abs(z_score) > z_stop:
        signal = "STOP"
        recommendation = f"⚠️ Zスコア={z_score:.2f}が停止閾値{z_stop}超え。相関崩壊の可能性"
    elif z_score > z_entry:
        signal = "SHORT_VIRTUAL_LONG_AIXBT"
        recommendation = f"VIRTUAL割高(Z={z_score:.2f}): VIRTUAL売り + AIXBT買い"
    elif z_score < -z_entry:
        signal = "LONG_VIRTUAL_SHORT_AIXBT"
        recommendation = f"VIRTUAL割安(Z={z_score:.2f}): VIRTUAL買い + AIXBT売り"
    elif abs(z_score) < z_exit:
        signal = "EXIT"
        recommendation = f"スプレッド収束(Z={z_score:.2f}): ポジションクローズ"
    else:
        signal = "NEUTRAL"
        recommendation = f"待機(Z={z_score:.2f}): エントリー閾値{z_entry}未達"
    
    return {
        "signal": signal,
        "z_score": round(z_score, 3),
        "spread": round(current_spread, 2),
        "spread_mean": round(spread_mean, 2),
        "spread_std": round(spread_std, 2),
        "recent_corr": round(recent_corr, 3),
        "recommendation": recommendation,
        "v_price": round(float(merged['VIRTUAL'].iloc[-1]), 6),
        "a_price": round(float(merged['AIXBT'].iloc[-1]), 6),
    }


def print_pair_status():
    """ペアトレード状態のサマリー表示"""
    result = calc_pair_signal()
    print("=== N.1 ペアトレード状態 ===")
    print(f"  シグナル: {result['signal']}")
    print(f"  Zスコア: {result['z_score']}")
    print(f"  スプレッド: {result.get('spread', 'N/A')} (平均={result.get('spread_mean', 'N/A')} ±{result.get('spread_std', 'N/A')})")
    print(f"  直近相関: {result.get('recent_corr', 'N/A')}")
    print(f"  VIRTUAL: ${result.get('v_price', 'N/A')}")
    print(f"  AIXBT: ${result.get('a_price', 'N/A')}")
    print(f"  推奨: {result.get('recommendation', 'N/A')}")
    return result


if __name__ == '__main__':
    print_pair_status()
