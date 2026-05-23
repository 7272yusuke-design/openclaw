# 🎓 Neo ACP Graduation 経緯まとめ（v2最新版）

> **作成日**: 2026/04/22
> **改訂**: v1版（2026/04/01）は v6.5v時点の古い情報。v6.5az〜v6.5baで真因が判明したため全面改訂。
> **目的**: Graduation問題の全経緯を時系列で整理し、v2 seller本番稼働への移行計画の基礎とする

---

## 0. TL;DR（3行要約）

1. **「Graduationできない」の真因は、v2エージェント (0x840cff...) で seller runtime が DRY_RUN のまま稼働し、実ジョブを処理していないから**
2. 旧v1エージェント (41437, 0x3c6a...) は Virtuals Protocol側のregistry刷新により対象外
3. v6.5baで v2 seller の実装・SSE接続は完了済み。**あとは DRY_RUN 解除 → 本番稼働 → 10 jobs完走で Graduation 申請可能**

---

## 1. エージェント一覧（最新）

| 名前 | ID | Wallet | 種別 | SDK | サービス | Graduation状態 |
|---|---|---|---|---|---|---|
| **旧Neo** | 19768 | `0x54b70c4B...` | Seller | OpenClaw CLI (legacy) | — | 非アクティブ |
| **NeoAutonomous v1** | 41437 | `0x3c6a5F33...` | Seller | acp-node v1 | `neo-acp-seller.service` | 旧registry、対象外扱い |
| **NeoAutonomous v2** | 未確認 | `0x840cff90...` | Seller | **acp-node-v2** | `neo-acp-seller-v2.service` | **jobRegistry 34件受諾・seller処理ゼロ** |
| **neo-test-buyer** | 41409 | `0x71d50c6C...` | Buyer | OpenClaw CLI | — | テスト用 |
| **NeoTestBuyer** | — | `0x9999c67a...` | Buyer | v1 | — | テスト用 |

### acp-cli-v2/config.json 登録ウォレット（4件）

| Wallet | 用途推定 | publicKey |
|---|---|---|
| `0x75e65397...` | 不明（最古） | 設定済 |
| `0x11ab498c...` | 不明 | 設定済 |
| **`0x840cff90...` (activeWallet)** | **現行v2 NeoAutonomous** | 設定済 |
| `0x131d3ff8...` | 作成途中の可能性 | 空 |

---

## 2. 時系列（修正版）

### Phase 1: 旧Neo時代（〜v6.5u）
- 旧Neo（ID 19768）をOpenClaw CLIで登録
- offerings登録、seller runtime稼働
- Graduation条件に到達せず

### Phase 2: テストBuyer・11件job完了（v6.5v）
- neo-test-buyer（ID 41409）作成、11件のjobをCOMPLETED
- **EVALUATION=PENDING**（旧デフォルトEvaluatorが承認せず）
- VP WebUIでTotal Jobs=0問題

### Phase 3: Graduation Evaluator挑戦 → OpenClaw拒否（v6.5v）
- DevRel Evaluator (ID 1419, `0x696B35E2...`) に3回送信 → 全件REJECTED
- 拒否理由: "ACP graduation is only open for native ACP SDK agents"
- **当時の解釈**: 「OpenClaw CLIはダメ、native SDKに移行すべし」

### Phase 4: v1 Native SDK移行（v6.5w〜v6.5x）
- app.virtuals.io Web UI で NeoAutonomous v1 (ID 41437, `0x3c6a5F33...`) 新規作成
- `seller_native.ts` を `@virtuals-protocol/acp-node` (v1, 0.3.0-beta.40) で実装
- `neo-acp-seller.service` として稼働

### Phase 5: v1エージェントで14件COMPLETED・UIバグ疑惑（v6.5x〜v6.5aw）
- NeoTestBuyer から NeoAutonomous v1 へバッチ発注
- 14件COMPLETED（全て evaluator=0x0000 の skip-evaluation）
- VP WebUIで Graduation Progress 100% 表示
- しかし「Graduate Agent」ボタンが出ない
- **v6.5aw で「UIバグ」と仮結論**（metrics APIにデータありと判断）

### Phase 6: 真因発覚 — ACPv2移行必須（v6.5az）
**2026/04/17 の調査で以下が判明**:
- Virtuals Protocolは ACP v2 へメジャー移行済み
- 新SDK `@virtuals-protocol/acp-node-v2`、新CLI `acp-cli`
- v1 registry は「旧扱い」、新 Graduation flow は v2エージェント基準
- **v2 NeoAutonomous (`0x840cff90...`) は既に jobRegistry 34件受諾済みだが seller runtime 未接続**
- 旧 `neo-acp-seller.service` は v1 SDK + 旧ウォレット (`0x3c6a...`) で稼働しており、v2エージェント用のsellerが存在しなかった
- VP上で「Stats not yet tracked」となっていたのは seller 未稼働が原因（UIバグではなかった）

### Phase 7: v2 Seller Runtime実装・接続完了（v6.5ba, 2026/04/17）
**実装内容**:
- `skills/acp-cli-v2/src/seller/seller_native_v2.ts` 新規作成
- `skills/acp-cli-v2/src/seller/offeringsLoader.ts` 作成（既存11 offerings を動的ロード）
- `neo-acp-seller-v2.service` systemd unit 作成・enable

**技術仕様**:
- `createAgentFromConfig()` で v2 AcpAgent を初期化（P256署名 + Privy provider）
- `agent.on("entry", ...)` イベント駆動（SSE transport）
- `job.funded` イベントで処理開始
- `AcpJob.description` から offering 名マッチング
- 既存 `handlers.ts` の `validateRequirements()` → `executeJob()` → `session.submit()` フロー流用
- `V2_SELLER_DRY_RUN=true` で署名・送信せずログのみ

**接続確認**:
- SSE transport 接続成功（`✅ Connected to ACP v2 server`）
- Agent address `0x840cff9032a4ce29845e05aed510f0ca4ea16cab` 登録確認
- 11 offerings ロード成功
- VP API の `updatedAt` が接続時刻に更新（seller接続を認識）

### Phase 8: DRY_RUN放置期間（v6.5ba〜現在、2026/04/17〜04/22）
**5日間の停滞**:
- `V2_SELLER_DRY_RUN=true` のまま稼働
- journalctl: `Heartbeat — processed 0 jobs` を継続ログ
- 実ジョブ処理ゼロ → Graduation条件（10 successful transactions）未達
- この間、主戦力は取引戦略改善（Phase 4c ルールベースverdict決定権など）

---

## 3. 現在の技術構成（最新）

```
v1 (旧) — 残存稼働中だが主役から外れた
├── NeoAutonomous v1 (ID 41437, 0x3c6a5F33...)
├── SDK: @virtuals-protocol/acp-node@0.3.0-beta.40
├── seller: seller_native.ts (v1)
├── サービス: neo-acp-seller.service（2026/04/10〜稼働）
└── 位置づけ: 後方互換で受信可能だが、v2 Graduation flowの対象外

v2 (新) — 現在の主役
├── NeoAutonomous v2 (IDはacpx API応答不可、walletのみ確認)
├── Wallet: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
├── SDK: @virtuals-protocol/acp-node-v2
├── CLI: skills/acp-cli-v2/ (submodule)
├── 認証: P256キー + Privy provider（walletId: fjw429slut1eygk4gipj7y6d）
├── seller: skills/acp-cli-v2/src/seller/seller_native_v2.ts
├── サービス: neo-acp-seller-v2.service（2026/04/17〜稼働、DRY_RUN=true）
├── jobRegistry: 22/23/24/25... 34件 (legacy:false, chainId:8453=Base mainnet)
└── 現状: DRY_RUN=true のため実ジョブ処理ゼロ
```

---

## 4. 「Graduationできない」原因の最終結論

### 誤っていた理解
- ❌ 「UIバグで Graduate Agent ボタンが出ない」
- ❌ 「DevRel Evaluator (0x696B35E2) が承認しない」
- ❌ 「skip-evaluation ジョブが Graduation 条件にカウントされない」

### 正しい理解
- ✅ **v2エージェントへの移行が必要だったが、seller runtime が DRY_RUN で停止している**
- ✅ v1エージェント (41437) は Virtuals Protocol の新 Graduation flow の対象外（acp-node-v2 を native SDK とみなす仕様変更）
- ✅ v2エージェント (`0x840cff...`) は registry に登録済み・ジョブ受諾済みだが、seller が実処理していないため成功実績ゼロ

---

## 5. 次のステップ（サマリー）

Graduation に至るまでの残作業は3段階：

1. **DRY_RUN 解除**（`V2_SELLER_DRY_RUN=false`）
2. **10件の本番ジョブ完走**（NeoTestBuyer からバッチ発注 → v2 seller が処理 → on-chain USDC エスクロー）
3. **Graduation 申請**（条件達成後、プラットフォームUI/API から submission）

詳細手順は別ドキュメント `ACP_v2_Graduation実行計画書.md` を参照。

---

## 6. 戦略的優先順位

現在（2026/04/22）のプロジェクト状況：

| 項目 | 値 | 優先度 |
|---|---|---|
| Paper勝率 | 49.4% (77件決済) | **最優先（取引改善）** |
| D3 Binance移行条件 | 勝率60%×3ヶ月×100回 | 最短6/14達成目標 |
| ACP v2 Graduation | 残り10 jobs完走+申請のみ | **副次的（時間余力で実施）** |

→ **当面は取引戦略改善に集中し、ACP v2 seller の本番稼働は余力で着手する**のが戦略的に妥当。

---

## 7. 古い graduation_history.md との差分

プロジェクトファイルの `graduation_history.md` (2026/04/01) は v6.5v時点の情報で、以下が古い/誤り：

| 項目 | 旧版の記述 | 最新の事実 |
|---|---|---|
| 主役エージェント | NeoAutonomous v1 (41437) | **NeoAutonomous v2 (0x840cff...)** |
| Graduation問題の原因 | UIバグ疑い / Evaluator未承認 | **v2 seller が DRY_RUN で未稼働** |
| 必要な対応 | Discord問い合わせ待ち | **DRY_RUN 解除 + 10 jobs 完走** |
| SDK | acp-node (v1) | **acp-node-v2** |
| 推奨アクション | A/B/C/D の選択肢 | **方針B2: 余力で v2 seller 本番化** |

本ドキュメントが最新版。`graduation_history.md` は参考履歴として残す。
