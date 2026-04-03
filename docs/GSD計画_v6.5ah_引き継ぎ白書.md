# 📐 GSD計画 v6.5ah 引き継ぎ白書

> **更新日時**: 2026/04/03 02:30 JST
> **セッション**: v6.5ah（Planning過剰抑制修正 + 3:3:3戦略リバランス + BTC底値圏評価）
> **自己採点**: 95/100（構造的取引ブロックの根本原因特定→4重修正で confidence 20→48）

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
| bt_confidence | **HIGH**（旧: LOW）← 3:3:3戦略+SQLite長期データ |
| 最終confidence | **48**（旧: 20）← streak解消で**58見込み**（04/04 03:23 UTC以降） |
| 自己進化 | E1-E3+Phase1e完了 — 5層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: Planning過剰抑制の修正（confidence 20→48の主因）
- **根本原因**: BTC -45%が4箇所で重複ペナルティ（LLMバナー/Planning/EvolveR/streak）
- **修正1**: trinity_council.py Planning confidence_modifierをmax(-10, min(10))でクランプ（旧: ±15）
- **修正2**: planning_agent.py btc_context引数追加 + 割安チャンス評価の指針をプロンプトに注入
- **効果**: Planning -15 → -5〜+5 に改善

### Task 2: BTC警戒バナー緩和
- **問題**: 180d<-20% AND 30d<0% → 「構造的な下落、BUYは極めて慎重に」がLLMに恐怖を注入
- **修正**: 条件を細分化
  - 30d < -5% → ⚠️「下落加速」（本当に危険な時のみ警戒）
  - 30d < 0 AND 24h < -3% → ⚠️「短期急落」
  - 30d < 0（短期安定）→ 📊「BTC底値圏、通常判断でOK」（現在の条件にマッチ）
  - 30d >= 0 → 📊「底打ち兆候」
- **効果**: LLMが過度に萎縮しなくなった

### Task 3: 3:3:3戦略リバランス（最重要変更）
- **問題**: 全9戦略が短期テクニカルのみ → BTC -45%=割安の視点がゼロ → bt=LOW常態化
- **新構成**:

| 分類 | 戦略 | 時間軸 |
|---|---|---|
| 短期 | macd_cross, mean_reversion, gplearn_evolved | 2-8日 |
| 中期 | triple_ma_cross, ichimoku_cloud, atr_breakout | 8-17日 |
| 長期 | macro_value, golden_cross, dca_accumulation | 17-50日 |

- **削除**: alpha_strategy, bb_reversal, momentum_breakout, vp_momentum, ema_trend, rsi_bounce
- **バックテスト結果（VIRTUAL）**: macro_value=HIGH(10取引), mean_reversion=HIGH(16取引,62.5%WR), macd_cross=HIGH(39取引)

### Task 4: データソース最適化
- **問題**: BacktestAgentがGeckoTerminal(180本)を優先 → SMA200計算不可
- **修正**: backtest_agent.py SQLite(1071本)を優先、GeckoTerminalはフォールバック
- **効果**: bt_confidence LOW → HIGH

### Task 5: bt_confidence判定改善
- **修正**: backtest_agent.py 全戦略の最高confidenceを採用（旧: ベスト戦略のみ）

---

## ⏭️ 次セッションの作業

### 最優先 — Phase F1: 戦略別出口プロファイル
1. core/exit_profiles.py 新規作成 — short/mid/long の3プロファイル定義
   - short: SL-3%, trailing+5%/-2.5%, TP+14%, RSI65, 96h
   - mid: SL-5%, trailing+10%/-4%, TP+25%, RSI72, 336h(14日)
   - long: SL-8%, trailing+15%/-6%, TP+50%, RSI無効, 1080h(45日)
2. trinity_council.py Phase 5: BUY時にstrategy_tagのtimeframeからexit_profile設定
3. run_trigger.py Phase 0: 5層出口がexit_profileを参照するよう修正
4. 理由: 3:3:3にしたのに出口が短期用のまま。macro_valueで仕込んでも96hで強制決済される

### 短期
5. streak解消確認: 04/04 03:23 UTC以降にconfidence 58でBUYが発生するか確認
6. E1検証: SL発火で構造化内省JSONが正しく生成されるか確認
7. 戦略スコア蓄積: Nightly Batchでvault/strategy_scores.json更新確認
8. VP/Graduation: Discord返答確認

### Phase F2: ニュース駆動型リスク管理
9. Phase 0にLevel 1-3リスクチェック追加（センチメント急変/BTC急落/緊急事態）

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）

### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| agents/trinity_council.py | Planning上限±10クランプ、BTC警戒バナー細分化、btc_context渡し |
| agents/planning_agent.py | btc_context引数追加、機会評価指針プロンプト注入 |
| agents/backtest_agent.py | SQLite優先データソース、全戦略最高confidence採用 |
| research/backtests/run_backtest.py | 3:3:3戦略リバランス（6削除+6追加+strategy_map更新） |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | Nightly自動更新 |
| evolver_rule | 36件 | Nightly自動更新 + E3自動スコアリング反映 |
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

## 🔧 ブレスト結果: F1-F4ロードマップ

GitHub参考レポ調査済み（Erfaniaa/crypto-portfolio-optimizer, denisond/sharpe-optimization, egruttadauria98/Markowitz）。

F1: 戦略別exit_profile（short/mid/long） ← 最優先・次セッション
F2: ニュース駆動型Phase 0リスク管理 ← F1と並行可能
F3: Kelly基準ポジションサイジング ← 勝率60%回復後
F4: Markowitz + ボラティリティスケーリング ← BTC/ETH実績蓄積後
