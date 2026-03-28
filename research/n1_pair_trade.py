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


# ================================================================
# N.1 ペアトレード実行マネージャー（v6.5l）
# ================================================================
import json
from pathlib import Path

PAIR_STATE_FILE = Path("vault/n1_pair_state.json")

class PairTradeManager:
    """
    VIRTUAL/AIXBTペアトレードの実行管理。
    
    PaperWalletはSHORT非対応のため、ロング側のみBUYで実行。
    ショート側は「BUYしない」ことで疑似的に表現。
    
    エントリー条件:
      - |Z| > z_entry(2.0) → 割安側をBUY
      - 相関 > 0.4（相関崩壊時はエントリーしない）
      - 既存ペアポジションがないこと
    
    エグジット条件:
      - |Z| < z_exit(0.5) → ポジションクローズ（mean reversion完了）
      - |Z| > z_stop(3.0) → 損切り（相関崩壊）
    
    5層売却との共存:
      - ペアトレードポジションにはreason="N1_PAIR"タグ付与
      - 5層売却も通常通り発火する（安全装置として維持）
    """

    # ペアBUY額（USDC）— confidence固定で小さめ
    PAIR_BUY_USD = 2000.0
    MIN_CORRELATION = 0.4

    def __init__(self):
        self._load_state()

    def _load_state(self):
        if PAIR_STATE_FILE.exists():
            try:
                self.state = json.loads(PAIR_STATE_FILE.read_text())
            except Exception:
                self.state = {}
        else:
            self.state = {}

    def _save_state(self):
        PAIR_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PAIR_STATE_FILE.write_text(json.dumps(self.state, indent=2))

    @property
    def has_position(self) -> bool:
        return self.state.get("active", False)

    def check_and_execute(self) -> dict:
        """
        ペアトレードシグナルをチェックし、必要に応じてエントリー/エグジット。
        
        Returns:
            dict with action taken and details
        """
        from tools.paper_wallet import PaperWallet
        from tools.market_data import MarketData
        
        sig = calc_pair_signal()
        result = {"action": "NONE", "signal": sig.get("signal", "ERROR"), "z_score": sig.get("z_score", 0)}

        if sig.get("signal") == "NO_DATA":
            result["reason"] = sig.get("error", "データ不足")
            return result

        z = sig["z_score"]
        corr = sig.get("recent_corr", 0)

        # === エグジット判定（ポジション保有中） ===
        if self.has_position:
            long_sym = self.state.get("long_symbol", "")
            entry_z = self.state.get("entry_z", 0)

            should_exit = False
            exit_reason = ""

            if abs(z) < 0.5:
                should_exit = True
                exit_reason = f"Mean reversion完了 (Z: {entry_z:.2f} → {z:.2f})"
            elif abs(z) > 3.0:
                should_exit = True
                exit_reason = f"相関崩壊損切り (Z={z:.2f} > 3.0)"

            if should_exit and long_sym:
                pw = PaperWallet()
                holding = pw.state.get("holdings", {}).get(long_sym)
                if holding and holding.get("amount", 0) > 0:
                    current_price = _get_current_price(long_sym)
                    if current_price > 0:
                        sell_usd = holding["amount"] * current_price
                        sell_result = pw.execute_trade(
                            symbol=long_sym, action="SELL",
                            amount_usd=sell_usd, price=current_price,
                            reason=f"N1_PAIR_EXIT: {exit_reason}"
                        )
                        if sell_result.get("status") == "success":
                            result["action"] = "EXIT"
                            result["symbol"] = long_sym
                            result["reason"] = exit_reason
                            result["sell_usd"] = round(sell_usd, 2)
                            # ペア状態クリア
                            self.state = {"active": False}
                            self._save_state()
                            return result

            result["action"] = "HOLD"
            result["reason"] = f"ペアポジション保有中: {long_sym} (entry_Z={entry_z:.2f}, now_Z={z:.2f})"
            return result

        # === エントリー判定（ポジションなし） ===
        if corr < self.MIN_CORRELATION:
            result["reason"] = f"相関不足 ({corr:.2f} < {self.MIN_CORRELATION})"
            return result

        long_sym = ""
        if z > 2.0:
            # VIRTUAL割高 → AIXBT買い
            long_sym = "AIXBT"
        elif z < -2.0:
            # VIRTUAL割安 → VIRTUAL買い
            long_sym = "VIRTUAL"

        if not long_sym:
            result["reason"] = f"エントリー閾値未達 (Z={z:.2f})"
            return result

        # ポジションサイズ確認
        pw = PaperWallet()
        if pw.state["usd_balance"] < self.PAIR_BUY_USD:
            result["reason"] = f"USDC不足 (${pw.state['usd_balance']:,.0f} < ${self.PAIR_BUY_USD:,.0f})"
            return result

        # USDC下限15%ガード
        total_assets = pw.state["usd_balance"]
        for sym, h in pw.state.get("holdings", {}).items():
            p = _get_current_price(sym)
            if p > 0:
                total_assets += h.get("amount", 0) * p
        if (pw.state["usd_balance"] - self.PAIR_BUY_USD) / total_assets < 0.15:
            result["reason"] = "USDC下限15%ガード"
            return result

        current_price = _get_current_price(long_sym)
        if current_price <= 0:
            result["reason"] = f"{long_sym}の価格取得失敗"
            return result

        buy_result = pw.execute_trade(
            symbol=long_sym, action="BUY",
            amount_usd=self.PAIR_BUY_USD, price=current_price,
            reason=f"N1_PAIR_ENTRY: Z={z:.2f}, corr={corr:.2f}"
        )

        if buy_result.get("status") == "success":
            self.state = {
                "active": True,
                "long_symbol": long_sym,
                "entry_z": z,
                "entry_corr": corr,
                "entry_price": current_price,
                "entry_time": datetime.now(timezone.utc).isoformat(),
                "buy_usd": self.PAIR_BUY_USD,
            }
            self._save_state()
            result["action"] = "ENTRY"
            result["symbol"] = long_sym
            result["reason"] = f"Z={z:.2f} → {long_sym}買い (corr={corr:.2f})"
            result["buy_usd"] = self.PAIR_BUY_USD
        else:
            result["reason"] = f"BUY失敗: {buy_result.get('reason', 'unknown')}"

        return result


def _get_current_price(symbol: str) -> float:
    """現在価格を取得（collector DB → fallback DexScreener）"""
    try:
        from orchestration.data_collector import get_latest_price_from_db
        p = get_latest_price_from_db(symbol)
        if p and p > 0:
            return p
    except Exception:
        pass
    try:
        md = MarketData()
        return md.get_price(symbol) or 0.0
    except Exception:
        return 0.0
