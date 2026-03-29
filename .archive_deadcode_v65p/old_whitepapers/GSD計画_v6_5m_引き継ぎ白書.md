# 🎯 GSD計画 v6.5m — 引き継ぎ白書

> **更新日**: 2026/03/28 19:00 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/03/28 19:00 JST）

| 項目 | 状態 |
|---|---|
| **neo-radar.service** | ✅ 稼働中 |
| **neo-collector.service** | ✅ 稼働中（5分ティック + 60分ごと4h足OHLCVキャンドル自動取得） |
| **neo-resource-api.service** | ✅ FastAPI port 8099（ACP Resource用 — v6.5f /v1/プレフィックス追加） |
| **neo-acp-seller.service** | ✅ systemd管理下で稼働中（6 offerings提供中） |
| **PaperWallet** | $88,494 USDC（ポジションなし） |
| **総資産** | ~$88,494 |
| **勝率** | **61.5%**（FIFO決済済み26ペア / 73件取引） |
| **取引回数** | 73件（History基準: BUY=45, SELL=28） |
| **学習モード** | ✅ ON（目標100回中73回） |
| **ACP Graduation** | 🔴 **未卒業（Sandbox状態）** — Butler検索・Agent-to-Agentタブに表示されない |
| **ACP Job完了数** | 🔴 **0件** — Graduation要件10件に未到達 |
| **ACP Provider** | 6 offerings + 3 resources + Seller Runtime(systemd) + Resource API稼働中 |
| **ACP Evaluator SDK** | v6.5g @virtuals-protocol/acp-node導入済み。⚠️ ウォレット秘密鍵待ち |
| **Moltbook** | karma=75・followers=18 — VP分析洞察スタイル + 水曜ACP宣伝自動投稿 |
| **CostGuard** | 多層サーキットブレーカー（L1:LLMコスト / L2:日次損失 / L3:SL連続 / L4:DD5%） |
| **Git** | master 同期済み |

---

## 🔴 重大発見（v6.5m）: ACP Visibility問題

### 問題の本質
NeoはACP Marketplace上で**Sandbox（未卒業）状態**にあり、以下の集客経路が完全に閉ざされている：
- ❌ Butler検索からの自動ルーティング
- ❌ Agent-to-Agentタブでの発見
- ❌ ERC-8004オンチェーン信頼レイヤー

`browseAgents("market analysis")`の結果にNeoは含まれず、Tradescoop/Elfa AI/Loky等の競合のみ表示される。
`browseAgents("Neo")`でも別ウォレットの同名エージェントのみ。

### 根本原因
ACP Jobを**1件も完了していない**。Graduation要件は10件成功（うち3件連続）。

### Butlerの検索アルゴリズム（調査済み）
- **検索エンジン**: Google Vertex AI Search
- **検索方式**: ハイブリッド検索（キーワード＋エンベディング）→ メトリクスベースのリランカー
- **インデックス対象**: agent name / description / job offerings / SLA / success rate / ratings & reviews / unique buyer count
- **ソート可能メトリクス**: SUCCESSFUL_JOB_COUNT / SUCCESS_RATE / UNIQUE_BUYER_COUNT / MINS_FROM_LAST_ONLINE / GRADUATION_STATUS / ONLINE_STATUS
- **テキスト最適化**: VP公式ベストプラクティスで「クラスターキーワードを文頭に配置」「詩的表現を避ける」「Agent GoalをbrowseAgentsマッチに最適化」が推奨
- **前提条件**: Sandbox状態のエージェントはBrowse/Butler検索結果に含まれない（Graduated必須）
- **Leaderboardランキング**: aGDP / Job Volume / Unique Users / Success Rate

### Graduation要件（調査済み）
1. テスト用Buyerエージェントを作成（2つ目のウォレット）
2. Buyerから10件のSandboxジョブを成功させる（うち3件連続成功）
3. 各offering動作のビデオ録画を提出
4. Virtualsチームが手動レビュー（約7営業日）
5. 承認後、Agent-to-Agentタブ＋Butler検索に表示

### 必要リソース
- テスト用Buyerウォレット: 新規作成
- USDC: ~$10-20（6 offering × テストジョブ分）
- ETH (Base chain): ガス代用（ごく少額、~$1-2）

---

## 📅 残タスク

### 🔴 P0: ACP Graduation（最優先・集客のブロッカー）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **テスト用Buyerエージェント作成** | 2つ目のウォレット作成・ACP登録 | 1h | USDC+ETH入金必要 |
| **Sandbox 10件ジョブ完了** | 6 offeringを網羅的にテスト実行 | 2h | 3件連続成功必須 |
| **ビデオ録画・提出** | 各offering動作録画 + 起動手順録画 | 1h | VP提出フォーム経由 |
| **レビュー待ち** | Virtualsチーム手動レビュー | 7営業日 | 不合格なら再提出 |

### 🟠 P1: ACP Visibility最適化（Graduation後）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **プロフィール最適化** | Vertex AI Search ハイブリッド検索に最適化した説明文・Goalリライト | 1h | クラスターキーワード文頭配置 |
| **Offering文言最適化** | 6 offeringのdescription/requirementスキーマ改善 | 2h | Butler誘導精度向上 |
| **Job Examples整備** | 全offeringにサンプルリクエスト＋サンプル成果物追加 | 2h | VP公式機能（発見率向上） |
| **SLA最適化** | 現在全5分 → offering特性に合わせた適正値設定 | 30min | 成功率メトリクスに影響 |

### 🟡 P2: 集客チャネル拡張

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **Moltbook投稿強化** | 週1宣伝→日次分析投稿+週2宣伝に拡大 | 2h | karma/follower向上 |
| **X(Twitter)連携** | ACP CLI Twitter機能でVP関連自動反応 | 3h | Butler X連携と相乗効果 |
| **Buyerとしてジョブ発注** | 他エージェントのサービスを利用→関係性構築 | 1h | ACP Accounts蓄積 |
| **Resource API拡充** | 無料Resource追加で認知→有料Job導線 | 2h | — |

### 🟢 P3: ACP SEOサービス化（実績蓄積後）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **自己SEOスキル実装** | Voyager/EvolveRで最適化効果を自動学習 | 3h | 自分のメトリクス変化を追跡 |
| **ACP Profile Audit offering** | 他エージェントのプロフィール監査サービス | 2h | $5-10/回 |
| **Offering Optimization offering** | 説明文・スキーマ最適化代行 | 2h | $10-20/offering |
| **Visibility Boost Package** | Audit+最適化+テストジョブ一括 | 2h | $30-50 |

### 🔵 既存P1: 学習モード中（継続）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **ACP Evaluator役統合** | seller.tsにacp-node SDK統合 | 2h | ⚠️ ウォレット秘密鍵必要 |
| **学習モード100回完了** | 残27回 | — | 自動継続 |
| **通常モード移行設計確認** | SOUL原則通常モード復帰 | 30min | 100回達成後 |
| **ModelFactory Pro切り替え** | critical→Gemini Pro移行 | 30min | コスト確認後 |

### 既存P3: 実取引移行（STAGE 4）

| Task | 内容 | 備考 |
|---|---|---|
| **D2設計書レビュー** | 実取引チェックリスト確認 | 最短2026/06/14 |
| **実取引移行** | Aerodrome Finance DEX連携 | 勝率60%×3ヶ月 |

---

## ✅ 完了タスク一覧

### v6.5m（2026/03/28 — ACP Visibility調査+GSD計画策定）

| Task | 内容 | 結果 |
|---|---|---|
| **ACP検索アルゴリズム完全調査** | Vertex AI Search / browseAgents / Leaderboard / Graduation要件 | 検索ロジック6要素特定 ✅ |
| **Graduation状態確認** | browseAgentsでNeo未検出 → Sandbox確定 | 🔴 集客ブロッカー特定 ✅ |
| **ACP SEOサービス構想** | エージェント向け検索最適化サービスの設計 | P3として計画化 ✅ |
| **エージェント開発代行提案書** | VP特化・縁故¥500,000/一般¥1,300,000 | 提案書作成 ✅ |

### v6.5l以前の完了タスク

| Version | 内容 |
|---|---|
| v6.5l | ACP Correlation Risk offering、多層サーキットブレーカーL1-L4、N.1実行ロジック |
| v6.5k | Arb Discord alert修正、vp_whale_alert offering、残タスク整理 |
| v6.5j | ACP 4 offerings化、handlers.tsバグ修正、sentiment_scan/backtest追加、Moltbook ACP宣伝 |
| v6.5i | H.2 v2完全分析、ナンピン制限、RSI閾値、confidence引上げ、ModelFactory、Voyager、EvolveR、N.1基盤 |
| v6.5h | SL/TP後スキップ、Phase 4b、gplearn G2、ポジションサイズ可変、トレーリングストップ |
| v6.5g | ACP Trade Evaluator、FIFO credentials修正、acp-node SDK |
| v6.5f | paper_trade.logバグ修正、Seller Runtime systemd化、Resource APIバージョニング、gplearn G1 |
| v6.5e以前 | ACP Provider化・confidence修正・BB修正・Moltbook転換・VP Whitepaper精読・OHLCVデータ品質等 |

---

## 📊 自己採点（v6.5m）

| 項目 | スコア | 変化 | 備考 |
|---|---|---|---|
| 判断精度 | 92% | — | 変更なし |
| データ品質 | 99% | — | 変更なし |
| 自己評価力 | 95% | +3 | ACP検索アルゴリズム完全調査・Sandbox問題特定 |
| 影響力戦略 | 60% | -18 | 🔴 Sandbox状態＝Butler検索に出ない事実が判明。実質的な露出ゼロ |
| 経済圏参加 | 70% | -15 | 🔴 Job完了0件。offeringは整備済みだが利用実績なし |
| 戦略進化 | 55% | +5 | ACP SEOサービス構想・エージェント開発代行提案書 |
| リスク管理 | 98% | — | 変更なし |
| 総合 | 90% | -7 | Sandbox問題は深刻だが、特定＋対策計画化は大きな前進 |

---

## 🗺️ ロードマップ
```
【現在地】Sandbox状態 — Butler検索に出ない — Job完了0件

Phase 0: ACP Graduation（最優先）
  ├ テスト用Buyer作成 + USDC/ETH入金
  ├ 10件Sandboxジョブ完了（3件連続成功）
  ├ ビデオ録画・VP提出
  └ レビュー通過 → Graduated状態へ
     ⬇
Phase 1: ACP Visibility最適化
  ├ プロフィール・Offering文言をVertex AI Search最適化
  ├ Job Examples整備
  ├ SLA最適化
  └ Butler検索での発見率向上
     ⬇
Phase 2: 集客チャネル拡張
  ├ Moltbook投稿強化
  ├ X(Twitter)連携
  ├ Buyerとして他エージェント利用
  └ Resource API拡充
     ⬇
Phase 3: ACP SEOサービス化
  ├ 自己SEOスキルをVoyager/EvolveRで学習
  ├ Profile Audit / Offering Optimization offering
  └ エージェント向け「広告代理店」ポジション確立
```

---

> 📌 設計方針・安全機構・TrinityCouncilフロー・自律サイクル・緊急コマンド・ファイルパス等の不変情報は **Claudeプロジェクトファイルの「再開手順.md」** を参照してください。
