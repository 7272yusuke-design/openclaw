"""
Neo Arbitrage Monitor v2.0
Base chain内のDEXプール間スプレッド監視

戦略: 同一チェーン上の複数プール間の価格差を検知
  - Aerodrome Slipstream / Aerodrome Base / Uniswap V3 / Uniswap V2 / PancakeSwap V3
  - GeckoTerminal pools API で全プール一括取得
  - CoinGecko CEX価格は参考値として併記

Phase 1: スプレッド検知 + ログ蓄積 + Discordアラート
Phase 2: 収益性バックテスト（データ蓄積後）
Phase 3: 自動執行（実取引移行後 — アトミックswap）
"""
import time
import json
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("neo.tools.arbitrage_monitor")

# --- 設定 ---
SPREAD_ALERT_THRESHOLD = 1.5   # アラート閾値（%）
MIN_LIQUIDITY_USD = 50000      # 最低流動性（これ未満のプールは無視）
SPREAD_LOG_FILE = "data/arbitrage_spreads.json"
MAX_LOG_ENTRIES = 5000          # ログ上限（約7日分 @30分間隔）

# 監視対象トークン（Base chain上のコントラクトアドレス）
ARB_TOKENS = {
    "VIRTUAL": {
        "address": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
        "coingecko_id": "virtual-protocol",
    },
    "AIXBT": {
        "address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
        "coingecko_id": "aixbt",
    },
}

# DEX名の短縮マップ
DEX_SHORT = {
    "aerodrome-slipstream": "Aero-SL",
    "aerodrome-base": "Aero-V2",
    "uniswap-v3-base": "UniV3",
    "uniswap-v2-base": "UniV2",
    "uniswap-v4-base": "UniV4",
    "pancakeswap-v3-base": "PCSv3",
    "pancakeswap-v2-base": "PCSv2",
}


def _fetch_pools_from_geckoterminal(token_address: str) -> list:
    """GeckoTerminal APIで指定トークンの全Base chainプールを取得"""
    import requests
    from tools.market_data import MarketData

    # GeckoTerminal rate limit制御
    elapsed = time.time() - MarketData._last_gt_call
    if elapsed < MarketData._GT_INTERVAL:
        time.sleep(MarketData._GT_INTERVAL - elapsed)
    MarketData._last_gt_call = time.time()

    try:
        url = f"https://api.geckoterminal.com/api/v2/networks/base/tokens/{token_address}/pools"
        resp = requests.get(url, params={"page": 1}, timeout=15)
        resp.raise_for_status()
        raw_pools = resp.json().get("data", [])

        pools = []
        for pool in raw_pools:
            attrs = pool.get("attributes", {})
            rels = pool.get("relationships", {})
            dex_id = rels.get("dex", {}).get("data", {}).get("id", "unknown")
            pool_addr = pool.get("id", "").replace("base_", "")
            name = attrs.get("name", "?")

            price_str = attrs.get("base_token_price_usd", "0")
            price = float(price_str) if price_str else 0.0
            liq_str = attrs.get("reserve_in_usd", "0")
            liq = float(liq_str) if liq_str else 0.0
            vol_str = (attrs.get("volume_usd") or {}).get("h24", "0")
            vol24 = float(vol_str) if vol_str else 0.0

            # VIRTUALが実際にbase_tokenであるペアのみ対象
            # X/VIRTUAL形式のプール（TIBBIR/VIRTUAL等）はbase_priceがX側の値を返すため除外
            # 判定: プール名の先頭がシンボルで始まるかチェック
            # 例: "VIRTUAL / WETH" → OK, "AIXBT / VIRTUAL" → NG
            pool_name_upper = name.upper()
            # token_symbolは呼び出し元から渡す（後述）
            # base_token_price_usdが妥当な範囲かもチェック
            # CoinGecko参考価格の50%～200%の範囲外は異常値として除外
            if price < 0.001 or price > 1000:
                continue
            # 最低流動性フィルタ
            if liq < MIN_LIQUIDITY_USD:
                continue

            pools.append({
                "pool_address": pool_addr,
                "dex": dex_id,
                "dex_short": DEX_SHORT.get(dex_id, dex_id[:8]),
                "name": name,
                "price": price,
                "liquidity": liq,
                "volume_24h": vol24,
            })

        return pools
    except Exception as e:
        logger.error(f"GeckoTerminal pools fetch error: {e}")
        return []


def _fetch_coingecko_price(cg_id: str) -> float:
    """CoinGecko（CEX集約）から参考価格取得"""
    import requests
    from tools.market_data import MarketData
    MarketData._rate_limit_wait()
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": cg_id, "vs_currencies": "usd"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        price = resp.json().get(cg_id, {}).get("usd", 0)
        return float(price) if price and float(price) > 0 else 0.0
    except Exception as e:
        logger.warning(f"CoinGecko fetch error for {cg_id}: {e}")
        return 0.0


def _calc_spread(price_a: float, price_b: float) -> float:
    """2つの価格間のスプレッド(%)"""
    if price_a <= 0 or price_b <= 0:
        return 0.0
    mid = (price_a + price_b) / 2
    return abs(price_a - price_b) / mid * 100


def _load_spread_log() -> list:
    if not os.path.exists(SPREAD_LOG_FILE):
        return []
    try:
        with open(SPREAD_LOG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_spread_log(entries: list):
    if len(entries) > MAX_LOG_ENTRIES:
        entries = entries[-MAX_LOG_ENTRIES:]
    try:
        with open(SPREAD_LOG_FILE, "w") as f:
            json.dump(entries, f)
    except Exception as e:
        logger.error(f"Spread log save error: {e}")


def check_arbitrage_spreads() -> dict:
    """全監視トークンのプール間スプレッドをチェック

    Returns:
        {
            "timestamp": "...",
            "results": {
                "VIRTUAL": {
                    "pools": [...],
                    "cex_price": 0.65,
                    "max_spread_pct": 2.1,
                    "best_opportunity": {"buy_pool": ..., "sell_pool": ..., "spread": 2.1},
                    "alert": True
                }
            },
            "alerts": [...]
        }
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    results = {}
    alerts = []

    for symbol, config in ARB_TOKENS.items():
        logger.info(f"[Arb] {symbol} プール取得中...")

        pools = _fetch_pools_from_geckoterminal(config["address"])
        cex_price = _fetch_coingecko_price(config["coingecko_id"])

        # CEX価格を基準に±50%以内のプールのみ残す
        # （TIBBIR/VIRTUAL等、base_tokenがVIRTUALでないペアを除外）
        if cex_price > 0 and pools:
            before_count = len(pools)
            low = cex_price * 0.5
            high = cex_price * 1.5
            pools = [p for p in pools if low <= p["price"] <= high]
            filtered = before_count - len(pools)
            if filtered > 0:
                logger.debug(f"[Arb] {symbol}: {filtered} non-target pools filtered out")

        if len(pools) < 2:
            logger.info(f"[Arb] {symbol}: プール{len(pools)}件 — 比較不可、スキップ")
            results[symbol] = {
                "pools": pools,
                "cex_price": cex_price,
                "max_spread_pct": 0.0,
                "best_opportunity": None,
                "alert": False,
            }
            continue

        # 全プールペアのスプレッドを計算
        prices = [(p["price"], p) for p in pools]
        prices.sort(key=lambda x: x[0])

        cheapest_price, cheapest_pool = prices[0]
        expensive_price, expensive_pool = prices[-1]
        max_spread = _calc_spread(cheapest_price, expensive_price)

        opportunity = {
            "buy_pool": {
                "dex": cheapest_pool["dex_short"],
                "name": cheapest_pool["name"],
                "price": round(cheapest_price, 6),
                "liquidity": round(cheapest_pool["liquidity"], 2),
            },
            "sell_pool": {
                "dex": expensive_pool["dex_short"],
                "name": expensive_pool["name"],
                "price": round(expensive_price, 6),
                "liquidity": round(expensive_pool["liquidity"], 2),
            },
            "spread_pct": round(max_spread, 4),
        }

        is_alert = max_spread >= SPREAD_ALERT_THRESHOLD

        # ログ用のプール情報（簡潔版）
        pools_summary = [
            {
                "dex": p["dex_short"],
                "price": round(p["price"], 6),
                "liq": round(p["liquidity"], 0),
            }
            for p in pools
        ]

        results[symbol] = {
            "pools": pools_summary,
            "pool_count": len(pools),
            "cex_price": round(cex_price, 6),
            "max_spread_pct": round(max_spread, 4),
            "best_opportunity": opportunity,
            "alert": is_alert,
        }

        if is_alert:
            msg = (
                f"🔔 {symbol} プール間スプレッド {max_spread:.2f}% 検知！"
                f" BUY: {cheapest_pool['dex_short']} ${cheapest_price:.4f}"
                f" → SELL: {expensive_pool['dex_short']} ${expensive_price:.4f}"
                f" (CEX参考: ${cex_price:.4f})"
            )
            alerts.append(msg)
            logger.warning(msg)
        else:
            logger.info(
                f"[Arb] {symbol}: {len(pools)}プール max_spread={max_spread:.2f}%"
                f" (min=${cheapest_price:.4f}@{cheapest_pool['dex_short']}"
                f" max=${expensive_price:.4f}@{expensive_pool['dex_short']})"
            )

    # ログ保存
    log_entry = {"timestamp": timestamp, "results": results}
    spread_log = _load_spread_log()
    spread_log.append(log_entry)
    _save_spread_log(spread_log)

    return {"timestamp": timestamp, "results": results, "alerts": alerts}


def send_arbitrage_discord_alert(alerts: list, results: dict):
    """スプレッドアラートをDiscordに送信"""
    try:
        from tools.discord_reporter import DiscordReporter

        lines = ["## 📊 Arbitrage Spread Alert\n"]
        for symbol, data in results.items():
            emoji = "🔴" if data["alert"] else "🟢"
            opp = data.get("best_opportunity")
            if opp:
                lines.append(
                    f"{emoji} **{symbol}**: max spread **{data['max_spread_pct']:.2f}%**"
                    f" across {data['pool_count']} pools"
                )
                lines.append(
                    f"  └ BUY {opp['buy_pool']['dex']} ${opp['buy_pool']['price']:.4f}"
                    f" → SELL {opp['sell_pool']['dex']} ${opp['sell_pool']['price']:.4f}"
                )
                lines.append(f"  └ CEX ref: ${data['cex_price']:.4f}")
            else:
                lines.append(f"🔘 **{symbol}**: insufficient pools")

        message = "\n".join(lines)
        DiscordReporter.send_log("🔀 Arbitrage Spread Alert", message, 0xe74c3c)
        logger.info("[Arb] Discord alert sent")
    except Exception as e:
        logger.error(f"[Arb] Discord alert error: {e}")


def get_spread_summary() -> str:
    """直近24時間のスプレッド統計サマリー（Nightly Batch用）"""
    spread_log = _load_spread_log()
    if not spread_log:
        return "No arbitrage data yet."

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent = [e for e in spread_log if e["timestamp"] >= cutoff]
    if not recent:
        return "No arbitrage data in last 24h."

    lines = [f"📊 Arbitrage Summary (24h, {len(recent)} checks):"]
    for symbol in ARB_TOKENS:
        spreads = [
            e["results"][symbol]["max_spread_pct"]
            for e in recent
            if symbol in e.get("results", {})
            and e["results"][symbol].get("max_spread_pct", 0) > 0
        ]
        if not spreads:
            continue
        avg_s = sum(spreads) / len(spreads)
        max_s = max(spreads)
        alert_n = sum(1 for s in spreads if s >= SPREAD_ALERT_THRESHOLD)
        lines.append(
            f"  {symbol}: avg={avg_s:.2f}% max={max_s:.2f}% alerts={alert_n}"
        )
    return "\n".join(lines)
