"""
tools/crypto_news.py
クリプトニュースRSS取得モジュール（J.1: X/Twitter代替）
- CoinDesk / CoinTelegraph / The Block / Decrypt RSS
- VP/AI agent関連ニュースをフィルタリングしてSentimentCrewに注入
"""
import urllib.request
import re
import time
import logging

logger = logging.getLogger("neo.crypto_news")

_cache = {}
CACHE_TTL = 300  # 5分

VP_KEYWORDS = [
    "virtual", "virtuals", "virtual protocol", "aixbt", "ai agent", "ai agents",
    "luna", "base chain", "base network", "defi agent", "autonomous agent",
    "crypto agent", "trading agent", "on-chain ai", "aerodrome",
    "moltbook", "sentient", "ai token", "ai coin", "agent token",
]

MARKET_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "crypto", "defi", "altcoin", "bull", "bear", "rally",
    "dump", "pump", "liquidat", "fear", "greed",
]

RSS_SOURCES = {
    "CoinDesk":      "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "TheBlock":      "https://www.theblock.co/rss.xml",
    "Decrypt":       "https://decrypt.co/feed",
    "BlockworksDefi": "https://blockworks.co/feed",
    "DLNews":         "https://www.dlnews.com/arc/outboundfeeds/rss/",
}


def _fetch(url: str, timeout: int = 8) -> str:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"[CryptoNews] fetch失敗 {url}: {e}")
        return ""


def _extract_titles(content: str) -> list[str]:
    """RSSからタイトルを抽出（CDATA形式・通常形式両対応）"""
    titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', content)
    if not titles:
        titles = re.findall(r'<title>(.*?)</title>', content)
    # フィードタイトル（最初の1件）を除外 + HTMLエンティティ変換
    import html
    return [html.unescape(t.strip()) for t in titles[1:] if t.strip()]


def get_news(target_symbol: str = "") -> dict:
    """
    VP関連・市場全般ニュースを取得。
    Returns: {"vp_news": [...], "market_news": [...], "source_count": int}
    """
    cache_key = f"news_{target_symbol}"
    if cache_key in _cache and time.time() - _cache[cache_key]["ts"] < CACHE_TTL:
        return _cache[cache_key]["data"]

    target_clean = target_symbol.replace("/USDT", "").lower()
    vp_news = []
    market_news = []
    source_count = 0

    for source_name, url in RSS_SOURCES.items():
        content = _fetch(url)
        if not content:
            continue
        source_count += 1
        titles = _extract_titles(content)

        for title in titles[:30]:  # 各ソース最大30件をスキャン
            title_lower = title.lower()

            # VP/AI agent関連
            if any(k in title_lower for k in VP_KEYWORDS) or target_clean in title_lower:
                if title not in vp_news:
                    vp_news.append(title)

            # 市場全般
            elif any(k in title_lower for k in MARKET_KEYWORDS):
                if title not in market_news and len(market_news) < 5:
                    market_news.append(title)

    result = {
        "vp_news": vp_news[:5],
        "market_news": market_news[:3],
        "source_count": source_count,
    }
    _cache[cache_key] = {"ts": time.time(), "data": result}
    return result


def get_news_context_text(target_symbol: str = "") -> str:
    """
    SentimentCrewのcontextに注入するテキストを生成。
    """
    news = get_news(target_symbol)
    vp = news["vp_news"]
    market = news["market_news"]
    sources = news["source_count"]

    if not vp and not market:
        return ""

    lines = [f"【クリプトニュース ({sources}ソース)】"]

    if vp:
        lines.append("VP/AIエージェント関連:")
        for n in vp:
            lines.append(f"  - {n[:100]}")
    if market:
        lines.append("市場全般:")
        for n in market:
            lines.append(f"  - {n[:100]}")

    return "\n".join(lines)
