# 📐 GSD計画 v6.5ak 引き継ぎ白書

> **更新日時**: 2026/04/04 15:30 JST
> **セッション**: v6.5ak（Phase S戦略家モデル全4Phase + F2bマクロ急変検知 + プロンプト改善 + バグ3件修正）
> **自己採点**: 95/100（S1-S4全完了+F2b+重大バグ3件修正。Phase 3b動作検証は次回Council待ち）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | リセット後 **0件**（旧: 57.1% 28ペア — バグ期間のため参考外） |
| USDC | $83,580.91 |
| Holdings | VIRTUAL 6,808枚 @ $0.6461（exit=mid, SL=-5%） |
| サービス | 全4サービス稼働中 |
| CFO L4 | 正常（DD=0.7%, 閾値5%）HWM $88,494 — **本セッションで修正** |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄） |
| bt_confidence | **HIGH** |
| 自己進化 | E1-E3+Phase1e+F5+**Phase S(S1-S4)**+**F2b** — 8層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: Phase S — 戦略家モデル（全4Phase完了）

**S1: 戦略書出力（Phase 3b新設）**
- verdict=BUY時にLLMを「戦略家」として活用し、ポジション戦略書を自動生成
- thesis/bull_scenario/bear_scenario/invalidationの構造化JSON
- 根拠品質チェック: evidence≧3 + 定量データ含有 + 複数ソース + risk_pct≦6%
- evidence_snapshot自動付加（BT/センチメント/マクロ/BTC/テクニカル/Voyager/EvolveR）
- JSONパース失敗時はstrategy=Noneで既存フロー続行（フォールバック）
- Discord報告にthesis/TF/TP%/SL%を表示

**S1改善: リポジトリ調査ベースのプロンプト強化**
- 調査: AI-Brokers/AIBrokers, MRTASI/agents-for-trading, huygiatrng/AlpacaTradingAgent
- ATR(14)ベースのSL/TP推奨値をプロンプトに注入（ボラティリティ基準）
- ポートフォリオ3%ルール（最大損失$X）をハード制約として明記
- RR比1.5以上推奨、risk_pct>6%は品質チェックで自動却下
- invalidation/stop具体性を明示的に要求

**S2: 戦略書モニタリング（Phase 0拡張）**
- Phase 0（30秒サイクル）で保有ポジションのstrategyを読み込み
- bull進行度 / bear進行度をログ出力（30分毎）
- bear trigger 70%接近で警告、bull target 80%接近で通知

**S3: シナリオ動的出口**
- S3-1: 戦略書bear_scenario.stop_priceで固定SLを上書き（固定SLの2倍が安全上限）
- S3-2: bear trigger 70%接近でexit_profile 1段階引き締め（long→mid, mid→short）
- S3-3: bull target 100%到達でトレール早期開始
- 既存5層は最終安全網として維持

**S4: 戦略内省+進化連携**
- E1プロンプトに戦略書比較データ注入（thesis/bull/bear vs 実績）
- scenario_outcome（bull/bear/unexpected）とstrategy_quality_score（1-10）を出力
- ChromaDB metadataにscenario_outcome/strategy_quality_score保存

### Task 2: F2b — マクロ急変検知（お盆フレームワーク即時版）
- Phase 0にSPY/Gold急変検知を追加（30分間隔yfinanceキャッシュ）
- SPY急落 + Gold急騰 = リスクオフ加速 → F2と同じ3段階対応
  - L1: SPY -2% → SL引き締め
  - L2: SPY -3% + Gold +1.5% → 含み益利確
  - L3: SPY -5% + Gold +3% → 全ポジション緊急売却
- F2(BTC)とF2b(マクロ)の最大レベルを採用
- **目的**: BTCが動く前にマクロ指標で先回り（お盆フレームワークの即時版）

### Bug 1: L4 DD計算バグ修正（重大）
- `holding.get("current_value", 0)` → holdingsにcurrent_valueフィールドなし → DD誤算
- DD = 5.6%(USDC only) → 0.7%(時価込み) に正常化 → Council全ブロック解除

### Bug 2: CFR macro_data保持修正
- capital_flow_radar.pyがmacro_flow.jsonを全上書き → macro_dataフィールド消失
- read-modify-write方式でmacro_dataを保持するよう修正

### Bug 3: Phase 3b モデル参照バグ修正
- `self.pro_model`（CrewAI用LangChain）に`generate_content()`がなかった
- `ModelFactory.get_genai_model("critical")` に修正

---

## ⏭️ 次セッションの作業

### 最優先 — Phase S動作検証
1. `grep "Phase 3b" radar_output.log | tail -5` で戦略書生成成功確認（Bug3修正後）
2. `grep "\[S2\]" radar_output.log | tail -5` でモニタリング動作確認
3. `grep "F2b" radar_output.log | tail -5` でマクロ急変検知キャッシュ動作確認

### 検証待ち
4. E1検証: SL発火でscenario_outcome+strategy_quality_scoreが正しく生成されるか
5. S3検証: bear trigger接近でexit_profile引き締め動作確認

### 短期
6. VP/Graduation: Discord返答確認
7. E2拡張: Reflexionにstrategy_constraintsとevidence_reliability追加
8. E3拡張: 戦略パターンルール自動生成（strategy_quality_score蓄積後）
9. Voyager拡張: 成功戦略テンプレート蓄積

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| agents/trinity_council.py | S1: Phase 3b戦略書生成+品質チェック+ATR/リスク制約+entry_context保存+Discord表示+モデル修正 |
| run_trigger.py | S2: モニタリング / S3: 動的出口 / S4: 戦略内省 / F2b: マクロ急変検知 |
| core/cost_guard.py | Bug: L4 DD計算をholding時価ベースに修正 |
| tools/capital_flow_radar.py | Bug: macro_flow.json上書き→read-modify-write |

---

## 🛡️ リスクヘッジ全レイヤー

| 検知対象 | 仕組み | 頻度 | 対応速度 |
|---|---|---|---|
| BTC急落 | F2（L1-L3） | 30秒 | 即時 |
| マクロ急変（SPY/Gold） | F2b（L1-L3）**NEW** | 30分 | 先回り |
| マクロ環境悪化 | F5 capital_flow_phase | 2h | Council時 |
| ポジション個別 | Phase 0 5層出口 | 30秒 | 即時 |
| 戦略前提崩壊 | Phase S invalidation | 30秒 | 即時 |
| ポートフォリオ全体 | CostGuard L1-L4 | Council時 | 2h |
| ポートフォリオ集中 | Phase 5ガード6段 | BUY時 | 即時 |

---

## 🎯 Phase S 戦略家モデル — 実装完了マップ

| Phase | 内容 | 変更ファイル | 状態 |
|---|---|---|---|
| S1 | 戦略書出力（Phase 3b） | trinity_council.py | ✅ + ATR/リスク制約+モデル修正 |
| S2 | モニタリング（Phase 0） | run_trigger.py | ✅ |
| S3 | 動的出口 | run_trigger.py | ✅ |
| S4 | 戦略内省+進化連携 | run_trigger.py | ✅ |

### 戦略書のハード制約（プロンプト明記）
- 最大損失: 総資産の3%以内
- risk_pct > 6% は品質チェックで却下
- SL/TP: ATR(14)基準（SL=1.5-2.5×ATR, TP=2-4×ATR）
- RR比: 最低1.5以上推奨
- invalidation: 具体的数値・条件必須

### 安全装置
- 戦略SL上限 = 固定SLの2倍
- exit_profile変更は1段階のみ
- 既存5層は全て維持（最終安全網）
- JSONパース失敗時は戦略なしで従来フロー続行

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
| reflexion_result | 4件 | Fabric改修済み |
| macro_data | 5指標 | F5日次自動更新 — CFR上書きバグ修正済み |

---

## F5検証結果（本セッション確認）
- `macro-10(RISK_OFF_EXIT)` ✅ Phase 4bログで確認
- `plan-X`（旧ラベル）→ `macro+X(PHASE)` ✅ 置換成功
- Planning Agentの`capital_flow_phase`出力 ✅ 正常動作
