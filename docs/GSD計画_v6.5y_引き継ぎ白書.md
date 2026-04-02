# 🎯 GSD計画 v6.5y — 引き継ぎ白書

> **更新日**: 2026/04/02 11:00 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/04/02 11:00 JST）

| 項目 | 状態 |
|---|---|
| **neo-radar.service** | ✅ 稼働中 |
| **neo-collector.service** | ✅ 稼働中（DB復旧済み） |
| **neo-resource-api.service** | ✅ FastAPI port 8099 |
| **neo-acp-seller.service** | ✅ ネイティブACP SDK seller稼働中 |
| **PaperWallet** | $83,734 USDC + AIXBT $4,358 |
| **総資産** | ~$88,092 |
| **勝率** | **59.3%**（FIFO決済済み27ペア: 16W 11L） |
| **直近10ペア勝率** | **20.0%**（2W 8L）⚠️ |
| **取引回数** | 77件（BUY=46+, SELL=31+） |
| **学習モード** | ✅ ON（目標100回中77回） |
| **CFO DDブロック** | 🔒 DD 5.4%（HWM $88,494 → 現在 $83,734、解除条件: $84,069） |
| **ACP Graduation** | 🟡 100%表示・Submission Portal未解決 |
| **Moltbook** | **neoautonomous** karma=1・followers=3・posts=4 |
| **Git** | v6.5y committed |

---

## 🔴 v6.5yの作業内容

### 完了した作業

| Task | 内容 | 結果 |
|---|---|---|
| **DB readonly障害発見** | collector.logで03/31 11:11からreadonly化を特定、45時間のデータ欠損 | 再起動で復旧 ✅ |
| **OHLCV自前集約ロジック追加** | `get_ohlcv_from_db`に5分ティック→1時間足キャンドル集約を追加。GeckoTerminal障害時のフォールバック | 完了 ✅ |
| **OHLCV鮮度チェック追加** | GeckoTerminal由来OHLCVが6h以上古い場合、ティック集約に自動切替 | 完了 ✅ |
| **DB再接続ロジック追加** | main loopで3回連続エラーorreadonly検知時に自動再接続＋書き込みテスト | 完了 ✅ |
| **LUNAフィルターリセット** | 96%暴落($0.1545→$0.0059)後、異常値フィルターの基準価格を手動リセット | 完了 ✅ |
| **データ汚染チェック** | gplearn(03/28最終更新)、Voyager/EvolveR(取引履歴ベース)、バックテスト(フラット除外フィルター有効)→汚染なし | 確認済み ✅ |
| **勝率低下原因分析** | 直近10ペア2W8L。03/24-25にAIXBT高値圏($0.025-0.027)でBUY→下降トレンドで連続SL。DB欠損とは無関係 | 分析完了 ✅ |

### 判明した重要事実

| 事実 | 詳細 |
|---|---|
| **DB readonly化の原因** | コレクターのSQLiteコネクションが無効化（03/31 11:08のファイル更新がトリガーの可能性）。`get_db()`を起動時1回のみ呼ぶ設計が脆弱 |
| **GeckoTerminal 429頻発** | radar(30秒)+arbitrage_monitor+collectorが同時にGeckoTerminal APIを叩くため。自前集約でOHLCV依存は排除 |
| **LUNA 96%暴落** | $0.1545→$0.0059。大口売却の可能性大。DexScreenerデータは正常 |
| **AIXBT連敗パターン** | 03/24-28にAIXBT高値掴み→ナンピン→SLの繰り返し。損失-3%〜-12%と損大利小 |
| **DDブロック解除条件** | 総資産 ≥ $84,069（HWM $88,494の-5%未満）で解除。現在あと+$335必要 |
| **5層売却の現AIXBTポジション** | Entry $0.02318、PnL -1.1%、SLまで余裕1.9%、保有15.7h/96h。全層未発火 |

---

## 📅 残タスク

### 🔴 P0: Graduation完了（最優先）

| Task | 内容 | 備考 |
|---|---|---|
| **Submission Portal特定** | VP Discord等でフォームURL確認 | ホワイトペーパーページに埋め込み |
| **動画録画** | 各offering(offering_audit, profile_seo)のジョブフロー録画 | Submission要件 |
| **フォーム提出** | Portal経由で動画・スクリーンショット提出 | |
| **VP手動レビュー** | 提出後7営業日 | |

### 🟡 P1: トレード改善

| Task | 内容 | 備考 |
|---|---|---|
| **勝率回復監視** | 59.3%→60%回復が必要（DEX移行条件） | DDブロック中は自然回復待ち |
| **DDブロック解除待ち** | 総資産$84,069で解除 | AIXBTポジション次第 |

### 🟠 P2: その他

- 学習モード100回完了（残23回・自動継続）
- Moltbook反響モニタリング
- 旧Neo USDC回収（$3.12）

---

## 🔑 重要アドレス一覧

| 項目 | アドレス |
|---|---|
| NeoAutonomous Agent Wallet | `0x3c6a5F33eb070730d3b121E3aFA7E1dFe45f6CAa` |
| NeoAutonomous Dev Wallet | `0x80f91039844d384176E1489A6f31a94A08B0ad18` |
| NeoTestBuyer Agent Wallet | `0x9999c67ab316d9Ae6445Aefe153406df2b310E1c` |
| NeoTestBuyer Dev Wallet | `0x3E3E4345823B65c283d957a440028441b522515b` |
| **DevRel Graduation Evaluator** | **`0x696B35E2113345Faddad8904A903C2728c28196a`** (ID 1419) |
| Butler Agent | `0xe1dF851B17af3E25c2aDc79192D59eb1308cFa26` |
| 旧Neo Agent Wallet | `0x54b70c4BB03D01FC5f2D7b3790642f1eBEe5118d`（$3.12 USDC残） |

---

## 📊 USDC残高（2026/04/02時点）

| Wallet | 残高 |
|---|---|
| Buyer (NeoTestBuyer) | ~$3.50 |
| Seller (NeoAutonomous) | ~$3.36 |
| 旧Neo | ~$3.12 |

---

## 📊 自己採点（v6.5y）

| 項目 | スコア | 変化 | 備考 |
|---|---|---|---|
| 判断精度 | 85% | -7 | 直近10ペア20%勝率、AIXBT高値掴み連発 |
| データ品質 | 95% | -4 | 45h欠損発見→修正。自前集約で冗長化 |
| 自己評価力 | 95% | — | |
| 影響力戦略 | 75% | — | |
| 経済圏参加 | 92% | — | |
| 戦略進化 | 80% | — | |
| リスク管理 | 95% | -3 | DDブロック正常稼働だが、連敗を事前防止できず |
| 総合 | 92% | -4 | DB障害修正＋勝率低下が課題 |

---

> 📌 設計方針・安全機構・TrinityCouncilフロー・自律サイクル・緊急コマンド・ファイルパス等の不変情報は **Claudeプロジェクトファイルの「再開手順.md」** を参照してください。
