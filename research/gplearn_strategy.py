"""
gplearn Strategy — 遺伝的プログラミングによる取引戦略自動発見
Phase G1: 基盤構築
"""
import sys
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gplearn.genetic import SymbolicClassifier
from sklearn.metrics import accuracy_score, classification_report
from tools.market_data import MarketData
from feature_engineering.build_features import FeatureBuilder

# --- 設定 ---
HORIZON = 4          # 予測ホライズン（4足先 = 16h後）
TARGET_PCT = 0.01    # BUYシグナル閾値（1%以上の上昇）
TEST_RATIO = 0.20    # テスト分割比率
BEST_PROGRAM_PATH = Path("data/gplearn_best_program.json")

# Phase G2 でチューニング予定（G1はベースライン）
GP_PARAMS = {
    "population_size": 200,
    "generations": 10,
    "tournament_size": 5,
    "function_set": ["add", "sub", "mul", "div", "max", "min", "abs"],
    "parsimony_coefficient": 0.01,
    "max_samples": 0.8,
    "p_crossover": 0.7,
    "p_subtree_mutation": 0.1,
    "p_hoist_mutation": 0.05,
    "p_point_mutation": 0.1,
    "random_state": 42,
    "n_jobs": 1,
}

# 使用する特徴量（数値列のみ）
FEATURE_COLS = [
    "ma20", "ma50", "bb_bandwidth_20", "returns", "acceleration",
    "rsi_14", "ma_short", "ma_mid", "ma_long",
    "macd", "macd_signal", "macd_hist", "atr_14",
]


def prepare_data(symbol: str, days: int = 30) -> tuple:
    """OHLCVデータ取得 → 特徴量構築 → ターゲット変数生成 → 訓練/テスト分割"""
    print(f"  📊 データ取得: {symbol} ({days}日)")
    df = MarketData.fetch_ohlcv_custom(symbol, days=days)
    df = FeatureBuilder.build_from_memory(df)

    # ターゲット: HORIZON足先の価格が TARGET_PCT 以上上昇したら BUY(1)
    df["target"] = (df["close"].shift(-HORIZON) / df["close"] - 1 > TARGET_PCT).astype(int)

    # NaN除外（先頭の移動平均 + 末尾のshift分）
    df = df.dropna(subset=FEATURE_COLS + ["target"])

    X = df[FEATURE_COLS].values
    y = df["target"].values

    # 時系列分割（リーク防止: シャッフルしない）
    split_idx = int(len(X) * (1 - TEST_RATIO))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  📐 データ: {len(df)}行 → 訓練={len(X_train)} テスト={len(X_test)}")
    print(f"  🎯 BUY比率: 訓練={y_train.mean():.1%} テスト={y_test.mean():.1%}")

    return X_train, X_test, y_train, y_test, df


def train_and_evaluate(X_train, X_test, y_train, y_test) -> dict:
    """gplearn SymbolicClassifier で訓練・評価"""
    print(f"  🧬 gplearn開始: {GP_PARAMS['population_size']}個体 x {GP_PARAMS['generations']}世代")

    clf = SymbolicClassifier(**GP_PARAMS)
    clf.fit(X_train, y_train)

    y_pred_train = clf.predict(X_train)
    y_pred_test = clf.predict(X_test)

    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)

    # 発見された数式
    best_program = str(clf._program)

    print(f"  ✅ 訓練精度: {train_acc:.1%}")
    print(f"  ✅ テスト精度: {test_acc:.1%}")
    print(f"  📝 発見された数式: {best_program}")
    print(f"  📊 テスト詳細:")
    print(classification_report(y_test, y_pred_test, target_names=["WAIT", "BUY"], zero_division=0))

    return {
        "train_accuracy": round(train_acc * 100, 2),
        "test_accuracy": round(test_acc * 100, 2),
        "program": best_program,
        "horizon": HORIZON,
        "target_pct": TARGET_PCT,
        "features": FEATURE_COLS,
        "gp_params": {k: v for k, v in GP_PARAMS.items() if k != "random_state"},
    }


def save_best_program(result: dict):
    """最良プログラムをJSONに保存"""
    result["updated"] = datetime.now(timezone.utc).isoformat()
    BEST_PROGRAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BEST_PROGRAM_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  💾 保存: {BEST_PROGRAM_PATH}")


def run_gplearn_strategy(symbol: str = "VIRTUAL", days: int = 30) -> dict:
    """メインエントリポイント: 1銘柄のgplearn戦略探索"""
    print(f"\n🧬 gplearn戦略探索: {symbol}")
    print(f"{'=' * 50}")

    X_train, X_test, y_train, y_test, df = prepare_data(symbol, days)
    result = train_and_evaluate(X_train, X_test, y_train, y_test)
    result["symbol"] = symbol

    # 既存の最良結果と比較
    if BEST_PROGRAM_PATH.exists():
        with open(BEST_PROGRAM_PATH) as f:
            existing = json.load(f)
        if result["test_accuracy"] > existing.get("test_accuracy", 0):
            print(f"  🆕 新記録! {existing.get('test_accuracy', 0)}% → {result['test_accuracy']}%")
            save_best_program(result)
        else:
            print(f"  📌 既存が上: {existing.get('test_accuracy', 0)}% >= {result['test_accuracy']}%（保存スキップ）")
    else:
        save_best_program(result)

    return result


if __name__ == "__main__":
    results = {}
    for sym in ["VIRTUAL", "AIXBT"]:
        results[sym] = run_gplearn_strategy(sym, days=30)

    print(f"\n{'=' * 50}")
    print("📊 サマリー:")
    for sym, r in results.items():
        print(f"  {sym}: テスト精度={r['test_accuracy']}% 数式={r['program'][:60]}...")
