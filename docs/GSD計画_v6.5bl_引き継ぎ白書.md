# GSD計画 v6.5bl 引き継ぎ白書

- 更新日時: 2026/05/05 14:00 JST
- セッション: v6.5bl (ACP v2 Graduation 真因の最終切り分け + 公式ドキュメント精読)
- 自己採点: 7/10

---

## このセッションの主題

ACP v2 Graduation 真因の最終切り分け。実ジョブ1件を完走させて lastActiveAt 更新メカニズムを直接検証し、合わせて公式ドキュメントを精読することで、いくつかの仮説を最終的に棄却した。完全解決には至らなかったが、「我々の手で解決できる範囲はほぼ尽きた」ことが確定し、最後の自前検証として Sandbox Butler 経由のテストと、それでもダメなら VP 公式サポート問い合わせ、というアクションが明確になった。

取引ロジックには一切手を入れていない。

---

## 本セッションで達成したこと

### 1. 実ジョブ完走（Job #6407）
- buyer (neo-test-buyer-v2) から NeoAutonomous へ vp_sentiment_scan 発注
- create-job → fund (0.01 USDC) → seller execute → submit → complete の全フロー成功
- オンチェーンで完全に完了確認済
- コスト: 0.01 USDC + ガス約 0.20 USD = 合計約 0.21 USD

### 2. 仮説の決定的棄却

| 仮説 | 結果 | 根拠 |
|---|---|---|
| Tokenization が graduation に必要 | 棄却 | 公式ドキュメントで明確に不要と記載 |
| acpV2AgentId が v1 ID 流用なのが原因 | 棄却 | 旧 Neo (19768) も v1 ID 流用だが lastActiveAt は更新されている |
| Wallet whitelist が必要 | 棄却 | OpenClaw setup では whitelist 不要と公式に明記 |
| resources URL が dummy だから | 棄却 | localhost に変更しても効果なし |
| ジョブを処理すれば lastActiveAt が更新される | 新規棄却 | 実ジョブ完走後も seller 側 lastActiveAt は 2999-12-31 のまま |

### 3. 確定した事実

- 技術スタック側はすべて正常稼働（v2 seller, SDK 0.1.2, SseTransport, DRY_RUN=false, SSE 接続）
- オンチェーン処理は完全に動作（Job #6407 が証拠）
- buyer 側 lastActiveAt は正しく更新される (02:37 → 04:18)
- seller (NeoAutonomous) 側の lastActiveAt と Stats だけが追跡されない
- Sandbox visualizer で "Stats not yet tracked" 表示
- Revenue: 0 USD (実際にはオンチェーンで 0.01 USD 受け取り済み)
- Overview ページの Runtime フィールド: 空欄

### 4. 公式ドキュメント精読で判明したこと

- Graduation 条件: 10 successful sandbox transactions（うち 3 件は自前 test buyer から連続成功）+ 手動審査
- 公式メトリック名: SUCCESSFUL_JOB_COUNT
- 古い SDK の provider は OFFLINE 検出される（0.1.2 は OK）
- Trading agent vs Non-Trading agent の分類（DevRel Evaluator は Non-Trading 専用）
- Customize Agent には 3つのテスト方法が公式記載:
  1. ACP SDK 直接（我々の現状）
  2. ACP-GAME Plugin
  3. Sandbox Butler ← 未検証

### 5. ユーザー寄与の重要発見
- ユーザーが UI 上で Tokenize ボタンと "Required before deploying an instance" 文言を発見
- ユーザーが ACP セクションで黄色警告（missing description）を発見
- ユーザーから「公式ドキュメントを先に当たれ」との指摘 → 仮説検証の方向性を正しい方向に修正
- ユーザーが Customize Agent ドキュメントを発見 → Sandbox Butler という未検証ルートが浮上

---

## 残課題（最優先）

### 真因の最終候補

1. Sandbox Butler 経由でないと Stats が追跡されない可能性（要検証・コスト小）
   - 公式の3つのテスト方法のうち、我々は ACP SDK 直接のみ試行
   - Sandbox Butler が未検証 → これが「公式経路」として stats 集計の入り口かもしれない

2. VP プラットフォーム側の集計バグ or 反映遅延（1 が外れた場合の最有力）

3. Self-funded test job が集計対象外（同じ user が buyer/seller を所有しているため除外されている可能性）

### 次セッションの Action Items

優先順位:

1. Sandbox Butler 経由で1件テスト（最後の自前検証、コスト最小）
   - https://app.virtuals.io の Butler チャット
   - Sandbox mode に切替
   - NeoAutonomous の vp_sentiment_scan を発注
   - Stats が更新されたら真因確定 → 残り9件をこの経路で実施可能
   - 更新されなければ完全に platform 側問題 → サポート問い合わせ

2. 更新されなかった場合: VP Discord / GitHub Issues に問い合わせ
   - GitHub Issues を最優先（応答率高）: https://github.com/Virtual-Protocol/openclaw-acp/issues
   - 投稿時刻: JST 10〜19時（シンガポール営業時間）
   - 24時間後に1回 bump
   - テンプレート: 本白書末尾参照

3. 取引改善（D3 Binance 移行）に集中 — 元々の主目的
   - Paper 勝率 49.4% → 60% を目指す
   - 100 件決済 + 3ヶ月継続が D3 移行条件
   - これが本来の主戦線

---

## 本セッションの変更ファイル

### 新規作成・削除
- 新規: 5つの調査用 TS スクリプト（その後すべて archive へ移動）
  - check_lastactive.ts
  - compare_all_neo.ts
  - check_funds.ts
  - check_offering_schema.ts
  - full_check.ts
- アーカイブ: .archive_deadcode_v65p/scripts_v65bl/ に全て格納

### システム変更
- なし（v2 seller は v6.5bk から変更なし）
- アクティブエージェントを buyer → seller に戻して終了

### コスト
- USDC 消費: 0.01 USDC (job fund) — 実質 seller 側に戻ったため net 0 だが seller 残高に移動
- ガス消費: 約 0.20 USD (4 トランザクション)
- 実残高変化:
  - buyer (neo-test-buyer-v2): 1.86 USDC → 約 1.65 USDC（推定）
  - seller (NeoAutonomous): 2.26 USDC → 2.27 USDC (+0.01)
- Total net loss: 約 0.20 USD（ガスのみ）

### 取引ロジック関連
- なし（claude.ai 戦略セッションのため、本体コードには一切触れていない）

---

## ロールバック手順

### Job 6407 完了状態を取り消したい場合
- 不可。オンチェーンでファイナライズ済みのため。
- ただし悪影響は皆無（escrow が seller に正しく releases されただけ）。

### アクティブエージェントを buyer に戻したい場合

実行コマンド:
- cd /docker/openclaw-taan/data/.openclaw/workspace/skills/acp-cli-v2
- npx tsx bin/acp.ts agent use --agent-id 019d76d4-4e69-76c4-99d7-b90c64988af3

---

## 自己採点詳細 (7/10)

### 良かった点
- 1件の実ジョブ完走でジョブ処理パイプラインが完全に動作することを実証
- 4つの仮説を決定的に棄却できた（次回以降に再検証する必要なし）
- 公式ドキュメントを精読し、Graduation 条件と関連メカニズムを正確に把握
- 実費は約 0.20 USD（ガスのみ）。情報リターンは大きい
- 取引ロジックには一切触れていない（1ファイル1変更原則維持）
- ユーザーからの指摘を受けて方針修正できた（ドキュメントファースト）
- ユーザーが Customize Agent を発見してくれて、Sandbox Butler という未検証ルートが浮上

### 反省点
- セッション序盤、ドキュメントを当たらずに CLI ソース読みから始めた遠回り
- Tokenize 仮説を一時的に有力候補にしてしまった（直前で軌道修正）
- 「真因が我々の手の届かない場所にある可能性」をもっと早い段階で結論付けるべきだった
- Customize Agent の 3つのテスト方法（特に Sandbox Butler）にもっと早く気付くべきだった

### 次回への申し送り

最優先タスク（次回最初にやること）:
1. Sandbox Butler で1件テスト発注（コスト最小、診断価値大）
2. 結果が出たら判断:
   - 更新あり → 残り9件を Sandbox Butler 経由で実施 → Graduation
   - 更新なし → VP サポート問い合わせ + 取引改善に戻る

現在状態:
- v2 seller (neo-acp-seller-v2.service): DRY_RUN=false, SDK 0.1.2, SseTransport で稼働中、Job 6407 処理実績あり
- v1 seller (neo-acp-seller.service): 停止済（前セッションから）
- buyer USDC: 約 1.65 USDC (0x11ab498c...)
- seller USDC: 2.27 USDC (0x840cff...)
- アクティブ CLI agent: NeoAutonomous (seller, 0x840cff...)
- Job 6407: completed (vp_sentiment_scan, 0.01 USDC)

---

## VP 公式サポート問い合わせテンプレート

### 投稿先（優先度順）
1. GitHub Issues (最も応答率高い): https://github.com/Virtual-Protocol/openclaw-acp/issues
2. Discord builders / dev-support チャンネル
3. Telegram builders グループ

### 投稿時刻
- シンガポール営業時間（JST 10〜19時）に投稿、24時間後に1回 bump

### 簡潔版（英語、Sandbox Butler テスト後に更新版を使う想定）

Hi team — quick question. My v2 seller (NeoAutonomous, 0x840cff9032a4ce29845e05aed510f0ca4ea16cab, agentId 019d7b3f-c2d8-7a52-839c-9629f4abb5dc) successfully completed Job #6407 on-chain (vp_sentiment_scan, full lifecycle: created -> budget -> funded -> submitted -> completed). However, the agent's lastActiveAt is still stuck at 2999-12-31 and the Sandbox visualizer says "Stats not yet tracked". Buyer side updates fine.

[If Sandbox Butler test also did not update stats, add the following sentence:]
Also tried initiating the same job via Sandbox Butler — same result, stats still not tracked.

Using acp-node-v2 0.1.2, SseTransport, DRY_RUN=false. Migration COMPLETED. acpV2AgentId is 41437 (= legacy v1 ID, unlike other agents which have small fresh IDs).

Is there a registration step I am missing, or is this a known platform-side issue? Happy to share logs.

### 詳細版・日本語版は claude.ai セッション履歴を参照
