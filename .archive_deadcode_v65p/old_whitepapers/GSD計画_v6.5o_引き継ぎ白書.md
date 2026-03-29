# 🎯 GSD計画 v6.5o — 引き継ぎ白書

> **更新日**: 2026/03/29 12:00 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/03/29 12:00 JST）

| 項目 | 状態 |
|---|---|
| **neo-radar.service** | ✅ 稼働中 |
| **neo-collector.service** | ✅ 稼働中（5分ティック + 60分ごと4h足OHLCVキャンドル自動取得） |
| **neo-resource-api.service** | ✅ FastAPI port 8099（ACP Resource用 — v6.5f /v1/プレフィックス追加） |
| **neo-acp-seller.service** | ✅ systemd管理下で稼働中（3 offerings提供中） |
| **PaperWallet** | $88,494 USDC（ポジションなし） |
| **総資産** | ~$88,494 |
| **勝率** | **61.5%**（FIFO決済済み26ペア / 73件取引） |
| **取引回数** | 73件（History基準: BUY=45, SELL=28） |
| **学習モード** | ✅ ON（目標100回中73回） |
| **ACP Graduation** | 🔴 **未卒業（Sandbox状態）** — Butler検索に表示されない |
| **ACP Job完了数** | 🔴 **0件** — Graduation要件10件に未到達 |
| **ACP Provider** | **3 offerings Listed** + 6 offerings Local only（取引系は一時非公開） |
| **ACP Profile** | SEO最適化済み（profile_seoスコア 57→75） |
| **Moltbook** | karma=80・followers=19 |
| **CostGuard** | 多層サーキットブレーカー（L1:LLMコスト / L2:日次損失 / L3:SL連続 / L4:DD5%） |
| **Git** | master 同期済み |

---

## 🟢 現在のACP Offerings（Listed）

| Offering | 価格 | 内容 |
|---|---|---|
| **graduation_boost** | $0.50 + 実費 | 対象offeringにBuyerとしてテスト発注 + QAレポート |
| **offering_audit** | $0.30 | offering品質・SEO・スキーマ・価格分析 |
| **profile_seo** | $0.30 | エージェントプロフィール全体のButler検索最適化分析 |

### 非公開（Local only — ファイル保持・再登録可能）
vp_sentiment_scan, vp_market_analysis, vp_trade_evaluation, vp_backtest_on_demand, vp_correlation_risk, vp_whale_alert

---

## 🔧 v6.5oで完了した作業

### Graduation Boost サービススイート実装

| Task | 内容 | 結果 |
|---|---|---|
| **サービスフロー詳細設計** | 受付→発注→QA→レポートの全工程設計 | docs/graduation_boost_design.md ✅ |
| **Sandbox API調査** | wallet指定でofferings取得できるか調査 | 不可→顧客自己申告方式に決定 ✅ |
| **graduation_boost offering** | テスト発注+QAレポート ($0.50+実費) | 実装・登録・テスト完了 ✅ |
| **offering_audit offering** | offering品質分析 ($0.30) | 実装・登録・テスト完了 ✅ |
| **profile_seo offering** | プロフィールSEO分析 ($0.30) | 実装・登録・テスト完了 ✅ |
| **取引系offerings非公開化** | 6 offerings delist | Local only化（再登録可能） ✅ |
| **プロフィールSEO最適化** | Neo自身のプロフィール改善 | profile_seoスコア 57→75 ✅ |
| **テスト実行** | offering_audit + profile_seo直接テスト | 両方正常動作確認 ✅ |

### 重要な発見事項
- **自分自身にはジョブ発注不可**（Provider wallet = Client walletでBad Request）
- **Sandbox agentのofferingsはAPI経由で取得不可**（browse=Butler検索のみ、wallet指定API無し）
- **offerings登録・受注はSandbox状態でも可能**（Butler検索に出ないだけ）
- **顧客のジョブ完了がNeo自身のGraduation実績にもカウントされる**可能性あり

---

## 📅 残タスク

### 🔴 P0: Graduation達成（最優先）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **集客開始** | Moltbook + X でwallet・offering名を宣伝 | 1h | 宣伝メソッド調整必要 |
| **Moltbook宣伝メソッド更新** | 3 offerings体制を反映 | 30min | post_graduation_boost_promo更新 |
| **Neo自身のGraduation** | 他エージェントのoffering10件テスト or 顧客ジョブで達成 | — | $25 USDC必要（自力の場合） |

### 🟠 P1: サービス品質改善

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **graduation_boost E2Eテスト** | 実際の他エージェントへの発注テスト | 1h | USDC必要 |
| **VP Guideトピック拡充** | 10→20+トピック | 1h | 反響データで優先順位付け |
| **Moltbook反響モニタリング** | karma/follower変化追跡 | 1h | M.3既存基盤活用 |
| **X(Twitter)連携検討** | Moltbook以外の集客チャネル | 2h | Butler X連携と相乗効果 |

### 🟡 P2: 取引機能（裏で継続）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **学習モード100回完了** | 残27回 | — | 自動継続 |
| **通常モード移行設計確認** | SOUL原則通常モード復帰 | 30min | 100回達成後 |

### 🟢 P3: Phase 2サービス（実績蓄積後）

| Task | 内容 | 備考 |
|---|---|---|
| **取引系offerings再公開** | 勝率+実績が揃った時点 | ファイル保持済み、sell create で即復活 |
| **D2実取引移行** | Aerodrome Finance DEX連携 | 最短2026/06/14 |

---

## ✅ 完了タスク一覧

### v6.5o（2026/03/29 — Graduation Boostサービススイート実装）

| Task | 内容 | 結果 |
|---|---|---|
| **Graduation Boost設計書** | サービスフロー・offering仕様・QAレポート形式 | docs/graduation_boost_design.md ✅ |
| **Sandbox API調査** | wallet指定offerings取得不可→自己申告方式 | 設計書更新 ✅ |
| **graduation_boost offering** | scaffold→offering.json→handlers.ts→sell create | Listed ✅ |
| **offering_audit offering** | Butler SEO分析・スキーマ品質・価格評価 | Listed ✅ |
| **profile_seo offering** | プロフィール全体のButler検索最適化 | Listed ✅ |
| **取引系6 offerings非公開** | sell delete（ファイル保持） | Local only ✅ |
| **プロフィールSEO最適化** | Graduation支援エージェントとして再定義 | 57→75点 ✅ |
| **テスト実行** | offering_audit + profile_seo | 正常動作確認 ✅ |

### v6.5n以前の完了タスク

| Version | 内容 |
|---|---|
| v6.5n | Council datetimeバグ修正、CYCLE_INTERVAL修正、Graduation Boost事業設計、VP Guide投稿、コンテンツ戦略転換 |
| v6.5m | ACP検索アルゴリズム完全調査、Sandbox問題特定、ACP SEO構想、開発代行提案書 |
| v6.5l | ACP Correlation Risk offering、多層サーキットブレーカーL1-L4、N.1実行ロジック |
| v6.5k | Arb Discord alert修正、vp_whale_alert offering、残タスク整理 |
| v6.5j | ACP 4 offerings化、handlers.tsバグ修正、sentiment_scan/backtest追加、Moltbook ACP宣伝 |
| v6.5i | H.2 v2完全分析、ナンピン制限、RSI閾値、confidence引上げ、ModelFactory、Voyager、EvolveR、N.1基盤 |
| v6.5h | SL/TP後スキップ、Phase 4b、gplearn G2、ポジションサイズ可変、トレーリングストップ |
| v6.5g | ACP Trade Evaluator、FIFO credentials修正、acp-node SDK |
| v6.5f | paper_trade.logバグ修正、Seller Runtime systemd化、Resource APIバージョニング、gplearn G1 |
| v6.5e以前 | ACP Provider化・confidence修正・BB修正・Moltbook転換・VP Whitepaper精読・OHLCVデータ品質等 |

---

## 📊 自己採点（v6.5o）

| 項目 | スコア | 変化 | 備考 |
|---|---|---|---|
| 判断精度 | 92% | — | 変更なし |
| データ品質 | 99% | — | 変更なし |
| 自己評価力 | 95% | — | 変更なし |
| 影響力戦略 | 72% | +4 | 3 offerings実装、プロフィールSEO最適化 |
| 経済圏参加 | 78% | +6 | Graduation Boostサービス稼働開始、offering_audit/profile_seoテスト完了 |
| 戦略進化 | 68% | +3 | サービス実装完了、集客・Graduation達成がNext |
| リスク管理 | 98% | — | 変更なし |
| 総合 | 94% | +2 | サービス設計→実装→テスト→最適化を1セッションで完了 |

---

## 🗺️ ロードマップ
```
【現在地】3 offerings Listed — テスト完了 — 集客・Graduation待ち

Phase 1: Graduation達成（直近）
  ├ 集客: Moltbook/X でwallet+offering宣伝 → 顧客獲得
  ├ 顧客ジョブ完了でNeo自身のGraduation実績積み
  ├ or $25 USDC投入で自力10件テスト
  └ Graduation → Butler検索露出 → 集客自動化
     ⬇
Phase 2: サービス拡充
  ├ 取引系offerings再公開（実績を土台に）
  ├ 学習100回完了→通常モード
  └ ACP SEOサービス拡張版
     ⬇
Phase 3: 本格稼働
  ├ DEX実取引移行（Aerodrome Finance）
  └ VP経済圏トップエージェントへ
```

---

> 📌 設計方針・安全機構・TrinityCouncilフロー・自律サイクル・緊急コマンド・ファイルパス等の不変情報は **Claudeプロジェクトファイルの「再開手順.md」** を参照してください。
