# 📐 GSD計画 v6.5an 引き継ぎ白書

> **更新日時**: 2026/04/05 01:30 JST
> **セッション**: v6.5an（BUYゲート緩和・LLM戦略策定ベース転換）
> **自己採点**: 90/100（設計思想転換完了。次回Council結果で効果検証）

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
| 設計転換 | 入口ゲート→出口管理（BUY閾値30, conf連動サイズ） |
| 自己進化 | E1-E3+Phase1e+F5+Phase S(S1-S4)+F2b — 8層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: BUYゲート緩和（入口→出口管理への設計転換）
- **BUY閾値**: 50→30（ゲートではなくサイズ制御に転換）
- **F5マクロ**: RISK_OFF_EXIT -10→-3, DISTRIBUTE -5→-2（二重減点排除）
- **時間帯**: US -10→-3, Asia/EU 5→3（振れ幅縮小）
- **ナンピン**: -10→-5（戦略書ありなら戦略的ナンピン許容）
- **根拠**: リスクは出口側8層（F2/F2b/CostGuard/5層/S3等）で既に十分管理されている

### Task 2: confidence連動ポジションサイズ有効化
- FLAT_POSITION_SIZE=True(一律5%)→False(conf連動)
- 30-39:2%, 40-49:3%, 50-59:5%, 60-69:7%, 70+:10%
- マクロ悪化＝買わない→小さく買うに転換

### Task 3: LLMを戦略策定ベースに転換
- **Neoのgoal**: BUY/WAIT判断→楽観/悲観シナリオ策定
- **SOUL原則5条件→戦略策定原則**: 市場環境はパラメータ調整材料
- **btc_warning**: 「リスク/機会」→「戦略調整: SL引き締め・短期シナリオ推奨」
- **caution_note**: 「慎重に」→「SL調整してBUY」
- WAITはBTC 24h -5%急落 or 同パターン損切のみ

### Task 4: WAIT時Moltbook観察投稿
- WAIT時スキップ→市場観察・思考過程として投稿
- 取引推奨なし（トークン名/BUY/SELL/金額一切含まず）

---

## ⏭️ 次セッションの作業

### 最優先 — v6.5an設計転換の効果検証
1. `grep "Phase 4b" radar_output.log | tail -10` でスコア改善確認（旧: 22-47 → 新: 39+期待）
2. `grep "Phase 5" radar_output.log | tail -10` でBUY実行確認
3. `grep "Phase 3b" radar_output.log | tail -5` で戦略書生成確認
4. conf連動サイズが正しく適用されているか確認
5. WAIT時Moltbook投稿が正しく動作するか確認

### 検証待ち
6. S2/S3: BUY後の戦略書モニタリング・動的出口の動作確認
7. E1検証: SL発火でscenario_outcome+strategy_quality_score確認
8. E2.5/E2.6: Reflexionに戦略制約・根拠信頼性スコア確認

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
| core/config.py | TZ_SCORE緩和(US:-3,Asia/EU:+3), FLAT_POSITION_SIZE=False |
| agents/trinity_council.py | BUY閾値30, F5緩和, ナンピン-5, Neo goal/backstory戦略策定ベース, btc_warning/caution_note転換, conf連動サイズ(2-10%) |
| tools/moltbook_tool.py | WAIT時観察投稿追加 |

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
