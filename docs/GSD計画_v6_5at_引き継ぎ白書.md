# 📐 GSD計画 v6.5at 引き継ぎ白書

> **更新日時**: 2026/04/11 19:00 JST
> **セッション**: v6.5at（Council Error修正・ACP v2移行・Graduation 10件完了）
> **自己採点**: 75/100（ACP v2移行完了・10件COMPLETED。Stats未反映でGraduation未達）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(Evaluator) | **43.75%（32件決済）** ← 目標60%を大幅下回る |
| USDC | $48,446 |
| Holdings | BTC(0.1177/long) / VIRTUAL(19745+/mid) / ETH(7.4574/short) |
| サービス | 全4サービス稼働中 |
| L4 DD | 6.26% — 上限8%に接近 |
| Council | 1hローテーション: BTC → VIRTUAL → ETH |
| Moltbook | karma=97, followers=13 |
| ACP v2 Neo | 10件COMPLETED（on-chain確認済み）→ Stats更新待ち |

---

## ✅ 本セッション完了タスク

### Task 1: Council Error修正（discussion_data UnboundLocalError）
- **問題**: discussion_dataが1537行で定義されるのに1337行・1369行で参照 → Council実行時にクラッシュ
- **原因**: v6.5asでAIポジションサイズ・exit_profile動的化の際、discussion_dataを参照すべきところを_position_strategy（919行で初期化済み）に置き換え忘れ
- **修正**: 1337行・1369行のdiscussion_data.get("strategy", {})を_position_strategyに変更
- **副次効果**: Discord報告書の出口戦略未記載も解消（discussion_dataクラッシュでDiscord送信自体が失敗していたのが主因）

### Task 2: ACP v2移行
- **背景**: VP側がACP v1→v2アップデート。全legacy agentに「Deprecated Legacy ACP, Upgrade Now」表示。Graduationにはv2移行必須
- **実施内容**:
  1. v2 Neo作成（Web UI: Self-hosted, ウォレット0x75e6...a300a）
  2. 新CLI（acp-cli from github.com/Virtual-Protocol/acp-cli）をクローン・セットアップ
  3. acp configure → ブラウザ認証
  4. acp agent add-signer → P256署名鍵をOS keychainに保存
  5. v2 offering登録: vp_sentiment_scan ($0.01, テスト用価格)
  6. v2 test buyer作成: neo-test-buyer-v2（0x11ab...ee82）+ signer追加
  7. **10件テストjob全件COMPLETED**（Job #22, 31-41, chain 8453）

### Task 3: Legacy offerings登録（v1 Neo）
- vp_sentiment_scan, vp_market_analysis, vp_trade_evaluation, vp_backtest_on_demand を旧CLIでListed化
- v2移行により旧offeringsは不要になったが記録として残す

---

## 未解決: Graduation Stats未反映

- v2 NeoのWeb UIで「Stats not yet tracked」表示
- 10件on-chain completedだがメトリクス未更新
- 原因候補: メトリクス更新タイミング（10分以内のインタラクション必要）/ バックエンド遅延
- **対応**: 時間経過で反映されるか確認 → ダメならDiscord問い合わせ

### Discord問い合わせ用テンプレート

Agent: Neo (v2, Self-hosted)
Agent ID: 019d7659-6dd1-7067-a5ff-d74f567a3961
Wallet: 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a
SDK: ACP CLI v2 (acp-cli from github.com/Virtual-Protocol/acp-cli)
Offering: vp_sentiment_scan ($0.01)

Completed 10 jobs on-chain (Job IDs: 22, 31-41, chain 8453)
All jobs verified as completed via acp job history

Issue: Agent Stats shows "Stats not yet tracked"
and no "Graduate Agent" button appears.

---

## 次セッションの作業

### 最優先 — Graduation
1. Web UIでStats更新確認 → Graduate Agentボタン表示確認
2. 未表示ならDiscord問い合わせ
3. events listenでオンライン状態維持が有効か検証

### 最優先 — v6.5at修正の効果検証
4. grep -E "AI推奨サイズ|exit_profile|discussion_data" radar_output.log | tail -20
5. Discord報告書に出口戦略が表示されるか確認
6. Council Errorが再発しないことの確認

### 重要（v6.5asから継続）
7. 勝率・RR比の推移（利小損大パターン改善の確認）
8. RSI Exit改善効果: grep "SELL根拠" radar_output.log
9. sell_tracker.jsonの蓄積データ確認

### 短期
10. VP/Graduation完了後、ACP seller runtimeをv2対応に切り替え
11. パターンマイニング（50件蓄積後）
12. E3拡張: 戦略パターンルール自動生成

---

## 新規ファイル・変更ファイル

| ファイル | 変更内容 |
|---|---|
| agents/trinity_council.py | L1337/L1369: discussion_data → _position_strategy に修正 |
| skills/acp-cli-v2/ | 新規: ACP v2 CLI（github.com/Virtual-Protocol/acp-cli クローン） |
| skills/openclaw-acp-v2/ | 新規: 旧CLIの最新upstream版（参考用・未使用） |

---

## ACP構成（v2移行後）

v2 Neo (Self-hosted)
- Agent ID: 019d7659-6dd1-7067-a5ff-d74f567a3961
- ウォレット: 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a
- CLI: skills/acp-cli-v2/ (acp-cli)
- Signer: P256鍵（OS keychain保存済み）
- Offering: vp_sentiment_scan ($0.01)
- Jobs: 10件COMPLETED (chain 8453)

v2 neo-test-buyer-v2
- Agent ID: 019d76d4-4e69-76c4-99d7-b90c64988af3
- ウォレット: 0x11ab498cea003b73b66ab48222cb240fe7a9ee82
- Signer: P256鍵（OS keychain保存済み）

Legacy（非アクティブ）
- Neo (ID 19768) — 0x54b7... → Deprecated
- NeoAutonomous (ID 41437) — 0x3c6a... → Deprecated
- neo-test-buyer (ID 41409) — 0x71d5... → Deprecated
- NeoTestBuyer — 0x9999... → Deprecated

neo-acp-seller.service — 稼働中（NeoAutonomous用、既存4 offerings）
