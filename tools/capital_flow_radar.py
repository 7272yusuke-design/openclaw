"""
Capital Flow Radar — マクロ資金フロー分析モジュール

データソース:
  - yfinance: S&P500, VIX, 10年債, DXY, ゴールド
  - alternative.me: Crypto Fear & Greed Index
  - CoinGecko: BTC Dominance, Total MCap

スコアリング: ルールベース（z-score重み付け合算）
  → 将来HMMレジーム判定に差し替え可能

参考: economic-dashboard (yfinance統合), RegimeDetectionHMM (特徴量設計)
"""
import logging
import json
import os
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("neo.capital_flow")

# --- 設定 ---
BLACKBOARD_PATH = "vault/blackboard/macro_flow.json"

# 重み（計画書準拠）
WEIGHTS = {
    "vix":           0.25,
    "dxy":           0.20,
    "sp500":         0.15,
    "treasury_10y":  0.15,
    "gold":          0.10,
    "fear_greed":    0.10,
    "btc_dominance": 0.05,
}


# ============================
# データ取得層（指標ごとに独立関数）
# ============================

def _fetch_yfinance_changes() -> dict:
    """yfinanceから主要マクロ指標の変化率を取得（economic-dashboardパターン）"""
    import yfinance as yf

    tickers = {
        "sp500":        "^GSPC",
        "vix":          "^VIX",
        "treasury_10y": "^TNX",
        "dxy":          "DX-Y.NYB",
        "gold":         "GC=F",
    }
    results = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                latest = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                pct_change = (latest - prev) / prev * 100
                results[name] = {
                    "value": round(float(latest), 4),
                    "change_pct": round(float(pct_change), 4),
                }
            else:
                logger.warning(f"yfinance insufficient data for {symbol}")
        except Exception as e:
            logger.warning(f"yfinance error {symbol}: {e}")
    return results


def _fetch_fear_greed() -> dict:
    """Crypto Fear & Greed Index取得（alternative.me API）"""
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=2", timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if len(data) >= 2:
            current = int(data[0]["value"])
            previous = int(data[1]["value"])
            return {
                "value": current,
                "classification": data[0]["value_classification"],
                "change": current - previous,
            }
    except Exception as e:
        logger.warning(f"Fear & Greed fetch error: {e}")
    return {}


def _fetch_crypto_global() -> dict:
    """CoinGecko /global からBTC Dominance, Total MCap取得"""
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        resp.raise_for_status()
        g = resp.json().get("data", {})
        btc_dom = g.get("market_cap_percentage", {}).get("btc", 0)
        total_mcap = g.get("total_market_cap", {}).get("usd", 0)
        mcap_change = g.get("market_cap_change_percentage_24h_usd", 0)
        return {
            "btc_dominance": round(float(btc_dom), 2),
            "total_mcap_usd": total_mcap,
            "mcap_change_24h": round(float(mcap_change), 2),
        }
    except Exception as e:
        logger.warning(f"CoinGecko global fetch error: {e}")
    return {}


# ============================
# スコアリング層
# ============================

def _compute_score(yf_data: dict, fg_data: dict, cg_data: dict) -> tuple:
    """
    各指標を暗号資産にとっての資金フロースコアに変換。
    正 = crypto有利（Risk-On）、負 = crypto不利（Risk-Off）

    設計思想（RegimeDetectionHMM参考）:
    - 各指標の変化率を方向性スコア(-1〜+1)に変換
    - 重み付け合算 → -100〜+100スケール
    """
    scores = {}

    # VIX: 急騰 → 恐怖 → crypto不利（逆相関）
    if "vix" in yf_data:
        vix_chg = yf_data["vix"]["change_pct"]
        # VIX +10%以上で最大ペナルティ、-10%以下で最大ボーナス
        scores["vix"] = max(-1.0, min(1.0, -vix_chg / 10.0))

    # DXY: ドル高 → crypto不利（逆相関）
    if "dxy" in yf_data:
        dxy_chg = yf_data["dxy"]["change_pct"]
        scores["dxy"] = max(-1.0, min(1.0, -dxy_chg / 1.0))

    # S&P500: 上昇 → リスクオン → crypto有利（順相関）
    if "sp500" in yf_data:
        sp_chg = yf_data["sp500"]["change_pct"]
        scores["sp500"] = max(-1.0, min(1.0, sp_chg / 2.0))

    # 10年債利回り: 上昇 → 引き締め → crypto不利（逆相関）
    if "treasury_10y" in yf_data:
        tn_chg = yf_data["treasury_10y"]["change_pct"]
        scores["treasury_10y"] = max(-1.0, min(1.0, -tn_chg / 3.0))

    # ゴールド: 急騰 → 安全逃避 → crypto不利（逆相関）
    if "gold" in yf_data:
        gold_chg = yf_data["gold"]["change_pct"]
        scores["gold"] = max(-1.0, min(1.0, -gold_chg / 2.0))

    # Fear & Greed: Extreme Fear → 逆張りプラス
    if fg_data.get("value") is not None:
        fg_val = fg_data["value"]
        # 0=Extreme Fear → +1（逆張り買いシグナル）
        # 100=Extreme Greed → -1（過熱警告）
        scores["fear_greed"] = max(-1.0, min(1.0, (50 - fg_val) / 50.0))

    # BTC Dominance: 上昇 → altから資金流出 → 中立寄り
    if cg_data.get("mcap_change_24h") is not None:
        mcap_chg = cg_data["mcap_change_24h"]
        scores["btc_dominance"] = max(-1.0, min(1.0, mcap_chg / 5.0))

    # 重み付け合算
    total_score = 0.0
    total_weight = 0.0
    details = {}
    for key, weight in WEIGHTS.items():
        if key in scores:
            contribution = scores[key] * weight * 100
            total_score += contribution
            total_weight += weight
            details[key] = {
                "raw_score": round(scores[key], 3),
                "weight": weight,
                "contribution": round(contribution, 2),
            }

    # 重みの欠損分を補正
    if total_weight > 0 and total_weight < 1.0:
        total_score = total_score / total_weight

    total_score = max(-100, min(100, total_score))

    # レジーム判定
    if total_score >= 30:
        regime = "Risk-On"
    elif total_score <= -30:
        regime = "Risk-Off"
    else:
        regime = "Neutral"

    return round(total_score, 2), regime, details


# ============================
# メインエントリーポイント
# ============================

def run_capital_flow_radar() -> dict:
    """Capital Flow Radar実行 → Blackboard出力"""
    logger.info("=== Capital Flow Radar 起動 ===")

    # データ取得
    yf_data = _fetch_yfinance_changes()
    fg_data = _fetch_fear_greed()
    cg_data = _fetch_crypto_global()

    # スコアリング
    score, regime, details = _compute_score(yf_data, fg_data, cg_data)

    # 結果構築
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "regime": regime,
        "details": details,
        "raw": {
            "yfinance": yf_data,
            "fear_greed": fg_data,
            "crypto_global": cg_data,
        },
    }

    # Blackboard書き込み（既存のmacro_dataを保持してマージ）
    try:
        os.makedirs(os.path.dirname(BLACKBOARD_PATH), exist_ok=True)
        _existing_bb = {}
        if os.path.exists(BLACKBOARD_PATH):
            try:
                with open(BLACKBOARD_PATH, "r") as _ef:
                    _existing_bb = json.load(_ef)
            except Exception:
                pass
        _preserved_macro = _existing_bb.get("macro_data")
        result_merged = {**result}
        if _preserved_macro:
            result_merged["macro_data"] = _preserved_macro
        with open(BLACKBOARD_PATH, "w") as f:
            json.dump(result_merged, f, indent=2, default=str)
        logger.info(f"Blackboard更新: {BLACKBOARD_PATH}")
    except Exception as e:
        logger.error(f"Blackboard write error: {e}")

    logger.info(f"📊 Capital Flow Score: {score} | Regime: {regime}")
    for key, d in details.items():
        logger.info(f"  {key}: score={d['raw_score']} × weight={d['weight']} = {d['contribution']}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    result = run_capital_flow_radar()
    print(json.dumps(result, indent=2, default=str))
