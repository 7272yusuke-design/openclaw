# GSD計画 v6.5bk 引き継ぎ白書

- 更新日時: 2026/05/05 03:50 JST
- セッション: v6.5bk (ACP v2 Graduation真因深掘り + SDK 0.1.2 アップグレード)
- 自己採点: 6/10

---

## このセッションの主題

**ACP v2 Graduation の Stats not yet tracked 問題の真因を深掘り**。仮説を1つずつ潰していき、SDK 0.0.4 → 0.1.2 アップグレード、resources URL 変更まで実施したが、**lastActiveAt は依然 2999-12-31 のまま**で根本解決には至らず。次回への土台は固められた。

取引ロジック（neo-radar / TrinityCouncil 等）には一切手を入れていない。

---

## 本セッションで達成したこと

### 1. CLI 認証完了 (`acp configure`)
- `acp-cli-v2` を Virtuals Protocol API に対して認証
- これにより `agent whoami / list / browse` などが使えるように
- トークンは OS keychain に保存（macOS Keychain / Linux Secret Service 等）

### 2. 仮説の段階的検証で真因を絞り込み

| 検証した仮説 | 結果 |
|---|---|
| Restricted signer が原因 | ❌ 棄却（buyer も Restricted で更新されている） |
| Migration 未完了が原因 | ❌ 棄却（CLI API で COMPLETED 確認） |
| `acpV2AgentId: 41437` (v1 ID 流用) が原因 | ⚠️ 状況証拠あり（次回検証推奨） |
| SSE transport の heartbeat 欠如 | ❌ 棄却（SocketTransport にしても効果なし、0.1.2では削除済） |
| SDK が古すぎる | ❌ 部分棄却（0.1.2 でも heartbeat / lastActiveAt 更新コードなし） |
| resources URL がダミー（example.com） | ⚠️ localhost に変更したが即時効果なし（要時間経過観察） |

### 3. SDK 0.0.4 → 0.1.2 アップグレード完了

- `@virtuals-protocol/acp-node-v2` 0.0.4 → 0.1.2
- `socketTransport` は 0.1.x で削除されていた（`SseTransport` のみ残存）
- `agentFactory.ts` は SseTransport を維持（修正後の状態 = 元の状態）
- サービス再起動・正常稼働確認済

### 4. resources URL を localhost:8099 に修正

旧 Neo (`0x75e6...`, `lastActiveAt: 2026-04-11`) と同条件にするため：
- `https://neo-agent.example.com/...` (ダミー) → `http://localhost:8099/...` (旧Neoと同形式)
- 3件の resources すべて API 経由で更新成功
- ただし `lastActiveAt` は即時には更新されず（要観察）

### 5. エージェント全体の正確な棚卸し

| ID (UUID) | name | wallet | lastActiveAt | acpV2AgentId | 備考 |
|---|---|---|---|---|---|
| 019d7b3f-... | NeoAutonomous | 0x840cff... | **2999-12-31** | **41437 (v1ID流用)** | 主役・問題児 |
| 019d76d4-... | neo-test-buyer-v2 | 0x11ab498c... | 2026-05-05 02:37 | N/A | 正常稼働 |
| 019d7659-... | Neo (旧) | 0x75e65397... | 2026-04-11 | 19768 | レガシー |
| 019d7bb4-... | neo-test-buyer | 0x131d3ff8... | null | 41409 | isHidden=true |

### 6. legacy agents の migration 状態確認

- ID 19768 (旧Neo): COMPLETED
- ID 41409 (neo-test-buyer): IN_PROGRESS (放置中)
- **ID 41437 (NeoAutonomous): COMPLETED**
- ID 41440 (NeoTestBuyer): PENDING

NeoAutonomous の migration はサーバー側では COMPLETED だが、`acpV2AgentId: 41437` が v1 ID のまま流用されている点が違和感あり。他のエージェントは v2 用の小さな新規 ID（2043, 12392, 21257）を持っている。

---

## 残課題（最優先）

### 真因として最有力の仮説

**「v2 用の新しい acpV2AgentId が割り当てられていないため、v2 registry に正規登録されていない」**

根拠:
- 他のエージェント（Argonaut AI など）は acpV2AgentId が小さい数字（2043, 12392, 21257）
- NeoAutonomous は 41437 で v1 ID と同一
- browse 結果に NeoAutonomous が出てこない（discoverable でない可能性）
- migration COMPLETED と表示されているが実態は途中段階の可能性

### 次セッションで試すべきこと

1. **resources URL 変更の時間経過観察**（数時間後に lastActiveAt が更新されるか）
2. **chains の更新**: `acpV2AgentId` を null にして再登録できるか確認（API があれば）
3. **agent update での再登録試行**: `acp agent update` で何かが triggered されるか
4. **VP UI で agent を一旦 hidden にして再公開**（再登録パターンの強制）
5. **neo-test-buyer (41409) の IN_PROGRESS を完了させてみる**: パターン学習用
6. **DevRel ACP Agents Evaluator 経由のテスト発注**: 集計に乗る公式パターンを試す

---

## 本セッションの変更ファイル

### 新規作成
- なし（試行スクリプトはすべて削除）

### バックアップ (`.archive_deadcode_v65p/`)
- `agentFactory.ts.bak_v65bj_20260505`
- `package.json.bak_v65bj_20260505`
- `package-lock.json.bak_v65bj_20260505`

### システム変更
- `skills/acp-cli-v2/package.json`: `^0.0.4` → `^0.1.1` (実体は 0.1.2)
- `skills/acp-cli-v2/node_modules/`: SDK 全体を更新
- `skills/acp-cli-v2/src/lib/agentFactory.ts`: 試行的に SocketTransport に変更後 SseTransport に戻した（実質変更なし）
- VP API 経由で NeoAutonomous の resources URL を `localhost:8099/...` に変更
- CLI 認証トークン取得済（OS keychain 内）

### 取引ロジック関連
- **なし**（claude.aiでの戦略セッションのため、本体コードには一切触れていない）

---

## ロールバック手順

### SDK を 0.0.4 に戻す場合
```bash
cd /docker/openclaw-taan/data/.openclaw/workspace/skills/acp-cli-v2
cp .archive_deadcode_v65p/package.json.bak_v65bj_20260505 package.json
cp .archive_deadcode_v65p/package-lock.json.bak_v65bj_20260505 package-lock.json
npm install
systemctl restart neo-acp-seller-v2.service
```

### resources URL を example.com に戻す場合
（CLI 経由で `resource update` 対話メニューで再度変更）

---

## 自己採点詳細 (6/10)

### 良かった点
- CLI 認証を完了させ、Virtuals Protocol API を直接叩ける状態を確立
- 4つの仮説を順に棄却し、真因の輪郭を絞り込んだ
- SDK アップグレードの過程で重要発見（SocketTransport 削除）を得た
- resources URL を旧 Neo と同条件に揃えた（次回の比較検証材料）
- 取引ロジックには一切触れていない（1ファイル1変更原則維持）
- バックアップを毎回 `.archive_deadcode_v65p/` に格納

### 反省点
- **真因にまだ到達していない**: lastActiveAt 更新メカニズムの本質を特定できていない
- 仮説検証に時間を消費しすぎた（特に SocketTransport 切替えは効果なし）
- VP UI の Sandbox Visualizer を直接見る試行を後回しにした
- DevRel Evaluator 経由のテスト発注（前白書の優先案）を試していない

### 次回への申し送り

最優先順:
1. **resources URL 変更の効果確認**（次セッション開始時に lastActiveAt をチェック）
2. **DevRel ACP Agents Evaluator 経由のテスト発注**（前回の方針通り、これが最も効果ある可能性）
3. **「acpV2AgentId が v1 ID 流用」仮説の検証**（VP UI で再登録できるか）

その他状態:
- v2 seller (`neo-acp-seller-v2.service`): DRY_RUN=false, SDK 0.1.2, SseTransport で稼働中
- v1 seller (`neo-acp-seller.service`): 停止済 (前セッションから)
- buyer USDC: 約 $1.86 (0x11ab498c...)
- seller USDC: 約 $2.26 (0x840cff...)

