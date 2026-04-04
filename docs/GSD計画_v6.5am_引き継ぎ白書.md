# 📐 GSD計画 v6.5am 引き継ぎ白書

> **更新日時**: 2026/04/04 22:30 JST
> **セッション**: v6.5am（google.genai SDK移行 + E2 Reflexion拡張）
> **自己採点**: 85/100（SDK移行+E2拡張完了。Phase 3b+E2.5/E2.6動作検証は次回BUY待ち）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | リセット後 **0件**（旧: 57.1% 28ペア — バグ期間のため参考外） |
| USDC | $79,185.70 |
| Holdings | VIRTUAL 13,694枚 @ $0.6422（exit=mid, SL=-5%） |
| サービス | 全4サービス稼働中 |
| CFO L4 | 正常（DD=0.7%, 閾値5%） |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄） |
| bt_confidence | **HIGH** |
| 自己進化 | E1-E3+Phase1e+F5+Phase S(S1-S4)+F2b — 8層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: google.genai SDK移行（deprecated対応）
- `google.generativeai`（deprecated）→ `google.genai` SDKに移行
- `core/model_factory.py`: `_GenaiModelWrapper`クラスを追加し旧`generate_content()`インターフェースを維持
- 呼び出し元（trinity_council, planning_agent, run_trigger）は変更なし
- FutureWarning完全解消、新旧両SDK動作確認済み

### Task 2: E2 Reflexion拡張（strategy_constraints + evidence_reliability）
- **E2.5 strategy_constraints**: 既存ポジション戦略書からinvalidation条件・SL/TPを取得しReflexionプロンプトに注入
  - 戦略書がある場合: テーゼ・TP/SL・無効化条件・無効化時アクションをチェック対象に
  - 戦略書がない場合: 「なし（戦略書未生成）」でフォールバック
- **E2.6 evidence_reliability**: Council判断の根拠データソース多様性を評価
  - backtest/sentiment/onchain/pair_trade/planning/macroの使用状況を集計
  - LLMに1-5の信頼性スコア+最大弱点を評価させる
- LLM出力に3フィールド追加: strategy_constraint_violated, evidence_reliability_score, evidence_weakness
- reflexion_insightに戦略制約違反・根拠信頼性スコアを表示

### 確認事項
- Phase 3b戦略書生成エラー: 前セッション(v6.5al)で修正済み → 次回BUY待ち
- ナイトバッチ報告(Voyager/EvolveR/教訓): 実装・Discord送信確認OK

---

## ⏭️ 次セッションの作業

### 最優先 — Phase S + E2拡張 動作検証（BUY verdict待ち）
1. `grep "Phase 3b" radar_output.log | tail -5` で戦略書生成成功確認
2. Discord Council報告で戦略サマリーが正しく表示されるか確認
3. ダッシュボードで戦略進行度が正しく表示されるか確認
4. E2.5/E2.6: Reflexionに戦略制約・根拠信頼性スコアが出力されるか確認
   - `grep "E2 Reflexion" radar_output.log | tail -5`

### 検証待ち
5. S2/S3: 次回BUYで戦略書が入った後にモニタリング・動的出口が動くか確認
6. E1検証: SL発火でscenario_outcome+strategy_quality_scoreが正しく生成されるか

### 短期
7. VP/Graduation: Discord返答確認
8. E3拡張: 戦略パターンルール自動生成（strategy_quality_score蓄積後）
9. Voyager拡張: 成功戦略テンプレート蓄積

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| core/model_factory.py | google.generativeai → google.genai SDK移行（_GenaiModelWrapperラッパー追加） |
| agents/trinity_council.py | E2.5 strategy_constraints + E2.6 evidence_reliability追加 |

---

## 🛡️ リスクヘッジ全レイヤー

| 検知対象 | 仕組み | 頻度 | 対応速度 |
|---|---|---|---|
| BTC急落 | F2（L1-L3） | 30秒 | 即時 |
| マクロ急変（SPY/Gold） | F2b（L1-L3）— os import修正済み | 30分 | 先回り |
| マクロ環境悪化 | F5 capital_flow_phase | 2h | Council時 |
| ポジション個別 | Phase 0 5層出口 | 30秒 | 即時 |
| 戦略前提崩壊 | Phase S invalidation | 30秒 | 即時 |
| ポートフォリオ全体 | CostGuard L1-L4 | Council時 | 2h |
| ポートフォリオ集中 | Phase 5ガード6段 | BUY時 | 即時 |

---

## 📢 Discord報告体系（v6.5al更新）

| 報告 | タイミング | 内容 |
|---|---|---|
| Council Minutes | BUY/SELL時 | 市況+ポジション+戦略書サマリー（or Bull/Bear意見）+スコアリング内訳+判断+取引結果+出口プロファイル |
| Performance Dashboard | 6h毎 | 勝率+Tier別+ポートフォリオ（戦略進行度・PnL USD付き）+直近決済5件 |
| Nightly Batch Report | JST 02:00 | 勝率+Alpha+Moltbook+WAIT品質+H.2+gplearn+**Voyager学習**+**EvolveR進化**+**直近教訓** |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | Nightly自動更新 |
| evolver_rule | 36件 | Nightly自動更新 + E3自動スコアリング |
| trade_result | 31件 | E1+S4: scenario_outcome/quality_score追加 |
| reflexion_result | 4件 | E2.5/E2.6拡張済み（strategy_constraints+evidence_reliability） |
| macro_data | 5指標 | F5日次自動更新 |
