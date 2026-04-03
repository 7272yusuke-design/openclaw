# 📐 GSD計画 v6.5ai 引き継ぎ白書

> **更新日時**: 2026/04/03 11:30 JST
> **セッション**: v6.5ai（F1戦略別exit_profile + F2 BTC急落リスク管理 + 二重ペナルティ修正）
> **自己採点**: 90/100（F1/F2実装完了 + confidence阻害要因3件解消。BUY発生は次セッション確認）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続 |
| USDC | $87,979.91 |
| Holdings | なし |
| サービス | 全4サービス稼働中 |
| CFO L4 | 正常（DD=0.58%, 閾値5%）HWM $88,494 |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄） |
| bt_confidence | **HIGH** |
| 最終confidence | **43前回→53〜58見込み**（streak解消04/04 03:23 UTC以降） |
| 自己進化 | E1-E3+Phase1e完了 — 5層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: F1 戦略別exit_profile（short/mid/long）
- EXIT_PROFILESをmean_reversion/trend_follow/evolved → **short/mid/long** に再定義
- STRATEGY_TO_EXIT_PROFILEを3:3:3新戦略に完全対応

| プロファイル | SL | Trail Start/Drop | TP | RSI出口 | 時間上限 |
|---|---|---|---|---|---|
| **short** | -3% | +5%/-2.5% | +14% | >65 | 192h(8日) |
| **mid** | -5% | +10%/-4% | +25% | >72 | 408h(17日) |
| **long** | -8% | +15%/-6% | +50% | 無効 | 1080h(45日) |

- Phase 0第3層: RSI閾値をプロファイル別に動的参照（long=スキップ）

### Task 2: E3 sentiment_range二重適用防止
- R_wl_ratio_bad（sentiment_range条件）がPhase 4bのsent減点と二重ペナルティだった
- timezone同様にsentiment_range型ルールをE3でスキップ
- **効果**: evol -5 → 0（常時+5改善）

### Task 3: ニュース過多警戒閾値引き上げ
- 旧閾値6件: 30回中27回（90%）発火 → LLMに常時「慎重に」を注入していた
- 新閾値: 10件以上=警戒、7-9件=中立表現、6件以下=非表示
- LLMプロンプトの注入テキストも段階化

### Task 4: F2 BTC急落リスク管理（3レベル）
- Phase 0の5層出口の**前**にBTC 24h変動チェックを挿入

| Level | BTC 24h | アクション |
|---|---|---|
| L1 | ≤ -5% | SL幅を0.5倍に引き締め |
| L2 | ≤ -8% | 含み益ポジションを即利確 |
| L3 | ≤ -12% | 全ポジション緊急売却 |

### 調査: Evaluator勝率乖離
- Evaluator 74件/59.46% vs FIFO 28ペア/57.1%
- 原因: EvaluatorがUSD金額ベースの部分マッチング（1BUYが複数closedに分割）
- Phase 4bでは両方50-70帯で同一スコア → **実害なし、修正は後回し**

---

## ⏭️ 次セッションの作業

### 最優先 — BUY発生確認
1. streak解消確認: **04/04 03:23 UTC以降**にconfidence 53〜58でBUY発生するか
2. `grep "BUY\|Phase 5" radar_output.log | tail -20` で確認

### 検証待ち（BUY発生後）
3. E1検証: SL発火で構造化内省JSONが正しく生成されるか確認
4. 戦略スコア蓄積: Nightly Batchでvault/strategy_scores.json更新確認（旧取引はtag=none）
5. F2動作確認: BTC急落時にL1-L3が正しく発火するか（テスト困難・実地確認）

### 短期
6. VP/Graduation: Discord返答確認
7. Evaluator勝率計算をトレード単位FIFOに統一（優先度低）

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| core/config.py | EXIT_PROFILES short/mid/long再定義 + STRATEGY_TO_EXIT_PROFILE 3:3:3対応 |
| run_trigger.py | Phase 0第3層RSIプロファイル対応 + F2 BTC急落3レベルリスク管理 |
| agents/trinity_council.py | E3 sentiment_range二重適用防止 + ニュース過多閾値6→10件 |
| ARCHITECTURE.md | exit_profile名更新 + F2記載追加 |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | Nightly自動更新 |
| evolver_rule | 36件 | Nightly自動更新 + E3自動スコアリング（tz/sent除外） |
| trade_result | 31件 | E1実装済み |
| reflexion_result | 4件 | Fabric改修済み |

---

## 📈 勝率分析サマリー

| 銘柄 | 決済ペア | 勝 | 負 | 勝率 | 備考 |
|---|---|---|---|---|---|
| VIRTUAL | 10 | 7 | 3 | **70.0%** | 健全 |
| AIXBT | 18 | 9 | 9 | **50.0%** | Tier2降格済み |
| BTC | 0 | — | — | — | streak解消後に初取引見込み |
| ETH | 0 | — | — | — | ローテーション追加済み |
| **合計** | **28** | **16** | **12** | **57.1%** | 60%割れ継続 |

---

## 🔧 Confidence改善の経緯（v6.5ah→v6.5ai）

| ペナルティ | v6.5ah前 | v6.5ah後 | v6.5ai後 | streak解消後 |
|---|---|---|---|---|
| Planning | -15 | -7〜-10 | -7〜-10 | -7〜-10 |
| streak | -10 | -10 | -10 | **0** |
| EvolveR | -5 | -5 | **0** | **0** |
| ニュース | LLM恐怖注入 | LLM恐怖注入 | **中立/非表示** | 中立/非表示 |
| 最終confidence | 20 | 38〜48 | 43〜48 | **53〜58** |
