"""
F5: マクロ資本フローデータ収集器
- yfinance: SPY, DX-Y.NYB, GC=F, ^TNX (30日分日足)
- CoinGecko: BTC Dominance
- vault/blackboard/macro_flow.json の macro_data フィールドに保存
"""

import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MACRO_FLOW_PATH = "vault/blackboard/macro_flow.json"

TICKERS = {
    "spy": "SPY",
    "dxy": "DX-Y.NYB",
    "gold": "GC=F",
    "us10y": "^TNX",
}


def _calc_change_pct(closes, days: int) -> float | None:
    """直近終値と days 日前の終値から変動率を計算"""
    if closes is None or len(closes) < days + 1:
        return None
    current = float(closes.iloc[-1])
    past = float(closes.iloc[-(days + 1)])
    if past == 0:
        return None
    return round((current - past) / past * 100, 2)


def _fetch_yfinance_data() -> dict:
    """yfinance で 4 指標の現在値 + 1d/7d/30d 変動率を取得"""
    import yfinance as yf

    result = {}
    for key, ticker in TICKERS.items():
        try:
            data = yf.download(ticker, period="35d", interval="1d", progress=False, auto_adjust=True)
            if data is None or data.empty:
                logger.warning(f"[macro_collector] No data for {ticker}")
                result[key] = {"error": "no_data"}
                continue

            closes = data["Close"]
            if hasattr(closes, "columns"):
                closes = closes.iloc[:, 0]

            current = float(closes.iloc[-1])
            result[key] = {
                "value": round(current, 4),
                "change_1d": _calc_change_pct(closes, 1),
                "change_7d": _calc_change_pct(closes, 5),   # 5 trading days ≈ 7 calendar days
                "change_30d": _calc_change_pct(closes, 22),  # 22 trading days ≈ 30 calendar days
                "ticker": ticker,
            }
            logger.info(f"[macro_collector] {key}: {current:.4f} (1d:{result[key]['change_1d']}%, 7d:{result[key]['change_7d']}%, 30d:{result[key]['change_30d']}%)")
        except Exception as e:
            logger.warning(f"[macro_collector] Failed to fetch {ticker}: {e}")
            result[key] = {"error": str(e)}

    return result


def _fetch_btc_dominance() -> dict:
    """CoinGecko /global から BTC Dominance を取得"""
    import requests

    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=15,
            headers={"accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        btc_dom = data.get("market_cap_percentage", {}).get("btc")
        if btc_dom is None:
            return {"error": "btc_dom_not_found"}
        return {
            "value": round(btc_dom, 2),
            "total_market_cap_usd": data.get("total_market_cap", {}).get("usd"),
        }
    except Exception as e:
        logger.warning(f"[macro_collector] Failed to fetch BTC dominance: {e}")
        return {"error": str(e)}


def collect_macro_data() -> dict:
    """全マクロデータを収集し macro_flow.json に保存"""
    logger.info("[macro_collector] Starting macro data collection...")

    yf_data = _fetch_yfinance_data()
    btc_dom = _fetch_btc_dominance()

    macro_data = {
        "spy": yf_data.get("spy", {}),
        "dxy": yf_data.get("dxy", {}),
        "gold": yf_data.get("gold", {}),
        "us10y": yf_data.get("us10y", {}),
        "btc_dominance": btc_dom,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    # 既存の macro_flow.json を読み込み、macro_data フィールドを追加/更新
    existing = {}
    if os.path.exists(MACRO_FLOW_PATH):
        try:
            with open(MACRO_FLOW_PATH, "r") as f:
                existing = json.load(f)
        except Exception:
            pass

    existing["macro_data"] = macro_data

    os.makedirs(os.path.dirname(MACRO_FLOW_PATH), exist_ok=True)
    with open(MACRO_FLOW_PATH, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    logger.info(f"[macro_collector] Saved macro_data to {MACRO_FLOW_PATH}")
    return macro_data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = collect_macro_data()
    print(json.dumps(result, indent=2, default=str))
