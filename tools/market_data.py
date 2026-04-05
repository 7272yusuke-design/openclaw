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
    _GECKO_PAIRS = {
        "VIRTUAL": "0x3f0296BF652e19bca772EC3dF08b32732F93014A",
        "AIXBT":   "0xf1fdc83c3a336bdbdc9fb06e318b08eaddc82ff4",
        "TIBBIR":  "0x0c3b466104545efa096b8f944c1e524e1d0d4888",  # TIBBIR/VIRTUAL 流動性$2.6M
        "ROBO":    "0x0bdf1509320b344131b257c66871f34de26f953d",   # ROBO/VIRTUAL 1% 流動性$550K
        # LUNA: Solanaチェーントークンのため GeckoTerminal(Base chain) 対象外
        # CoinGecko経由で価格取得する
    }
    
    # Rate Limit対策: 最後のAPI呼び出し時刻
    _last_cg_call = 0
    _CG_INTERVAL = 6  # CoinGecko無料枠: 10-30 req/min → 6秒間隔で安全
    _last_gt_call = 0
    _GT_INTERVAL = 10  # GeckoTerminal無料枠: 6req/min → 10秒間隔で安全

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
    def _fetch_price_from_geckoterminal(symbol: str):
        """GeckoTerminalからVP銘柄の価格取得（Base chain DEX実データ）"""
        import requests as _req
        # GeckoTerminal レートリミット制御
        elapsed = time.time() - MarketData._last_gt_call
        if elapsed < MarketData._GT_INTERVAL:
            wait_time = MarketData._GT_INTERVAL - elapsed
            logger.debug(f"GT rate limit: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        MarketData._last_gt_call = time.time()
        clean = symbol.split('/')[0].strip().upper()
        pair_address = MarketData._GECKO_PAIRS.get(clean)
        if not pair_address:
            return None
        try:
            url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{pair_address}"
            resp = _req.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            attrs = data.get("data", {}).get("attributes", {})
            price = float(attrs.get("base_token_price_usd", 0) or 0)
            if price <= 0:
                return None
            vol_24h = float(attrs.get("volume_usd", {}).get("h24", 0) or 0)
            price_change_24h = float(attrs.get("price_change_percentage", {}).get("h24", 0) or 0)
            return {
                "status": "success",
                "symbol": clean,
                "name": clean,
                "priceUsd": str(price),
                "priceChange": {"h24": price_change_24h},
                "volume": {"h24": vol_24h},
                "liquidity": {},
                "txns": {},
                "whale_sentiment": "Neutral",
                "timestamp": time.time()
            }
        except Exception as e:
            logger.warning(f"GeckoTerminal price fetch error for {symbol}: {e}")
            return None

    @staticmethod
    def fetch_btc_trend() -> dict:
        """BTC価格トレンドを3段階（24h/30d/180d）で取得
        新興トークンのバックテスト不足を補うマクロフィルターとして使用
        データソース: Binance API（APIキー不要）"""
        try:
            # 日足180本取得（30d/180d変化率算出用）
            resp = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": "BTCUSDT", "interval": "1d", "limit": 180},
                timeout=15
            )
            resp.raise_for_status()
            klines = resp.json()
            if len(klines) < 30:
                return {}

            price_now  = float(klines[-1][4])   # close
            price_30d  = float(klines[-30][1])   # open of 30d ago
            price_180d = float(klines[0][1])     # open of 180d ago

            # 24h変化率はBinance 24hrティッカーから取得
            resp24 = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "BTCUSDT"},
                timeout=10
            )
            resp24.raise_for_status()
            change_24h = float(resp24.json().get("priceChangePercent", 0))

            change_30d  = (price_now - price_30d)  / price_30d  * 100
            change_180d = (price_now - price_180d) / price_180d * 100

            # トレンド判定
            def _trend(c30, c180):
                if c180 < -20 and c30 < 0:
                    return "長期下落トレンド🔴"
                elif c180 < -20 and c30 >= 0:
                    return "長期下落・短期反発⚠️"
                elif c180 >= 0 and c30 >= 0:
                    return "長期上昇トレンド🟢"
                elif c180 >= 0 and c30 < 0:
                    return "長期上昇・短期調整🟡"
                else:
                    return "中立横ばい⚪"

            trend_label = _trend(change_30d, change_180d)

            return {
                "price": price_now,
                "change_24h": round(change_24h, 2),
                "change_30d": round(change_30d, 2),
                "change_180d": round(change_180d, 2),
                "trend": trend_label
            }
        except Exception as e:
            logger.warning(f"fetch_btc_trend error: {e}")
            return {}

    @staticmethod
    def _fetch_price_from_coingecko(symbol: str):
        """CoinGecko simple/price APIで価格取得（主要銘柄専用）"""
        cg_id = COINGECKO_ID_MAP.get(symbol)
        if not cg_id:
            return None
        try:
            MarketData._rate_limit_wait()
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": cg_id, "vs_currencies": "usd",
                      "include_24hr_change": "true", "include_24hr_vol": "true"}
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if cg_id not in data:
                return None
            d = data[cg_id]
            price = d.get("usd", 0.0)
            if not price or price <= 0:
                return None
            return {
                "status": "success",
                "symbol": symbol,
                "name": symbol,
                "priceUsd": str(price),
                "priceChange": {"h24": d.get("usd_24h_change", 0.0)},
                "volume": {"h24": d.get("usd_24h_vol", 0.0)},
                "liquidity": {},
                "txns": {},
                "whale_sentiment": "Neutral",
                "timestamp": time.time()
            }
        except Exception as e:
            logger.warning(f"CoinGecko price fetch error for {symbol}: {e}")
            return None

    @staticmethod
    def fetch_token_data(query: str):
        """リアルタイム価格データを取得。
        VP銘柄(VIRTUAL/AIXBT/LUNA): GeckoTerminal優先
        主要銘柄(ETH/SOL/BNB等): CoinGecko優先
        その他: DexScreener使用
        """
        clean_symbol = MarketData._normalize_symbol(query)
        cache_file = f"data/market_cache_{clean_symbol}.json"

        # VP銘柄はGeckoTerminalを優先（DexScreenerの誤マッチを防ぐ）
        if clean_symbol in MarketData._GECKO_PAIRS:
            gt_result = MarketData._fetch_price_from_geckoterminal(clean_symbol)
            if gt_result:
                NeoUtils.write_json(cache_file, gt_result)
                return gt_result
            logger.warning(f"GeckoTerminal failed for {clean_symbol}, falling back")

        # CoinGecko IDマップにある主要銘柄はCoinGeckoを優先
        if clean_symbol in COINGECKO_ID_MAP:
            cg_result = MarketData._fetch_price_from_coingecko(clean_symbol)
            if cg_result:
                NeoUtils.write_json(cache_file, cg_result)
                return cg_result
            logger.warning(f"CoinGecko failed for {clean_symbol}, falling back to DexScreener")

            # CoinGecko失敗時: DexScreenerの歪み価格を避けるためキャッシュ優先
            try:
                cached = NeoUtils.read_json(cache_file)
                if cached and float(cached.get("priceUsd", 0)) > 0:
                    _cache_age = time.time() - cached.get("timestamp", 0)
                    if _cache_age < 1800:  # 30分以内のキャッシュなら使う
                        logger.info(f"Using cached price for {clean_symbol} (age={_cache_age:.0f}s)")
                        return cached
            except Exception:
                pass

        # DexScreener（VP銘柄 or CoinGeckoフォールバック）
        try:
            params = {"q": query}
            response = requests.get(MarketData.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            pairs = data.get("pairs", [])
            if not pairs:
                raise ValueError(f"No pairs found for query: {query}")

            # 流動性が最も高いペアを選択（pairs[0]の無条件使用をやめる）
            best_pair = max(pairs, key=lambda p: float(
                p.get("liquidity", {}).get("usd", 0) or 0))
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
    def fetch_ohlcv_geckoterminal(symbol: str, days: int = 30) -> pd.DataFrame:
        """
        GeckoTerminal API で Base chain DEX の OHLCV を取得（APIキー不要）
        CoinGeckoより高品質なDEXデータ
        """
        clean = symbol.split('/')[0].strip().upper()
        pair_address = MarketData._GECKO_PAIRS.get(clean)
        if not pair_address:
            return pd.DataFrame()
        try:
            # 4時間足・最大1000件
            limit = min(days * 6, 1000)
            url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{pair_address}/ohlcv/hour"
            resp = requests.get(url,
                params={"aggregate": "4", "limit": limit},
                headers={"Accept": "application/json"},
                timeout=15)
            resp.raise_for_status()
            ohlcv_list = resp.json().get('data', {}).get('attributes', {}).get('ohlcv_list', [])
            if not ohlcv_list:
                return pd.DataFrame()
            df = pd.DataFrame(ohlcv_list, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
            df = df.drop(columns=["timestamp", "volume"])
            df = df.sort_values("datetime").reset_index(drop=True)
            logger.info(f"GeckoTerminal OHLCV for {clean}: {len(df)} candles")
            return df
        except Exception as e:
            logger.warning(f"GeckoTerminal fetch failed for {clean}: {e}")
            return pd.DataFrame()

    @staticmethod
    def fetch_ohlcv_binance(symbol: str, days: int = 30) -> pd.DataFrame:
        """Binance klines APIからOHLCVを取得（BTC/ETH専用フォールバック）"""
        BINANCE_PAIRS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
        pair = BINANCE_PAIRS.get(symbol.upper())
        if not pair:
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])
        try:
            limit = min(days * 24, 1000)
            resp = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": pair, "interval": "1h", "limit": limit},
                timeout=15
            )
            resp.raise_for_status()
            klines = resp.json()
            if not klines:
                return pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])
            rows = []
            for k in klines:
                rows.append([int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4])])
            df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close"])
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.drop(columns=["timestamp"])
            logger.info(f"OHLCV from Binance API for {symbol}: {len(df)} rows")
            return df
        except Exception as e:
            logger.warning(f"Binance OHLCV fetch error for {symbol}: {e}")
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])

    @staticmethod
    def fetch_ohlcv_custom(query: str, days: int = 30) -> pd.DataFrame:
        """
        OHLCVデータ取得。優先順位:
          1. ローカルSQLite（data_collector蓄積済みデータ）
          1.5. GeckoTerminal API（DEX高品質データ・APIキー不要）
          2. CoinGecko API（フォールバック）
        
        Returns:
            pd.DataFrame with columns: [datetime, open, high, low, close]
            エラー時は空のDataFrameを返す
        """
        symbol = MarketData._normalize_symbol(query)
        cg_id = MarketData._get_coingecko_id(symbol)

        # --- Step 1: ローカルSQLite参照（I.1 data_collector蓄積データ） ---
        try:
            from orchestration.data_collector import get_ohlcv_from_db
            limit = days * 24 * 12  # 5分足換算（最大）
            db_rows = get_ohlcv_from_db(symbol, limit=min(limit, 5000))
            if len(db_rows) >= 10:  # 最低10件あれば使用
                df = pd.DataFrame(db_rows, columns=["timestamp", "open", "high", "low", "close"])
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.drop(columns=["timestamp"])
                logger.info(f"OHLCV from local DB for {symbol}: {len(df)} rows")
                return df
            else:
                logger.info(f"Local DB insufficient for {symbol} ({len(db_rows)} rows), falling back to GeckoTerminal")
        except Exception as e:
            logger.warning(f"Local DB read failed for {symbol}: {e}, falling back to GeckoTerminal")

        # --- Step 1.5: GeckoTerminal API（DEX高品質OHLCVデータ） ---
        try:
            gt_df = MarketData.fetch_ohlcv_geckoterminal(symbol, days)
            if len(gt_df) >= 10:
                logger.info(f"OHLCV from GeckoTerminal for {symbol}: {len(gt_df)} rows")
                return gt_df
        except Exception as e:
            logger.warning(f"GeckoTerminal failed for {symbol}: {e}")

        # --- Step 1.7: Binance API直接（BTC/ETH用フォールバック） ---
        if symbol.upper() in ("BTC", "ETH"):
            try:
                bn_df = MarketData.fetch_ohlcv_binance(symbol, days)
                if len(bn_df) >= 10:
                    return bn_df
            except Exception as e:
                logger.warning(f"Binance fallback failed for {symbol}: {e}")

        # --- Step 2: CoinGecko API（フォールバック） ---
        # CoinGecko IDマップにない銘柄（ROBO, TIBBIR等）はスキップ（404回避）
        if symbol not in COINGECKO_ID_MAP:
            logger.info(f"No CoinGecko ID for {symbol} — skipping CoinGecko OHLCV fallback")
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])

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
