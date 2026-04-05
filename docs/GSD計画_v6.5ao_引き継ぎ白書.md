# 📐 GSD計画 v6.5ao 引き継ぎ白書

> **更新日時**: 2026/04/05 11:00 JST
> **セッション**: v6.5ap（参考情報データ品質調査・Scout/Reflexion/S3バグ修正）
> **自己採点**: 85/100（報告体系改善完了。データ拡充の仕込み完了、蓄積待ち）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | リセット後 **0件**（旧: 57.1% 28ペア — バグ期間のため参考外） |
| USDC | $74,794.48 |
| Holdings | VIRTUAL 13,694枚 @ $0.6422（exit=mid）/ ETH 2.12枚 @ $2,067.77（exit=mid） |
| サービス | 全4サービス稼働中 |
| CFO L4 | 正常 |
| Council | **1h**ローテーション: BTC → VIRTUAL → ETH（3銘柄） |
| bt_confidence | **HIGH** |
| 設計転換 | 入口ゲート→出口管理（BUY閾値30, conf連動サイズ） |
| 自己進化 | E1-E3+Phase1e+F5+Phase S(S1-S4)+F2b — 8層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: Discord報告体系整理
- **Nightly Batch Report**: description文字列連結 → embed fields構造化
  - Dashboardと重複する勝率/Tier別/Moltbook統計を削除
  - Voyager学習/EvolveR進化/gplearn G4/WAIT品質/直近教訓のみに特化
  - 各フィールド300-400文字制限で省略されない設計
- **Moltbook活動レポート（新設）**: `send_moltbook_report()` をDiscordReporterに追加
  - karma推移・フォロワー推移・エンゲージメント・submolt別分析を独立embedで送信
  - Nightly Step 7bとして実行

### Task 2: trade_resultメタデータ拡充（パターンマイニング準備）
- SELL/SL/TP時にentry_contextからスコアリング要素をtrade_resultに引き継ぎ
- **追加12項目**: conf_total, bt, tz, cfr, macro, npin, streak, sent, capital_flow_phase, btc_trend, entry_hour, entry_weekday
- 50-100件蓄積後にefficient-aprioriでアソシエーションルール抽出予定
- `efficient-apriori` パッケージインストール済み

---

### Task 4: K.3クジラ監視デバッグ（v6.5ap）
- **閾値修正**: $50K→$10K（VIRTUAL $0.64で78,125枚→15,600枚。検出ゼロ常態化を解消）
- **amount_tokens追加**: large_txsにトークン数を表示（キー欠落バグ修正）
- **往復フィルタ追加**: 同一アドレスペア3回以上の往復をスキップ（8件→3件に正常化）
- **参考情報品質調査結果**: FinBERT✅ / 恐怖指数✅ / capital_flow_phase✅ / クジラ❌→✅修正済み
- **BTC/ETH**: Base chain上にネイティブトークンなし。CFR+F2/F2bで十分カバー、K.3対応不要と判断

### Task 5: Scout run_alpha_strategy修正（v6.5ap）
- **原因**: CoreBacktest.run_alpha_strategy は存在しないメソッド → Sharpeが全銘柄で常時0.0
- **修正**: run_all_strategies + best抽出に変更。Alpha Sweepでも同じバグが発生していた
- DLNews RSS（404）をcrypto_news.pyから除去

### Task 6: E2 Reflexion ModelFactory スコープバグ修正（v6.5ap）
- **原因**: Phase 3b（971行）でローカルimport → Python 3.12が関数全体でModelFactoryをローカル変数扱い → 351行のReflexionで未定義エラー
- **修正**: 冗長なローカルimport削除（29行のトップレベルimportのみに統一）

### Task 7: S3 exit引き締めログスパム抑制（v6.5ap）
- **原因**: 30秒サイクル毎に同じS3警告を出力（bear≧70%の間ずっと）
- **修正**: モジュールレベル _s3_dedup_cache で初回のみ出力に変更

### Task 3: Council間隔 2h→1h化
- `UNIFIED_COUNCIL_INTERVAL_SEC`: 7200→3600
- 各銘柄3時間に1回チェック（旧: 6時間に1回）
- gemini-2.5-flashでコスト影響軽微

---

## ⏭️ 次セッションの作業

### 最優先 — v6.5an設計転換の効果検証
1. `grep "Phase 4b" radar_output.log | tail -10` でスコア改善確認（旧: 22-47 → 新: 39+期待）
2. `grep "Phase 5" radar_output.log | tail -10` でBUY実行確認
3. `grep "Phase 3b" radar_output.log | tail -5` で戦略書生成確認
4. conf連動サイズが正しく適用されているか確認
5. WAIT時Moltbook投稿が正しく動作するか確認

### 重要発見 — DexScreener ETH/BTC価格乖離
- DexScreenerのETH価格がBase chain低流動性プールから$2,929を返す（CoinGecko正解: $2,043、+43%乖離）
- CoinGecko 429フォールバック時にCouncilでこの歪んだ価格が使われるリスクあり
- **対策案**: ETH/BTCの価格取得はCoinGecko優先＋DexScreener使用時に乖離チェック追加

### 検証待ち
6. S2/S3: BUY後の戦略書モニタリング・動的出口の動作確認
7. E1検証: SL発火でscenario_outcome+strategy_quality_score確認
8. 拡充メタデータ: 次回SELL/SL時にconf_total/tz/cfr等が正しくChromaDBに保存されるか確認

### 短期 — パターンマイニング実装
9. 50件蓄積後: `research/pattern_miner.py` 作成（Apriori + 異常検知）
10. min_support=0.1-0.2, min_confidence=0.4 でテスト
11. 発見ルールを `vault/mined_patterns.json` に保存 → Phase 4bでスコア調整に活用

### その他
12. VP/Graduation: Discord返答確認
13. E3拡張: 戦略パターンルール自動生成（strategy_quality_score蓄積後）

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| run_trigger.py | Nightly Step 7をembed fields構造化、Step 7b Moltbookレポート追加、trade_resultメタデータ拡充（12項目追加） |
| tools/discord_reporter.py | `send_moltbook_report()` 新規追加 |

---

## 📢 Discord報告体系（v6.5ao更新）

| 報告 | タイミング | 内容 |
|---|---|---|
| Council Minutes | BUY/SELL時 | 市況+ポジション+戦略書+スコアリング内訳+判断+取引結果+出口プロファイル |
| Performance Dashboard | 6h毎 | 勝率+Tier別+ポートフォリオ（戦略進行度・PnL USD付き）+直近決済5件 |
| Nightly Batch Report | JST 02:00 | **自己進化日報**: Voyager学習+EvolveR進化+gplearn G4+WAIT品質+直近教訓 |
| Moltbook活動レポート | JST 02:00 | **新設**: karma推移+エンゲージメント+submolt別パフォーマンス |

---

## 🛡️ リスクヘッジ全レイヤー

| 検知対象 | 仕組み | 頻度 | 対応速度 |
|---|---|---|---|
| BTC急落 | F2（L1-L3） | 30秒 | 即時 |
| マクロ急変（SPY/Gold） | F2b（L1-L3） | 30分 | 先回り |
| マクロ環境悪化 | F5 capital_flow_phase | 2h | Council時 |
| ポジション個別 | Phase 0 5層出口 | 30秒 | 即時 |
| 戦略前提崩壊 | Phase S invalidation | 30秒 | 即時 |
| ポートフォリオ全体 | CostGuard L1-L4 | Council時 | 2h |
| ポートフォリオ集中 | Phase 5ガード6段 | BUY時 | 即時 |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | Nightly自動更新 |
| evolver_rule | 36件 | Nightly自動更新 + E3自動スコアリング |
| trade_result | 31件 | **v6.5aoで18項目メタデータに拡充**（旧6項目→今後の新規分から適用） |
| reflexion_result | 4件 | E2.5/E2.6拡張済み |
| macro_data | 5指標 | F5日次自動更新 |

---

## 📐 パターンマイニング計画

| フェーズ | 条件 | 内容 |
|---|---|---|
| 現在 | 蓄積中 | trade_resultに18項目メタデータを保存開始 |
| 50件到達 | trade_result 50件 | Apriori初回テスト（min_support=0.2） |
| 100件到達 | trade_result 100件 | 本格運用（異常検知追加・Phase 4bスコア調整連携） |
| 将来 | 十分な蓄積後 | ロジスティック回帰・クラスタリング |
