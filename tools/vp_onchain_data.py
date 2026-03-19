"""
VP Onchain Data Tool — VirtualsProtocol生態系のオンチェーン・DEXデータ取得
DexScreener API（無料・キー不要）を使用
"""
import os
import json
import time
import logging
import urllib.request
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("neo.vp_onchain")

# VP生態系銘柄のコントラクトアドレス（Base chain）
VP_CONTRACT_ADDRESSES = {
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
    "AIXBT":   "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
    "LUNA":    None,  # 検索APIで取得
}

CACHE_FILE = Path("data/vp_onchain_cache.json")
CACHE_TTL  = 300  # 5分キャッシュ


def _fetch_url(url: str) -> dict:
    """シンプルなHTTP GETラッパー。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Neo/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"[OnChain] fetch失敗 {url}: {e}")
        return {}


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if time.time() - data.get("_ts", 0) < CACHE_TTL:
                return data
        except Exception:
            pass
    return {}


def _save_cache(data: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["_ts"] = time.time()
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False))


def fetch_dex_data(symbol: str) -> dict:
    """
    DexScreener APIからDEX取引データを取得。
    戻り値:
        price_usd       : DEX価格
        volume_24h      : 24h取引量(USD)
        liquidity_usd   : 流動性(USD)
        price_change_24h: 24h価格変化(%)
        cex_dex_spread  : CEX-DEX価格乖離(%) ※CoinGeckoと比較
    """
    cache = _load_cache()
    cache_key = f"dex_{symbol}"
    if cache_key in cache:
        return cache[cache_key]

    address = VP_CONTRACT_ADDRESSES.get(symbol)
    if address:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    else:
        url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"

    data = _fetch_url(url)
    pairs = data.get("pairs", [])

    if not pairs:
        logger.warning(f"[OnChain] {symbol} DEXデータなし")
        return {}

    # 流動性が最も高いペアを採用
    best = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)

    result = {
        "symbol":           symbol,
        "price_usd":        float(best.get("priceUsd") or 0),
        "volume_24h":       float((best.get("volume") or {}).get("h24") or 0),
        "liquidity_usd":    float((best.get("liquidity") or {}).get("usd") or 0),
        "price_change_24h": float((best.get("priceChange") or {}).get("h24") or 0),
        "dex_name":         best.get("dexId", "unknown"),
        "chain":            best.get("chainId", "unknown"),
        "fetched_at":       datetime.now(timezone.utc).isoformat(),
    }

    cache[cache_key] = result
    _save_cache(cache)
    logger.info(f"[OnChain] {symbol} DEX: 価格=${result['price_usd']:.4f} 出来高=${result['volume_24h']:,.0f} 流動性=${result['liquidity_usd']:,.0f}")
    return result


def fetch_all_vp_dex_data() -> dict:
    """
    VP Tier1+2の全銘柄のDEXデータを一括取得。
    Blackboard更新用。
    """
    from core.config import SWEEP_SYMBOLS
    results = {}
    for symbol in SWEEP_SYMBOLS:
        results[symbol] = fetch_dex_data(symbol)
        time.sleep(1)  # Rate Limit対策
    return results


def build_onchain_context(symbol: str) -> str:
    """
    TrinityCouncilのプロンプトに注入するオンチェーン情報テキストを生成。
    """
    dex = fetch_dex_data(symbol)
    if not dex:
        return f"[オンチェーン] {symbol}: データ取得不可"

    lines = [f"[オンチェーン情報 - {symbol}]"]
    lines.append(f"  DEX価格: ${dex.get('price_usd', 0):.4f} ({dex.get('dex_name','?')} / {dex.get('chain','?')})")
    lines.append(f"  24h出来高: ${dex.get('volume_24h', 0):,.0f}")
    lines.append(f"  DEX流動性: ${dex.get('liquidity_usd', 0):,.0f}")

    change = dex.get("price_change_24h", 0)
    direction = "📈" if change > 0 else "📉"
    lines.append(f"  24h価格変化: {direction} {change:+.2f}%")

    # 流動性シグナル判定
    liq = dex.get("liquidity_usd", 0)
    if liq > 1_000_000:
        lines.append(f"  流動性シグナル: 🟢 HIGH（大口取引可能）")
    elif liq > 300_000:
        lines.append(f"  流動性シグナル: 🟡 MEDIUM")
    else:
        lines.append(f"  流動性シグナル: 🔴 LOW（スリッページ注意）")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== VP Onchain Data テスト ===")
    for sym in ["VIRTUAL", "AIXBT", "LUNA"]:
        print(build_onchain_context(sym))
        print()
