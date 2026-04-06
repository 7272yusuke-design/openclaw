import json
import logging
import re
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

BUDGET_FILE = Path("vault/cost_guard_daily.json")
BREAKER_FILE = Path("vault/cost_guard_breaker.json")

class CostGuard:
    """
    Neo's CFO — 多層サーキットブレーカー。
    
    Layer 1: LLMコスト日次上限（$5/日）
    Layer 2: 日次実現損失上限（-$3,000/日）
    Layer 3: SL連続発火（3連続 → 6時間冷却）
    Layer 4: ポートフォリオドローダウン（HWMから-5%で全停止）
    Layer 5: 連続エラー（5回連続 → 既存のDiscord通知）
    
    各レイヤーは独立判定。1つでもブロックすればCouncil召集を停止。
    """

    # --- Layer 1: LLMコスト ---
    PRICE_PER_1K_TOKENS = {
        "gpt-4o": 0.03,
        "claude-3-5-sonnet": 0.015,
        "gemini-2.0-flash": 0.001,
        "gemini-2.5-flash": 0.001,
        "gemini-3-flash-preview": 0.001,
        "gemini-flash": 0.001,
        "deepseek-chat": 0.005,
    }
    DAILY_BUDGET_USD = 5.0
    MAX_RETRIES_PER_TASK = 3

    # --- Layer 2: 日次損失上限 ---
    DAILY_LOSS_LIMIT_USD = -3000.0

    # --- Layer 3: SL連続 ---
    CONSECUTIVE_SL_LIMIT = 3
    SL_COOLDOWN_HOURS = 6

    # --- Layer 4: ドローダウン ---
    DRAWDOWN_LIMIT_PCT = 5.0  # HWMから-5%で停止
    INITIAL_CAPITAL = 88494.0  # Paper取引開始時実績ベース

    def __init__(self):
        self.retry_counts = {}
        self._load_daily()
        self._load_breaker()

    # ================================================================
    # Persistence
    # ================================================================
    def _load_daily(self):
        """今日のLLM消費額をロード。日付が変わったらリセット。"""
        today = str(date.today())
        if BUDGET_FILE.exists():
            try:
                data = json.loads(BUDGET_FILE.read_text())
                if data.get("date") == today:
                    self.daily_spent = data.get("spent", 0.0)
                    return
            except Exception:
                pass
        self.daily_spent = 0.0
        self._save_daily()

    def _save_daily(self):
        BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_FILE.write_text(json.dumps({
            "date": str(date.today()),
            "spent": self.daily_spent,
        }))

    def _load_breaker(self):
        """サーキットブレーカー状態をロード。"""
        if BREAKER_FILE.exists():
            try:
                self._breaker = json.loads(BREAKER_FILE.read_text())
            except Exception:
                self._breaker = {}
        else:
            self._breaker = {}
        # HWMの初期化
        if "hwm" not in self._breaker:
            self._breaker["hwm"] = self.INITIAL_CAPITAL

    def _save_breaker(self):
        BREAKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        BREAKER_FILE.write_text(json.dumps(self._breaker, indent=2))

    # ================================================================
    # Layer 1: LLMコスト
    # ================================================================
    def approve_execution(self, crew_name: str, model_name: str,
                          estimated_input_tokens: int,
                          estimated_output_tokens: int) -> bool:
        cost = self._estimate_cost(model_name, estimated_input_tokens, estimated_output_tokens)
        if self.daily_spent + cost > self.DAILY_BUDGET_USD:
            logging.warning(f"[CFO-L1] DENIED: LLM日次予算超過 ({crew_name}) "
                            f"消費=${self.daily_spent:.4f} 推定=${cost:.4f} 上限=${self.DAILY_BUDGET_USD}")
            return False
        if self.retry_counts.get(crew_name, 0) >= self.MAX_RETRIES_PER_TASK:
            logging.error(f"[CFO-L1] BLOCKED: {crew_name} が{self.retry_counts[crew_name]}回ループ中")
            return False
        self.daily_spent += cost
        self._save_daily()
        return True

    def record_failure(self, crew_name: str):
        self.retry_counts[crew_name] = self.retry_counts.get(crew_name, 0) + 1

    def reset_failures(self, crew_name: str):
        self.retry_counts[crew_name] = 0

    def _estimate_cost(self, model: str, input_tok: int, output_tok: int) -> float:
        rate = 0.001
        for key, price in self.PRICE_PER_1K_TOKENS.items():
            if key in model:
                rate = price
                break
        return ((input_tok + output_tok) / 1000) * rate

    # ================================================================
    # Layer 2: 日次実現損失
    # ================================================================
    def check_daily_loss(self) -> tuple[bool, float]:
        """
        今日のSELL取引からFIFOで実現損益を計算。
        Returns: (allowed: bool, daily_pnl: float)
        """
        try:
            from tools.paper_wallet import PaperWallet
            pw = PaperWallet()
            hist = pw.state.get("history", [])

            today_str = str(date.today())
            buy_queues = {}
            daily_pnl = 0.0

            for h in hist:
                sym = h.get("symbol", "")
                if h["action"] == "BUY":
                    buy_queues.setdefault(sym, []).append({
                        "price": float(h["price"]),
                        "amount": float(h.get("amount", 0)),
                    })
                elif h["action"] == "SELL" and buy_queues.get(sym):
                    buy_entry = buy_queues[sym].pop(0)
                    sell_price = float(h["price"])
                    amount = float(h.get("amount", buy_entry.get("amount", 0)))
                    pnl = (sell_price - buy_entry["price"]) * amount
                    # 今日の取引のみ集計
                    ts = h.get("timestamp", "")
                    if today_str in ts:
                        daily_pnl += pnl

            if daily_pnl < self.DAILY_LOSS_LIMIT_USD:
                logging.warning(f"[CFO-L2] BLOCKED: 日次損失${daily_pnl:,.0f} < 上限${self.DAILY_LOSS_LIMIT_USD:,.0f}")
                return False, daily_pnl

            return True, daily_pnl
        except Exception as e:
            logging.error(f"[CFO-L2] 損失チェックエラー: {e}")
            return True, 0.0  # エラー時は通過（安全側）

    # ================================================================
    # Layer 3: SL連続発火
    # ================================================================
    def record_sl_fire(self):
        """SL発火を記録。"""
        now = datetime.now(timezone.utc).isoformat()
        sl_history = self._breaker.get("sl_fires", [])
        sl_history.append(now)
        # 直近24時間分のみ保持
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        sl_history = [t for t in sl_history if t > cutoff]
        self._breaker["sl_fires"] = sl_history
        self._save_breaker()

    def record_non_sl_exit(self):
        """SL以外の決済（TP/RSI等）でSL連続カウントをリセット。"""
        self._breaker["sl_fires"] = []
        self._save_breaker()

    def check_consecutive_sl(self) -> tuple[bool, int]:
        """
        直近のSL連続数をチェック。
        Returns: (allowed: bool, consecutive_count: int)
        """
        sl_fires = self._breaker.get("sl_fires", [])
        count = len(sl_fires)

        if count >= self.CONSECUTIVE_SL_LIMIT:
            # 最後のSLから冷却時間が経過しているか
            if sl_fires:
                last_sl = datetime.fromisoformat(sl_fires[-1])
                cooldown_end = last_sl + timedelta(hours=self.SL_COOLDOWN_HOURS)
                now = datetime.now(timezone.utc)
                if now < cooldown_end:
                    remaining = (cooldown_end - now).total_seconds() / 60
                    logging.warning(f"[CFO-L3] BLOCKED: SL{count}連続 — 冷却残り{remaining:.0f}分")
                    return False, count
                else:
                    # 冷却完了 → リセット
                    self._breaker["sl_fires"] = []
                    self._save_breaker()
                    logging.info("[CFO-L3] SL冷却完了 → リセット")
                    return True, 0

        return True, count

    # ================================================================
    # Layer 4: ポートフォリオドローダウン
    # ================================================================
    def update_hwm(self, current_total: float):
        """総資産のHigh Water Markを更新。"""
        hwm = self._breaker.get("hwm", self.INITIAL_CAPITAL)
        if current_total > hwm:
            self._breaker["hwm"] = current_total
            self._save_breaker()
            logging.info(f"[CFO-L4] HWM更新: ${current_total:,.0f}")

    def check_drawdown(self) -> tuple[bool, float]:
        """
        現在の総資産がHWMからX%以上下落していないかチェック。
        Returns: (allowed: bool, drawdown_pct: float)
        """
        try:
            from tools.paper_wallet import PaperWallet
            pw = PaperWallet()
            total = pw.state.get("usd_balance", 0)
            # ポジション評価額も加算（時価で計算）
            for sym, holding in pw.state.get("holdings", {}).items():
                if isinstance(holding, dict):
                    _amt = float(holding.get("amount", 0))
                else:
                    _amt = float(holding)
                if _amt > 0:
                    try:
                        from tools.market_data import MarketData
                        _td = MarketData.fetch_token_data(sym)
                        _price = float(_td.get("priceUsd", 0)) if _td else 0
                        total += _amt * _price
                    except Exception:
                        pass

            hwm = self._breaker.get("hwm", self.INITIAL_CAPITAL)
            self.update_hwm(total)

            if hwm <= 0:
                return True, 0.0

            drawdown_pct = ((hwm - total) / hwm) * 100
            if drawdown_pct >= self.DRAWDOWN_LIMIT_PCT:
                # 状態変化時のみログ出力（スパム防止）
                if not self._breaker.get('_l4_blocked', False):
                    logging.warning(f'[CFO-L4] BLOCKED: ドローダウン{drawdown_pct:.1f}% ≥ {self.DRAWDOWN_LIMIT_PCT}% '
                                    f'(HWM=${hwm:,.0f} 現在=${total:,.0f})')
                    self._breaker['_l4_blocked'] = True
                return False, drawdown_pct

            if self._breaker.get('_l4_blocked', False):
                logging.info(f'[CFO-L4] CLEARED: ドローダウン{drawdown_pct:.1f}% (HWM=${hwm:,.0f} 現在=${total:,.0f})')
                self._breaker['_l4_blocked'] = False
            return True, drawdown_pct
        except Exception as e:
            logging.error(f"[CFO-L4] ドローダウンチェックエラー: {e}")
            return True, 0.0

    # ================================================================
    # Master Gate: 全レイヤー統合チェック
    # ================================================================
    def approve_council(self) -> tuple[bool, str]:
        """
        Council召集前の統合チェック。全レイヤーを順にチェックし、
        1つでもブロックならCouncil召集を停止する。
        
        Returns: (approved: bool, reason: str)
        """
        # Layer 2: 日次損失
        l2_ok, daily_pnl = self.check_daily_loss()
        if not l2_ok:
            return False, f"L2:日次損失${daily_pnl:,.0f}超過"

        # Layer 3: SL連続
        l3_ok, sl_count = self.check_consecutive_sl()
        if not l3_ok:
            return False, f"L3:SL{sl_count}連続（冷却中）"

        # Layer 4: ドローダウン
        l4_ok, dd_pct = self.check_drawdown()
        if not l4_ok:
            return False, f"L4:DD{dd_pct:.1f}%（HWMから-{self.DRAWDOWN_LIMIT_PCT}%超過）"

        logging.info(f"[CFO] ALL CLEAR — L2:${daily_pnl:,.0f} L3:SL{sl_count}連 L4:DD{dd_pct:.1f}%")
        return True, "OK"

    def get_status(self) -> dict:
        """ダッシュボード用ステータス。"""
        l2_ok, daily_pnl = self.check_daily_loss()
        l3_ok, sl_count = self.check_consecutive_sl()
        l4_ok, dd_pct = self.check_drawdown()
        return {
            "l1_daily_spent": round(self.daily_spent, 4),
            "l1_budget": self.DAILY_BUDGET_USD,
            "l2_daily_pnl": round(daily_pnl, 2),
            "l2_limit": self.DAILY_LOSS_LIMIT_USD,
            "l2_ok": l2_ok,
            "l3_sl_count": sl_count,
            "l3_limit": self.CONSECUTIVE_SL_LIMIT,
            "l3_ok": l3_ok,
            "l4_drawdown_pct": round(dd_pct, 2),
            "l4_limit": self.DRAWDOWN_LIMIT_PCT,
            "l4_ok": l4_ok,
            "hwm": self._breaker.get("hwm", self.INITIAL_CAPITAL),
        }
