# 📐 GSD計画 v6.5aj 引き継ぎ白書

> **更新日時**: 2026/04/03 21:30 JST
> **セッション**: v6.5aj（F5お盆フレームワーク実装 + PortfolioManager bugfix）
> **自己採点**: 92/100（F5 S1-S6完了 + bugfix + BUY手動補完。検証は次回Council待ち）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続 |
| USDC | $83,580.91 |
| Holdings | VIRTUAL 6,808枚 @ $0.6461（exit=mid, SL=-5%） |
| サービス | 全4サービス稼働中 |
| CFO L4 | 正常（DD=0.58%, 閾値5%）HWM $88,494 |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄） |
| bt_confidence | **HIGH** |
| 最終confidence | 60（直近BUY時） |
| 自己進化 | E1-E3+Phase1e+F5完了 — 6層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: PortfolioManager.state bugfix
- `self.portfolio.state` → `self.portfolio.get_full_state()`（1箇所）
- `self.portfolio._save_wallet()` → `self.portfolio.wallet._save_wallet()`（3箇所）
- **原因**: BUY実行後のstrategy_tag/exit_profile/entry_context保存で例外 → Phase 6/7スキップ
- VIRTUAL BUY（04/03 05:55 UTC）のstrategy_tag/exit_profile/entry_context/historyを手動補完

### Task 2: F5 お盆フレームワーク — 資本ローテーション解釈レイヤー（S1-S6全完了）

**S1: tools/macro_collector.py 新規作成**
- yfinance: SPY, DXY(DX-Y.NYB), Gold(GC=F), US10Y(^TNX) — 30日分日足
- CoinGecko: BTC Dominance
- vault/blackboard/macro_flow.json の macro_data フィールドに保存
- 全5指標取得確認済み

**S2: neo-collector.service 日次バッチ組込み**
- data_collector.pyの日次パージ直後にmacro_collector.collect_macro_data()呼び出し
- 失敗時はスキップ（既存データ維持）

**S3: planning_agent.py プロンプト拡張**
- 「分析官であり判断者ではない」方針を明記
- お盆フレームワーク解釈ガイド（5指標の意味 + 4フェーズ定義）をプロンプトに注入
- macro_flow.jsonからmacro_dataを読み込みプロンプトに渡す

**S3b: confidence_modifier廃止 → capital_flow_phase置換**
- Planning出力: confidence_modifier(int) → capital_flow_phase(4フェーズ) + macro_summary(str)
- デフォルト: RISK_ON_RIDE（判断不能時）

**S4: Phase 4b スコアリング統合**
- capital_flow_phase → macro_adj（別枠）:
  - RISK_OFF_ACCUMULATE: +5
  - RISK_ON_RIDE: +0
  - RISK_ON_DISTRIBUTE: -5
  - RISK_OFF_EXIT: -10
- ログラベル: `macro+X(PHASE)`（旧`plan-X`を置換）

**S5: BUY時entry_contextにcapital_flow_phase保存**
- scoring_breakdown に macro ラベル追加
- entry_context 直下に capital_flow_phase 追加

**S6: E3にcapital_flow_phase条件タイプ追加**
- scoring_adjustments.json の condition.type="capital_flow_phase" をサポート
- Phase 4b条件マッチングに追加

### 調査: GeckoTerminal 429エラー
- 13件/数日 — market_data.pyとdata_collector.pyが別々にレート制限管理
- DexScreenerフォールバックあり、実害小 → 対策は後回し

### 調査: strategy_scores.json
- scores空 — 全79件のhistoryがtag=none（F1実装前の取引）
- 最新BUY(index 78)をatr_breakoutに手動補完済み
- 今後のtag付き取引が決済されれば自動蓄積

---

## ⏭️ 次セッションの作業

### 最優先 — F5検証
1. `grep "Phase 4b.*ルールベース" radar_output.log | tail -3` で `macro+X(PHASE)` 確認
2. Planning Agentがcapital_flow_phaseを正しく出力しているか確認

### 検証待ち
3. E1検証: SL発火で構造化内省JSONが正しく生成されるか確認
4. 戦略スコア蓄積: tag付き取引のSELL後にstrategy_scores.json更新確認
5. F2動作確認: BTC急落時にL1-L3が正しく発火するか

### 短期
6. VP/Graduation: Discord返答確認
7. Evaluator勝率計算をトレード単位FIFOに統一（優先度低）

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）
### E2段階的移行: capital_flow_phase別15件蓄積後

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| tools/macro_collector.py | **新規** — F5マクロ資本フローデータ収集（yfinance+CoinGecko） |
| orchestration/data_collector.py | 日次バッチにmacro_collector組込み |
| agents/planning_agent.py | 分析官方針+お盆FW+capital_flow_phase出力（confidence_modifier廃止） |
| agents/trinity_council.py | F5スコアリング統合+E3条件タイプ追加+PortfolioManager bugfix |
| data/paper_wallet.json | VIRTUAL entry手動補完（tag/exit/entry_context） |

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
| **macro_data** | **5指標** | **F5新規 — 日次自動更新** |

---

## 📈 勝率分析サマリー

| 銘柄 | 決済ペア | 勝 | 負 | 勝率 | 備考 |
|---|---|---|---|---|---|
| VIRTUAL | 10 | 7 | 3 | **70.0%** | 現在保有中（mid exit） |
| AIXBT | 18 | 9 | 9 | **50.0%** | Tier2降格済み |
| BTC | 0 | — | — | — | ローテーション対象 |
| ETH | 0 | — | — | — | ローテーション対象 |
| **合計** | **28** | **16** | **12** | **57.1%** | 60%割れ継続 |

---

## 🔧 F5 Phase 4bスコアリング変更

| 旧ラベル | 新ラベル | 説明 |
|---|---|---|
| `plan-X` | `macro+X(PHASE)` | LLM confidence_modifier → 資本フローフェーズ固定値 |

| Phase | 修正値 | 条件 |
|---|---|---|
| RISK_OFF_ACCUMULATE | +5 | 株式↑ DXY↓ Gold横 US10Y↓ — 仕込み時 |
| RISK_ON_RIDE | +0 | 通常判断 |
| RISK_ON_DISTRIBUTE | -5 | BTC Dom急落 アルト急騰 — 利確検討 |
| RISK_OFF_EXIT | -10 | 株式↓ DXY↑ Gold↑ US10Y↑ — 撤退 |
