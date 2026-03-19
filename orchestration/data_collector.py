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
            # open/high/low/close を現在価格で埋める（ティックデータとして蓄積）
            conn.execute(
                "INSERT OR IGNORE INTO prices (symbol, timestamp, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (symbol, now_ms, price, price, price, price,
                 data.get("volume", {}).get("h1", 0))
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


def get_ohlcv_from_db(symbol: str, limit: int = 180) -> list:
    """
    SQLiteからOHLCVデータを取得。market_data.pyから呼ばれる。
    Returns: [[timestamp_ms, open, high, low, close], ...] or []
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            "SELECT timestamp, open, high, low, close FROM prices "
            "WHERE symbol=? ORDER BY timestamp DESC LIMIT ?",
            (symbol.upper(), limit)
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []
        # 昇順に並び替えて返す
        rows.reverse()
        return [list(r) for r in rows]
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

    while True:
        try:
            logger.info("--- Collecting ---")
            collect_once(conn)

            # 1日ごとにパージ
            if time.time() - last_purge > PURGE_INTERVAL:
                purge_old(conn)
                last_purge = time.time()

        except Exception as e:
            logger.error(f"Main loop error: {e}")

        time.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    main()
