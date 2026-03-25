# 🧬 gplearn GSD計画 — 遺伝的戦略自動発見

> **作成日**: 2026/03/25
> **ゴール**: Neoが自分で取引戦略を発見・進化させる能力を獲得する
> **前提**: gplearn v0.4.3インストール済み、PoC 53%精度ベースライン

---

## 概要

現在の8戦略（EMA, RSI, MACD等）は全て人間が設計した固定ルール。
gplearnは遺伝的プログラミングで**数式ベースの戦略を自動発見**する。
成功すれば「Neo自身が市場に適応して戦略を進化させる」能力を持つ。

---

## Phase G1: 基盤構築（1セッション・60min）

### G1.1 gplearn戦略ファイル作成
- `research/gplearn_strategy.py` を新規作成
- SymbolicClassifier の基本パイプライン実装
- 入力: FeatureBuilder出力（20カラム）
- 出力: BUY(1) / WAIT(0) のバイナリ分類

### G1.2 ターゲット変数の設計
- PoC: 1足先 → **4足先（16h後）に変更**
- 理由: Neoの取引頻度は数時間〜1日。1足先は短すぎる
- `target = (close.shift(-4) / close - 1 > 0.01).astype(int)`
- 1%以上の上昇をBUYシグナルと定義

### G1.3 訓練/テスト分割
- 時系列分割: 直近20%をテスト、残り80%を訓練
- リーク防止: shift(-4)の最後4行を除外

**完了条件**: `./neo-env/bin/python research/gplearn_strategy.py` で精度が出力される

---

## Phase G2: チューニング（1セッション・60min）

### G2.1 個体数・世代数の拡大
- PoC: 200個体x10世代 → **500個体x50世代**
- `population_size=500, generations=50`
- 実行時間目安: 2-5分（CPU、特徴量20列x900行）

### G2.2 特徴量の最適化
- FeatureBuilder出力から数値列のみ抽出（market_regime等はエンコード）
- NaN行を除外（先頭50行程度）
- 正規化は不要（gplearnは数式探索なのでスケール不問）

### G2.3 演算子セットの調整
- デフォルト: +, -, x, /
- 追加候補: `max`, `min`, `abs`, `sqrt`
- `function_set=['add','sub','mul','div','max','min','abs']`

### G2.4 過学習防止
- `parsimony_coefficient=0.01`（複雑な数式にペナルティ）
- `max_samples=0.8`（サンプリング）
- `p_crossover=0.7, p_mutation=0.1`

**完了条件**: テストセット精度55%以上 or 意味のある数式が発見される

---

## Phase G3: バックテスト統合（1セッション・45min）

### G3.1 gplearn戦略をバックテストに追加
- `run_backtest.py` の `strategy_map` に `"gplearn_evolved"` を追加
- gplearn発見の数式でBUYシグナル生成 → `_manual_backtest()` で評価

### G3.2 Sharpeフィルター
- Sharpe > 0 の場合のみCouncilに提示（既存戦略と同じルール）
- confidence = gplearnテスト精度をベースに算出

### G3.3 永続化
- 発見された最良の数式を `data/gplearn_best_program.json` に保存
- 形式: `{"program": "...", "accuracy": 0.58, "updated": "..."}`

**完了条件**: `run_all_strategies()` に gplearn_evolved が含まれ、Sharpeが計算される

---

## Phase G4: Nightly進化（1セッション・45min）

### G4.1 Nightly Batchに進化ステップ追加
- Step 8.5（ログ切り詰めの前）に配置
- 最新30日データで1世代だけ進化（warm_start）
- 実行時間上限: 60秒

### G4.2 進化ログ
- `data/gplearn_evolution_log.json` に世代ごとの最良精度を蓄積
- Discord報告に「gplearn精度: XX%」を追加

### G4.3 戦略自動更新
- 新しい数式のテスト精度が既存を上回った場合のみ更新
- 既存数式は `data/gplearn_archive/` にバージョニング保存

**完了条件**: Nightly Batchで毎晩gplearnが1世代進化し、結果がログに記録される

---

## Phase G5: マルチホライズン（オプション・30min）

### G5.1 マルチホライズン
- 4足先に加えて8足先（32h）のターゲットも並行探索
- 最良精度のホライズンを自動選択

---

## 技術制約

- CPU: AMD EPYC 9354P 2vCPU — 大規模探索は時間がかかる
- RAM: 8GB — 500個体x50世代は問題なし
- データ: VIRTUAL/AIXBT各900行（4h足30日分）
- 実行場所: ./neo-env/bin/python
- 依存: gplearn==0.4.3, pandas, numpy, scikit-learn

---

## リスクと対策

| リスク | 対策 |
|---|---|
| 過学習 | parsimony_coefficient + テスト分割 + Sharpeフィルター |
| 実行時間 | Nightly進化は1世代のみ（60秒上限） |
| 無意味な数式 | trades < 3 は自動除外（既存Sharpeガードと同じ） |
| 精度が上がらない | 有用な負の結果として記録。人間設計戦略で継続 |

---

## 進捗トラッキング

| Phase | 状態 | 完了日 |
|---|---|---|
| G1: 基盤構築 | 未着手 | - |
| G2: チューニング | 未着手 | - |
| G3: バックテスト統合 | 未着手 | - |
| G4: Nightly進化 | 未着手 | - |
| G5: マルチホライズン | オプション | - |
