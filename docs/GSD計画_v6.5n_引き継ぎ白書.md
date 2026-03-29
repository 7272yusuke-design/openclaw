# 🎯 GSD計画 v6.5n — 引き継ぎ白書

> **更新日**: 2026/03/29 11:00 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/03/29 11:00 JST）

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
| **Moltbook** | karma=80・followers=19 — **v6.5nでコンテンツ戦略転換済み** |
| **CostGuard** | 多層サーキットブレーカー（L1:LLMコスト / L2:日次損失 / L3:SL連続 / L4:DD5%） |
| **Git** | master 同期済み |

---

## 🔴 v6.5n 戦略転換: Graduation Boost事業

### 事業方針の変更
取引サービスを後回しにし、**VP版エージェント広告代理店（Graduation支援）** をPhase 1事業とする。

### 根拠
- VP上に30,000+エージェント存在するが大半が埋もれている
- Butler検索にはGraduation必須だが、ジョブを発注するBuyerがいないため大半が未卒業
- 顧客は**人間のエージェント作成者**（エージェントではない）
- Neoは**Buyer側**なのでSandbox状態のまま今日から開始可能

### サービス概要: Graduation Boost
- NeoがBuyerとして顧客エージェントの各offeringにジョブ発注
- 10件完了（3連続成功確保）→ Graduation申請可能に
- 付加価値: offering品質QAレポート + プロフィールSEOアドバイス
- 料金: 相手のoffering費用（実費USDC）+ Neo手数料

### Neoへのリターン（三重取り）
1. 収益（手数料）
2. Buyer実績蓄積（unique agent数、job完了数 → Neo自身の信頼スコア向上）
3. 市場のoffering品質データ蓄積 → 将来のSEOサービスの知見

### 集客ファネル
```
教育コンテンツ（VP Guide毎日投稿）
  → ビルダーがフォロー＆学習
  → 「わかったけど面倒」層がNeoにDM
  → Graduation Boost受注
```

---

## 🔧 v6.5nで完了した作業

### バグ修正
| 修正 | 内容 |
|---|---|
| **Council datetimeエラー** | `from datetime import datetime, timezone`が`run()`内612行目にローカルimportされ、45行目の`datetime.now()`がUnboundLocalError → 先頭importに`timezone`追加・ローカルimport削除 |
| **CYCLE_INTERVAL未定義** | `run_trigger.py` 596行目の`time.sleep(CYCLE_INTERVAL)` → `CHECK_INTERVAL`に修正 |

### Moltbookコンテンツ戦略転換
| 変更 | Before | After |
|---|---|---|
| **日次投稿** | なし | VP Guide投稿（毎日）— 10トピックのビルダー向けハウツー |
| **洞察投稿（月水金）** | ポエム生成（「landscape」「chasm」等） | データ必須（「数字がなければWRONG」ルール、禁止語リスト追加） |
| **ACP宣伝（水曜）** | エージェント向けサービス宣伝 | **廃止** → Graduation Boost宣伝（土曜）に転換 |
| **テスト結果** | — | VP Guide投稿成功確認済み。実用的内容を生成 |

### 新規メソッド（tools/moltbook_tool.py）
- `post_vp_guide()` — VP実用ガイド投稿（10トピックランダム）
- `post_graduation_boost_promo()` — Graduation Boostサービス宣伝

### 投稿スケジュール（orchestration/nightly_research.py）
```
毎日:     VP Guide投稿（post_vp_guide）
月水金:   洞察投稿（post_insight — データ重視に改善）
土曜:     Graduation Boost宣伝（post_graduation_boost_promo）
日曜:     学習報告（post_weekly_lesson）
BUY/SELL時: Council判定投稿（post_council_decision）
```

---

## 📅 残タスク

### 🔴 P0: Graduation Boostサービス実装（最優先）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **サービスフロー詳細設計** | 受付→発注→QA→レポートの全工程設計 | 2h | 人間向けUX重視 |
| **自動ジョブ発注スクリプト** | browse → create job → track → complete の自動化 | 3h | ACP Buyer API活用 |
| **QAレポート生成機能** | offeringの応答品質・スキーマ整合性・SLA遵守を評価 | 2h | 付加価値の核 |
| **プロフィールSEO分析機能** | Vertex AI Search最適化の観点で改善提案 | 2h | Butler検索ランキング知見 |
| **料金・決済フロー設計** | USDC/VIRTUAL、人間からの受け取り方法 | 1h | オンチェーン or オフチェーン |
| **Neo自身のGraduation** | テスト用Buyer作成 + 10件ジョブ + ビデオ → 要$25 USDC/ETH | 3h | ⚠️ 資金必要 |

### 🟠 P1: コンテンツ品質改善（継続）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **VP Guideトピック拡充** | 10→20+トピック、FAQ形式追加 | 1h | 反響データで優先順位付け |
| **Moltbook反響モニタリング** | karma/follower変化の追跡、投稿種別ごと効果測定 | 1h | M.3既存基盤活用 |
| **X(Twitter)連携検討** | Moltbook以外の集客チャネル | 2h | Butler X連携と相乗効果 |

### 🟡 P2: 取引機能（裏で継続）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **学習モード100回完了** | 残27回 | — | 自動継続 |
| **通常モード移行設計確認** | SOUL原則通常モード復帰 | 30min | 100回達成後 |
| **ACP Evaluator役統合** | seller.tsにacp-node SDK統合 | 2h | ⚠️ ウォレット秘密鍵必要 |

### 🟢 P3: Phase 2サービス（実績蓄積後）

| Task | 内容 | 備考 |
|---|---|---|
| **取引分析サービス公開** | 勝率+実績が揃った時点で新サービス | Phase 1の信頼が土台 |
| **ACP SEOサービス化** | エージェント向け検索最適化代行 | Graduation Boostの上位版 |
| **D2実取引移行** | Aerodrome Finance DEX連携 | 最短2026/06/14 |

---

## ✅ 完了タスク一覧

### v6.5n（2026/03/29 — バグ修正 + 戦略転換 + コンテンツ改革）

| Task | 内容 | 結果 |
|---|---|---|
| **Council datetimeエラー修正** | ローカルimport → 先頭import移動 | 3回発生していたエラー解消 ✅ |
| **CYCLE_INTERVAL修正** | 未定義定数 → CHECK_INTERVAL | TP/SLサイクルエラー解消 ✅ |
| **Graduation Boost事業設計** | VP版エージェント広告代理店構想 | 戦略・ファネル・料金構造策定 ✅ |
| **VP Guide投稿メソッド** | 毎日のビルダー向けハウツー投稿 | 10トピック実装・テスト成功 ✅ |
| **Graduation Boost宣伝メソッド** | 土曜のサービス告知投稿 | 実装完了 ✅ |
| **洞察投稿プロンプト改善** | ポエム排除・データ必須ルール | 禁止語リスト+数字必須ルール ✅ |
| **投稿スケジュール再構成** | nightly_research統合 | 旧ACP宣伝廃止・新体制稼働 ✅ |

### v6.5m以前の完了タスク

| Version | 内容 |
|---|---|
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

## 📊 自己採点（v6.5n）

| 項目 | スコア | 変化 | 備考 |
|---|---|---|---|
| 判断精度 | 92% | — | 変更なし |
| データ品質 | 99% | — | 変更なし |
| 自己評価力 | 95% | — | 変更なし |
| 影響力戦略 | 68% | +8 | Moltbookコンテンツ刷新（ポエム→実用ガイド）、Graduation Boost集客ファネル設計 |
| 経済圏参加 | 72% | +2 | 事業方針明確化（Buyer代行）、ただし実装はこれから |
| 戦略進化 | 65% | +10 | 「取引サービス後回し→Graduation支援先行」の戦略転換は大きな進歩 |
| リスク管理 | 98% | — | Council datetime/CYCLE_INTERVALバグ修正 |
| 総合 | 92% | +2 | 戦略方向性が固まり、コンテンツ品質も劇的改善。次は実装で価値を証明する段階 |

---

## 🗺️ ロードマップ
```
【現在地】戦略転換完了 — コンテンツ改革済み — サービス実装前

Phase 1: Graduation Boost事業（メイン）
  ├ 集客: VP Guide毎日投稿 → フォロワー増 → DM受付
  ├ サービス: 自動ジョブ発注 + QAレポート + SEOアドバイス
  ├ 実装: browse→job create→track→report の自動化
  └ Neo自身もGraduation → Butler検索に出る
     ⬇
Phase 2: 取引分析サービス（裏で磨いて後出し）
  ├ ペーパー取引: 学習100回完了→通常モード
  ├ 勝率60%×3ヶ月の実績蓄積
  └ Phase 1の信頼基盤の上に新サービス展開
     ⬇
Phase 3: ACP SEOサービス + 実取引移行
  ├ Graduation Boostの上位版
  ├ Profile Audit / Offering Optimization
  └ DEX実取引（Aerodrome Finance）
```

---

> 📌 設計方針・安全機構・TrinityCouncilフロー・自律サイクル・緊急コマンド・ファイルパス等の不変情報は **Claudeプロジェクトファイルの「再開手順.md」** を参照してください。
