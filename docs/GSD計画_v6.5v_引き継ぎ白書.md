# 🎯 GSD計画 v6.5v — 引き継ぎ白書

> **更新日**: 2026/03/31 20:00 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/03/31 20:00 JST）

| 項目 | 状態 |
|---|---|
| **neo-radar.service** | ✅ 稼働中 |
| **neo-collector.service** | ✅ 稼働中（5分ティック + 60分ごと4h足OHLCVキャンドル自動取得） |
| **neo-resource-api.service** | ✅ FastAPI port 8099（ACP Resource用 — v6.5f /v1/プレフィックス追加） |
| **neo-acp-seller.service** | ✅ systemd管理下で稼働中（2 offerings提供中） |
| **PaperWallet** | $88,494 USDC（ポジションなし） |
| **総資産** | ~$88,494 |
| **勝率** | **61.5%**（FIFO決済済み26ペア / 73件取引） |
| **取引回数** | 73件（History基準: BUY=45, SELL=28） |
| **学習モード** | ✅ ON（目標100回中73回） |
| **ACP Graduation** | 🔴 **OpenClawエージェントはGraduation対象外（現時点）** — 下記詳細参照 |
| **ACP Job完了数** | ✅ **11件COMPLETED**（API確認済み・VP WebUI metricsは0のまま） |
| **ACP Provider** | **2 offerings Listed**（offering_audit, profile_seo） + 8 offerings Local only |
| **ACP Profile** | SEO最適化済み（profile_seoスコア 57→75） |
| **Moltbook** | **neoautonomous** karma=1・followers=3・posts=4 |
| **CostGuard** | 多層サーキットブレーカー（L1:LLMコスト / L2:日次損失 / L3:SL連続 / L4:DD5%） |
| **テストBuyer** | **neo-test-buyer** wallet=0x71d5...eC91（USDC残高あり） |
| **Git** | master 同期必要 |

---

## 🟢 現在のACP Offerings（Listed）

| Offering | 価格 | 内容 |
|---|---|---|
| **offering_audit** | $0.30 | offering品質・SEO・スキーマ・価格分析 |
| **profile_seo** | $0.30 | エージェントプロフィール全体のButler検索最適化分析 |

### 非公開（Local only — ファイル保持・再登録可能）
graduation_boost, graduation_complete, vp_sentiment_scan, vp_market_analysis, vp_trade_evaluation, vp_backtest_on_demand, vp_correlation_risk, vp_whale_alert

---

## 🔴 v6.5vで判明した重大事実：OpenClaw Graduation制限

### VP DevRel Graduation Evaluatorからの回答（原文）
> "We have not established a standard path for OpenClaw ACP agents to be graduated, but they are still eligible to compete for AGDP. ACP graduation is only open for native ACP SDK agents. To run a developer quality/throughput check only (not for ACP graduation), set openClawNonGraduationQualityCheckConsent to true on the job requirement and resubmit."

### 意味
- **OpenClaw CLI**（`openclaw-acp`リポジトリ）でビルドされたエージェントは、現時点でGraduation審査の正式対象外
- 「not established」= まだ確立していないだけで、永久不可ではない
- AGDP（Agent GDP）競争には参加可能
- 品質チェック（Graduation不要）は `openClawNonGraduationQualityCheckConsent: true` で実行可能

### 決定した方針：ネイティブACP SDK移行
- OpenClaw CLIのseller runtimeを、**@virtuals-protocol/acp-node SDKを直接使う方式**に書き換える
- offering定義・handlers.ts（ビジネスロジック）はそのまま再利用
- 変更箇所はseller runtimeの起動部分のみ（推定50行程度・2〜3時間）
- 移行後、再度Graduation Evaluatorに挑戦

---

## 🔧 v6.5vで完了した作業

| Task | 内容 | 結果 |
|---|---|---|
| **テストBuyer作成** | neo-test-buyer（agent ID 41409）作成 | 完了 ✅ |
| **USDC入金** | MetaMask→Buyer wallet $4 USDC送金 | 完了 ✅ |
| **Seller jobフロー確認** | Buyer curl→Seller accept→execute→deliver→COMPLETED | 完了 ✅ |
| **11件job完了** | offering_audit×5 + profile_seo×5 + 1追加 全COMPLETED | 完了 ✅ |
| **VP WebUI metrics問題発見** | API上11件完了だがWebUI Total Jobs=0のまま | 発見 ⚠️ |
| **EVALUATION PENDING問題調査** | 全jobでevaluation memo=PENDING・VP default evaluator未承認 | 調査済み |
| **Graduation Evaluator挑戦** | 3回REJECTED — OpenClaw制限判明 | 重要発見 🔴 |
| **ネイティブSDK移行方針決定** | seller runtimeのみ書き換え・handlers再利用 | 方針確定 ✅ |
| **funds-required offerings非公開** | graduation_boost, graduation_complete → Local only | 完了 ✅ |

---

## 📝 v6.5vで得た知見

### ACP Job作成フロー（curlでBuyerとして発注）
```bash
# Seller稼働中に、Buyerのx-api-keyでPOST
curl -s -X POST "https://claw-api.virtuals.io/acp/jobs" \
  -H "x-api-key: $BUYER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"providerWalletAddress":"<SELLER_WALLET>","jobOfferingName":"<OFFERING>","serviceRequirements":{...}}'
```

### 重要：agent switch時のAPIキー再生成
- `acp agent switch`するたびにAPIキーが再生成される
- `.env`の`LITE_AGENT_API_KEY`も毎回更新が必要
- Buyerキーを使う場合は`/tmp/buyer_key.txt`等に事前保存してcurlで使う

### ACP Jobフェーズ（実測）
```
REQUEST → Seller accepts + requestPayment → NEGOTIATION
NEGOTIATION → Buyer pays (auto if USDC sufficient) → TRANSACTION
TRANSACTION → Seller executes + delivers → EVALUATION → COMPLETED
```

### EVALUATION PENDINGについて
- VP default evaluator `0x3675E1AB3c4E0B32A950BD55a989B97F5dEf6199` が自動承認するはずだが、OpenClawエージェントではPENDINGのまま
- jobはCOMPLETEDフェーズに進むが、metricsにカウントされない可能性

---

## 📅 残タスク

### 🔴 P0: ネイティブACP SDK移行 → Graduation（最優先）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **native seller runtime作成** | ACP Node SDKでWebSocket接続・onNewTask/onEvaluate処理 | 2h | 既存handlersを接続 |
| **offerings再登録** | native SDKで offering_audit, profile_seo を登録 | 30min | |
| **テスト** | Buyer→新Seller→job完了→metrics反映確認 | 1h | |
| **Graduation Evaluator再挑戦** | 品質テスト→100%合格→手動レビュー申請 | 1h + 5-10営業日 | $4.59程度 |
| **graduation_boost/complete再公開** | Evaluator合格後に再登録 | 15min | |

### 🟠 P1: サービス品質改善（変更なし）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **Moltbook反響モニタリング** | karma/follower変化追跡 | 1h | M.3既存基盤活用 |
| **X(Twitter)連携検討** | Moltbook以外の集客チャネル | 2h | |
| **Buyer戦略: 情報購入→Council統合** | Orion/Wolfpack等の情報offeringをBuyer発注 | 3h | Graduation後 |

### 🟡 P2: 取引機能（裏で継続・変更なし）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **学習モード100回完了** | 残27回 | — | 自動継続 |
| **通常モード移行設計確認** | SOUL原則通常モード復帰 | 30min | 100回達成後 |

### 🟢 P3: Phase 2サービス（変更なし）

| Task | 内容 | 備考 |
|---|---|---|
| **取引系offerings再公開** | 勝率+実績が揃った時点 | ファイル保持済み |
| **D2実取引移行** | Aerodrome Finance DEX連携 | 最短2026/06/14 |

---

## ✅ 完了タスク一覧

### v6.5v（2026/03/31 — Graduation挑戦・OpenClaw制限判明・SDK移行方針決定）

| Task | 内容 | 結果 |
|---|---|---|
| **テストBuyer作成** | neo-test-buyer wallet作成 | 完了 ✅ |
| **USDC入金** | MetaMask→Buyer $4 | 完了 ✅ |
| **11件job完了** | curl発注→Seller処理→全COMPLETED | 完了 ✅ |
| **Graduation Evaluator挑戦** | OpenClaw制限で3回REJECTED | 重要発見 🔴 |
| **方針決定: native SDK移行** | seller runtime書き換え→Graduation再挑戦 | 方針確定 ✅ |
| **offerings整理** | graduation_boost/complete非公開化 | 完了 ✅ |

### v6.5u以前の完了タスク

| Version | 内容 |
|---|---|
| v6.5u | VP ACP経済圏データ把握、価格改定、ACPプロフィール更新、USDC入金 |
| v6.5t | N.1 Z-score統合、旧アカウント排除、Graduation要件調査 |
| v6.5s | Moltbookエンゲージャー全面刷新・新アカウント |
| v6.5r | streak連敗ペナルティ改善、VP Guideトピック拡充 |
| v6.5q | コードベース整理・ARCHITECTURE.md・バグ修正 |
| v6.5p | Moltbook投稿スケジュール刷新 |
| v6.5o | Graduation Boostサービススイート実装 |
| v6.5n以前 | Council修正、ACP検索調査、多層CB、Arb修正、ACP4化、H.2分析、gplearn等 |

---

## 📊 自己採点（v6.5v）

| 項目 | スコア | 変化 | 備考 |
|---|---|---|---|
| 判断精度 | 92% | — | 変更なし |
| データ品質 | 99% | — | 変更なし |
| 自己評価力 | 95% | — | 変更なし |
| 影響力戦略 | 75% | — | 変更なし |
| 経済圏参加 | 82% | +2 | 11件job完了、Graduation制限理解、SDK移行計画 |
| 戦略進化 | 75% | +5 | OpenClaw制限の発見と対応方針の迅速な決定 |
| リスク管理 | 98% | — | 変更なし |
| 総合 | 95% | — | Graduation未達だが障害の特定と対策方針は明確 |

---

## 🗺️ ロードマップ（修正版）
```
【現在地】11件job完了 — OpenClaw Graduation制限判明

Phase 0: ネイティブACP SDK移行（次回セッション）
  ├ seller runtimeをnative SDKで再実装（50行程度）
  ├ 既存handlers.ts接続・offerings再登録
  ├ テスト（Buyer→Seller→COMPLETED→metrics反映確認）
  └ Graduation Evaluator再挑戦→100%合格→手動レビュー申請
     ⬇
Phase 1: Graduation達成
  ├ DevRelレビュー（5-10営業日）
  ├ Graduation → Butler検索露出 → 集客自動化
  └ graduation_boost/complete再公開
     ⬇
Phase 2: サービス拡充 + Buyer戦略（変更なし）
     ⬇
Phase 3: 本格稼働（変更なし）
```

---

## 🔑 テストBuyer情報

| 項目 | 値 |
|---|---|
| Agent名 | neo-test-buyer |
| Agent ID | 41409 |
| Wallet | 0x71d50c6CBEb24C5B54b28dd574EC46dBd820eC91 |
| APIキー保存先 | /tmp/buyer_key.txt（再起動で消えるので注意） |
| USDC残高 | ~$3.64（$6.64 - $3.00 consumed） |

---

> 📌 設計方針・安全機構・TrinityCouncilフロー・自律サイクル・緊急コマンド・ファイルパス等の不変情報は **Claudeプロジェクトファイルの「再開手順.md」** を参照してください。
