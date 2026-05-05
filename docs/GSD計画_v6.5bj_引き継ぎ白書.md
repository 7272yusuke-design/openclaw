# GSD計画 v6.5bj 引き継ぎ白書

- 更新日時: 2026/05/05 12:30 JST
- セッション: v6.5bj (ACP v2 Phase 2.3 完走 + Graduation真因判明 + エージェント整理開始)
- 自己採点: 7/10

---

## このセッションの主題

**ACP v2 Graduation Phase 2.3 (10件ジョブ完走) を実行。**11件すべて Job completed by evaluator まで成功させたが、**VP プラットフォームの集計には1件もカウントされていない**ことが判明。原因は self_evaluation (buyer = evaluator) で発注したジョブが VP 側の Successful Transactions メトリクスに反映されない仕様の可能性が高い。

取引ロジック (neo-radar / TrinityCouncil 等) には一切手を入れていない。

---

## 本セッションで達成したこと

### 1. ACP v2 ジョブ完走 (11件)

| Job ID | 完走時刻 | 経路 |
|---|---|---|
| 6333 | 前セッション | buyer_test_v2 |
| 6340 | 02:15:11 | buyer_test_v2 (救出) |
| 6343 | 02:18:41 | buyer_batch (救出) |
| 6346 | 02:19:05 | buyer_batch (新規) |
| 6349 | 02:24:47 | buyer_batch (新規) |
| 6353 | 02:29:43 | buyer_batch (新規) |
| 6354 | 02:31:53 | Iter 1 (test_v2 5回ループ) |
| 6355 | 02:32:53 | Iter 2 |
| 6357 | 02:33:53 | Iter 3 |
| 6359 | 02:34:51 | Iter 4 |
| 6360 | 02:35:57 | Iter 5 |

オンチェーンとして全件成功 (Base mainnet)。seller-v2 も全件 `Job completed by evaluator` を記録。

### 2. Graduation問題の真因判明 (重要)

VP UI のエージェントプロフィール (`app.virtuals.io/acp/agents/<id>`) で確認:
- **Stats not yet tracked** / **No transactions recorded** 表示
- 11件オンチェーン成立しているのに、VP バックエンドが0件と認識
- これは前セッションでも疑われていた「skip-evaluation/self_evaluation はカウントされない」仮説の傍証

ドキュメント上 (whitepaper.virtuals.io) では self_evaluation 例も推奨されているが、**Graduation 集計には別ルート (DevRel ACP Agents Evaluator 経由など) が必要な可能性**が高い。

### 3. v1 seller サービス停止

`neo-acp-seller.service` (v1 seller, ID 41437, `0x3c6a5F33...`) を停止・disable。
- v1 SDK は今後使わない方針 (v2 SDK が主役)
- v2 seller (`neo-acp-seller-v2.service`) はそのまま稼働継続

### 4. 全エージェント・ウォレットの棚卸し

10ウォレット存在することが判明 (詳細は次セクション)。

### 5. バッチ発注スクリプト作成 (副産物)

`skills/acp-cli-v2-buyer/buyer_batch_v2.ts` を新規作成。途中バグあり (status巻き戻り問題) で完成途中だが、ループ管理を `Map<jobId, JobState>` で行う設計は健全。最終的には `buyer_test_v2.ts` を5回シェルループする方法で目的達成。

---

## 全エージェント・ウォレット一覧 (2026/05/05時点)

### v2 SDK 側 (skills/acp-cli-v2/config.json)

| Wallet | Agent ID | 用途 | USDC |
|---|---|---|---|
| 0x75e6...300a | 019d7659-... | ECONOMYOS (用途不明) | $0.10 |
| 0x11ab...ee82 | 019d76d4-... | neo-test-buyer-v2 | **$1.86** |
| **0x840c...16cab** | 019d7b3f-... | **NeoAutonomous v2 (主役)** | **$2.26** |
| 0x131d...5912 | 019d7bb4-... | publicKey空 (未完成) | $0 |

### v1 SDK 側 (skills/virtuals-protocol-acp/config.json + .env + skills/openclaw-acp-v2/config.json)

| Wallet | 名前 | USDC |
|---|---|---|
| 0x54b7...118d | 旧Neo (ID 19768) | $3.20 |
| 0x71d5...eC91 | neo-test-buyer (ID 41409) | $0 |
| 0x3c6a...6CAa | NeoAutonomous v1 (ID 41437) | $3.36 |
| 0x9999...0E1c | NeoTestBuyer | $3.50 |
| 0x80f9...ad18 | WHITELISTED (認証用) | $0 |
| 0x3E3E...515b | BUYER WHITELISTED (認証用) | $0 |

**全資金合計: $17.28**
- v1 側に $10.06 滞留 (回収候補)
- v2 側に $4.22

---

## 残課題 (次セッション以降)

### 最優先: Graduation問題の根本解決
1. **Discord で公式に問い合わせ**
   - 「11件 self_evaluation 完走したが Stats not yet tracked のまま」
   - エビデンス: seller-v2 ログ + Basescan の取引履歴
2. **DevRel ACP Agents Evaluator 経由でのテスト**
   - VP UI に「Hire to Test」ボタンあり
   - 公式 Evaluator が外部評価することで集計対象になる可能性

### 中優先: 資金回収・整理
1. v1 側の $10.06 を v2 主役 ($0x840c...) またはメインウォレットへ集約
2. 不要ウォレットの最終確認・廃止判断
3. ECONOMYOS の正体確認 (VP UI で履歴を見れば判明するかも)

### 低優先: コード整理
1. `buyer_batch_v2.ts` の status巻き戻りバグ修正 (完成すれば便利)
2. v1 SDK 関連コードの archive 化
3. `skills/openclaw-acp-v2/` の archive 化

### 並行課題
- D3 Binance移行準備 (Paper勝率改善)
- 取引戦略の継続改善

---

## 戦略的優先順位の更新

| 項目 | v6.5bi時点 | v6.5bj時点 |
|---|---|---|
| Paper勝率改善 | 引き続き重要 | 引き続き重要 |
| VP Graduation優先度 | 最高 (バッチ完走で達成見込み) | **保留** (Discord問い合わせ待ち) |
| D3 Binance移行 | 引き続き重要 | 引き続き重要 |
| エージェント整理 | - | **新規追加** (v1停止済、資金回収は次回) |

---

## 本セッションの変更ファイル

### 新規作成
- `skills/acp-cli-v2-buyer/buyer_batch_v2.ts` (途中バグあり、参考程度)

### バックアップ (`.archive_deadcode_v65p/`)
- `buyer_test_v2.ts.ref_20260505`
- `buyer_batch_v2.ts.bak_before_fix_20260505_0216`
- `buyer_batch_v2.ts.bak_v2_20260505_0223`

### システム変更
- `neo-acp-seller.service` (v1 seller): stop + disable

### 取引ロジック関連
- **なし** (claude.aiでの戦略セッションのため、本体コードには一切触れていない)

---

## ロールバック手順

### v1 seller を再起動したい場合
```bash
systemctl enable neo-acp-seller.service
systemctl start neo-acp-seller.service
```

### v2 seller を DRY_RUN に戻したい場合 (前セッションの手順)
```bash
sed -i 's/^Environment=V2_SELLER_DRY_RUN=false$/Environment=V2_SELLER_DRY_RUN=true/' \
    /etc/systemd/system/neo-acp-seller-v2.service
systemctl daemon-reload
systemctl restart neo-acp-seller-v2.service
```

---

## 自己採点詳細 (7/10)

### 良かった点
- Phase 2.3 のジョブ完走を達成 (オンチェーン的には100%成功)
- VP UI の表示を粘り強く調査して真因 (バックエンド集計に乗らない) を特定
- 公式ドキュメントを読んで仕様を確認 (Sandbox Visualizer / self_evaluation の存在)
- 全ウォレット・エージェントの棚卸しを完了 (10ウォレット = $17.28 把握)
- v1 seller を停止して構成をシンプル化
- 取引ロジックには一切触れていない (1ファイル1変更原則維持)
- バックアップを毎回 `.archive_deadcode_v65p/` に格納

### 反省点
- **計画書 (ACP_v2_Graduation実行計画書.md) の前提自体が崩れた**: Phase 2.3 達成 = Graduation条件達成と書かれていたが、実際は VP 側で集計されない問題があった。前セッションでドキュメントを十分読まずに計画書を作ったツケ
- バッチスクリプトの status 管理バグに時間を消費 (約1時間)
  - 修正版もまだ完成していない
- VP UI の Sandbox Visualizer を最初から見るべきだった
- **真の Graduation 達成にはまだ進んでいない**: 11件完走したが集計0件

### 次回への申し送り
- **次セッション最初に Discord で問い合わせる** (DM テンプレートを用意してから着手推奨)
- v2 seller は DRY_RUN=false の本番モードで稼働継続中。不意のジョブ着信に注意
- v1 seller は停止済 (再起動が必要なら手動で)
- 資金回収は時間に余裕があるときに丁寧に実行
- ECONOMYOS の正体は時間あるときにVP UI で確認する価値あり
