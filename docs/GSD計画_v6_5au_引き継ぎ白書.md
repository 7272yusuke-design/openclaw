# 📐 GSD計画 v6.5au 引き継ぎ白書

> **更新日時**: 2026/04/12 08:20 JST
> **セッション**: v6.5au（SELL報告修正・ダッシュボード修正・起動時送信追加）
> **自己採点**: 85/100（勝率60.9%達成！ダッシュボード・SELL報告の複数バグ修正）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(Evaluator) | **60.9%（46件決済: 28勝18敗）** ← 目標60%達成！ |
| Tier0 (BTC/ETH) | 66.7%（18件） |
| Tier1 (VIRTUAL) | 57.1%（28件） |
| USDC | $66,230 |
| Holdings | BTC(0.1177/long) / VIRTUAL(11342/short) / ETH(2.2873/short) |
| サービス | 全4サービス稼働中 |
| L4 DD | 4.27% — 安全圏 |
| Council | 1hローテーション: BTC → VIRTUAL → ETH |
| 学習モード | 67/100件（67%） |

---

## ✅ 本セッション完了タスク

### Task 1: SELL報告書のスナップショット修正
- **問題**: Discord SELL報告のRSI=0.0、BTC24h=+0.0%、保有時間=0.0h
- **原因3つ**:
  1. `_btc_24h_change` → 存在しない変数。正しくは `_btc_24h_chg_f2`（L90で定義）
  2. `rsi_val` → RSI Exit時のみ設定。他の売却理由では未定義→0.0にフォールバック
  3. `buy_date` → holdingsのキーは `entry_time`
- **修正**: `_calc_rsi()`で常に取得 / `_btc_24h_chg_f2`に修正 / `entry_time`に修正

### Task 2: ダッシュボード直近5件の時系列ソート
- **問題**: 直近5件がすべてVIRTUALで表示される
- **原因**: `_calc_closed_trades`がシンボル別にループするため、VIRTUAL全件→ETH全件の順になり、`closed[-5:]`が最後のシンボルの末尾5件になる
- **修正**: closedに`sell_time`を追加し、時系列順にソート

### Task 3: Tier0/Tier1表示がN/A
- **問題**: evaluatorは53.8%/47.8%と計算しているのにダッシュボード表示がN/A
- **原因**: `PerformanceSummary` Pydanticモデルに`tier0_accuracy`等のフィールドが未定義。`PerformanceSummary(**data).model_dump()`で未知フィールドが切り捨てられてNoneになる
- **修正**: `PerformanceSummary`に`tier0_accuracy/tier0_trades/tier1_accuracy/tier1_trades/open_positions_count/open_positions/advanced_metrics`を追加

### Task 4: TP/SL進捗%の異常値
- **問題**: BTC「TP 300%到達」「SL -655%接近」と表示
- **原因**: 現在価格がTP/SLを超えた場合にclampされていない
- **修正**: `max(0, min(100, ...))` でclamp

### Task 5: 起動時ダッシュボード送信
- **問題**: サービス再起動後、6時間（720サイクル）経過するまでダッシュボードが送信されない
- **原因**: `cycle_count`がL1009で先にインクリメントされ、最初のチェックが`1 % 720 != 0`
- **修正**: メインループ開始前に`evaluate_performance(send_dashboard=True)`を呼び出し

---

## ⏭️ 次セッションの作業

### 最優先 — 勝率60%維持確認
1. 勝率推移の監視（60%以上を維持できているか）
2. v6.5as改善（AI主導化・RSI Exit改善）の効果が継続しているか

### 最優先 — Graduation
3. Web UIでStats更新確認 → Graduate Agentボタン表示確認
4. 未表示ならDiscord問い合わせ

### 重要 — Phase F3: Kelly基準ポジションサイジング
5. 勝率60%達成によりPhase F3の前提条件クリア
6. 過去の勝率(W)と平均RR比から最適ポジションサイズを計算
7. AI推奨サイズのフォールバックとして組み込み

### 重要 — 効果検証
8. SELL報告書にRSI・BTC24h・保有時間が正しく表示されるか確認
9. sell_tracker.jsonの蓄積データ確認
10. RSI Exit改善効果: grep "SELL根拠" radar_output.log

### 短期
11. パターンマイニング（50件蓄積後 → sell_trackerは6件のみ、要蓄積）
12. VP/Graduation完了後、ACP seller runtimeをv2対応に切り替え
13. E3拡張: 戦略パターンルール自動生成
14. Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 新規ファイル・変更ファイル

| ファイル | 変更内容 |
|---|---|
| run_trigger.py | SELL根拠スナップショット3変数修正 / 起動時ダッシュボード送信追加 |
| orchestration/performance_evaluator.py | closedにsell_time追加・時系列ソート |
| core/blackboard.py | PerformanceSummaryにTier・open_positions等フィールド追加 |
| tools/discord_reporter.py | TP/SL進捗%を0-100にclamp |

---

## ACP構成（v2移行後）

v2 Neo (Self-hosted)
- Agent ID: 019d7659-6dd1-7067-a5ff-d74f567a3961
- ウォレット: 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a
- CLI: skills/acp-cli-v2/ (acp-cli)
- Signer: P256鍵（OS keychain保存済み）
- Offering: vp_sentiment_scan ($0.01)
- Jobs: 10件COMPLETED (chain 8453)
- Stats: 未反映（要確認）

neo-acp-seller.service — 稼働中（NeoAutonomous用、既存4 offerings）

---

## 📊 移行条件進捗（D3準拠）

| 条件 | 現在 | 必要 | 判定 |
|---|---|---|---|
| Paper勝率 | **60.9%** | 60%以上 | ✅ 達成 |
| 継続期間 | 2026/04/03〜（9日） | 3ヶ月継続 | ⏳ 最短 07/03 |
| 取引回数 | 67件 | 100件完了 | ⏳ 進行中 |
| 学習モード | ON | OFF（100回後） | ⏳ |
