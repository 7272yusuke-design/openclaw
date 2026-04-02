# 📐 GSD計画 v6.5ag 引き継ぎ白書

> **更新日時**: 2026/04/02 22:00 JST
> **セッション**: v6.5ag（戦略スコア蓄積 + E1改善 + 相関分析ベース調整）
> **自己採点**: 92/100（相関分析で重大発見→即座にデータ駆動型調整を実装・フラグ切替可能）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続（AIXBT 50%が主因） |
| Tier0勝率 | 0%（BTC/ETH取引開始待ち） |
| USDC | $87,979.91 |
| Holdings | なし |
| サービス | 全4サービス稼働中 |
| CFO L4 | 正常（DD=0.58%, 閾値5%）HWM $88,494 |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄・AIXBTはTier2降格） |
| 自己進化 | **E1-E3+Phase1e完了** — 5層進化スタック + Fabric思考バイアス検出 |
| モデル | MODEL_FAST=gemini-2.5-flash（.env設定済み） |

---

## ✅ 本セッション完了タスク

### Task 5-6: 戦略別勝率スコア蓄積 + Phase 4b戦略信頼度反映（ContestTrade方式）
- **背景**: 9戦略のバックテストシグナルが「実際に当たったか」を追跡し、信頼できる戦略を加点
- **実装内容**:
  - `run_trigger.py`: ChromaDB trade_result metadataに`strategy_tag`追加
  - `trinity_council.py`: BUY historyレコードに`strategy_tag`保存（SELL後も参照可能）
  - `h2_trade_analysis.py`: `generate_strategy_scores()`関数新設 → `vault/strategy_scores.json`に戦略別勝率蓄積
  - `h2_trade_analysis.py`: get_clean_pairsにstrategy_tag追加
  - `run_trigger.py`: Nightly Step 6a2にstrategy_scores生成追加
  - `trinity_council.py`: Phase 4bに`strat±5`スコア追加（高勝率戦略+5、低勝率-5）
  - Phase 4bログに`strat_label`表示確認済み
- **データ蓄積**: 既存23ペアにはstrategy_tagなし → 次回BUY→SELLサイクルから蓄積開始

### Task 8: E1内省プロンプト改善（Fabric improve_prompt監査）
- **背景**: E1構造化内省プロンプトにChain of ThoughtとFew-shot例が不足
- **改修内容**:
  - 3段階分析手順（Step 1: 根拠仕分け → Step 2: 見落とし特定 → Step 3: カテゴリ選定）追加
  - few-shot例: btc_correlationの具体的内省JSON追加
  - `confidence_was_justified`: true固定 → true/false判断に修正
  - データ表示をエントリー/決済対比形式に整理

### CFO L4誤記修正
- 前セッション白書に「L4ドローダウンブロック発動中」と記載 → 実際はDD=0.58%（閾値5%）で正常
- WAITが続く原因はPhase 4b confidence不足（BTC=42, VIRTUAL=25）

### 相関分析 → データ駆動型Phase 4b調整（★最重要）
- **発見1: confidence逆相関** — 高conf(65-78)=47%WR vs 低conf(45-54)=83%WR
  - 対策: `FLAT_POSITION_SIZE=True`（一律5%、config.pyフラグで切替可能）
  - 対策: verdict bias +5 → 無効化（LLM BUY判断を信じるほど負ける）
- **発見2: 時間帯スコア逆転** — Asia=67% > EU=62% > US=33%
  - 対策: Asia-10→+5, EU+10→+5, US+0→-10（config.py TZ_SCORE_*で管理）
  - 対策: E3 EvolveRのtimezoneルール除外（config管理で一元化、二重適用防止）
- **発見3: BT confidence全件LOW** — 9戦略中どれも高信頼度を出していない（要調査）
- 全変更はフラグ切替可能（`FLAT_POSITION_SIZE`, `TZ_SCORE_*`）

---

## ⏭️ 次セッションの作業

### 最優先（次回）— アーキテクチャ方針をデータで決定する
1. ~~LLM confidence vs 実勝率の相関分析~~ → **✅ 本セッション完了**
2. ~~Phase 4bの重み調整~~ → **✅ フラットサイズ+TZ修正+verdict bias無効化 完了**

### 短期
3. **E1検証**: SL発火で構造化内省JSONが正しく生成されるか確認（CoT+few-shot改善済み、未発火）
4. **E2検証**: ログで思考バイアス検出の多様性維持を数回分確認（BTCとVIRTUALで異なるbiases確認済み）
5. **戦略スコア蓄積確認**: Nightly Batchでvault/strategy_scores.json更新とPhase 4b strat_label表示を確認
6. **VP/Graduation**: Discord返答確認 + NeoAutonomous Graduateボタン出現チェック

### 短中期（ContestTrade方式 — 実績ベース重み付け）
7. **銘柄別勝率閾値**: 45%以下で自動取引停止（AIXBTの50%問題への構造的対策）
8. **データソース信頼度トラッキング**: RSI/センチメント/BTC相関/クジラの各ソース的中率をvault/source_reliability.jsonに蓄積
9. **E1 few-shot例追加**: 実際のSL発火データが蓄積されたら、実例ベースのfew-shot例に差し替え

### 中期
9. **ACP登録**: vp_market_intelligenceをNeoAutonomousに登録（VP復旧後）
10. **旧offering整理**: sentiment_scan / backtest_on_demand のACP登録解除検討
11. **実取引エンジン**: `tools/cex_executor.py` 新設（Binance Spot API）

---

## 🔒 OpenClawアップデートメモ（Graduation後に対応）

| 項目 | 値 |
|---|---|
| 現在のバージョン | **2026.2.19**（ビルド日: 2026-02-20） |
| 最新安定版 | **2026.3.31**（6週間・13リリース分の遅れ） |
| 結論 | 緊急対応不要。Graduation完了後にアップデート推奨 |

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `run_trigger.py` | ChromaDB strategy_tag追加、Nightly 6a2戦略スコア、E1プロンプトCoT+few-shot改善 |
| `agents/trinity_council.py` | BUY history strategy_tag保存、Phase 4b strat±5スコア追加、ログstrat_label追加 |
| `research/h2_trade_analysis.py` | get_clean_pairs strategy_tag追加、generate_strategy_scores()新設 |
| `vault/strategy_scores.json` | 戦略別勝率データ（新規） |
| `core/config.py` | FLAT_POSITION_SIZE, TZ_SCORE_* フラグ追加（相関分析ベース） |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | Nightly自動更新 |
| evolver_rule | 36件 | Nightly自動更新 + E3自動スコアリング反映 |
| trade_result | 31件 | **E1実装済み（次回SL発火でfailure_category付き保存）** |
| reflexion_result | 4件 | **Fabric改修後: thinking_biases + current_pattern_match** |

### E1〜E4 進捗

| Phase | 名称 | ステータス | 残作業 |
|---|---|---|---|
| E1 | 深い内省 | ✅ **実装完了** | SL発火での実地検証待ち + improve_prompt監査 |
| E2 | 進化するReflexion | ✅ **実装完了+Fabric改修** | 数回分のログで多様性維持を確認 |
| E3 | 自律ルール適用 | ✅ **実装完了** | Nightly更新で安定稼働確認済み |
| E4 | モデル最適化 | ✅ **テスト完了** | flash維持。勝率60%未達なら再テスト |

### 5層進化スタック（完成形）
```
負け → E1構造化内省(failure_category) → E2 Reflexion(思考バイアス検出 ±10)
     → Phase 1e Planning(risk評価 ±15) → E3 EvolveR(auto rules ±30)
     → Phase 4b → 判断改善
```

---

## 📈 勝率分析サマリー

| 銘柄 | 決済ペア | 勝 | 負 | 勝率 | 備考 |
|---|---|---|---|---|---|
| VIRTUAL | 10 | 7 | 3 | **70.0%** | 健全 |
| AIXBT | 18 | 9 | 9 | **50.0%** | 3/26以降ほぼ全敗。Tier2降格で比率低下中 |
| BTC | 0 | — | — | — | 初回Council→WAIT |
| ETH | 0 | — | — | — | ローテーション追加済み |
| **合計** | **28** | **16** | **12** | **57.1%** | 60%割れ継続 |
