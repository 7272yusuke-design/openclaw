# 📐 GSD計画 v6.5aw 引き継ぎ白書

> **更新日時**: 2026/04/14 15:00 JST
> **セッション**: v6.5aw（ACP Graduation調査・Stats未表示問題の原因特定）
> **自己採点**: 75/100（根本原因を特定しAPI証拠を取得、ただしGraduation未完了）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(Evaluator FIFO) | **52.1%（71件決済: 37勝34敗）** ← 目標60%未達 |
| Tier0 (BTC/ETH) | 47.2%（36件）← 要改善 |
| Tier1 (VIRTUAL) | 57.1%（35件） |
| USDC | $73,028.64 |
| Holdings | BTC(0.1177/long) / VIRTUAL(8812/short) |
| サービス | 全4サービス稼働中 |
| L4 DD | ~5% — 要注意圏 |
| Council | 1hローテーション: BTC → VIRTUAL → ETH |
| ACP Graduation | **Stats API: 26件/100%成功** だがUI未表示（VP側バグ）→ Discord問い合わせ必要 |
| 学習モード | **97/100件（あと3件で到達）** |

### ⚠️ 重要な勝率修正
前セッションの白書では「60.9%（46件）」と記載していたが、これはEvaluatorの計算方式の問題だった。FIFOロット方式（ナンピンを個別ロットで計上）では**52.1%（71件）**が正確な値。H.2分析（SELL単位25件）とFIFOロット（71件）で銘柄別勝率が大きく異なることが判明し、本セッションで修正した。

---

## ✅ 本セッション完了タスク

### Task 1: ACP Graduation 状況調査（メインタスク）

**調査結果 — Stats未表示問題の原因特定:**

1. **V2 metrics API にはデータが存在する**
   - エンドポイント: `https://api.acp.virtuals.io/agents/019d7b3f-c2d8-7a52-839c-9629f4abb5dc/metrics`
   - jobs: 26件, successRate: 100%, volume: $6.90, revenue: $2.40, wallets: 2
   - ジョブ109-119（chain 8453）: 全11件 COMPLETED + ジョブ280追加

2. **Web UIが Stats を表示しない原因**
   - `browse` API の `lastActiveAt: 2999-12-31T00:00:00.000Z`（ダミー値）
   - UIがV2 metrics APIを参照していない → VP側フロントエンドのバグ
   - Graduation Progress バー・Graduate Agent ボタンも非表示

3. **DevRel Evaluator テスト結果**
   - V1 CLI（neo-test-buyer, OPENCLAW タグ付き）→ REJECTED
   - V2 CLI（neo-test-buyer-v2, タグなし, --legacy）→ REJECTED
   - Butler経由 → V1 only 警告、ウォレット入金+ETHガス代必要
   - 「Hire to Test」→ Non-Trading ACP SDK agents only

4. **PRO ラベル**: 両エージェントに自動付与済み（意味は不明、Graduationとは別）

**エージェント構成:**
| 名前 | UUID | ウォレット | cluster/tag | acpV2AgentId |
|---|---|---|---|---|
| Neo (v2) | 019d7659-... | 0x75e6...0a300a | OPENCLAW | 19768 |
| NeoAutonomous | 019d7b3f-... | 0x840C...16cab | なし | 41437 |
| neo-test-buyer-v2 | 019d76d4-... | 0x11ab...9ee82 | なし | なし |
| neo-test-buyer | 019d7bb4-... | 0x131d...5912 | OPENCLAW | 41409 |

**seller_native.ts の不整合:**
- .envの`NATIVE_AGENT_WALLET_ADDRESS=0x3c6a5F33...`は旧NeoAutonomous(v1)
- v2 NeoAutonomous(`0x840C...`)用のseller runtimeは未構築
- v2 CLIの`events listen`でSSE接続は可能（手動応答のみ）

**結論: Graduation進行にはDiscord問い合わせが必須**

---

## ⏭️ 次セッションの作業

### 最優先 — Graduation Discord問い合わせ
1. 下記テンプレートでDiscord投稿（API証拠付き）
2. 返答に応じてアクション判断

Discord投稿テンプレート:
    Agent: NeoAutonomous
    Agent ID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
    Wallet: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
    Chain: Base (8453)
    ISSUE: Stats shows "Stats not yet tracked" despite having metrics
    EVIDENCE: curl https://api.acp.virtuals.io/agents/019d7b3f-c2d8-7a52-839c-9629f4abb5dc/metrics
    Results: jobs=26, successRate=100%, volume=$6.90, revenue=$2.40, wallets=2
    UI shows: "Stats not yet tracked", No Graduation Progress, No Graduate Agent button
    Question: Is this a known V2 UI issue? How to proceed with graduation?

### 最優先 — 学習モード100件到達
3. あと3件で到達 → core/config.py の LEARNING_MODE = False に手動変更

### 最優先 — 勝率改善
4. Tier0（BTC/ETH）47.2%が全体を引き下げている
5. 銘柄別EvolveRルール（ETH -3）の効果確認

### 重要 — ACP seller v2対応
6. seller_native.tsをv2 NeoAutonomous(0x840C...)対応に改修
7. v2 SDK（AcpAgent + PrivyAlchemyEvmProviderAdapter）ベースのseller runtime
8. Graduation審査時にDevRel Evaluatorのテストジョブに自動応答が必要

### 重要 — Phase F3: Kelly基準ポジションサイジング
9. 勝率安定後に着手（現在は未達のため保留）

### 短期
10. パターンマイニング（sell_tracker蓄積後）
11. E3拡張: 戦略パターンルール自動生成
12. Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 新規ファイル・変更ファイル

| ファイル | 変更内容 |
|---|---|
| （本セッションではコード変更なし） | ACP調査・API検証のみ |

---

## ACP構成（v2移行後）

### Graduation対象: NeoAutonomous
- Agent UUID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
- ウォレット: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
- acpV2AgentId: 41437（V1時代のID）
- cluster/tag: なし（OPENCLAWフラグなし）
- Offerings: 6件（offering_audit, profile_seo, vp_sentiment_scan, vp_market_analysis, vp_trade_evaluation, vp_backtest_demand）
- Jobs: 26件COMPLETED (chain 8453, successRate 100%)
- Stats UI: 未表示（VP側バグ） — metrics APIにはデータあり
- PRO ラベル: あり

### v2 Neo (OPENCLAWタグ付き — Graduation対象外)
- Agent UUID: 019d7659-6dd1-7067-a5ff-d74f567a3961
- ウォレット: 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a
- cluster/tag: OPENCLAW

### seller runtime状況
- neo-acp-seller.service: 稼働中だが旧ウォレット(0x3c6a...)に接続
- v2 NeoAutonomous(0x840C...)用のseller: 未構築
- v2 CLI events listenでSSE接続可能（手動応答のみ）

### V2 CLI操作（skills/acp-cli-v2/）
- エージェント切替: npx tsx bin/acp.ts agent use --agent-id UUID
- ジョブ作成: npx tsx bin/acp.ts client create-job --provider WALLET --offering-name NAME --requirements JSON [--legacy]
- バジェット設定: npx tsx bin/acp.ts provider set-budget --job-id ID --amount USDC
- デリバラブル提出: npx tsx bin/acp.ts provider submit --job-id ID --chain-id 8453 --deliverable JSON
- 完了: npx tsx bin/acp.ts client complete --job-id ID --chain-id 8453 --reason TEXT
- Stats API: curl https://api.acp.virtuals.io/agents/019d7b3f-c2d8-7a52-839c-9629f4abb5dc/metrics

---

## 📊 移行条件進捗（D3準拠）

| 条件 | 現在 | 必要 | 判定 |
|---|---|---|---|
| Paper勝率 | **52.1%** | 60%以上 | ❌ 未達 |
| 継続期間 | 2026/04/03〜（11日） | 3ヶ月継続 | ⏳ 最短 07/03 |
| 取引回数 | 97件 | 100件完了 | ⏳ あと3件 |
| 学習モード | ON | OFF（100回後） | ⏳ |
