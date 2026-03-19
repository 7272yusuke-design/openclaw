"""
VP Discovery — Virtuals Protocol生態系の新興銘柄を自動発見
CoinGecko VP生態系カテゴリーから定期スキャンし、
スクリーニング基準を満たした銘柄をSweep監視リストに追加する。
毎週月曜 JST 04:00 に run_trigger.py から呼ばれる。
"""
import sys
import json
import time
import logging
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
sys.path.append(str(BASE_DIR))

from core.blackboard import NeoBlackboard
from core.memory_db import NeoMemoryDB

logger = logging.getLogger("neo.vp_discovery")

# スクリーニング基準
MIN_MARKET_CAP   = 5_000_000    # 時価総額 $5M以上
MIN_VOLUME_24H   = 500_000      # 24h出来高 $500K以上
MAX_SYMBOLS      = 10           # Sweep監視リスト上限

# 固定銘柄（常に含める）
CORE_SYMBOLS = ["VIRTUAL", "AIXBT", "LUNA"]

DISCOVERY_CACHE = Path("data/vp_discovery_cache.json")


def _fetch_vp_ecosystem() -> list:
    """CoinGecko VP生態系カテゴリーから銘柄一覧を取得。"""
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&category=virtuals-protocol-ecosystem"
        "&order=volume_desc&per_page=50&page=1"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Neo/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"[Discovery] CoinGecko取得失敗: {e}")
        return []


def run_vp_discovery() -> dict:
    """
    VP生態系をスキャンし、スクリーニング基準を満たす新興銘柄を発見。
    Blackboardの監視リストを更新し、発見銘柄をChromaDBに記録する。

    戻り値: {"added": [...], "removed": [...], "current": [...]}
    """
    logger.info("[Discovery] === VP新興銘柄スキャン開始 ===")

    coins = _fetch_vp_ecosystem()
    if not coins:
        logger.warning("[Discovery] データ取得失敗、スキャン中止")
        return {}

    # スクリーニング
    qualified = []
    for coin in coins:
        symbol = coin.get("symbol", "").upper()
        mc     = coin.get("market_cap") or 0
        vol    = coin.get("total_volume") or 0

        if mc >= MIN_MARKET_CAP and vol >= MIN_VOLUME_24H:
            qualified.append({
                "symbol":     symbol,
                "market_cap": mc,
                "volume_24h": vol,
                "price":      coin.get("current_price", 0),
            })
            logger.info(f"  ✅ {symbol}: MC=${mc:,.0f} 出来高=${vol:,.0f}")
        else:
            logger.info(f"  ❌ {symbol}: MC=${mc:,.0f} 出来高=${vol:,.0f} (基準未満)")

    # 出来高順でソートしてMAX_SYMBOLS件に絞る（CORE除く）
    non_core = [c for c in qualified if c["symbol"] not in CORE_SYMBOLS]
    non_core.sort(key=lambda x: x["volume_24h"], reverse=True)
    new_symbols = CORE_SYMBOLS + [c["symbol"] for c in non_core[:MAX_SYMBOLS - len(CORE_SYMBOLS)]]

    # 現在の監視リストと比較
    prev_cache = {}
    if DISCOVERY_CACHE.exists():
        try:
            prev_cache = json.loads(DISCOVERY_CACHE.read_text())
        except Exception:
            pass
    prev_symbols = prev_cache.get("symbols", CORE_SYMBOLS)

    added   = [s for s in new_symbols if s not in prev_symbols]
    removed = [s for s in prev_symbols if s not in new_symbols and s not in CORE_SYMBOLS]

    # キャッシュ更新
    DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_CACHE.write_text(json.dumps({
        "symbols":    new_symbols,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "qualified":  qualified,
    }, ensure_ascii=False))

    # Blackboardの監視リストを更新
    try:
        board = NeoBlackboard.load()
        board_data = board.get_all() if hasattr(board, "get_all") else {}
        # discovery_watchlist セクションに保存
        from core.blackboard import NeoBlackboard as _BB
        _BB.update("discovery_watchlist", {
            "symbols":    new_symbols,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "added":      added,
            "removed":    removed,
        })
        logger.info(f"[Discovery] Blackboard更新: {new_symbols}")
    except Exception as e:
        logger.error(f"[Discovery] Blackboard更新失敗: {e}")

    # ChromaDBに記録（追加銘柄のみ）
    if added:
        try:
            memory = NeoMemoryDB()
            memory.store(
                content=f"VP新興銘柄発見: {', '.join(added)}",
                metadata={
                    "category": "vp_discovery",
                    "tier": "3",
                    "symbols": ",".join(added),
                    "source": "coingecko_vp_ecosystem",
                }
            )
            logger.info(f"[Discovery] ChromaDB記録: {added}")
        except Exception as e:
            logger.error(f"[Discovery] ChromaDB記録失敗: {e}")

    logger.info(f"[Discovery] === スキャン完了 ===")
    logger.info(f"  監視リスト: {new_symbols}")
    logger.info(f"  新規追加: {added}")
    logger.info(f"  除外: {removed}")

    return {"added": added, "removed": removed, "current": new_symbols}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_vp_discovery()
    print(f"\n現在の監視リスト: {result.get('current', [])}")
    print(f"新規追加: {result.get('added', [])}")
