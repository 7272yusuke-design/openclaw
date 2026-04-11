"""
Neo Hybrid Radar v2 — 統合トリガーシステム
修正点:
  1. ボラティリティトリガー → TrinityCouncil直結（壊れたautonomous_post_cycle廃止）
  2. アルファトリガー → TrinityCouncil（既存、変更なし）
  3. 冷却期間をボラ/アルファ共通で管理
  4. 構造化ログ
"""
import time
import logging
from datetime import datetime, timezone
from tools.market_data import MarketData
from core.blackboard import NeoBlackboard
from agents.trinity_council import TrinityCouncil
from tools.discord_reporter import DiscordReporter
from orchestration.alpha_sweep_operation import run_sweep
from orchestration.data_collector import get_latest_price_from_db
from core.config import VOLATILITY_WATCH_SYMBOLS, COUNCIL_ELIGIBLE_SYMBOLS, TIER0_SYMBOLS
from orchestration.performance_evaluator import evaluate_performance
from orchestration.nightly_research import run_nightly_research
# [v6.5ac] arbitrage_monitor removed — see .archive_deadcode_v65p/
from orchestration.vp_discovery import run_vp_discovery
from core.config import LEARNING_MODE, LEARNING_TARGET_TRADES, LEARNING_SHARPE_THRESHOLD
from core.cost_guard import CostGuard

# --- TP/SLサイクルチェック（Council非依存・毎30秒） ---
_s3_dedup_cache = {}  # S3 exit引き締めログ重複排除

# === シンボル別売却冷却（二重発火防止）v6.5ar ===
_sell_cooldown = {}  # {symbol: timestamp}
SELL_COOLDOWN_SEC = 300  # 5分

def check_sell_aftermath():
    """売却後1h/6h/24hの価格を追跡し、売却判断の良否を記録 v6.5ar"""
    import json, os
    _path = 'vault/sell_tracker.json'
    if not os.path.exists(_path):
        return
    try:
        with open(_path) as f:
            _tracker = json.load(f)
        _changed = False
        for t in _tracker:
            _sell_time = datetime.fromisoformat(t['sell_time'].replace('Z','+00:00'))
            _elapsed_h = (datetime.now(timezone.utc) - _sell_time).total_seconds() / 3600
            _sym = t['symbol']
            _cur = 0.0
            try:
                if _sym in ('BTC','ETH'):
                    from orchestration.data_collector import get_latest_price_from_db
                    _cur = get_latest_price_from_db(_sym) or 0
                else:
                    _cur = float((MarketData._fetch_price_from_geckoterminal(_sym) or MarketData.fetch_token_data(_sym) or {}).get('priceUsd', 0))
            except Exception:
                continue
            if _cur <= 0:
                continue
            _sell_p = t['sell_price']
            _move_pct = (_cur - _sell_p) / _sell_p * 100
            for _hours, _key in [(1,'checked_1h'),(6,'checked_6h'),(24,'checked_24h')]:
                if _elapsed_h >= _hours and not t.get(_key, False):
                    t[_key] = True
                    t[f'price_{_hours}h'] = round(_cur, 6)
                    t[f'move_{_hours}h'] = round(_move_pct, 2)
                    _verdict = '✅正解' if (_move_pct < 0 and t.get('sell_reason', '') != 'SL' and 'Stop Loss' not in t.get('sell_reason', '')) or (_move_pct < -2) else '❌早すぎ' if _move_pct > 3 else '➡️中立'
                    logger.info(f"[売却追跡] {_sym} {t.get('sell_reason','?')[:20]} {_hours}h後: {_move_pct:+.1f}% → {_verdict} (売値 現在)")
                    _changed = True
        if _changed:
            with open(_path, 'w') as f:
                json.dump(_tracker, f)
    except Exception as e:
        logger.error(f'[売却追跡] エラー: {e}')

def check_tp_sl_all_positions():
    """保有中ポジションの利確/損切を毎サイクルチェック（Council召集不要）
    売却4層: SL固定(-3%) → TP固定(+7%) → テクニカル出口(RSI>65+含み益) → 時間制約(96h)
    Returns: True if any SELL was executed (triggers cooldown)"""
    from tools.paper_wallet import PaperWallet
    from core.memory_db import NeoMemoryDB
    import sqlite3, os
    from datetime import datetime, timezone
    pw = PaperWallet()
    holdings = pw.state.get("holdings", {})
    if not holdings:
        return False
    sell_executed = False
    memory = NeoMemoryDB()
    # === F2: BTC急落リスクチェック（5層出口の前に判定）v6.5ai ===
    _f2_level = 0
    _btc_24h_chg_f2 = 0.0
    try:
        import sqlite3 as _sq_f2
        _conn_f2 = _sq_f2.connect("vault/market_db/prices.sqlite")
        _cur_f2 = _conn_f2.cursor()
        _cur_f2.execute("SELECT close FROM prices WHERE symbol='BTC' ORDER BY timestamp DESC LIMIT 1")
        _r1 = _cur_f2.fetchone()
        _cur_f2.execute("SELECT close FROM prices WHERE symbol='BTC' AND timestamp <= datetime('now', '-24 hours') ORDER BY timestamp DESC LIMIT 1")
        _r2 = _cur_f2.fetchone()
        _conn_f2.close()
        if _r1 and _r2 and _r2[0] > 0:
            _btc_24h_chg_f2 = (_r1[0] - _r2[0]) / _r2[0] * 100
            if _btc_24h_chg_f2 <= -12:
                _f2_level = 3
                logger.warning(f"\N{POLICE CARS REVOLVING LIGHT} [F2 L3] BTC急落 {_btc_24h_chg_f2:.1f}% — 全ポジション緊急売却モード")
            elif _btc_24h_chg_f2 <= -8:
                _f2_level = 2
                logger.warning(f"\u26a0\ufe0f [F2 L2] BTC大幅下落 {_btc_24h_chg_f2:.1f}% — 含み益ポジション利確モード")
            elif _btc_24h_chg_f2 <= -5:
                _f2_level = 1
                logger.info(f"\U0001f4c9 [F2 L1] BTC下落 {_btc_24h_chg_f2:.1f}% — SL引き締めモード(x0.5)")
    except Exception:
        pass

    # === F2b: マクロ急変検知（SPY/Gold — 30分間隔キャッシュ）v6.5ak ===
    # BTCより先に動くマクロ指標で「先回り」するお盆フレームワークの即時版
    _f2b_level = 0
    try:
        import time as _time_f2b
        _f2b_cache_path = "vault/blackboard/f2b_macro_cache.json"
        _f2b_interval = 1800  # 30分
        _f2b_data = None
        _need_fetch = True
        if os.path.exists(_f2b_cache_path):
            try:
                import json as _json_f2b
                with open(_f2b_cache_path) as _fc:
                    _f2b_data = _json_f2b.load(_fc)
                if _time_f2b.time() - _f2b_data.get("ts", 0) < _f2b_interval:
                    _need_fetch = False
            except Exception:
                pass
        if _need_fetch:
            try:
                import yfinance as _yf_f2b
                import json as _json_f2b
                _spy_t = _yf_f2b.Ticker("SPY")
                _spy_h = _spy_t.history(period="2d", interval="1h")
                _gold_t = _yf_f2b.Ticker("GC=F")
                _gold_h = _gold_t.history(period="2d", interval="1h")
                _spy_now = float(_spy_h["Close"].iloc[-1]) if len(_spy_h) > 0 else 0
                _spy_prev = float(_spy_h["Close"].iloc[-24]) if len(_spy_h) >= 25 else float(_spy_h["Close"].iloc[0])
                _gold_now = float(_gold_h["Close"].iloc[-1]) if len(_gold_h) > 0 else 0
                _gold_prev = float(_gold_h["Close"].iloc[-24]) if len(_gold_h) >= 25 else float(_gold_h["Close"].iloc[0])
                _spy_chg = ((_spy_now - _spy_prev) / _spy_prev * 100) if _spy_prev > 0 else 0
                _gold_chg = ((_gold_now - _gold_prev) / _gold_prev * 100) if _gold_prev > 0 else 0
                _f2b_data = {"spy": _spy_now, "spy_chg": round(_spy_chg, 2), "gold": _gold_now, "gold_chg": round(_gold_chg, 2), "ts": _time_f2b.time()}
                os.makedirs(os.path.dirname(_f2b_cache_path), exist_ok=True)
                with open(_f2b_cache_path, "w") as _fc:
                    _json_f2b.dump(_f2b_data, _fc)
                logger.info(f"[F2b] キャッシュ更新: SPY {_spy_chg:+.1f}% Gold {_gold_chg:+.1f}%")
            except Exception as _yfe:
                logger.warning(f"[F2b] yfinance取得失敗: {_yfe}")
        if _f2b_data:
            _spy_chg_val = _f2b_data.get("spy_chg", 0)
            _gold_chg_val = _f2b_data.get("gold_chg", 0)
            # SPY急落 + Gold急騰 = リスクオフ加速（お盆の傾き）
            if _spy_chg_val <= -5 and _gold_chg_val >= 3:
                _f2b_level = 3
                logger.warning(f"[F2b L3] マクロ急変: SPY {_spy_chg_val:+.1f}% + Gold {_gold_chg_val:+.1f}% — 全ポジション緊急売却")
            elif _spy_chg_val <= -3 and _gold_chg_val >= 1.5:
                _f2b_level = 2
                logger.warning(f"[F2b L2] マクロ警戒: SPY {_spy_chg_val:+.1f}% + Gold {_gold_chg_val:+.1f}% — 含み益利確モード")
            elif _spy_chg_val <= -2:
                _f2b_level = 1
                logger.info(f"[F2b L1] SPY下落 {_spy_chg_val:+.1f}% — SL引き締めモード")
            # F2とF2bの最大レベルを採用
            if _f2b_level > _f2_level:
                _f2_level = _f2b_level
    except Exception as _f2b_outer_e:
        logger.warning(f"[F2b] 外部エラー: {_f2b_outer_e}")

    # RSI計算用ヘルパー（SQLiteの5分足から14期間RSI）
    def _calc_rsi(symbol, period=14):
        try:
            conn = sqlite3.connect("vault/market_db/prices.sqlite")
            cur = conn.cursor()
            cur.execute("SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT ?", (symbol, period + 1))
            rows = cur.fetchall()
            conn.close()
            if len(rows) < period + 1:
                return None
            closes = [r[0] for r in reversed(rows)]
            gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
            losses_list = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
            avg_gain = sum(gains) / period
            avg_loss = sum(losses_list) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except Exception:
            return None

    for clean_symbol, hdata in list(holdings.items()):
        amount = hdata.get("amount", 0)
        if amount <= 0:
            continue
        # === 二重発火防止: シンボル別冷却 v6.5ar ===
        import time as _time_sc
        _sc_until = _sell_cooldown.get(clean_symbol, 0)
        if _time_sc.time() < _sc_until:
            continue
        try:
            # Tier0（BTC/ETH）: ローカルDB優先（Binance蓄積・API節約）
            # VP銘柄: GeckoTerminal優先
            current_price = 0.0
            if clean_symbol in ("BTC", "ETH"):
                from orchestration.data_collector import get_latest_price_from_db
                _db_price = get_latest_price_from_db(clean_symbol)
                if _db_price and _db_price > 0:
                    current_price = _db_price
                else:
                    price_data = MarketData.fetch_token_data(clean_symbol)
                    if price_data and price_data.get("status") == "success":
                        current_price = float(price_data.get("priceUsd", 0.0))
            elif clean_symbol in ("VIRTUAL", "AIXBT"):
                price_data = MarketData._fetch_price_from_geckoterminal(clean_symbol)
                if not price_data:
                    price_data = MarketData.fetch_token_data(clean_symbol)
                if price_data and price_data.get("status") == "success":
                    current_price = float(price_data.get("priceUsd", 0.0))
            else:
                price_data = MarketData.fetch_token_data(clean_symbol)
                if price_data and price_data.get("status") == "success":
                    current_price = float(price_data.get("priceUsd", 0.0))
            if current_price <= 0:
                continue

            pnl = pw.get_unrealized_pnl(clean_symbol, current_price)

            # === 戦略別出口プロファイル読み込み ===
            from core.config import EXIT_PROFILES, EXIT_PROFILE_DEFAULT
            _exit_cat = hdata.get("exit_profile", EXIT_PROFILE_DEFAULT)
            _exit_p = EXIT_PROFILES.get(_exit_cat, EXIT_PROFILES[EXIT_PROFILE_DEFAULT])
            sl_pct = _exit_p["sl_pct"]
            _trail_start = _exit_p["trailing_start"]
            _trail_drop = _exit_p["trailing_drop"]
            _hard_tp = _exit_p["hard_tp_pct"]
            _time_limit = _exit_p["time_limit_hours"]
            # v6.5as: AI戦略書のexit_paramsでconfig値を上書き
            _ai_ep = hdata.get("entry_context", {}).get("exit_profile", {}) if isinstance(hdata.get("entry_context"), dict) else {}
            if _ai_ep.get("rsi_exit") is not None:
                _exit_p = dict(_exit_p)  # copy to avoid mutating config
                _exit_p["rsi_exit"] = _ai_ep["rsi_exit"]
            if _ai_ep.get("trailing_start"):
                _trail_start = _ai_ep["trailing_start"]
            if _ai_ep.get("trailing_drop"):
                _trail_drop = _ai_ep["trailing_drop"]

            # === S2: 戦略書シナリオモニタリング（Phase 0）===
            _strategy = hdata.get("entry_context", {}).get("strategy") if isinstance(hdata.get("entry_context"), dict) else None
            if _strategy and current_price > 0:
                try:
                    _s_thesis = _strategy.get("thesis", "?")[:50]
                    _s_entry = float(_strategy.get("entry_price", hdata.get("avg_price", 0)))
                    _s_bull = _strategy.get("bull_scenario", {})
                    _s_bear = _strategy.get("bear_scenario", {})
                    _s_target = float(_s_bull.get("target_price", 0))
                    _s_stop = float(_s_bear.get("stop_price", 0))
                    # bull進行度: entry→targetの何%まで来たか
                    _bull_prog = 0
                    if _s_target > _s_entry and _s_entry > 0:
                        _bull_prog = (current_price - _s_entry) / (_s_target - _s_entry) * 100
                    # bear進行度: entry→stopの何%まで来たか
                    _bear_prog = 0
                    if _s_entry > _s_stop and _s_entry > 0:
                        _bear_prog = (_s_entry - current_price) / (_s_entry - _s_stop) * 100
                    # invalidation条件チェック
                    _inv_conditions = _strategy.get("invalidation", {}).get("conditions", [])
                    # 60サイクル(30分)ごとにログ出力（毎30秒は過剰）
                    _s2_cycle = getattr(check_tp_sl_all_positions, '_s2_cycle', 0)
                    check_tp_sl_all_positions._s2_cycle = _s2_cycle + 1
                    if _s2_cycle % 60 == 0:
                        _s_tf = _strategy.get("thesis_timeframe", "?")
                        logger.info(
                            f"[S2] {clean_symbol} 戦略モニタ: {_s_thesis} | "
                            f"TF={_s_tf} | bull={_bull_prog:.0f}% | bear={_bear_prog:.0f}% | "
                            f"PnL={pnl['pnl_pct']:+.1f}% | "
                            f"target=${_s_target:.4f} stop=${_s_stop:.4f}"
                        )
                        if _bear_prog >= 70:
                            logger.warning(f"[S2] ⚠️ {clean_symbol} bear trigger接近: {_bear_prog:.0f}% → stop=${_s_stop:.4f}")
                        if _bull_prog >= 80:
                            logger.info(f"[S2] 🎯 {clean_symbol} bull target接近: {_bull_prog:.0f}% → target=${_s_target:.4f}")
                except Exception as _s2e:
                    pass

            # === S3: 戦略書動的出口 ===
            if _strategy and current_price > 0:
                try:
                    _s3_entry = float(hdata.get("avg_price", 0))
                    _s3_bear = _strategy.get("bear_scenario", {})
                    _s3_bull = _strategy.get("bull_scenario", {})
                    _s3_stop = float(_s3_bear.get("stop_price", 0))
                    _s3_target = float(_s3_bull.get("target_price", 0))

                    # S3-1: 戦略SLで固定SLを上書き（固定SLの2倍が安全上限）
                    if _s3_entry > 0 and _s3_stop > 0:
                        _strat_sl_pct = (_s3_entry - _s3_stop) / _s3_entry * 100
                        _max_sl = sl_pct * 2  # 固定SLの2倍まで許容
                        if 0 < _strat_sl_pct <= _max_sl:
                            sl_pct = _strat_sl_pct

                    # S3-2: bear trigger接近(70%) → exit_profile 1段階引き締め
                    if _s3_entry > 0 and _s3_stop > 0 and _s3_entry > _s3_stop:
                        _s3_bear_prog = (_s3_entry - current_price) / (_s3_entry - _s3_stop) * 100
                        if _s3_bear_prog >= 70:
                            from core.config import EXIT_PROFILES
                            _tighten_map = {"long": "mid", "mid": "short"}
                            _new_cat = _tighten_map.get(_exit_cat)
                            if _new_cat:
                                _new_p = EXIT_PROFILES.get(_new_cat)
                                if _new_p:
                                    _trail_start = _new_p["trailing_start"]
                                    _trail_drop = _new_p["trailing_drop"]
                                    _hard_tp = _new_p["hard_tp_pct"]
                                    _time_limit = _new_p["time_limit_hours"]
                                    _s3_log_key = f"{clean_symbol}_{_exit_cat}_{_new_cat}"
                                    if _s3_log_key not in _s3_dedup_cache:
                                        logger.warning(f"[S3] {clean_symbol} exit引き締め: {_exit_cat}→{_new_cat} (bear={_s3_bear_prog:.0f}%)")
                                        _s3_dedup_cache[_s3_log_key] = True

                    # S3-3: bull target到達(100%) → トレール早期開始
                    if _s3_entry > 0 and _s3_target > _s3_entry:
                        _s3_bull_prog = (current_price - _s3_entry) / (_s3_target - _s3_entry) * 100
                        if _s3_bull_prog >= 100 and pnl['pnl_pct'] > 0:
                            _trail_start = min(_trail_start, max(2.0, pnl['pnl_pct'] * 0.8))
                except Exception:
                    pass

            sell_reason = ""
            sell_label = ""
            # === F2: BTC急落リスク適用 v6.5ai ===
            if _f2_level >= 3:
                sell_reason = f"F2 L3 Emergency: BTC {_btc_24h_chg_f2:.1f}% — forced liquidation (profile: {_exit_cat})"
                sell_label = "F2-L3"
                logger.warning(f"[F2 L3] {clean_symbol} 緊急売却")
            elif _f2_level >= 2 and pnl['pnl_pct'] > 0:
                sell_reason = f"F2 L2 Profit-take: BTC {_btc_24h_chg_f2:.1f}% + profit {pnl['pnl_pct']:+.1f}% (profile: {_exit_cat})"
                sell_label = "F2-L2"
                logger.warning(f"[F2 L2] {clean_symbol} 含み益利確 +{pnl['pnl_pct']:.1f}%")
            elif _f2_level >= 1:
                sl_pct = sl_pct * 0.5  # SL引き締め

            # === 第0層: 戦略書exit_stages判定 ===
            _sell_fraction = 1.0  # デフォルト全量
            if not sell_reason and _strategy:
                _bull_stages = _strategy.get('bull_scenario', {}).get('exit_stages', [])
                _bear_stages = _strategy.get('bear_scenario', {}).get('exit_stages', [])
                _completed = hdata.get('completed_stages', [])
                # Bear exit_stages（損切り）
                for _si, _stg in enumerate(_bear_stages):
                    _stg_id = f'bear_{_si}'
                    if _stg_id in _completed:
                        continue
                    _trig = float(_stg.get('trigger_pct', -999))
                    if pnl['pnl_pct'] <= _trig:
                        _sf = min(100, max(1, int(_stg.get('sell_pct', 100)))) / 100.0
                        _sell_fraction = _sf
                        sell_reason = f"Strategy Bear Stage {_si}: {pnl['pnl_pct']:+.1f}% <= {_trig:+.1f}% (sell {_sf*100:.0f}%, {_stg.get('note','')})";
                        sell_label = 'Strategy SL'
                        _completed.append(_stg_id)
                        logger.warning(f'[Exit Stage] 📉 {clean_symbol} bear stage {_si}: {pnl["pnl_pct"]:+.1f}% (sell {_sf*100:.0f}%)')
                        break
                # Bull exit_stages（利確）
                if not sell_reason:
                    for _si, _stg in enumerate(_bull_stages):
                        _stg_id = f'bull_{_si}'
                        if _stg_id in _completed:
                            continue
                        _trig = float(_stg.get('trigger_pct', 999))
                        if pnl['pnl_pct'] >= _trig:
                            _sf = min(100, max(1, int(_stg.get('sell_pct', 100)))) / 100.0
                            _sell_fraction = _sf
                            sell_reason = f"Strategy Bull Stage {_si}: {pnl['pnl_pct']:+.1f}% >= {_trig:+.1f}% (sell {_sf*100:.0f}%, {_stg.get('note','')})";
                            sell_label = 'Strategy TP'
                            _completed.append(_stg_id)
                            logger.info(f'[Exit Stage] 📈 {clean_symbol} bull stage {_si}: {pnl["pnl_pct"]:+.1f}% (sell {_sf*100:.0f}%)')
                            break
                # completed_stagesを保存
                if _completed and clean_symbol in pw.state.get('holdings', {}):
                    pw.state['holdings'][clean_symbol]['completed_stages'] = _completed
                    pw._save_wallet()

            # === 第1層: 固定SL（戦略別） ===
            if not sell_reason and pw.should_stop_loss(clean_symbol, current_price, stop_pct=sl_pct):
                sell_reason = f"Stop Loss at {pnl['pnl_pct']:.1f}% (limit: -{sl_pct}%, profile: {_exit_cat})"
                sell_label = "SL"
                logger.warning(f"[TP/SL] 🛑 損切トリガー: {clean_symbol} {pnl['pnl_pct']:.1f}% (profile: {_exit_cat})")

            # === 第2層: トレーリングストップ（戦略別開始・ドロップ幅） ===
            elif pnl['pnl_pct'] >= _trail_start or hdata.get("high_water_pnl", 0) >= _trail_start:
                prev_hw = hdata.get("high_water_pnl", pnl['pnl_pct'])
                if pnl['pnl_pct'] > prev_hw:
                    hdata["high_water_pnl"] = pnl['pnl_pct']
                    pw.state["holdings"][clean_symbol]["high_water_pnl"] = pnl['pnl_pct']
                    pw._save_wallet()
                    logger.info(f"[TP/SL] 📈 高値更新: {clean_symbol} +{pnl['pnl_pct']:.1f}% (HWM)")
                    prev_hw = pnl['pnl_pct']
                drawdown_from_hw = prev_hw - pnl['pnl_pct']
                if drawdown_from_hw >= _trail_drop:
                    sell_reason = f"Trailing Stop at +{pnl['pnl_pct']:.1f}% (HWM: +{prev_hw:.1f}%, drop: -{drawdown_from_hw:.1f}%, profile: {_exit_cat})"
                    sell_label = "Trail TP"
                    logger.warning(f"[TP/SL] 🎯 トレーリング利確: {clean_symbol} +{pnl['pnl_pct']:.1f}% (HWM: +{prev_hw:.1f}%, profile: {_exit_cat})")

            # === 第2層b: 固定TP上限（戦略別） ===
            elif pnl['pnl_pct'] >= _hard_tp:
                sell_reason = f"Hard TP Ceiling at +{pnl['pnl_pct']:.1f}% (ceiling: +{_hard_tp:.0f}%, profile: {_exit_cat})"
                sell_label = "Hard TP"
                logger.warning(f"[TP/SL] 🎯 固定上限利確: {clean_symbol} +{pnl['pnl_pct']:.1f}% (profile: {_exit_cat})")

            # === 第3層: テクニカル出口（RSI > 閾値 + 含み益 > 1.5%）v6.5ai: プロファイル別RSI ===
            elif pnl['pnl_pct'] > 1.5:
                _rsi_exit_threshold = _exit_p.get("rsi_exit")
                if _rsi_exit_threshold is not None:
                    # v6.5as: AI戦略のbull_stage1未到達ならRSI Exitしない
                    _min_profit_for_rsi = 3.0  # デフォルト最低利益条件
                    try:
                        _ec_strat = hdata.get("entry_context", {}) if isinstance(hdata.get("entry_context"), dict) else {}
                        _bull_stages = _ec_strat.get("strategy", {}).get("bull_scenario", {}).get("exit_stages", []) if isinstance(_ec_strat.get("strategy"), dict) else []
                        if _bull_stages and isinstance(_bull_stages[0], dict):
                            _min_profit_for_rsi = max(3.0, _bull_stages[0].get("trigger_pct", 3.0))
                    except Exception:
                        pass
                    if pnl['pnl_pct'] >= _min_profit_for_rsi:
                        rsi_val = _calc_rsi(clean_symbol)
                        if rsi_val is not None and rsi_val > _rsi_exit_threshold:
                            sell_reason = f"RSI Exit at RSI={rsi_val:.1f} with +{pnl['pnl_pct']:.1f}% profit (RSI>{_rsi_exit_threshold}, min_profit={_min_profit_for_rsi:.1f}%, profile: {_exit_cat})"
                            sell_label = "RSI Exit"
                            logger.warning(f"[TP/SL] 📊 テクニカル出口: {clean_symbol} RSI={rsi_val:.1f}>{_rsi_exit_threshold} +{pnl['pnl_pct']:.1f}% (min={_min_profit_for_rsi:.1f}%, profile: {_exit_cat})")

            # === 第4層: 時間制約（戦略別） ===
            if not sell_reason:
                entry_time_str = hdata.get("entry_time", "")
                if entry_time_str:
                    try:
                        if entry_time_str.endswith('+00:00') or entry_time_str.endswith('Z'):
                            entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
                        else:
                            entry_time = datetime.fromisoformat(entry_time_str).replace(tzinfo=timezone.utc)
                        hours_held = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
                        if hours_held > _time_limit:
                            sell_reason = f"Time Exit after {hours_held:.0f}h (limit: {_time_limit}h, profile: {_exit_cat}) with {pnl['pnl_pct']:+.1f}%"
                            sell_label = "Time Exit"
                            logger.warning(f"[TP/SL] ⏰ 時間制約: {clean_symbol} {hours_held:.0f}h (limit: {_time_limit}h, profile: {_exit_cat}) {pnl['pnl_pct']:+.1f}%")
                    except Exception as _te:
                        logger.error(f"[TP/SL] entry_time解析エラー: {_te}")

            # === SELL実行 ===
            if sell_reason:
                sell_amount_usd = amount * current_price * _sell_fraction
                result = pw.execute_trade(symbol=clean_symbol, action="SELL", amount_usd=sell_amount_usd, price=current_price, reason=sell_reason)
                if result.get("status") == "success":
                    sell_executed = True
                    is_win = pnl['pnl_pct'] > 0
                    result_tag = "win" if is_win else "loss"
                    # サーキットブレーカー: SL記録
                    try:
                        _cg = CostGuard()
                        if sell_label == "SL":
                            _cg.record_sl_fire()
                            logger.info(f"[CFO] SL発火記録: {clean_symbol}")
                        else:
                            _cg.record_non_sl_exit()
                    except Exception as _cg_err:
                        logger.error(f"[CFO] SL記録エラー: {_cg_err}")
                    logger.info(f"[TP/SL] ✅ {sell_label}完了: {clean_symbol} ${sell_amount_usd:.2f} ({pnl['pnl_pct']:+.1f}%)")
                    # === 二重発火防止: 冷却セット v6.5ar ===
                    import time as _time_sc2
                    _sell_cooldown[clean_symbol] = _time_sc2.time() + SELL_COOLDOWN_SEC

                    # === SELL根拠スナップショット v6.5au ===
                    try:
                        try:
                            _rsi_snap = _calc_rsi(clean_symbol) or 0.0
                        except Exception:
                            _rsi_snap = 0.0
                        _btc_snap = _btc_24h_chg_f2
                        _entry_ctx = hdata.get('entry_context', {})
                        _buy_dt = hdata.get('entry_time', datetime.now(timezone.utc).isoformat())
                        _hold_h = (datetime.now(timezone.utc) - datetime.fromisoformat(_buy_dt.replace('Z','+00:00'))).total_seconds() / 3600
                        logger.info(f"[SELL根拠] {clean_symbol} | reason={sell_reason} | PnL={pnl['pnl_pct']:+.1f}% | RSI={_rsi_snap:.1f} | BTC24h={_btc_snap:+.1f}% | 保有{_hold_h:.1f}h | entry_conf={_entry_ctx.get('confidence','N/A')} | thesis={str(_entry_ctx.get('thesis','N/A'))[:80]}")
                        import json as _st_json
                        _st_path = 'vault/sell_tracker.json'
                        _st_data = []
                        if os.path.exists(_st_path):
                            try:
                                with open(_st_path) as _stf:
                                    _st_data = _st_json.load(_stf)
                            except Exception:
                                _st_data = []
                        _st_data.append({
                            'symbol': clean_symbol,
                            'sell_time': datetime.now(timezone.utc).isoformat(),
                            'sell_price': current_price,
                            'sell_reason': sell_reason,
                            'pnl_pct': round(pnl['pnl_pct'], 2),
                            'rsi': round(_rsi_snap, 1),
                            'btc_24h': round(_btc_snap, 1),
                            'hold_hours': round(_hold_h, 1),
                            'entry_confidence': _entry_ctx.get('confidence'),
                        })
                        with open(_st_path, 'w') as _stf:
                            _st_json.dump(_st_data, _stf)
                    except Exception as _snap_err:
                        logger.warning(f'[SELL根拠] スナップショット失敗: {_snap_err}')

                    # E1.1: 構造化内省（Deep Introspection）
                    introspection = ""
                    _failure_category = ""
                    if not is_win:
                        introspection = f"-{sl_pct}%到達。構造化内省を生成中。"
                        # エントリー時コンテキストの取得（E1.3で保存したもの）
                        _ectx = hdata.get("entry_context", {})
                        _entry_rsi = _ectx.get("rsi_14", "N/A")
                        _entry_bt = _ectx.get("bt_confidence", "N/A")
                        _entry_sent = _ectx.get("sentiment_label", "N/A")
                        _entry_conf = _ectx.get("confidence", "N/A")
                        _entry_btc = _ectx.get("btc_trend", "N/A")
                        _entry_btc_24h = _ectx.get("btc_24h", "N/A")
                        _entry_kf = _ectx.get("key_factor", "N/A")
                        # 現在のRSI取得
                        _cur_rsi = "N/A"
                        try:
                            _cur_rsi = round(_calc_rsi(clean_symbol), 1)
                        except Exception:
                            pass
                        # 現在のBTC変動取得
                        _cur_btc_24h = "N/A"
                        try:
                            _btc_now = MarketData.fetch_btc_trend()
                            _cur_btc_24h = f"{_btc_now.get('change_24h', 0):+.1f}" if _btc_now else "N/A"
                        except Exception:
                            pass
                        # 保有時間計算
                        _hold_hours = 0
                        try:
                            _et = hdata.get("entry_time", "")
                            if _et:
                                from datetime import datetime as _dt2
                                _etime = _dt2.fromisoformat(_et.replace("Z", "+00:00"))
                                _hold_hours = round((datetime.now(timezone.utc) - _etime).total_seconds() / 3600, 1)
                        except Exception:
                            pass
                        # S4: 戦略書データ準備
                        _strat_section = ""
                        _entry_strat = _ectx.get("strategy")
                        if _entry_strat:
                            _s4_bull = _entry_strat.get("bull_scenario", {})
                            _s4_bear = _entry_strat.get("bear_scenario", {})
                            _s4_target = _s4_bull.get("target_price", 0)
                            _s4_stop = _s4_bear.get("stop_price", 0)
                            _s4_inv = _entry_strat.get("invalidation", {}).get("conditions", [])
                            _strat_section = (
                                f"\n【戦略書（エントリー時に立案）】\n"
                                f"- テーゼ: {_entry_strat.get('thesis', 'N/A')}\n"
                                f"- TF: {_entry_strat.get('thesis_timeframe', 'N/A')}\n"
                                f"- 楽観: {_s4_bull.get('narrative', 'N/A')} (target=${_s4_target})\n"
                                f"- 楽観根拠: {', '.join(str(e)[:40] for e in _s4_bull.get('evidence', [])[:3])}\n"
                                f"- 悲観: {_s4_bear.get('narrative', 'N/A')} (stop=${_s4_stop})\n"
                                f"- 悲観根拠: {', '.join(str(e)[:40] for e in _s4_bear.get('evidence', [])[:3])}\n"
                                f"- 無効化条件: {', '.join(str(c)[:40] for c in _s4_inv[:2])}\n"
                                f"- 結果: 現在価格${current_price:.6f} vs target=${_s4_target} / stop=${_s4_stop}\n"
                            )
                        try:
                            from core.model_factory import ModelFactory
                            _model = ModelFactory.get_genai_model("fast")
                            _prompt = (
                                f"あなたは自律取引AIエージェントNeoの内省モジュールだ。\n\n"
                                f"【取引データ】\n"
                                f"- 銘柄: {clean_symbol}\n"
                                f"- エントリー: ${pnl['avg_price']:.6f} → 決済: ${current_price:.6f} ({pnl['pnl_pct']:+.1f}%)\n"
                                f"- 保有時間: {_hold_hours}h\n"
                                f"- エントリー時RSI: {_entry_rsi} / 決済時RSI: {_cur_rsi}\n"
                                f"- エントリー時BT信頼度: {_entry_bt} / センチメント: {_entry_sent}\n"
                                f"- エントリー時BTC: {_entry_btc} / 決済時BTC 24h: {_cur_btc_24h}%\n"
                                f"- エントリー時confidence: {_entry_conf} / key_factor: {_entry_kf}\n"
                                f"- 決済理由: {sell_reason}\n"
                                f"{_strat_section}\n"
                                f"【分析手順（Step by Step）】\n"
                                f"Step 1: エントリー時の判断根拠を列挙し、どれが正しくどれが間違いだったか仕分けよ\n"
                                f"Step 2: 見落としていたシグナル（RSI乖離、BTC連動、センチメント過信等）を特定せよ\n"
                                f"Step 3: 7カテゴリから最も適切な失敗原因を1つ選び、再発防止ルールを具体化せよ\n\n"
                                f"【few-shot例】\n"
                                f'AIXBT: entry=$0.027 exit=$0.026 (-3.1%), RSI=58→42, BTC -4.2%\n'
                                f'{{"failure_category":"btc_correlation","entry_mistake":"BTC下落トレンド中にアルト買い","missed_signal":"BTC 30d=-8%の長期下落を軽視","market_context_gap":"アルト個別材料を過信しBTC連動リスクを無視","next_time_rule":"BTC 24h<-3%時はアルトBUY見送り","confidence_was_justified":false}}\n\n'
                                f"分析手順に従い思考した上で、最終回答をJSON形式のみで出力せよ（日本語、各フィールド30字以内）:\n"
                                f'{{"failure_category": "trend_against | btc_correlation | overconfidence | bad_timing | signal_false | volatility_spike | averaging_down",'
                                f'"entry_mistake": "...",'
                                f'"missed_signal": "...",'
                                f'"market_context_gap": "...",'
                                f'"next_time_rule": "...",'
                                f'"confidence_was_justified": true/false,'
                                f'"scenario_outcome": "bull | bear | unexpected",'
                                f'"strategy_quality_score": 1-10}}'
                            )
                            _resp = _model.generate_content(_prompt)
                            _raw = _resp.text.strip()
                            # JSONパース試行
                            import json as _json
                            # ```json ... ``` ブロック除去
                            _clean = _raw
                            if "```" in _clean:
                                _clean = _clean.split("```json")[-1].split("```")[0] if "```json" in _clean else _clean.split("```")[1] if _clean.count("```") >= 2 else _clean
                            _clean = _clean.strip()
                            _parsed = _json.loads(_clean)
                            _failure_category = _parsed.get("failure_category", "").split("|")[0].strip().split(" ")[0].strip()
                            _scenario_outcome = _parsed.get("scenario_outcome", "unexpected")
                            _strategy_quality = _parsed.get("strategy_quality_score", 5)
                            introspection = (
                                f"[{_failure_category}] "
                                f"判断ミス: {_parsed.get('entry_mistake', 'N/A')} | "
                                f"見落とし: {_parsed.get('missed_signal', 'N/A')} | "
                                f"乖離: {_parsed.get('market_context_gap', 'N/A')} | "
                                f"次回: {_parsed.get('next_time_rule', 'N/A')} | "
                                f"scenario={_scenario_outcome} quality={_strategy_quality}/10"
                            )
                            logger.info(f"[E1] 構造化内省成功: category={_failure_category}, scenario={_scenario_outcome}, quality={_strategy_quality}")
                        except Exception as _ie:
                            logger.error(f"[E1] 構造化内省失敗（フォールバック）: {_ie}")
                            introspection = f"SL発火 {pnl['pnl_pct']:+.1f}% ({sell_reason})"
                            _failure_category = "unknown"

                    # メモリ保存
                    mem_text = f"【{sell_label}】{clean_symbol} エントリー${pnl['avg_price']:.4f}→決済${current_price:.4f} {pnl['pnl_pct']:+.1f}% (${pnl['pnl_usd']:+.2f})"
                    if introspection:
                        mem_text += "\n内省: " + introspection
                        logger.info(f"[TP/SL] 🧠 内省: {introspection}")
                    _s4_meta = {"symbol": clean_symbol, "category": "trade_result", "result": result_tag, "pnl_pct": str(pnl['pnl_pct']), "exit_type": sell_label, "failure_category": _failure_category if not is_win else "", "strategy_tag": hdata.get("strategy_tag", "unknown"), "tier": "2"}
                    # entry_contextからスコアリング要素をtrade_resultに引き継ぎ（パターンマイニング用）
                    _ec = hdata.get('entry_context', {}) if isinstance(hdata, dict) else {}
                    _sb = _ec.get('scoring_breakdown', {})
                    if _sb:
                        _s4_meta['conf_total'] = str(_sb.get('total', ''))
                        _s4_meta['bt'] = str(_sb.get('bt', ''))
                        _s4_meta['tz'] = str(_sb.get('tz', ''))
                        _s4_meta['cfr'] = str(_sb.get('cfr', ''))
                        _s4_meta['macro'] = str(_sb.get('macro', ''))
                        _s4_meta['npin'] = str(_sb.get('npin', ''))
                        _s4_meta['streak'] = str(_sb.get('streak', ''))
                        _s4_meta['sent'] = str(_sb.get('sent', ''))
                    _s4_meta['capital_flow_phase'] = str(_ec.get('capital_flow_phase', ''))
                    _s4_meta['btc_trend'] = str(_ec.get('btc_trend', ''))
                    # 時間帯・曜日を自動付与
                    try:
                        from datetime import datetime as _dt2
                        _entry_ts = _ec.get('timestamp', '')
                        if _entry_ts:
                            _edt = _dt2.fromisoformat(_entry_ts)
                            _s4_meta['entry_hour'] = str(_edt.hour)
                            _s4_meta['entry_weekday'] = str(_edt.strftime('%a'))
                    except Exception:
                        pass
                    if not is_win and '_scenario_outcome' in dir():
                        _s4_meta["scenario_outcome"] = _scenario_outcome
                        _s4_meta["strategy_quality_score"] = str(_strategy_quality)
                    memory.store(mem_text, metadata=_s4_meta)

                    # paper_trade.logに記録（Evaluatorが参照）
                    try:
                        from datetime import datetime, timezone
                        _now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        _bal = pw.get_balance()  # PaperWallet returns float directly
                        _acc = 0.0
                        try:
                            _bb = NeoBlackboard.read()
                            _ps = _bb.get("performance_summary", {})
                            _acc = _ps.get("accuracy_score", 0.0)
                        except Exception:
                            pass
                        _log_line = f"[{_now}] {clean_symbol}/USDT: ${current_price:.6f} | Action: SELL | Amount: ${sell_amount_usd:.2f} | Status: {sell_label} | Accuracy: {_acc}% | BT_Confidence: LOW\n"
                        with open("/docker/openclaw-taan/data/.openclaw/workspace/paper_trade.log", "a") as _lf:
                            _lf.write(_log_line)
                        logger.info(f"[TP/SL] 📝 paper_trade.log記録: {clean_symbol} SELL ${sell_amount_usd:.2f}")
                    except Exception as _le:
                        logger.error(f"[TP/SL] paper_trade.log記録失敗: {_le}")
                    # Discord報告
                    try:
                        _disc_reason = f"{sell_label} | entry:{DiscordReporter._fmt_price(pnl['avg_price'], clean_symbol)} pnl:${pnl['pnl_usd']:+.2f}"
                        _disc_reason += f"\nRSI: {_rsi_snap:.1f} | BTC24h: {_btc_24h_chg_f2:+.1f}%"
                        _disc_reason += f"\n保有: {_hold_h:.1f}h | conf: {_entry_ctx.get('confidence','?')}"
                        _thesis_str = str(_entry_ctx.get("thesis",""))[:80]
                        if _thesis_str:
                            _disc_reason += f"\n戦略: {_thesis_str}"
                        DiscordReporter.send_trade_alert(
                            symbol=f"{clean_symbol} ({sell_label} {pnl['pnl_pct']:+.1f}%)",
                            action="SELL",
                            amount_usd=sell_amount_usd,
                            price=current_price,
                            status=_disc_reason,
                            balance_after=_bal,
                            exit_profile=_exit_cat
                        )
                    except Exception as _de:
                        logger.error(f"[TP/SL] Discord報告失敗: {_de}")

        except Exception as e:
            logger.error(f"[TP/SL] {clean_symbol} チェックエラー: {e}")
    return sell_executed

# --- 設定 ---
CHECK_INTERVAL = 30           # 監視間隔（秒）
VOLATILITY_THRESHOLD = 2.0    # ボラティリティ閾値（%）
ALPHA_THRESHOLD = LEARNING_SHARPE_THRESHOLD if LEARNING_MODE else 5.0  # 学習モード中は緩和
COUNCIL_COOLDOWN = 1800       # 冷却期間（30分）— Moltbook Rate Limit保護
SWEEP_INTERVAL   = 120        # Sweepサイクル間隔（30秒×120=60分）
# [v6.5ac] ARB_INTERVAL removed
EVAL_INTERVAL    = 720        # Evaluatorサイクル間隔（30秒×720=6時間）
CFR_INTERVAL     = 720        # Capital Flow Radar間隔（30秒×720=6時間）
ENGAGE_INTERVAL  = 240
UNIFIED_COUNCIL_INTERVAL_SEC = 3600  # 1時間ごと（秒）— タイムスタンプベース・リスタート耐性あり
HEARTBEAT_INTERVAL = 60       # 稼働報告間隔（30秒×60=30分）        # Moltbookエンゲージメント間隔（30秒×240=2時間）
NIGHTLY_HOUR     = 2           # Nightly Batch実行時刻（JST 02:00 — now_jst_hourと比較）

from logging.handlers import RotatingFileHandler as _RFH
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        _RFH("radar.log", maxBytes=1_000_000, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("neo.radar")

def _run_nightly_batch():
    """
    Nightly Batch — JST 02:00に1日1回実行
    1. Alpha Sweep フルスキャン（全銘柄）
    2. Performance Evaluator（勝率更新 + Discordダッシュボード）
    3. Discord日次サマリー送信
    """
    batch_start = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info(f"[Nightly] === {today} バッチ開始 ===")

    # 1. Alpha Sweep フルスキャン
    logger.info("[Nightly] Step 1/8: Alpha Sweep フルスキャン")
    try:
        run_sweep(nightly=True)
        logger.info("[Nightly] Sweep完了（全Tier）")
    except Exception as e:
        logger.error(f"[Nightly] Sweep失敗: {e}")

    # 2. Performance Evaluator
    logger.info("[Nightly] Step 2/8: Performance Evaluator")
    try:
        evaluate_performance()
        logger.info("[Nightly] Evaluator完了（Discordダッシュボード送信済み）")
    except Exception as e:
        logger.error(f"[Nightly] Evaluator失敗: {e}")

    # 3. VP Discovery（週次・月曜のみ）
    if datetime.now(timezone.utc).weekday() == 0:  # 0=月曜
        logger.info("[Nightly] Step 3b: VP新興銘柄スキャン（週次）")
        try:
            result = run_vp_discovery()
            added = result.get("added", [])
            if added:
                DiscordReporter.send_log(
                    "🔍 VP Discovery: 新興銘柄発見",
                    f"**新規追加**: {', '.join(added)}\n**監視リスト**: {', '.join(result.get('current', []))}",
                    0x2ecc71
                )
        except Exception as e:
            logger.error(f"[Nightly] VP Discovery失敗: {e}")

    # 3. Nightly Research（洞察投稿・学習報告）
    logger.info("[Nightly] Step 3/8: Nightly Research")
    try:
        run_nightly_research()
    except Exception as e:
        logger.error(f"[Nightly] Nightly Research失敗: {e}")

    # 4. Tearsheetレポート生成（M.2）
    logger.info("[Nightly] Step 4/8: quantstats HTMLティアシート生成")
    try:
        from orchestration.tearsheet_generator import generate_tearsheet
        tearsheet_path = generate_tearsheet()
        if tearsheet_path:
            DiscordReporter.send_log(
                "📊 Neo Tearsheet生成完了",
                f"HTMLレポートを生成しました: `{tearsheet_path}`",
                0x3498db
            )
    except Exception as e:
        logger.error(f"[Nightly] Tearsheet生成失敗: {e}")

    # 5. WAIT品質検証
    logger.info("[Nightly] Step 5/8: WAIT品質検証")
    wait_quality_text = ""
    try:
        from research.wait_quality_analysis import run_nightly_summary
        wq = run_nightly_summary()
        wait_quality_text = "\n\n" + wq.get('discord_text', '')
        logger.info(f"[Nightly] WAIT品質: {wq.get('status')} (正解率={wq.get('overall_correct_rate', 0):.1f}%)")
    except Exception as e:
        logger.error(f"[Nightly] WAIT品質検証失敗: {e}")

    # 6. H.2取引分析進捗
    logger.info("[Nightly] Step 6/8: H.2取引分析進捗")
    h2_progress_text = ""
    try:
        from research.h2_trade_analysis import get_progress_report
        h2 = get_progress_report()
        h2_progress_text = "\n\n" + h2.get('discord_text', '')
        if h2.get('ready'):
            logger.info("[Nightly] H.2分析: データ十分 → v2完全分析を自動実行")
            try:
                from research.h2_trade_analysis import run_full_analysis
                run_full_analysis()
                # ダッシュボードに週次レポート送信（日曜のみ）
                import datetime as _dt
                if _dt.datetime.now(_dt.timezone.utc).weekday() == 6:  # 日曜
                    _h2_webhook = DiscordReporter.DASHBOARD_WEBHOOK or DiscordReporter.REPORT_WEBHOOK
                    _h2_payload = {"embeds": [{"title": "📊 H.2 週次分析レポート", "description": h2_progress_text.strip(), "color": 0x9b59b6}]}
                    import requests as _req
                    _req.post(_h2_webhook, json=_h2_payload, timeout=10)
                    logger.info("[Nightly] H.2週次レポートをダッシュボードに送信")
            except Exception as _h2e:
                logger.error(f"[Nightly] H.2完全分析エラー: {_h2e}")
        else:
            logger.info(f"[Nightly] H.2分析: 完結ペア{h2.get('completed',0)}/{h2.get('remaining',20)+h2.get('completed',0)}件")
    except Exception as e:
        logger.error(f"[Nightly] H.2進捗取得失敗: {e}")

    # 6a2. Strategy Scores生成（Task 5: 戦略別勝率蓄積）
    try:
        from research.h2_trade_analysis import generate_strategy_scores
        generate_strategy_scores()
        logger.info("[Nightly] Strategy scores: vault/strategy_scores.json更新完了")
    except Exception as _ss:
        logger.error(f"[Nightly] Strategy scores生成失敗: {_ss}")
    # 6b. Voyagerスキル更新
    voyager_nightly_text = ""
    try:
        from research.voyager_skills import run_voyager_update
        _voyager_skills = run_voyager_update()
        if _voyager_skills:
            _voy_lines = [f"{s['skill_name']}: 勝率{s['win_rate']}% ({s['sample_size']}件)" for s in _voyager_skills[:5]]
            voyager_nightly_text = "\n\n🔭 **Voyager学習**: " + " / ".join(_voy_lines)
        else:
            voyager_nightly_text = "\n\n🔭 **Voyager**: データ不足（スキップ）"
        logger.info("[Nightly] Voyager: スキル更新完了")
    except Exception as _ve:
        logger.error(f"[Nightly] Voyager更新失敗: {_ve}")

    # 6c. EvolveRルール更新
    evolver_nightly_text = ""
    try:
        from research.evolver_rules import run_evolver_update
        _evolver_rules = run_evolver_update()
        if _evolver_rules:
            _sev_icon = {"high": "🔴", "warning": "🟡", "info": "🟢"}
            _evo_lines = [f"{_sev_icon.get(r['severity'], '⚪')} {r['rule'][:60]}" for r in _evolver_rules[:5]]
            evolver_nightly_text = "\n\n🧬 **EvolveR進化**: " + " / ".join(_evo_lines)
        else:
            evolver_nightly_text = "\n\n🧬 **EvolveR**: データ不足（スキップ）"
        logger.info("[Nightly] EvolveR: ルール更新完了")
        # 6c2. EvolveR Scoring Adjustment生成 (E3)
        try:
            from research.evolver_agent import generate_scoring_adjustments
            generate_scoring_adjustments()
            logger.info("[Nightly] E3 EvolverAgent: scoring_adjustments.json更新完了")
        except Exception as _ea:
            logger.error(f"[Nightly] E3 EvolverAgent失敗: {_ea}")
    except Exception as _ve:
        logger.error(f"[Nightly] EvolveR更新失敗: {_ve}")

    # 6d. gplearn Nightly進化（G4: 毎晩1シード×2銘柄）
    gplearn_nightly_text = ""
    try:
        from research.gplearn_strategy import run_nightly_evolution
        logger.info("[Nightly] Step 6d: gplearn Nightly進化")
        _gp_results = run_nightly_evolution()
        _gp_lines = []
        for _sym, _r in _gp_results.items():
            _gp_lines.append(f"{_sym}: acc={_r['acc']}% recall={_r['recall']}% [{_r['saved']}]")
        gplearn_nightly_text = "\n\n🧬 **gplearn G4**: " + " / ".join(_gp_lines)
        logger.info(f"[Nightly] gplearn G4完了: {' / '.join(_gp_lines)}")
    except Exception as _gpe:
        logger.error(f"[Nightly] gplearn G4失敗: {_gpe}")

    # 6e. Graduation Boost宣伝はnightly_research内で土曜に自動投稿
    # （旧ACP Provider宣伝は廃止 → VP Guide毎日投稿+Graduation Boost土曜投稿に転換）

    # 7. Discord日次サマリー（自己進化日報 — embed fields構造化）
    logger.info("[Nightly] Step 7/8: Discord日次サマリー送信")
    try:
        elapsed = round(time.time() - batch_start, 1)
        _trunc = lambda s, n=300: (str(s)[:n-3] + "...") if len(str(s)) > n else str(s)

        fields = []

        # --- 自己進化セクション（Nightlyでしか報告されない情報） ---
        if voyager_nightly_text.strip():
            _voy_clean = voyager_nightly_text.strip()
            for _prefix in ["🔭 **Voyager学習**: ", "🔭 **Voyager**: "]:
                _voy_clean = _voy_clean.replace(_prefix, "")
            fields.append({"name": "🔭 Voyager学習", "value": _trunc(_voy_clean, 400), "inline": False})
        if evolver_nightly_text.strip():
            _evo_clean = evolver_nightly_text.strip()
            for _prefix in ["🧬 **EvolveR進化**: ", "🧬 **EvolveR**: "]:
                _evo_clean = _evo_clean.replace(_prefix, "")
            fields.append({"name": "🧬 EvolveR進化", "value": _trunc(_evo_clean, 400), "inline": False})
        if gplearn_nightly_text.strip():
            _gp_clean = gplearn_nightly_text.strip().replace("🧬 **gplearn G4**: ", "")
            fields.append({"name": "🧬 gplearn G4", "value": _trunc(_gp_clean, 300), "inline": False})

        # --- WAIT品質（Nightlyでしか報告されない） ---
        if wait_quality_text.strip():
            fields.append({"name": "⏸️ WAIT品質", "value": _trunc(wait_quality_text.strip(), 300), "inline": False})

        # --- 直近教訓（ChromaDBから） ---
        try:
            from core.memory_db import NeoMemoryDB
            _nm = NeoMemoryDB()
            _lessons = _nm.recall(query="trade lesson insight failure", n_results=3, where={"category": "trade_result"})
            _lesson_docs = _lessons.get("documents", [[]])[0] if _lessons else []
            if _lesson_docs:
                _lesson_lines = [f"• {d[:100]}" for d in _lesson_docs[:3] if isinstance(d, str)]
                fields.append({"name": "📝 直近の教訓", "value": "\n".join(_lesson_lines), "inline": False})
        except Exception:
            pass

        # フィールドがゼロなら最低限のステータスを追加
        if not fields:
            fields.append({"name": "✅ ステータス", "value": "全ステップ正常完了（進化データ蓄積中）", "inline": False})

        # Nightly専用チャンネルに送信
        import requests as _req
        _nightly_url = DiscordReporter.NIGHTLY_WEBHOOK or DiscordReporter.LOG_WEBHOOK
        _payload = {
            "embeds": [{
                "title": f"🌙 Nightly Batch Report — {today}",
                "description": f"⏱️ 実行時間: {elapsed}秒 | 自己進化サイクル完了",
                "color": 0x9b59b6,
                "fields": fields,
                "footer": {"text": "Neo自己進化日報 | Voyager+EvolveR+gplearn"},
            }]
        }
        _req.post(_nightly_url, json=_payload, timeout=10)
        logger.info(f"[Nightly] === バッチ完了 ({elapsed}秒) ===")
    except Exception as e:
        logger.error(f"[Nightly] サマリー送信失敗: {e}")

    # 7b. Moltbook活動レポート（独立embed送信）
    logger.info("[Nightly] Step 7b: Moltbook反響取得+活動レポート送信")
    try:
        from tools.moltbook_tracker import run_tracking
        _mt_summary = run_tracking()
        logger.info(f"[Nightly] MoltbookTracker: {_mt_summary[:100]}")
        DiscordReporter.send_moltbook_report()
    except Exception as e:
        logger.error("[Nightly] Moltbookレポート送信失敗: " + str(e))

    # Step 8: radar_output.log 自動切り詰め（最新10000行を保持）
    logger.info("[Nightly] Step 8/8: ログ自動切り詰め")
    try:
        import subprocess
        _log_path = "radar_output.log"
        _result = subprocess.run(["wc", "-l", _log_path], capture_output=True, text=True)
        _lines = int(_result.stdout.strip().split()[0])
        if _lines > 10000:
            # inode保持方式: tail→tmpに書き出し、元ファイルをtruncate+上書き（fdが切れない）
            subprocess.run(f"tail -10000 {_log_path} > {_log_path}.tmp", shell=True)
            with open(_log_path + '.tmp', 'r') as _tmp_f:
                _kept = _tmp_f.read()
            with open(_log_path, 'w') as _orig_f:
                _orig_f.write(_kept)
            import os; os.remove(_log_path + '.tmp')
            logger.info(f"[Nightly] ログ切り詰め: {_lines}行 → 10000行（inode保持）")
    except Exception as e:
        logger.error(f"[Nightly] ログ切り詰め失敗: {e}")


def start_hybrid_radar():
    print("=" * 60)
    print(f" 📡 Neo Hybrid Radar v2: UNIFIED TRIGGER MODE")
    print(f" ⏱️  Interval: {CHECK_INTERVAL}s | Vol: {VOLATILITY_THRESHOLD}% | Alpha: {ALPHA_THRESHOLD}")
    print(f" 🧊 Cooldown: {COUNCIL_COOLDOWN // 60}min")
    print("=" * 60)
    
    # 初期価格の取得（Tier1全銘柄）
    anchor_prices = {}
    for _sym in VOLATILITY_WATCH_SYMBOLS:
        _data = MarketData.fetch_token_data(_sym)
        _price = float(_data.get("priceUsd", 0.0)) if _data else 0.0
        if _price <= 0:
            logger.error(f"❌ {_sym} 初期価格取得失敗。5秒後リトライ...")
            time.sleep(5)
            _data = MarketData.fetch_token_data(_sym)
            _price = float(_data.get("priceUsd", 0.0)) if _data else 0.0
        anchor_prices[_sym] = _price
        logger.info(f"🎯 Anchor price [{_sym}]: ${_price:.6f}")
    anchor_price = anchor_prices.get("VIRTUAL", 0.0)  # ステータス表示用
    
    processed_alphas = {}     # 処理済みアルファのタイムスタンプ
    last_nightly_date = None  # 最後にNightly Batchを実行した日付
    last_council_time = 0     # 最後に評議会を開いた時刻
    cycle_count = 0
    consecutive_errors = 0
    last_trade_time = time.time()
    NO_TRADE_ALERT_HOURS = 24
    no_trade_alerted = False

    try:
        while True:
            cycle_count += 1
            current_time = time.time()
            time_since_last = current_time - last_council_time
            cooldown_remaining = max(0, COUNCIL_COOLDOWN - time_since_last)
            is_cooled_down = cooldown_remaining == 0
            
            trigger_type = None
            trigger_symbol = None
            trigger_context = None

            # ============================================================
            # 0. Alpha Sweep 自動実行（60分ごと）
            # ============================================================
            if cycle_count % EVAL_INTERVAL == 0:
                logger.info(f"[Evaluator] 定期評価開始 (cycle={cycle_count})")
                try:
                    evaluate_performance(send_dashboard=True)
                except Exception as e:
                    logger.error(f"[Evaluator] エラー: {e}")

            if cycle_count % CFR_INTERVAL == 0 and cycle_count > 0:
                try:
                    from tools.capital_flow_radar import run_capital_flow_radar
                    cfr = run_capital_flow_radar()
                    logger.info(f"📊 Capital Flow: score={cfr['score']} regime={cfr['regime']}")
                except Exception as e:
                    logger.error(f"Capital Flow Radar error: {e}")

            if cycle_count % SWEEP_INTERVAL == 0:
                logger.info(f"[Sweep] 定期スキャン開始 (cycle={cycle_count})")
                try:
                    run_sweep()
                    logger.info("[Sweep] 完了 — Blackboard更新済み")
                except Exception as e:
                    logger.error(f"[Sweep] エラー: {e}")

            # ============================================================
            # 0a-1b. Arbitrage Spread Monitor（30分ごと）
            # ============================================================
            # [v6.5ac] Arbitrage monitoring removed — see .archive_deadcode_v65p/
            # ============================================================
            # 0a-2. Moltbookエンゲージメント（2時間ごと）
            # ============================================================
            if cycle_count % ENGAGE_INTERVAL == 0:
                logger.info(f"[Engager] Moltbookエンゲージメント開始 (cycle={cycle_count})")
                try:
                    from tools.moltbook_engager import MoltbookEngager
                    engage_result = MoltbookEngager.run_engagement_cycle()
                    r = engage_result.get("replies", {})
                    f = engage_result.get("feed", {})
                    s = engage_result.get("search", {})
                    logger.info(f"[Engager] 完了 — 返信:{r.get('replied',0)} upvote:{f.get('upvoted',0)} コメント:{f.get('commented',0)} 営業:{s.get('commented',0)}")
                except Exception as e:
                    logger.error(f"[Engager] エラー: {e}")

            # ============================================================
            # 0a-3. Heartbeat稼働報告（30分ごと）
            # ============================================================
            if cycle_count > 0 and cycle_count % HEARTBEAT_INTERVAL == 0:
                try:
                    from tools.paper_wallet import PaperWallet as _HBW
                    _hbw = _HBW()
                    _hb_usdc = _hbw.state.get("usd_balance", 0)
                    _hb_holdings = _hbw.state.get("holdings", {})
                    _hb_hist = len(_hbw.state.get("history", []))
                    _hb_lines = []
                    _hb_lines.append("💰 USDC: ${:,.0f}".format(_hb_usdc))
                    _hb_total = _hb_usdc
                    for _hbs, _hbd in _hb_holdings.items():
                        try:
                            if _hbs in ('BTC','ETH'):
                                from orchestration.data_collector import get_latest_price_from_db
                                _hbpr = get_latest_price_from_db(_hbs) or 0
                            else:
                                _hbp = MarketData._fetch_price_from_geckoterminal(_hbs)
                                if not _hbp:
                                    _hbp = MarketData.fetch_token_data(_hbs)
                                _hbpr = float(_hbp.get('priceUsd', 0)) if _hbp and _hbp.get('status') == 'success' else 0
                            if _hbpr > 0:
                                _hb_val = _hbd["amount"] * _hbpr
                                _hb_total += _hb_val
                                _hb_pnl = ((_hbpr - _hbd["avg_price"]) / _hbd["avg_price"] * 100) if _hbd["avg_price"] > 0 else 0
                                _hb_lines.append("📊 {}: {} ({:+.2f}%)".format(_hbs, DiscordReporter._fmt_price(_hbpr, _hbs), _hb_pnl))
                        except Exception:
                            pass
                    _hb_lines.append("💎 Total: ${:,.0f}".format(_hb_total))
                    # Tier別勝率
                    try:
                        _hb_bb = NeoBlackboard.load()
                        _hb_ps = _hb_bb.get("performance_summary", {})
                        _hb_t0a = _hb_ps.get("tier0_accuracy", 0)
                        _hb_t0n = _hb_ps.get("tier0_trades", 0)
                        _hb_t1a = _hb_ps.get("tier1_accuracy", 0)
                        _hb_t1n = _hb_ps.get("tier1_trades", 0)
                        _hb_total_acc = _hb_ps.get("accuracy_score", 0)
                        _hb_total_n = _hb_ps.get("total_evaluated_trades", 0)
                        _hb_lines.append("🎯 勝率: {:.1f}% ({}件) | T0:{:.0f}%({}) T1:{:.0f}%({})".format(
                            _hb_total_acc, _hb_total_n, _hb_t0a, _hb_t0n, _hb_t1a, _hb_t1n))
                    except Exception:
                        _hb_lines.append("🎯 Learn: {}/{}".format(_hb_hist, LEARNING_TARGET_TRADES))
                    # CFOステータス
                    try:
                        _hb_cg = CostGuard()
                        _hb_dd_ok, _hb_dd_pct = _hb_cg.check_drawdown()
                        _hb_hwm = _hb_cg._breaker.get("hwm", 0)
                        _hb_dd_status = "✅ OK" if _hb_dd_ok else f"🚫 BLOCKED ({_hb_dd_pct:.1f}%)"
                        _hb_lines.append("🛡️ CFO: DD={} | HWM: ${:,.0f}".format(_hb_dd_status, _hb_hwm))
                    except Exception:
                        pass
                    # 次ローテーション情報
                    try:
                        import json as _hb_json
                        with open("vault/blackboard/live_intel.json", "r") as _hb_f:
                            _hb_bbi = _hb_json.load(_hb_f)
                        _hb_last_ts = float(_hb_bbi.get("last_unified_council_ts", 0))
                        _hb_last_sym = _hb_bbi.get("last_unified_council_symbol", "?")
                        _hb_rotation = ["BTC", "VIRTUAL", "ETH"]
                        _hb_next_idx = (_hb_rotation.index(_hb_last_sym) + 1) % len(_hb_rotation) if _hb_last_sym in _hb_rotation else 0
                        _hb_next_sym = _hb_rotation[_hb_next_idx]
                        _hb_elapsed = time.time() - _hb_last_ts
                        _hb_remain = max(0, UNIFIED_COUNCIL_INTERVAL_SEC - _hb_elapsed)
                        _hb_lines.append("⏰ Next: {} (残{:.0f}分)".format(_hb_next_sym, _hb_remain / 60))
                    except Exception:
                        pass
                    _hb_lines.append("🔄 Cycle: #{}".format(cycle_count))
                    DiscordReporter.send_log("💓 Heartbeat", chr(10).join(_hb_lines), 0x3498db)
                    logger.info("[Heartbeat] ✅ 送信完了 (cycle #{})".format(cycle_count))
                except Exception as _hbe:
                    logger.error("[Heartbeat] error: {}".format(_hbe))

            # ============================================================
            # 0b. Nightly Batch（JST 02:00 = UTC 17:00 に1日1回）
            # ============================================================
            now_utc = datetime.now(timezone.utc)
            now_jst_hour = (now_utc.hour + 9) % 24
            today_str = now_utc.strftime('%Y-%m-%d')
            if now_jst_hour == NIGHTLY_HOUR and last_nightly_date != today_str:
                last_nightly_date = today_str
                logger.info(f'[Nightly] 深夜バッチ開始 JST{now_jst_hour:02d}:00 ({today_str})')
                try:
                    _run_nightly_batch()
                except Exception as e:
                    logger.error(f'[Nightly] バッチ失敗: {e}')


            # ============================================================
            # 0-pre. 売却後価格追跡（v6.5ar）
            # ============================================================
            try:
                check_sell_aftermath()
            except Exception as _sa_e:
                logger.error(f'[売却追跡] メインループエラー: {_sa_e}')

            # ============================================================
            # 0. TP/SLサイクルチェック（毎30秒・Council非依存）
            # ============================================================
            try:
                if check_tp_sl_all_positions():
                    last_council_time = time.time()
                    logger.info("[TP/SL] 🧊 SELL発火 → 冷却開始（30分）")
                    time.sleep(CHECK_INTERVAL)
                    continue  # SL/TP発火サイクルではCouncil召集しない
            except Exception as _tpsl_e:
                logger.error(f"[TP/SL] サイクルチェックエラー: {_tpsl_e}")

                        # ============================================================
            # 1. ボラティリティ監視 (Tier1: VIRTUAL / AIXBT)
            # ============================================================
            current_price = anchor_prices.get("VIRTUAL", 0.0)  # ステータス表示用
            for _vsym in VOLATILITY_WATCH_SYMBOLS:
                try:
                    # SQLite優先（API呼び出し削減・429対策）
                    _vprice = get_latest_price_from_db(_vsym)
                    if _vprice is None:
                        _vdata = MarketData.fetch_token_data(_vsym)
                        _vprice = float(_vdata.get("priceUsd", 0.0)) if _vdata and _vdata.get("status") == "success" else 0.0
                    if _vprice > 0:
                        _anchor = anchor_prices.get(_vsym, 0.0)
                        _change = abs((_vprice - _anchor) / _anchor) * 100 if _anchor > 0 else 0

                        if _vsym == "VIRTUAL":
                            current_price = _vprice  # ステータス表示用更新

                        if _change >= VOLATILITY_THRESHOLD:
                            _dir = "上昇" if _vprice > _anchor else "下落"
                            logger.warning(f"🚨 [VOLATILITY] {_vsym} {_dir} {_change:.2f}% (${_anchor:.6f} → ${_vprice:.6f})")

                            if is_cooled_down and trigger_type is None:
                                trigger_type = "VOLATILITY"
                                trigger_symbol = _vsym
                                trigger_context = f"{_vsym}価格が{_change:.2f}%{_dir}（${_anchor:.6f}→${_vprice:.6f}）"
                            else:
                                logger.info(f"  ⏳ 冷却中（残り{int(cooldown_remaining/60)}分）— {_vsym}ボラトリガーを保留")

                        # アンカー価格はトリガー発火時のみ更新（毎サイクル更新すると30秒で2%必要になる）
                        if _change >= VOLATILITY_THRESHOLD:
                            anchor_prices[_vsym] = _vprice
                except Exception as e:
                    logger.error(f"ボラティリティ監視エラー [{_vsym}]: {e}")

            # ============================================================
            # 2. アルファ監視 (Blackboard経由)
            # ============================================================
            if trigger_type is None and is_cooled_down:
                try:
                    board = NeoBlackboard.load()
                    strat = board.get("strategic_intel", {})
                    opps = strat.get("active_opportunities", {})

                    eligible = []
                    council_ok = [sym + "/USDT" for sym in COUNCIL_ELIGIBLE_SYMBOLS]
                    for s, d in opps.items():
                        if s not in council_ok:
                            logger.debug(f"⏭️ [ALPHA] {s} はCouncil対象外 — スキップ")
                            continue
                        sharpe = d.get("sharpe", 0.0)
                        last_detected = d.get("last_detected")
                        if sharpe >= ALPHA_THRESHOLD and processed_alphas.get(s) != last_detected:
                            eligible.append((s, d))

                    if eligible:
                        eligible.sort(key=lambda x: x[1].get("sharpe", 0.0), reverse=True)
                        symbol, data = eligible[0]
                        
                        trigger_type = "ALPHA"
                        trigger_symbol = symbol
                        trigger_context = f"Alpha Sweep Hit: Sharpe={data['sharpe']}, confidence={data.get('confidence', 'N/A')}"
                        
                        logger.warning(f"🔥 [ALPHA] {symbol} (Sharpe: {data['sharpe']}) 採択")
                except Exception as e:
                    logger.error(f"アルファ監視エラー: {e}")

            # ============================================================
            # 2. 統合定期Council召集（タイムスタンプベース・2時間ローテーション）
            #    順序: BTC → VIRTUAL → ETH → BTC → ...（AIXBTはTier2降格 v6.5ab）
            #    リスタート耐性: Blackboardに最終実行時刻を永続保存
            # ============================================================
            if trigger_type is None:
                _rotation_symbols = ["BTC", "VIRTUAL", "ETH"]
                _now_ts = time.time()
                try:
                    import json as _json_uc
                    with open("vault/blackboard/live_intel.json", "r") as _f_uc:
                        _bb_uc = _json_uc.load(_f_uc)
                    _last_uc_ts = float(_bb_uc.get("last_unified_council_ts", 0))
                    _last_uc_sym = _bb_uc.get("last_unified_council_symbol", "")
                except Exception:
                    _last_uc_ts = 0
                    _last_uc_sym = ""
                _elapsed = _now_ts - _last_uc_ts
                if _elapsed >= UNIFIED_COUNCIL_INTERVAL_SEC:
                    if is_cooled_down:
                        # ローテーション: 前回の次の銘柄
                        if _last_uc_sym and _last_uc_sym in _rotation_symbols:
                            _uc_idx = (_rotation_symbols.index(_last_uc_sym) + 1) % len(_rotation_symbols)
                        else:
                            _uc_idx = 0
                        _uc_sym = _rotation_symbols[_uc_idx]
                        _uc_tier = "TIER0" if _uc_sym in TIER0_SYMBOLS else "PERIODIC"
                        trigger_type = _uc_tier
                        trigger_symbol = _uc_sym
                        trigger_context = f"定期Council（2時間ローテーション）: {_uc_sym}"
                        # Blackboardに記録（永続化）
                        try:
                            import json as _json_ucw
                            with open("vault/blackboard/live_intel.json", "r") as _f_ucw:
                                _bb_ucw = _json_ucw.load(_f_ucw)
                            _bb_ucw["last_unified_council_ts"] = _now_ts
                            _bb_ucw["last_unified_council_symbol"] = _uc_sym
                            with open("vault/blackboard/live_intel.json", "w") as _f_ucw:
                                _json_ucw.dump(_bb_ucw, _f_ucw, indent=2, ensure_ascii=False)
                        except Exception as _uc_err:
                            logger.warning(f"[COUNCIL] Blackboard書き込み失敗: {_uc_err}")
                        logger.info(f"⏰ [{_uc_tier}] 定期Council召集: {_uc_sym}（{_elapsed/3600:.1f}h経過）")
                    else:
                        logger.info(f"⏰ [COUNCIL] 定期Council時刻だが冷却中（残り{int(cooldown_remaining/60)}分）— スキップ")

            # ============================================================
            # 3. Council召集（トリガー発火時のみ）
            # ============================================================
            if trigger_type and trigger_symbol:
                # 最終ガード: COUNCIL_ELIGIBLE_SYMBOLSに含まれない銘柄はブロック
                _clean_sym = trigger_symbol.split('/')[0].strip()
                if _clean_sym not in COUNCIL_ELIGIBLE_SYMBOLS:
                    logger.warning(f"🚫 [GUARD] {trigger_symbol} はCOUNCIL_ELIGIBLE_SYMBOLS外 → Council召集ブロック")
                    trigger_type = None
                    trigger_symbol = None

            if trigger_type and trigger_symbol:
                # サーキットブレーカー: 全レイヤーチェック
                try:
                    _cg = CostGuard()
                    _cg_ok, _cg_reason = _cg.approve_council()
                    if not _cg_ok:
                        logger.warning(f"🚫 [CFO] Council召集ブロック: {_cg_reason}")
                        DiscordReporter.send_log(
                            "🚫 サーキットブレーカー発動",
                            f"**Trigger:** {trigger_type} {trigger_symbol}\n**Reason:** {_cg_reason}",
                            0xff6600
                        )
                        trigger_type = None
                        trigger_symbol = None
                except Exception as _cg_err:
                    logger.error(f"[CFO] サーキットブレーカーチェックエラー: {_cg_err}")

            if trigger_type and trigger_symbol:
                logger.info(f"🏛️ Council召集: [{trigger_type}] {trigger_symbol}")
                
                # Discord通知: Council開始
                DiscordReporter.send_log(
                    f"📡 Radar Trigger: {trigger_type}",
                    f"**Symbol:** {trigger_symbol}\n**Context:** {trigger_context}\n**Council召集中...**",
                    0xf39c12
                )
                
                try:
                    council = TrinityCouncil()
                    result = council.run(
                        sentiment_score=1.0 if trigger_type == "ALPHA" else 0.5,
                        context=trigger_context,
                        target_symbol=trigger_symbol
                    )
                    
                    last_council_time = time.time()
                    
                    # アルファの処理済みマーク
                    if trigger_type == "ALPHA":
                        board = NeoBlackboard.load()
                        opp_data = board.get("strategic_intel", {}).get("active_opportunities", {}).get(trigger_symbol, {})
                        processed_alphas[trigger_symbol] = opp_data.get("last_detected")
                    
                    verdict = result.get("verdict", "UNKNOWN")
                    logger.info(f"✅ Council完了: {verdict} | 冷却開始（{COUNCIL_COOLDOWN//60}分）")
                    consecutive_errors = 0
                    if verdict in ("BUY", "SELL"):
                        last_trade_time = time.time()
                        no_trade_alerted = False
                    # 取引後に勝率を即時更新
                    try:
                        evaluate_performance(send_dashboard=False)
                    except Exception as _e:
                        logger.error(f"[Evaluator] Post-council error: {_e}")
                    
                except Exception as e:
                    logger.error(f"⚠️ Council Error: {e}", exc_info=True)
                    last_council_time = time.time()  # エラー時も冷却開始（連続エラー防止）
                    consecutive_errors += 1
                    
                    DiscordReporter.send_log(
                        "❌ Council Error",
                        f"**Symbol:** {trigger_symbol}\n**Error:** {str(e)[:500]}",
                        0xe74c3c
                    )
                    if consecutive_errors >= 3:
                        DiscordReporter.send_log(
                            "🚨 連続エラー警告",
                            f"Councilが{consecutive_errors}回連続エラー。手動確認が必要です。",
                            0xff0000
                        )

            # ============================================================
            # 3b. 長時間無取引検知
            # ============================================================
            hours_since_trade = (time.time() - last_trade_time) / 3600
            if hours_since_trade > NO_TRADE_ALERT_HOURS and not no_trade_alerted:
                DiscordReporter.send_log(
                    "⏰ 無取引アラート",
                    f"直近の取引から {hours_since_trade:.1f} 時間経過。\n"
                    f"BUYデッドロック再発や市場データ障害の可能性。",
                    0xf39c12
                )
                no_trade_alerted = True
                logger.warning(f"[Monitor] 無取引 {hours_since_trade:.1f}h")

            # ============================================================
            # 4. ステータス表示
            # ============================================================
            if is_cooled_down:
                alpha_status = "🟢 Ready"
            else:
                alpha_status = f"🧊 Cooling ({int(cooldown_remaining/60)}m)"
            
            status = f"[Radar #{cycle_count}] VIRTUAL ${current_price:.4f} | {alpha_status}"
            
            # 100サイクルごとにログ出力（ノイズ抑制）
            if cycle_count % 100 == 0:
                logger.info(status)
            else:
                print(f"\r{status}", end="", flush=True)
            
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("\n[Radar] Terminated by Commander. 👋")

if __name__ == "__main__":
    start_hybrid_radar()
