"""
K.3: VPオンチェーンイベント監視 — web3.pyによるクジラ検知
Base chain上のVIRTUAL/AIXBTトークンの大口Transferを監視する。
"""
import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = logging.getLogger("neo.whale_monitor")

# VIRTUALトークン ERC20 ABI（Transfer イベントのみ）
_ERC20_ABI = json.loads('[{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],"stateMutability":"view","type":"function"}]')

VP_CONTRACTS = {
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
    "AIXBT":   "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
}

BASE_PUBLIC_RPC     = "https://mainnet.base.org"  # 制限なし・無料
WHALE_THRESHOLD_USD = 10_000  # $10K以上を大口と判定（VIRTUAL $0.64で約15,600枚）
BLOCKS_TO_SCAN      = 300     # 約10分（Base: 2秒/block）
CACHE_FILE          = Path("data/whale_cache.json")
CACHE_TTL           = 300     # 5分キャッシュ

_w3 = None

def _get_w3():
    global _w3
    if _w3 and _w3.is_connected():
        return _w3
    try:
        from web3 import Web3
        rpc = os.environ.get("BASE_RPC_URL")
        if not rpc:
            logger.warning("[K.3] BASE_RPC_URL未設定")
            return None
        _w3 = Web3(Web3.HTTPProvider(rpc))
        if _w3.is_connected():
            logger.info(f"[K.3] Base chain接続 block={_w3.eth.block_number}")
        return _w3
    except Exception as e:
        logger.error(f"[K.3] web3接続失敗: {e}")
        return None

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
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def fetch_whale_events(symbol: str = "VIRTUAL") -> dict:
    """直近300ブロックの大口Transferを検出して返す。"""
    cache = _load_cache()
    key = f"whale_{symbol}"
    if key in cache:
        return cache[key]

    address = VP_CONTRACTS.get(symbol)
    if not address:
        return {"signal": "NEUTRAL", "whale_count": 0, "whale_volume_usd": 0, "large_txs": [], "scanned_blocks": BLOCKS_TO_SCAN}

    w3 = _get_w3()
    if not w3:
        return {"signal": "NEUTRAL", "whale_count": 0, "whale_volume_usd": 0, "large_txs": [], "scanned_blocks": BLOCKS_TO_SCAN}

    try:
        from web3 import Web3
        from datetime import datetime, timezone
        from tools.vp_onchain_data import fetch_dex_data

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=_ERC20_ABI
        )
        decimals  = contract.functions.decimals().call()
        dex       = fetch_dex_data(symbol)
        price_usd = dex.get("price_usd", 0)
        if price_usd == 0:
            return {"signal": "NEUTRAL", "whale_count": 0, "whale_volume_usd": 0, "large_txs": [], "scanned_blocks": BLOCKS_TO_SCAN}

        latest = w3.eth.block_number
        # requests経由でeth_getLogs（Base公式RPC・制限なし）
        import requests as _req
        _resp = _req.post(BASE_PUBLIC_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(latest - BLOCKS_TO_SCAN),
                "toBlock":   hex(latest),
                "address":   Web3.to_checksum_address(address),
                "topics":    ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
            }]
        }, timeout=15).json()
        raw_logs = _resp.get("result", [])
        events = []
        for log in raw_logs:
            try:
                events.append(contract.events.Transfer().process_log(log))
            except Exception:
                pass
                pass

        # Aerodrome Router除外（通常スワップはクジラではない）
        dex_addrs = {"0xcf77a3ba9a5ca399b7c97c74d54e5b1beb874e43"}

        large_txs = []
        seen_pairs = {}  # 同一ペア往復フィルタ
        for e in events:
            amt_tokens = e["args"]["value"] / 10**decimals
            amt_usd  = amt_tokens * price_usd
            from_a   = e["args"]["from"].lower()
            to_a     = e["args"]["to"].lower()
            if from_a in dex_addrs or to_a in dex_addrs:
                continue
            if amt_usd >= WHALE_THRESHOLD_USD:
                # 同一ペア往復検出（A→BとB→Aを両方カウントしない）
                pair_key = tuple(sorted([from_a[:10], to_a[:10]]))
                seen_pairs[pair_key] = seen_pairs.get(pair_key, 0) + 1
                if seen_pairs[pair_key] > 2:
                    continue  # 3回以上の往復はボット/内部移動とみなしスキップ
                large_txs.append({
                    "from":         e["args"]["from"][:10] + "...",
                    "to":           e["args"]["to"][:10] + "...",
                    "amount_usd":   round(amt_usd),
                    "amount_tokens": round(amt_tokens),
                    "tx_hash":      (e["transactionHash"].hex() if hasattr(e["transactionHash"], "hex") else e["transactionHash"])[:16] + "...",
                })

        vol    = sum(t["amount_usd"] for t in large_txs)
        signal = "WHALE_ACTIVE" if (len(large_txs) >= 2 or vol >= 200_000) else "NEUTRAL"

        result = {
            "symbol": symbol, "whale_count": len(large_txs),
            "whale_volume_usd": vol, "large_txs": large_txs[:5],
            "signal": signal, "scanned_blocks": BLOCKS_TO_SCAN,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        cache[key] = result
        _save_cache(cache)
        logger.info(f"[K.3] {symbol}: {len(large_txs)}件 ${vol:,.0f} signal={signal}")
        return result

    except Exception as e:
        logger.error(f"[K.3] クジラ監視エラー: {e}")
        return {"signal": "NEUTRAL", "whale_count": 0, "whale_volume_usd": 0, "large_txs": [], "scanned_blocks": BLOCKS_TO_SCAN}

def build_whale_context(symbol: str) -> str:
    """TrinityCouncilに注入するクジラ監視テキストを生成。"""
    r = fetch_whale_events(symbol)
    if r["signal"] == "WHALE_ACTIVE":
        return (f"[K.3 クジラ監視 - {symbol}]\n"
                f"  🐋 大口送金{r['whale_count']}件 / 総額${r['whale_volume_usd']:,.0f}\n"
                f"  ⚠️ クジラ活発 — ダマシの可能性を考慮せよ")
    return (f"[K.3 クジラ監視 - {symbol}]\n"
            f"  🔵 大口送金なし（直近{r['scanned_blocks']}ブロック）\n"
            f"  クジラ動向: 静穏")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for sym in ["VIRTUAL", "AIXBT"]:
        print(build_whale_context(sym))
        print()
