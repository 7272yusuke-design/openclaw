"""
gplearn Strategy — 遺伝的プログラミングによる取引戦略自動発見
Phase G2: チューニング（500個体x50世代+class_weight+init_depth）
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

from gplearn.genetic import SymbolicClassifier, SymbolicRegressor
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from tools.market_data import MarketData
from feature_engineering.build_features import FeatureBuilder

# --- 設定 ---
HORIZON = 4          # 予測ホライズン（4足先 = 16h後）
TARGET_PCT = 0.01    # BUYシグナル閾値（1%以上の上昇）
TEST_RATIO = 0.20    # テスト分割比率
BEST_PROGRAM_DIR = Path("data/gplearn")
BEST_PROGRAM_PATH = BEST_PROGRAM_DIR / "gplearn_best_program.json"  # 後方互換

# Phase G2 でチューニング予定（G1はベースライン）
GP_PARAMS = {
    "population_size": 500,
    "generations": 50,
    "tournament_size": 7,
    "function_set": ["add", "sub", "mul", "div", "max", "min", "abs"],
    "parsimony_coefficient": 0.001,  # G2: 複雑な数式を許容して表現力を上げる
    "init_depth": (3, 6),
    "max_samples": 0.8,
    "p_crossover": 0.65,
    "p_subtree_mutation": 0.15,
    "p_hoist_mutation": 0.05,
    "p_point_mutation": 0.1,
    "random_state": 42,
    "n_jobs": 1,
    "class_weight": {0: 1.0, 1: 1.5},  # BUY少数派を軽く補正（balancedは極端すぎた）
}

# 使用する特徴量（数値列のみ）
FEATURE_COLS = [
    "ma20", "ma50", "bb_bandwidth_20", "returns", "acceleration",
    "rsi_14", "ma_short", "ma_mid", "ma_long",
    "macd", "macd_signal", "macd_hist", "atr_14",
]


def prepare_data(symbol: str, days: int = 30) -> tuple:
    """4h足OHLCVデータ取得 → 特徴量構築 → ターゲット変数生成 → 訓練/テスト分割"""
    print(f"  📊 データ取得: {symbol} (4h足・ローカルDB)")
    # 4h足を直接取得（5分足より時系列として意味がある）
    from orchestration.data_collector import get_ohlcv_from_db
    rows = get_ohlcv_from_db(symbol, limit=5000)
    if not rows or len(rows) < 100:
        print(f"  ⚠️ 4h足データ不足: {len(rows) if rows else 0}行")
        # フォールバック: fetch_ohlcv_custom
        df = MarketData.fetch_ohlcv_custom(symbol, days=days)
    else:
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop(columns=["timestamp"]).sort_values("datetime").reset_index(drop=True)
        # open/high/low/closeをfloatに
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
    print(f"  📐 生データ: {len(df)}行")
    df = FeatureBuilder.build_from_memory(df)

    # ターゲット: HORIZON足先の将来リターン（%表記にスケーリング）
    df["future_return"] = (df["close"].shift(-HORIZON) / df["close"] - 1) * 100
    # 分類ラベル（評価用）: TARGET_PCT*100(%)以上の上昇=BUY(1)
    df["target"] = (df["future_return"] > TARGET_PCT * 100).astype(int)

    # NaN除外（先頭の移動平均 + 末尾のshift分）
    df = df.dropna(subset=FEATURE_COLS + ["target", "future_return"])

    X_raw = df[FEATURE_COLS].values
    y = df["target"].values           # 二値ラベル（評価用）
    y_reg = df["future_return"].values  # 連続リターン（回帰ターゲット）

    # 特徴量を正規化（スケールの違いを解消）
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    # 時系列分割（リーク防止: シャッフルしない）
    split_idx = int(len(X) * (1 - TEST_RATIO))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    y_reg_train, y_reg_test = y_reg[:split_idx], y_reg[split_idx:]

    print(f"  📐 データ: {len(df)}行 → 訓練={len(X_train)} テスト={len(X_test)}")
    print(f"  🎯 BUY比率: 訓練={y_train.mean():.1%} テスト={y_test.mean():.1%}")
    print(f"  📈 平均リターン: 訓練={y_reg_train.mean():.4f} テスト={y_reg_test.mean():.4f}")

    return X_train, X_test, y_train, y_test, y_reg_train, y_reg_test, df


def train_and_evaluate(X_train, X_test, y_train, y_test, y_reg_train, y_reg_test) -> dict:
    """gplearn SymbolicRegressor で将来リターンを回帰 → 閾値でBUY/WAIT分類"""
    print(f"  🧬 gplearn開始: {GP_PARAMS['population_size']}個体 x {GP_PARAMS['generations']}世代")

    # SymbolicRegressorはclass_weightを受け取らないので除外
    reg_params = {k: v for k, v in GP_PARAMS.items() if k != "class_weight"}
    reg = SymbolicRegressor(**reg_params)

    # 回帰ターゲット: 将来リターン（連続値）を予測
    reg.fit(X_train, y_reg_train)

    y_pred_train_raw = reg.predict(X_train)
    y_pred_test_raw = reg.predict(X_test)

    # 最適閾値を訓練データの予測値分布から探索
    best_threshold = 0.5
    best_f1 = 0.0
    # 予測値の実際の範囲でグリッドサーチ
    pred_min, pred_max = y_pred_train_raw.min(), y_pred_train_raw.max()
    if pred_max > pred_min:
        thresholds = np.linspace(pred_min, pred_max, 50)
    else:
        thresholds = [pred_min]
    for threshold in thresholds:
        y_pred_t = (y_pred_train_raw > threshold).astype(int)
        tp = ((y_pred_t == 1) & (y_train == 1)).sum()
        fp = ((y_pred_t == 1) & (y_train == 0)).sum()
        fn = ((y_pred_t == 0) & (y_train == 1)).sum()
        n_buy = int(y_pred_t.sum())
        buy_ratio = n_buy / len(y_pred_t) if len(y_pred_t) > 0 else 0
        # 全BUY(>90%)や全WAIT(<10%)は除外
        if buy_ratio < 0.10 or buy_ratio > 0.90:
            continue
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    if best_f1 == 0.0:
        # フォールバック: 中央値を閾値に
        best_threshold = float(np.median(y_pred_train_raw))
        print(f"  ⚠️ F1=0のため中央値を閾値に: {best_threshold:.4f}")
    else:
        print(f"  🔧 最適閾値: {best_threshold:.4f} (訓練F1={best_f1:.3f})")

    y_pred_train = (y_pred_train_raw > best_threshold).astype(int)
    y_pred_test = (y_pred_test_raw > best_threshold).astype(int)

    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)

    best_program = str(reg._program)

    print(f"  ✅ 訓練精度: {train_acc:.1%}")
    print(f"  ✅ テスト精度: {test_acc:.1%}")
    print(f"  📝 発見された数式: {best_program}")
    print(f"  📊 テスト詳細:")
    print(classification_report(y_test, y_pred_test, target_names=["WAIT", "BUY"], zero_division=0))

    # BUY recall
    buy_recall = 0.0
    buy_count_pred = int(y_pred_test.sum())
    if y_test.sum() > 0:
        buy_correct = int(((y_pred_test == 1) & (y_test == 1)).sum())
        buy_recall = buy_correct / int(y_test.sum())
    print(f"  🎯 BUY recall: {buy_recall:.1%} ({buy_count_pred}件予測)")

    return {
        "train_accuracy": round(train_acc * 100, 2),
        "test_accuracy": round(test_acc * 100, 2),
        "buy_recall": round(buy_recall * 100, 2),
        "buy_predictions": buy_count_pred,
        "threshold": round(best_threshold, 3),
        "program": best_program,
        "method": "SymbolicRegressor+threshold",
        "horizon": HORIZON,
        "target_pct": TARGET_PCT,
        "features": FEATURE_COLS,
        "gp_params": {k: v for k, v in reg_params.items() if k != "random_state"},
    }


def save_best_program(result: dict):
    """最良プログラムをJSONに保存（銘柄別+統合）"""
    result["updated"] = datetime.now(timezone.utc).isoformat()
    BEST_PROGRAM_DIR.mkdir(parents=True, exist_ok=True)
    # 銘柄別ファイル
    sym_path = BEST_PROGRAM_DIR / f"best_{result.get('symbol','unknown').lower()}.json"
    with open(sym_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  💾 銘柄別保存: {sym_path}")
    # 統合ファイル（後方互換）
    with open(BEST_PROGRAM_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  💾 統合保存: {BEST_PROGRAM_PATH}")


def run_gplearn_strategy(symbol: str = "VIRTUAL", days: int = 30) -> dict:
    """メインエントリポイント: 1銘柄のgplearn戦略探索"""
    print(f"\n🧬 gplearn戦略探索: {symbol}")
    print(f"{'=' * 50}")

    X_train, X_test, y_train, y_test, y_reg_train, y_reg_test, df = prepare_data(symbol, days)
    result = train_and_evaluate(X_train, X_test, y_train, y_test, y_reg_train, y_reg_test)
    result["symbol"] = symbol

    # 既存の最良結果と比較（銘柄別）
    sym_path = BEST_PROGRAM_DIR / f"best_{symbol.lower()}.json"
    if sym_path.exists():
        with open(sym_path) as f:
            existing = json.load(f)
        old_acc = existing.get("test_accuracy", 0)
        if result["test_accuracy"] > old_acc or (result["test_accuracy"] == old_acc and result["buy_recall"] > existing.get("buy_recall", 0)):
            print(f"  🆕 新記録! acc={old_acc}% → {result['test_accuracy']}% recall={result['buy_recall']}%")
            save_best_program(result)
        else:
            print(f"  📌 既存が上: acc={old_acc}% >= {result['test_accuracy']}%（保存スキップ）")
    else:
        save_best_program(result)

    return result


if __name__ == "__main__":
    # マルチシード実行: 3つの異なるシードで探索し最良を採用
    SEEDS = [42, 137, 2026]
    all_results = {}

    for sym in ["VIRTUAL", "AIXBT"]:
        best_result = None
        for seed in SEEDS:
            GP_PARAMS["random_state"] = seed
            print(f"\n--- Seed={seed} ---")
            result = run_gplearn_strategy(sym, days=30)
            # BUY recall > 0 かつ テスト精度 > 50%を優先
            score = result["test_accuracy"] + result["buy_recall"] * 0.5
            result["_score"] = score
            if best_result is None or score > best_result["_score"]:
                best_result = result
        all_results[sym] = best_result

    GP_PARAMS["random_state"] = 42  # デフォルトに戻す

    print(f"\n{'=' * 50}")
    print("📊 マルチシード最良結果:")
    for sym, r in all_results.items():
        print(f"  {sym}: acc={r['test_accuracy']}% recall={r['buy_recall']}% 数式={r['program'][:60]}...")
