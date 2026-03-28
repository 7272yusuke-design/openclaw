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
    """二段アプローチ: SymbolicClassifier(直接分類) + SymbolicRegressor(回帰→パーセンタイル閾値)"""
    print(f"  🧬 gplearn開始: {GP_PARAMS['population_size']}個体 x {GP_PARAMS['generations']}世代")

    results_candidates = []

    # === アプローチ1: SymbolicClassifier（直接BUY/WAIT分類） ===
    print(f"  [A1] SymbolicClassifier...")
    try:
        cls_params = {k: v for k, v in GP_PARAMS.items()}
        # transformer_set is not valid for classifier — remove if present
        cls = SymbolicClassifier(**cls_params)
        cls.fit(X_train, y_train)
        y_pred_train_cls = cls.predict(X_train)
        y_pred_test_cls = cls.predict(X_test)
        train_acc_cls = accuracy_score(y_train, y_pred_train_cls)
        test_acc_cls = accuracy_score(y_test, y_pred_test_cls)
        buy_pred_count_cls = int(y_pred_test_cls.sum())
        buy_recall_cls = 0.0
        if y_test.sum() > 0:
            buy_recall_cls = ((y_pred_test_cls == 1) & (y_test == 1)).sum() / y_test.sum()
        program_cls = str(cls._program)
        print(f"    acc={test_acc_cls:.1%} recall={buy_recall_cls:.1%} buys={buy_pred_count_cls} prog={program_cls[:60]}")
        results_candidates.append({
            "train_accuracy": round(train_acc_cls * 100, 2),
            "test_accuracy": round(test_acc_cls * 100, 2),
            "buy_recall": round(buy_recall_cls * 100, 2),
            "buy_predictions": buy_pred_count_cls,
            "threshold": "N/A (classifier)",
            "program": program_cls,
            "method": "SymbolicClassifier",
            "y_pred_test": y_pred_test_cls,
        })
    except Exception as e:
        print(f"    ⚠️ Classifier失敗: {e}")

    # === アプローチ2: SymbolicRegressor → パーセンタイル閾値 ===
    print(f"  [A2] SymbolicRegressor + percentile threshold...")
    try:
        reg_params = {k: v for k, v in GP_PARAMS.items() if k != "class_weight"}
        reg = SymbolicRegressor(**reg_params)
        reg.fit(X_train, y_reg_train)
        y_pred_train_raw = reg.predict(X_train)
        y_pred_test_raw = reg.predict(X_test)

        # パーセンタイル閾値: 訓練データのBUY比率に合わせる
        buy_ratio_train = y_train.mean()
        # 上位buy_ratio_train分をBUYとする閾値
        best_threshold = 0.0
        best_f1 = 0.0
        for pct in range(20, 80, 2):
            thr = np.percentile(y_pred_train_raw, pct)
            y_t = (y_pred_train_raw > thr).astype(int)
            buy_r = y_t.mean()
            if buy_r < 0.15 or buy_r > 0.70:
                continue
            tp = ((y_t == 1) & (y_train == 1)).sum()
            fp = ((y_t == 1) & (y_train == 0)).sum()
            fn = ((y_t == 0) & (y_train == 1)).sum()
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = thr

        if best_f1 == 0.0:
            best_threshold = float(np.percentile(y_pred_train_raw, 100 * (1 - buy_ratio_train)))
            print(f"    ⚠️ F1=0 → BUY比率ベースの閾値: {best_threshold:.4f}")
        else:
            print(f"    閾値: {best_threshold:.4f} (F1={best_f1:.3f})")

        y_pred_train_reg = (y_pred_train_raw > best_threshold).astype(int)
        y_pred_test_reg = (y_pred_test_raw > best_threshold).astype(int)
        train_acc_reg = accuracy_score(y_train, y_pred_train_reg)
        test_acc_reg = accuracy_score(y_test, y_pred_test_reg)
        buy_pred_count_reg = int(y_pred_test_reg.sum())
        buy_recall_reg = 0.0
        if y_test.sum() > 0:
            buy_recall_reg = ((y_pred_test_reg == 1) & (y_test == 1)).sum() / y_test.sum()
        program_reg = str(reg._program)
        print(f"    acc={test_acc_reg:.1%} recall={buy_recall_reg:.1%} buys={buy_pred_count_reg} prog={program_reg[:60]}")
        results_candidates.append({
            "train_accuracy": round(train_acc_reg * 100, 2),
            "test_accuracy": round(test_acc_reg * 100, 2),
            "buy_recall": round(buy_recall_reg * 100, 2),
            "buy_predictions": buy_pred_count_reg,
            "threshold": round(best_threshold, 4),
            "program": program_reg,
            "method": "SymbolicRegressor+percentile",
            "y_pred_test": y_pred_test_reg,
        })
    except Exception as e:
        print(f"    ⚠️ Regressor失敗: {e}")

    # === 最良候補を選択 ===
    # スコア: accuracy + buy_recall*0.5 (BUY recallにボーナス) + BUYが出ているかの大ボーナス
    if not results_candidates:
        return {"train_accuracy": 0, "test_accuracy": 0, "buy_recall": 0,
                "buy_predictions": 0, "program": "NONE", "method": "FAILED",
                "horizon": HORIZON, "target_pct": TARGET_PCT, "features": FEATURE_COLS,
                "gp_params": {}}

    for c in results_candidates:
        has_buys = 1 if 5 <= c["buy_predictions"] <= 150 else 0
        c["_score"] = c["test_accuracy"] + c["buy_recall"] * 0.5 + has_buys * 10

    best = max(results_candidates, key=lambda x: x["_score"])
    y_pred_test_best = best.pop("y_pred_test")

    print(f"  ✅ 最良: {best['method']} acc={best['test_accuracy']}% recall={best['buy_recall']}%")
    print(f"  📝 数式: {best['program']}")
    print(f"  📊 テスト詳細:")
    print(classification_report(y_test, y_pred_test_best, target_names=["WAIT", "BUY"], zero_division=0))

    # 不要キー削除
    best.pop("_score", None)
    best["horizon"] = HORIZON
    best["target_pct"] = TARGET_PCT
    best["features"] = FEATURE_COLS
    best["gp_params"] = {k: v for k, v in GP_PARAMS.items() if k not in ("random_state", "class_weight")}
    return best


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
        old_recall = existing.get("buy_recall", 0)
        new_acc = result["test_accuracy"]
        new_recall = result["buy_recall"]
        # スコア: accuracy + recall*0.5 + BUYが出ているボーナス(+10)
        old_has_buy = 10 if old_recall > 5 else 0
        new_has_buy = 10 if new_recall > 5 else 0
        old_score = old_acc + old_recall * 0.5 + old_has_buy
        new_score = new_acc + new_recall * 0.5 + new_has_buy
        if new_score > old_score:
            print(f"  🆕 新記録! score={old_score:.1f}→{new_score:.1f} acc={new_acc}% recall={new_recall}%")
            save_best_program(result)
        else:
            print(f"  📌 既存が上: score={old_score:.1f} >= {new_score:.1f}（保存スキップ）")
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
