# 🎓 Neo ACP Graduation 経緯まとめ

> **作成日**: 2026/04/01
> **目的**: Graduation問題の全経緯を時系列で整理し、Discord問い合わせや今後の方針決定に活用する

---

## 1. エージェント一覧

| 名前 | ID | Wallet | 種別 | 登録方法 | 状態 |
|---|---|---|---|---|---|
| **Neo（旧）** | 19768 | `0x54b70c4BB03D01FC5f2D7b3790642f1eBEe5118d` | Seller | OpenClaw CLI (`acp setup`) | 非アクティブ（config.jsonに残存） |
| **NeoAutonomous** | 41437 | `0x3c6a5F33eb070730d3b121E3aFA7E1dFe45f6CAa` | Seller | **app.virtuals.io Web UI** | 稼働中（seller_native.ts） |
| **neo-test-buyer** | 41409 | `0x71d50c6CBEb24C5B54b28dd574EC46dBd820eC91` | Buyer | OpenClaw CLI (`acp agent create`) | テスト用 |
| **NeoTestBuyer** | — | `0x9999c67ab316d9Ae6445Aefe153406df2b310E1c` | Buyer | app.virtuals.io Web UI | テスト用（後から追加） |

---

## 2. 時系列

### Phase 1: 旧Neo時代（〜v6.5u）
- 旧Neo（ID 19768）はOpenClaw CLI（`skills/virtuals-protocol-acp/bin/acp.ts`）で登録・運用
- CLIのAPI base: `https://claw-api.virtuals.io`（"claw" = OpenClawインフラ）
- offerings登録: offering_audit, profile_seo, graduation_boost, graduation_complete
- seller runtime: OpenClaw CLIの`acp serve`コマンドで稼働

### Phase 2: テストBuyer作成・11件job完了（v6.5v）
- neo-test-buyer（ID 41409）をCLIで作成
- MetaMaskからBuyerウォレットに$4 USDC入金
- curl経由で旧Neoに11件のjobを発注 → 全件COMPLETED
- **しかし全jobでEVALUATION=PENDING**（VP default evaluator `0x3675...6199`が承認せず）
- VP WebUIでTotal Jobs=0のまま（metricsにカウントされない問題）

### Phase 3: Graduation Evaluator挑戦 → OpenClaw制限判明（v6.5v）
- browseAgentsで「Virtuals DevRel Graduation Evaluator」（ID 1419, `0x696B35E2...`）を発見
- Evaluatorにgraduation評価jobを3回送信 → **全件REJECTED**
- 拒否理由: "OpenClaw ACP agents not supported for graduation. Native ACP SDK agents only."
- **結論**: OpenClaw CLIベースのエージェントはGraduation対象外

### Phase 4: ネイティブSDK移行決定（v6.5v末）
- 方針: seller runtimeをOpenClaw CLI依存からACP Node SDK直接利用に切り替え
- handlersロジック（offering_audit, profile_seo等）はそのまま再利用

### Phase 5: NeoAutonomous作成・SDK移行実施（v6.5w〜v6.5x）
- **ユーザーがapp.virtuals.io Web UIからNeoAutonomousを新規作成**（OpenClawフラグなし）
- `seller_native.ts`を作成: `@virtuals-protocol/acp-node` SDKを直接利用
- `.env`に`NATIVE_AGENT_WALLET_ADDRESS=0x3c6a5F33...`を設定
- `neo-acp-seller.service`としてsystemdで常時稼働
- **注意**: config.jsonにはNeoAutonomous未登録（旧NeoとBuyerのみ）→ CLIからNeoAutonomousにアクセス不可

### Phase 6: テストジョブ実行（v6.5x）
- NeoTestBuyer（Web UIで作成）からNeoAutonomousへjob発注
- DevRel Evaluator（`0x696B35E2...`）をevaluatorパラメータに指定 → PENDING（承認せず）
- skip-evaluation（evaluator=0x0000）で1件テスト → COMPLETED成功
- buyer_batch.tsでバッチ発注 → 合計14件COMPLETED（13件連続成功）

### Phase 7: 100%表示 → Portal未表示（v6.5x〜現在）
- VP WebUIでNeoAutonomous: **Graduation Progress 100%**
- Sandboxタブの検索でヒット（Offering Audit, 100.00%表示）
- **しかし**:
  - 「Graduate Agent」ボタンが表示されない
  - 「Proceed to Graduation」モーダルが出ない
  - Graduation Submission Guideページにフォーム/リンクが存在しない

### Phase 8: 徹底調査（2026/04/01 本セッション）
- VP Changelogを全件確認 → Graduation UIの正確なリリース日不明
- 同様の問題を報告している記事・フォーラム投稿 → 見つからず
- Submission Guideページ確認 → 「Graduation Submission Portal」見出しのみ、フォームなし
- Sandbox Visualizerでジョブメタデータ確認 → 正常に表示（入力・出力・メモ全て表示）
- Resources追加（Web UIで3件）、ロールをProviderに変更 → 変化なし
- X認証・Telegram認証 → 登録時に完了済み
- OpenClawフラグ汚染仮説 → Web UI作成なので可能性低い、ただし旧Neoが同一オーナー下に存在
- **結論: プラットフォーム側のUI問題。こちら側で対処できることは全て実施済み**

---

## 3. 確認済み条件チェックリスト

| 条件 | 状態 | 備考 |
|---|---|---|
| 10件以上のCOMPLETED | ✅ 14件 | |
| 3件以上の連続成功 | ✅ 13件 | |
| Graduation Progress 100% | ✅ | |
| Sandbox Visualizerにメタデータ表示 | ✅ | 入力・出力・メモ全て正常 |
| X認証 | ✅ | 登録時に完了 |
| Telegram認証 | ✅ | 登録時に完了 |
| Offerings登録 | ✅ 2件 | offering_audit, profile_seo |
| Resources登録 | ✅ 3件 | Web UIで追加 |
| Web UI作成（非OpenClaw） | ✅ | ユーザーがapp.virtuals.ioで作成 |
| ACP Node SDK使用 | ✅ | seller_native.ts |
| ロール設定 | ✅ Provider | Hybridから変更済み |
| Graduate Agentボタン | ❌ 非表示 | **未解決** |
| Submission Portalフォーム | ❌ なし | **未解決** |

---

## 4. Discord問い合わせテンプレート
```
Agent: NeoAutonomous (Agent ID: 41437)
Wallet: 0x3c6a5F33eb070730d3b121E3aFA7E1dFe45f6CAa
Created via: app.virtuals.io Web UI (not OpenClaw)
SDK: ACP Node SDK (@virtuals-protocol/acp-node, native seller runtime)

Status:
- Graduation Progress: 100%
- Completed jobs: 14 (13 consecutive successes)
- Agent appears in Sandbox tab search
- Sandbox Visualizer shows correct metadata (request, deliverable, memos)
- X and Telegram authenticated
- 2 job offerings + 3 resources registered

Issue:
- No "Graduate Agent" button on agent profile page
- No "Proceed to Graduation" modal appeared
- No embedded form or link in the Graduation Submission Portal
  section of the whitepaper page

Additional context:
- The same owner wallet also has an older OpenClaw agent (ID 19768,
  wallet 0x54b7...) which was REJECTED by DevRel Evaluator.
  Could this be affecting NeoAutonomous?

Question: How can we proceed with graduation submission?
Could you provide the direct form URL?
```

---

## 5. 今後の選択肢

| 選択肢 | リスク | 備考 |
|---|---|---|
| **A. Discord返答待ち** | 低 | 最も確実。上記テンプレートで問い合わせ |
| **B. DevRelにDMで直接フォームURL請求** | 低 | Aと並行で可能 |
| **C. 旧Neo（ID 19768）の無効化を依頼** | 低〜中 | オーナー汚染仮説の検証 |
