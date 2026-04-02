"""
I.1: ローカルデータ収集デーモン
5分ごとにTier1/2銘柄の価格をDexScreenerから取得し、SQLiteに蓄積する。
最大180日分保持（古いデータは自動パージ）。
"""
import sqlite3
import time
import logging
import os
import sys

sys.path.insert(0, "/docker/openclaw-taan/data/.openclaw/workspace")

from tools.market_data import MarketData
import requests

logger = logging.getLogger("neo.collector")
logger.setLevel(logging.INFO)
logger.propagate = False  # 親ロガーへの伝播を止めて二重出力を防ぐ
_fmt = logging.Formatter("%(asctime)s [Collector] %(message)s")
_fh = logging.FileHandler("collector.log")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
logger.addHandler(_fh)
logger.addHandler(_sh)

DB_PATH = "vault/market_db/prices.sqlite"
COLLECT_INTERVAL = 300          # 5分
PURGE_DAYS = 180                # 180日分保持
PURGE_INTERVAL = 86400          # 1日ごとにパージ

# 収集対象銘柄（Tier1+2）
COLLECT_SYMBOLS = ["VIRTUAL", "AIXBT", "LUNA"]

OHLCV_INTERVAL = 3600           # 60分ごとにOHLCVキャンドル取得
OHLCV_SYMBOLS = {
    "VIRTUAL": "0x3f0296BF652e19bca772EC3dF08b32732F93014A",
    "AIXBT":   "0xf1fdc83c3a336bdbdc9fb06e318b08eaddc82ff4",
}
GT_INTERVAL = 10  # GeckoTerminal Rate Limit: 10秒間隔


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol    TEXT    NOT NULL,
            timestamp INTEGER NOT NULL,
            open      REAL,
            high      REAL,
            low       REAL,
            close     REAL,
            volume    REAL,
            UNIQUE(symbol, timestamp)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_ts ON prices(symbol, timestamp)")
    conn.commit()
    return conn


def collect_once(conn):
    """全銘柄の現在価格を1件ずつ取得してINSERT"""
    now_ms = int(time.time() * 1000)
    inserted = 0
    for symbol in COLLECT_SYMBOLS:
        try:
            data = MarketData.fetch_token_data(symbol)
            if not data or data.get("status") != "success":
                logger.warning(f"fetch_token_data failed for {symbol}: {data}")
                continue
            price = float(data.get("priceUsd", 0))
            if price == 0:
                continue
            # 異常値フィルター: 直近価格との乖離が50%超なら棄却
            try:
                row = conn.execute(
                    "SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT 1",
                    (symbol,)
                ).fetchone()
                if row and row[0] > 0:
                    last_price = row[0]
                    deviation = abs(price - last_price) / last_price
                    if deviation > 0.5:
                        logger.warning(f"⚠️ {symbol} 異常値棄却: ${price:.6f} (前回${last_price:.6f}, 乖離{deviation:.1%})")
                        continue
            except Exception:
                pass  # 初回データ等はフィルターなしで通す
            # スナップショット価格（5分ティック）— open=high=low=closeだがvolume付き
            vol_h1 = 0
            try:
                vol_raw = data.get("volume", {})
                if isinstance(vol_raw, dict):
                    vol_h1 = float(vol_raw.get("h1", 0) or 0)
                else:
                    vol_h1 = float(vol_raw or 0)
            except (TypeError, ValueError):
                vol_h1 = 0
            conn.execute(
                "INSERT OR IGNORE INTO prices (symbol, timestamp, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (symbol, now_ms, price, price, price, price, vol_h1)
            )
            inserted += 1
            logger.info(f"  {symbol}: ${price:.6f}")
            time.sleep(1)   # DexScreener負荷対策
        except Exception as e:
            logger.error(f"collect error {symbol}: {e}")
    conn.commit()
    logger.info(f"Collected {inserted}/{len(COLLECT_SYMBOLS)} symbols")


def purge_old(conn):
    """180日より古いデータを削除"""
    cutoff_ms = int((time.time() - PURGE_DAYS * 86400) * 1000)
    cur = conn.execute("DELETE FROM prices WHERE timestamp < ?", (cutoff_ms,))
    conn.commit()
    if cur.rowcount > 0:
        logger.info(f"Purged {cur.rowcount} old rows (>{PURGE_DAYS}d)")


def collect_ohlcv_candles(conn):
    """GeckoTerminalから直近の4h足OHLCVキャンドルを取得してSQLiteに蓄積"""
    total_inserted = 0
    for symbol, pair_addr in OHLCV_SYMBOLS.items():
        try:
            url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{pair_addr}/ohlcv/hour"
            resp = requests.get(url,
                params={"aggregate": "4", "limit": 10},
                headers={"Accept": "application/json"},
                timeout=15)
            resp.raise_for_status()
            ohlcv_list = resp.json().get('data', {}).get('attributes', {}).get('ohlcv_list', [])
            inserted = 0
            for candle in ohlcv_list:
                ts_s = candle[0]
                o, h, l, c, v = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4]), float(candle[5])
                ts_ms = ts_s * 1000
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO prices (symbol, timestamp, open, high, low, close, volume) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (symbol, ts_ms, o, h, l, c, v)
                    )
                    inserted += 1
                except Exception:
                    pass
            conn.commit()
            total_inserted += inserted
            logger.info(f"  OHLCV candles {symbol}: {len(ohlcv_list)} fetched, {inserted} new")
            time.sleep(GT_INTERVAL)
        except Exception as e:
            logger.warning(f"OHLCV candle fetch error {symbol}: {e}")
    return total_inserted


def _aggregate_ticks_to_1h(conn, symbol: str, limit: int) -> list:
    """5分ティック(flat O=H=L=C)を1時間足OHLCVに集約する。
    12ティック/時間を集約するので、始値!=終値の本物のキャンドルが得られる。
    Returns: [[timestamp_ms, open, high, low, close], ...] 昇順
    """
    # limit時間分 = limit * 12 ティック分を取得（余裕を持って+50%）
    # フラットティック（DexScreener 5分足）のみ対象。GeckoTerminal 4hキャンドルを除外
    tick_limit = int(limit * 12 * 1.5)
    cur = conn.execute(
        "SELECT timestamp, close FROM prices "
        "WHERE symbol=? AND (open=high AND high=low AND low=close) "
        "ORDER BY timestamp DESC LIMIT ?",
        (symbol.upper(), tick_limit)
    )
    ticks = cur.fetchall()
    if len(ticks) < 2:
        return []
    # 昇順に
    ticks.reverse()
    # 1時間バケットに集約（timestamp_msを3600000で切り捨て）
    buckets = {}
    for ts_ms, price in ticks:
        hour_key = (ts_ms // 3600000) * 3600000
        if hour_key not in buckets:
            buckets[hour_key] = {"open": price, "high": price, "low": price, "close": price}
        else:
            b = buckets[hour_key]
            if price > b["high"]:
                b["high"] = price
            if price < b["low"]:
                b["low"] = price
            b["close"] = price  # 最後のティックが終値
    # リスト化して昇順ソート、最新limit件
    result = []
    for ts_ms in sorted(buckets.keys()):
        b = buckets[ts_ms]
        result.append([ts_ms, b["open"], b["high"], b["low"], b["close"]])
    # 最新limit件に制限
    if len(result) > limit:
        result = result[-limit:]
    return result


def get_ohlcv_from_db(symbol: str, limit: int = 180) -> list:
    """
    SQLiteからOHLCVデータを取得。market_data.pyから呼ばれる。
    優先順位:
      1. GeckoTerminal由来の本物のOHLCVキャンドル（O!=H or H!=L or L!=C）
      2. 5分ティックから1時間足に自前集約したキャンドル
    Returns: [[timestamp_ms, open, high, low, close], ...] or []
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Step 1: 本物のOHLCVキャンドルを試行（鮮度チェック付き）
        cur = conn.execute(
            "SELECT timestamp, open, high, low, close FROM prices "
            "WHERE symbol=? AND NOT (open=high AND high=low AND low=close) "
            "ORDER BY timestamp DESC LIMIT ?",
            (symbol.upper(), limit)
        )
        rows = cur.fetchall()
        if len(rows) >= 10:
            newest_ts = rows[0][0]  # DESC順なので先頭が最新
            age_hours = (time.time() * 1000 - newest_ts) / 3600000
            if age_hours <= 6:  # 6時間以内なら本物OHLCVを使用
                conn.close()
                rows_list = [list(r) for r in rows]
                rows_list.reverse()
                return rows_list
            logger.info(f"Real OHLCV for {symbol} is stale ({age_hours:.1f}h old), using tick aggregation")
        # Step 2: 不足時 → 5分ティックから1時間足を自前合成
        logger.info(f"Real OHLCV insufficient for {symbol} ({len(rows)} rows), aggregating from ticks")
        agg = _aggregate_ticks_to_1h(conn, symbol, limit)
        conn.close()
        if agg:
            logger.info(f"Aggregated {len(agg)} 1h candles for {symbol} from ticks")
        return agg
    except Exception as e:
        logger.warning(f"DB read error for {symbol}: {e}")
        return []


def get_latest_price_from_db(symbol: str) -> float | None:
    """SQLiteから最新価格を取得（ボラティリティ監視用・API呼び出し削減）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            "SELECT close, timestamp FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT 1",
            (symbol.upper(),)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        price, ts = row
        # 10分以上古いデータは使わない
        import time
        age_sec = (time.time() * 1000 - ts) / 1000
        if age_sec > 600:
            return None
        return float(price)
    except Exception as e:
        logger.warning(f"DB latest price error for {symbol}: {e}")
        return None

def get_db_stats() -> dict:
    """DB統計を返す（確認用）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        stats = {}
        for symbol in COLLECT_SYMBOLS:
            cur = conn.execute(
                "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM prices WHERE symbol=?",
                (symbol,)
            )
            count, ts_min, ts_max = cur.fetchone()
            stats[symbol] = {
                "count": count,
                "oldest": ts_min,
                "newest": ts_max,
            }
        conn.close()
        return stats
    except Exception:
        return {}


def main():
    logger.info("=== Neo Data Collector started ===")
    logger.info(f"Symbols: {COLLECT_SYMBOLS}")
    logger.info(f"Interval: {COLLECT_INTERVAL}s | Purge: {PURGE_DAYS}d")

    conn = get_db()
    last_purge = 0
    last_ohlcv = 0
    consecutive_errors = 0

    while True:
        try:
            logger.info("--- Collecting ---")
            collect_once(conn)

            # 60分ごとにGeckoTerminal OHLCVキャンドル取得
            if time.time() - last_ohlcv > OHLCV_INTERVAL:
                logger.info("--- OHLCV Candle Update ---")
                collect_ohlcv_candles(conn)
                last_ohlcv = time.time()

            # 1日ごとにパージ
            if time.time() - last_purge > PURGE_INTERVAL:
                purge_old(conn)
                last_purge = time.time()

            consecutive_errors = 0

        except Exception as e:
            logger.error(f"Main loop error: {e}")
            consecutive_errors += 1
            # DB接続が壊れた場合（readonly等）→ 再接続
            if consecutive_errors >= 3 or "readonly" in str(e).lower():
                logger.warning(f"DB connection may be broken ({consecutive_errors} consecutive errors), reconnecting...")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_db()
                # 書き込みテストで確認
                try:
                    conn.execute("CREATE TABLE IF NOT EXISTS _health (x INTEGER)")
                    conn.execute("DELETE FROM _health")
                    conn.execute("INSERT INTO _health VALUES (1)")
                    conn.commit()
                    logger.info("DB reconnection successful, write test passed")
                    consecutive_errors = 0
                except Exception as e2:
                    logger.error(f"DB reconnection failed: {e2}")

        time.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    main()
