# 📐 GSD計画 v6.5ay 引き継ぎ白書

> **更新日時**: 2026/04/17 JST
> **セッション**: v6.5ay（Discord報告メンテナンス — 学習モードOFF後のクリーンアップ）
> **自己採点**: 88/100（5つのDiscord表示問題を一括解消、dead code削減）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(FIFOロット) | v6.5ax時点: 49.4%（77件決済: 38勝39敗） |
| USDC | $70,393.48 |
| Holdings | BTC(0.1177) / ETH(3.7310) — v6.5ax時点のVIRTUAL売却完了 |
| 総資産 | $87,886.93（+$751.25 PnL） |
| サービス | 全4サービス稼働中 |
| L4 DD | v6.5ax時点 ~5% — 要注意圏 |
| 学習モード | OFF（完全にdead path削除） |

---

## ✅ 本セッション完了タスク（v6.5ay: Discord報告メンテ）

### Task 1: EXIT_PROFILES誤キー修正（根本原因解決）
**問題**: Discord表示側が `trailing_start_pct` / `trailing_drop_pct` / `max_hold_hours` を参照していたが、config.py の EXIT_PROFILES の実キーは `trailing_start` / `trailing_drop` / `time_limit_hours` だった。3行の誤キーにより None 表示になっていた。

- agents/trinity_council.py:1588-1589 修正
- tools/discord_reporter.py:456 修正
- 他の参照箇所（run_trigger.py/config.py/trinity_council.py他）は全て正しいキーを使っており影響なし

### Task 2: ハードコードTP/SL削除（二重管理解消）
**問題**: trinity_council.py:100-102 で学習OFF時に TP=20%, SL=10% というハードコード値が使われており、EXIT_PROFILES（short=TP14/SL3, mid=TP25/SL5, long=TP50/SL8）と食い違っていた。

- ハードコード削除 → 保有ポジションの strategy_tag から正しい出口プロファイルを動的取得
- self.portfolio.wallet.state.get("holdings", ...) 経由で strategy_tag 参照

### Task 3: LEARNING_MODE dead path整理（5箇所）
**問題**: 学習モードOFF確定後も、LEARNING_MODE分岐が5箇所残存（caution_note / bear_backstory / Neo backstory三項演算 / Bearタスク説明 / import文）。コード可読性低下。

- trinity_council.py の LEARNING_MODE 実行参照を全削除（コメントとして削除履歴のみ残存）
- 約60行のdead code削除

### Task 4: Dashboard 学習モード進捗バー削除
**問題**: 学習OFF後も `▓▓▓▓▓▓▓▓▓▓ 107/100 (100%)` と無意味な進捗バーが表示されていた。

- tools/discord_reporter.py の send_performance_dashboard に三項分岐を導入
- 通常モード時は進捗バー削除、「📐 戦略別 出口プロファイル」を独立フィールドとして目立たせる
- EXIT_PROFILESの表示を1行圧縮→複数行展開で視認性向上
- ImportError時のフォールバック値を LEARNING_MODE=True→False に修正

### Task 5: 協議会レポートに現在モード/新TP/SL幅追加
**問題**: 協議会レポートに現在の運用モードと戦略別出口プロファイル情報がなく、学習OFF後の新TP/SL幅が見えにくかった。

- discussion_data に exit_profiles_summary キー追加
- send_council_minutes が新フィールドを受け取り協議会レポートの末尾に表示
- 「⚡ 通常モード稼働中」ラベル + EXIT_PROFILESダイジェスト表示

---

## ⏭️ 次セッションの作業

### 最優先 — v6.5ax から引き継ぎの効果モニタリング
1. 数日後にログで新confidence分布を確認
2. TP/SL幅通常化でL4 DD（~5%）が悪化しないか監視
3. ブラックリスト戦略除外後の新勝率推移を確認

### 最優先 — ACP Graduation Discord問い合わせ（v6.5ax 引き継ぎ・未完了）

Agent: NeoAutonomous
Agent ID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
Wallet: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
Chain: Base (8453)
ISSUE: Stats shows "Stats not yet tracked" despite having metrics
Results: jobs=26, successRate=100%, volume=$6.90, revenue=$2.40, wallets=2

### 重要 — ACP seller v2対応
- seller_native.tsをv2 NeoAutonomous(0x840C...)対応に改修
- v2 SDK（AcpAgent + PrivyAlchemyEvmProviderAdapter）ベースのseller runtime

### 重要 — bt常時HIGH問題
- バックテストconfidenceが常にHIGHで+15固定 → 情報価値なし、要調査

### 中期
- Phase F3: Kelly基準ポジションサイジング（勝率60%安定後）
- パターンマイニング（sell_tracker蓄積後）
- Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 移行条件進捗（D3準拠）

| 条件 | 現在 | 必要 | 判定 |
|---|---|---|---|
| Paper勝率 | v6.5ax時点: 49.4%（FIFOロット） | 60%以上 | ❌ 未達（改善施策適用済み） |
| 継続期間 | 2026/04/03〜（14日） | 3ヶ月継続 | ⏳ 最短 07/03 |
| 取引回数 | 107件 | 100件完了 | ✅ 達成 |
| 学習モード | **OFF** | OFF（100回後） | ✅ 達成 |

---

## 新規ファイル・変更ファイル（v6.5ay）

| ファイル | 変更内容 |
|---|---|
| agents/trinity_council.py | 誤キー修正 / ハードコードTP/SL削除 / LEARNING_MODE dead path全削除 / exit_profiles_summary生成追加 |
| tools/discord_reporter.py | 誤キー修正 / Dashboard進捗バー条件分岐 / exit_profiles_summaryフィールド受付追加 / EXIT_PROFILES表示を複数行展開 |

---

## v6.5ay Discord報告の新表示イメージ

### 協議会レポート末尾（新規追加）

📐 戦略別 出口プロファイル
⚡ 通常モード稼働中
short: SL -3.0% / HardTP +14.0% / Trail +5.0%開始-2.5%利確 / 上限 192h
mid:   SL -5.0% / HardTP +25.0% / Trail +10.0%開始-4.0%利確 / 上限 408h
long:  SL -8.0% / HardTP +50.0% / Trail +15.0%開始-6.0%利確 / 上限 1080h

### Dashboard（学習OFF後）

📐 戦略別 出口プロファイル
short: SL -3.0% / HardTP +14.0% / Trail +5.0%開始-2.5%利確 / 上限 192h
mid:   SL -5.0% / HardTP +25.0% / Trail +10.0%開始-4.0%利確 / 上限 408h
long:  SL -8.0% / HardTP +50.0% / Trail +15.0%開始-6.0%利確 / 上限 1080h

（進捗バー「107/100 (100%)」は削除）

---

## ACP構成（v6.5ax から変更なし）

### Graduation対象: NeoAutonomous
- Agent UUID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
- ウォレット: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
- acpV2AgentId: 41437（V1時代のID）
- Stats UI: 未表示（VP側バグ） — metrics APIにはデータあり
- PRO ラベル: あり

### seller runtime状況
- neo-acp-seller.service: 稼働中だが旧ウォレット(0x3c6a...)に接続
- v2 NeoAutonomous(0x840C...)用のseller: 未構築
