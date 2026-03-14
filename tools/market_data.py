import requests
import json
import os
import time
import logging
import pandas as pd
from core.utils import NeoUtils

logger = logging.getLogger("neo.tools.market_data")

# シンボル → CoinGecko ID マッピング
COINGECKO_ID_MAP = {
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "VIRTUAL": "virtual-protocol",
    "BTC": "bitcoin",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "AIXBT": "aixbt",
}

class MarketData:
    BASE_URL = "https://api.dexscreener.com/latest/dex/search"
    COINGECKO_OHLC_URL = "https://api.coingecko.com/api/v3/coins/{}/ohlc"
    
    # Rate Limit対策: 最後のAPI呼び出し時刻
    _last_cg_call = 0
    _CG_INTERVAL = 6  # CoinGecko無料枠: 10-30 req/min → 6秒間隔で安全

    @staticmethod
    def _normalize_symbol(query: str) -> str:
        """クエリからクリーンなシンボル名を抽出"""
        symbol = query.strip().upper()
        # "ETH/USDT" → "ETH"
        if "/" in symbol:
            symbol = symbol.split("/")[0].strip()
        return symbol

    @staticmethod
    def _get_coingecko_id(symbol: str) -> str:
        """シンボルからCoinGecko IDを取得"""
        clean = MarketData._normalize_symbol(symbol)
        cg_id = COINGECKO_ID_MAP.get(clean)
        if not cg_id:
            # マップにない場合はシンボルをそのまま小文字で試す
            cg_id = clean.lower()
            logger.warning(f"No CoinGecko mapping for '{clean}', trying '{cg_id}'")
        return cg_id

    @staticmethod
    def _rate_limit_wait():
        """CoinGecko Rate Limit対策の待機"""
        elapsed = time.time() - MarketData._last_cg_call
        if elapsed < MarketData._CG_INTERVAL:
            wait_time = MarketData._CG_INTERVAL - elapsed
            logger.debug(f"Rate limit: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        MarketData._last_cg_call = time.time()

    @staticmethod
    def fetch_token_data(query: str):
        """DexScreenerからリアルタイム価格データを取得（既存互換）"""
        clean_symbol = MarketData._normalize_symbol(query)
        cache_file = f"data/market_cache_{clean_symbol}.json"
        try:
            params = {"q": query}
            response = requests.get(MarketData.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            pairs = data.get("pairs", [])
            if not pairs:
                raise ValueError(f"No pairs found for query: {query}")
            
            best_pair = pairs[0]
            price_usd = best_pair.get("priceUsd")
            if not price_usd or float(price_usd) <= 0:
                raise ValueError(f"Invalid price detected: {price_usd}")

            txns = best_pair.get("txns", {})
            m5_buys = txns.get("m5", {}).get("buys", 0)
            m5_sells = txns.get("m5", {}).get("sells", 0)
            whale_sentiment = "Accumulating" if m5_buys > (m5_sells * 2) and m5_buys > 5 else "Neutral"

            result = {
                "status": "success",
                "symbol": best_pair.get("baseToken", {}).get("symbol"),
                "name": best_pair.get("baseToken", {}).get("name"),
                "priceUsd": price_usd,
                "priceChange": best_pair.get("priceChange", {}),
                "volume": best_pair.get("volume", {}),
                "liquidity": best_pair.get("liquidity", {}),
                "txns": txns,
                "whale_sentiment": whale_sentiment,
                "timestamp": time.time()
            }
            NeoUtils.write_json(cache_file, result)
            return result
        except Exception as e:
            logger.warning(f"Market API error: {e}. Attempting cache recovery.")
            cached_data = NeoUtils.read_json(cache_file)
            if cached_data:
                cached_data["status"] = "success_from_cache"
                return cached_data
            return {"status": "error", "message": str(e)}

    @staticmethod
    def fetch_ohlcv_custom(query: str, days: int = 30) -> pd.DataFrame:
        """
        CoinGecko OHLC APIから実際の価格履歴を取得。
        
        Returns:
            pd.DataFrame with columns: [datetime, open, high, low, close]
            エラー時は空のDataFrameを返す
        """
        symbol = MarketData._normalize_symbol(query)
        cg_id = MarketData._get_coingecko_id(symbol)
        
        # キャッシュ確認（1時間以内のキャッシュがあれば再利用）
        cache_file = f"data/ohlcv_cache_{symbol}.json"
        cache_path = os.path.join("/docker/openclaw-taan/data/.openclaw/workspace", cache_file)
        
        if os.path.exists(cache_path):
            try:
                cache_age = time.time() - os.path.getmtime(cache_path)
                if cache_age < 3600:  # 1時間以内
                    with open(cache_path, "r") as f:
                        cached = json.load(f)
                    df = pd.DataFrame(cached, columns=["timestamp", "open", "high", "low", "close"])
                    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df = df.drop(columns=["timestamp"])
                    logger.info(f"OHLCV cache hit for {symbol}: {len(df)} candles")
                    return df
            except Exception as e:
                logger.warning(f"Cache read error for {symbol}: {e}")

        # CoinGecko API呼び出し（Rate Limit対策付き）
        MarketData._rate_limit_wait()
        
        try:
            url = MarketData.COINGECKO_OHLC_URL.format(cg_id)
            params = {"vs_currency": "usd", "days": days}
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list) or len(data) == 0:
                logger.error(f"CoinGecko returned empty/invalid data for {symbol}: {data}")
                return pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])
            
            # キャッシュに保存
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(data, f)
            
            # DataFrame変換: [timestamp_ms, open, high, low, close]
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.drop(columns=["timestamp"])
            
            logger.info(f"OHLCV fetched for {symbol}: {len(df)} candles ({days}d)")
            return df
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                logger.warning(f"CoinGecko rate limited for {symbol}. Using cache if available.")
            else:
                logger.error(f"CoinGecko HTTP error for {symbol}: {e}")
        except Exception as e:
            logger.error(f"OHLCV fetch failed for {symbol}: {e}")
        
        # フォールバック: 古いキャッシュがあれば使う
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    cached = json.load(f)
                df = pd.DataFrame(cached, columns=["timestamp", "open", "high", "low", "close"])
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.drop(columns=["timestamp"])
                logger.warning(f"Using stale cache for {symbol}: {len(df)} candles")
                return df
            except:
                pass
        
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])

    @staticmethod
    def get_token_price(symbol: str) -> dict:
        """既存互換: 単一価格取得"""
        data = MarketData.fetch_token_data(symbol)
        if data.get("status") in ["success", "success_from_cache"]:
            return {"priceUsd": float(data["priceUsd"]), "status": "success", "whale_sentiment": data.get("whale_sentiment")}
        return {"priceUsd": 0.0, "status": "error"}
