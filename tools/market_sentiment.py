"""
tools/market_sentiment.py
市場センチメント実データ取得モジュール（C.3）
- Fear & Greed Index (alternative.me)
- CoinGecko Trending
"""
import urllib.request
import json
import logging
import time

logger = logging.getLogger("neo.market_sentiment")

_cache = {}
CACHE_TTL = 300  # 5分キャッシュ


def _fetch_json(url: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def get_fear_and_greed() -> dict:
    """
    Fear & Greed Index を取得。
    Returns: {"value": int, "label": str, "score": float(-1.0~1.0)}
    """
    cache_key = "fng"
    if cache_key in _cache and time.time() - _cache[cache_key]["ts"] < CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        d = _fetch_json("https://api.alternative.me/fng/?limit=1")
        item = d["data"][0]
        value = int(item["value"])
        label = item["value_classification"]
        # 0-100 → -1.0~1.0 に変換
        score = (value - 50) / 50.0
        result = {"value": value, "label": label, "score": round(score, 3)}
        _cache[cache_key] = {"ts": time.time(), "data": result}
        return result
    except Exception as e:
        logger.warning(f"[FearGreed] 取得失敗: {e}")
        return {"value": 50, "label": "Neutral", "score": 0.0}


def get_trending_coins(limit: int = 5) -> list[dict]:
    """
    CoinGecko Trendingコインを取得。
    Returns: [{"symbol": str, "name": str, "rank": int}, ...]
    """
    cache_key = "trending"
    if cache_key in _cache and time.time() - _cache[cache_key]["ts"] < CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        d = _fetch_json("https://api.coingecko.com/api/v3/search/trending")
        coins = []
        for c in d.get("coins", [])[:limit]:
            item = c["item"]
            coins.append({
                "symbol": item["symbol"],
                "name": item["name"],
                "rank": item.get("market_cap_rank", 999),
            })
        _cache[cache_key] = {"ts": time.time(), "data": coins}
        return coins
    except Exception as e:
        logger.warning(f"[Trending] 取得失敗: {e}")
        return []


def get_market_context_text(target_symbol: str = "") -> str:
    """
    SentimentCrewのcontextに注入するテキストを生成。
    """
    fng = get_fear_and_greed()
    trending = get_trending_coins()

    trending_symbols = [c["symbol"].upper() for c in trending]
    target_clean = target_symbol.replace("/USDT", "").upper()
    is_trending = target_clean in trending_symbols

    trending_str = ", ".join(
        [f"{c['symbol']}(#{c['rank']})" for c in trending]
    ) if trending else "取得失敗"

    trending_note = f"⚡ {target_clean}はトレンド入りしている。" if is_trending else ""

    text = (
        f"【市場センチメント実データ】\n"
        f"Fear & Greed Index: {fng['value']}/100 ({fng['label']}) → score={fng['score']:+.2f}\n"
        f"CoinGecko Trending TOP5: {trending_str}\n"
        f"{trending_note}"
    )
    return text.strip()
