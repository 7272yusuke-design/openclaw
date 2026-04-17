# 📐 GSD計画 v6.5ba 引き継ぎ白書

> **更新日時**: 2026/04/17 JST
> **セッション**: v6.5ba（ACP v2 seller runtime 実装・接続完了）
> **自己採点**: 9/10（設計通りの実装完了・SSE接続成功・DRY_RUNで安全起動）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(FIFOロット) | v6.5ax時点: 49.4%（77件決済: 38勝39敗） |
| USDC | $70,393.48 |
| Holdings | BTC(0.1177) / ETH(3.7310) — v6.5ax時点のVIRTUAL売却完了 |
| 総資産 | $87,886.93（+$751.25 PnL） |
| サービス | **全5サービス稼働中**（neo-acp-seller-v2 追加） |
| L4 DD | v6.5ax時点 ~5% — 要注意圏 |
| 学習モード | OFF（完全にdead path削除） |

---

## ✅ 本セッション完了タスク（v6.5ba）

### Task 1: ACP v2 Seller Runtime 実装

**背景**: v6.5azで判明した「seller runtime未接続」問題の解決。旧 `neo-acp-seller.service` は v1 SDK + 旧ウォレット（0x3c6a...）で稼働しており、v2 NeoAutonomous（0x840cff90...）用のsellerが存在しなかった。

**作成ファイル**:
- `skills/acp-cli-v2/src/seller/offeringsLoader.ts` — 既存11 offerings を動的ロードするラッパー
- `skills/acp-cli-v2/src/seller/seller_native_v2.ts` — v2 SDK イベント駆動seller runtime

**seller_native_v2.ts 設計**:
- `createAgentFromConfig()` で v2 AcpAgent を初期化（P256署名 + Privy provider）
- `agent.on("entry", ...)` でイベント駆動（SSE transport）
- `job.funded` イベントをトリガーに処理開始
- `AcpJob.description` からoffering名をマッチング（完全一致 → 部分一致 → config.name照合）
- `contentType: "requirement"` メッセージからリクエストパラメータ抽出
- 既存 `handlers.ts` の `validateRequirements()` → `executeJob()` → `session.submit()` フロー
- `V2_SELLER_DRY_RUN=true` で署名・送信せずログのみ
- Discord通知・graceful shutdown・二重処理防止（processedJobs Set）

### Task 2: neo-acp-seller-v2.service 作成・起動

- `/etc/systemd/system/neo-acp-seller-v2.service` 作成
- `V2_SELLER_DRY_RUN=true` で安全起動
- `systemctl enable` で自動起動有効化

### Task 3: 接続確認・エージェント状態検証

- SSE transport 接続成功確認（ログ: `✅ Connected to ACP v2 server`）
- Agent address: `0x840cff9032a4ce29845e05aed510f0ca4ea16cab` ✅
- 11 offerings ロード成功
- VP API確認: `updatedAt` が接続時刻（2026-04-17T03:49:41.085Z）に更新 → VP側がseller接続を認識
- offerings 6件・resources 3件がAPI上で正常表示

---

## ⏭️ 次セッションの作業

### 最優先 — VP WebUI確認 & DRY_RUN解除

1. **VP WebUI確認**: app.virtuals.io でNeoAutonomousのプロフィールを確認
   - 「Graduate Agent」ボタンが出現しているか？
   - Stats が「not yet tracked」から変わっているか？
   - Graduation Progress の表示は？
2. **DRY_RUN解除**: VP WebUI確認後、問題なければ：
```bash
   # /etc/systemd/system/neo-acp-seller-v2.service の
   # Environment=V2_SELLER_DRY_RUN=true を false に変更
   sed -i 's/V2_SELLER_DRY_RUN=true/V2_SELLER_DRY_RUN=false/' /etc/systemd/system/neo-acp-seller-v2.service
   systemctl daemon-reload
   systemctl restart neo-acp-seller-v2.service
```
3. **旧サービス切替**: v2安定稼働確認後
```bash
   systemctl stop neo-acp-seller.service
   systemctl disable neo-acp-seller.service
   # seller_native.ts を .archive_deadcode_v65p/ に退避
```

### 最優先 — 勝率モニタリング
- v6.5ax施策（ブラックリスト戦略除外・confidence分布変更・TP/SL正常化）の効果確認
- 現在49.4% → 60%目標への推移を監視

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
| 学習モード | OFF | OFF（100回後） | ✅ 達成 |

---

## 🤖 サービス構成（v6.5ba）

| サービス | 状態 | 備考 |
|---|---|---|
| neo-radar | active | メインループ |
| neo-collector | active | 市場データ収集 |
| neo-resource-api | active | FastAPI port 8099 |
| neo-acp-seller | active | **旧v1** — 旧ウォレット(0x3c6a)接続。v2安定後に停止予定 |
| **neo-acp-seller-v2** | **active (NEW)** | **v2 SDK** — 正しいウォレット(0x840c)でSSE接続。DRY_RUN=true |

---

## ACP構成（v6.5ba 更新）

### Graduation対象: NeoAutonomous
- Agent UUID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
- ウォレット: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
- acpV2AgentId: 41437
- role: HYBRID
- offerings: 6件公開（offering_audit, profile_seo, vp_sentiment_scan, vp_market_analysis, vp_trade_evaluation, vp_backtest_demand）
- resources: 3件（active_positions, historical_performance, vp_market_pulse）
- PRO ラベル: あり
- **seller runtime**: ✅ v2 SSE接続済み（2026/04/17 03:49 UTC〜）
- **VP updatedAt**: 2026-04-17T03:49:41.085Z（seller接続で更新確認）

### seller runtime状況
- neo-acp-seller-v2.service: ✅ 稼働中（DRY_RUN=true）、正しいウォレット(0x840C)でSSE接続
- neo-acp-seller.service: 稼働中だが旧ウォレット(0x3c6a)に接続 → v2安定後に停止予定

### Graduation要件チェック
| 要件 | 状態 |
|---|---|
| ネイティブSDKエージェント | ✅ Web UI作成、v2 SDK |
| ジョブ完了実績 | ✅ jobRegistry 34件 |
| 3件連続成功 | ✅ successRate 100% |
| seller runtime稼働 | ✅ **v6.5baで解決** |
| offerings登録 | ✅ 6件公開 |
| resources登録 | ✅ 3件 |
| **VP WebUI確認** | ⏳ 未確認（要手動チェック） |

---

## 新規ファイル・変更ファイル（v6.5ba）

| ファイル | 変更内容 |
|---|---|
| skills/acp-cli-v2/src/seller/offeringsLoader.ts | **新規** — 既存offerings動的ローダー |
| skills/acp-cli-v2/src/seller/seller_native_v2.ts | **新規** — v2 SDK イベント駆動seller runtime |
| /etc/systemd/system/neo-acp-seller-v2.service | **新規** — systemdサービス（DRY_RUN=true） |

---

## v6.5ay〜az からの引き継ぎ（変更なし）

- EXIT_PROFILES誤キー修正済み
- ハードコードTP/SL削除済み
- LEARNING_MODE dead path全削除済み
- Dashboard学習モード進捗バー削除済み
- 協議会レポートにexit_profiles_summary追加済み
