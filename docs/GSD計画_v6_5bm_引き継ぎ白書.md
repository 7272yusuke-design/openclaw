# GSD計画 v6.5bm 引き継ぎ白書

- 更新日時: 2026/05/05 15:00 JST
- セッション: v6.5bm (Sandbox Butler 検証 + Withdraw 異常検出 + GitHub Issue 投稿)
- 自己採点: 8/10

---

## このセッションの主題

v6.5bl で残った最後の自前検証ルート「Sandbox Butler 経由のジョブ発注」を実施。あわせて副次的に発見した「Withdraw 機能が1ヶ月放置で完了していない」異常もエビデンスとして整理し、3症状をまとめて Virtuals Protocol 公式 GitHub Issue として投稿した。

ACP 関連は「VP側調査待ち」状態に確定。これで本来の主戦線である取引改善(D3 Binance移行)に100%集中できる体制になった。

取引ロジックには一切手を入れていない。コード変更ゼロセッション。

---

## 本セッションで達成したこと

### 1. Sandbox Butler ルートの検証 → 棄却

**実施内容**:
- app.virtuals.io の Butler 画面で NeoAutonomous (`0x840cff...`) を発注しようと試行
- Butler は「該当エージェントが ACP マーケットプレイスに見つからない」と回答
- Butler に Sandbox/Production の切替スイッチは存在せず、常に公開エージェント全体を検索している

**判明した事実**:
- NeoAutonomous はオンチェーンでは登録済み(Job #6407 で実証)だが、**ACP マーケットプレイスのインデックスに登録されていない**
- これは Stats not yet tracked / lastActiveAt 凍結と同根の症状

**結論**: Sandbox Butler ルートでも自前検証は不可能。我々の手で解決できる範囲は完全に終了。

### 2. Withdraw 機能の異常を発見(副次的だが重要)

**契機**: ACP 関連が詰まったので、各エージェントウォレットの USDC を MetaMask に戻そうとした

**判明した事実**:
- ECONOMYOS (`0x75e65...`) から $0.10 を `0x8824ADF8...` (VP login wallet) 宛に1ヶ月前に Withdraw 操作済み
- しかし1ヶ月経過後の現在も:
  - 送金元残高: $0.10 → **$0.099** ($0.001だけ減少)
  - 送金先残高: 変化なし
  - VP ポートフォリオ表示: $0(両方とも)
  - Basescan 履歴に該当 tx なし
- 1ヶ月放置でも完了せず、ガス代相当だけ消費されて凍結している状態

**判断**: 残り2ウォレット($1.85 + $2.27)の Withdraw 試行は**絶対禁止**(同じく$0.001だけ消費して凍結する可能性)

### 3. ウォレット構造の確定

`acp-cli-v2/config.json` の解析結果:
- 全エージェントウォレットは Privy 管理(P256キー + walletId)
- `privateKey` フィールドは存在しない = サーバー側に秘密鍵なし
- 通常の web3 スクリプトでは送金不可能
- VP/Privy の WebUI または API 経由でのみ操作可能
- ETH ガス残高ゼロでもジョブが動く理由 = Virtuals 側がガスをスポンサー

### 4. GitHub Issue 投稿(Issue #82)

**URL**: https://github.com/Virtual-Protocol/openclaw-acp/issues/82
**タイトル**: Multiple functions broken on a single VP account: ACP graduation stats, Butler search, and Withdraw all stalled
**投稿者**: 7272yusuke-design
**ステータス**: Open

**含めた内容**:
- 環境情報(login wallet, 3エージェント, SDK, transport, network)
- 症状1: ACP Graduation stats 未追跡(Job #6407 完走済みなのに)
- 症状2: Sandbox Butler が自エージェントを検索結果に出さない
- 症状3: Withdraw が1ヶ月停滞($0.001 だけ消費)
- 3症状が同一アカウントで発生 → アカウントレベルの状態異常を疑っている旨
- 求めるアクション: アカウント調査、再インデックス、Withdraw 解決またはリカバリー手順

---

## オンチェーン残高スナップショット(2026/05/05 14:55 JST)

| ウォレット | アドレス | USDC | ETH |
|---|---|---|---|
| ECONOMYOS | `0x75e65397...` | $0.099 | 0 |
| neo-test-buyer-v2 | `0x11ab498c...` | $1.853 | 0 |
| NeoAutonomous v2 (seller) | `0x840cff90...` | $2.268 | 0 |
| (未使用) | `0x131d3ff8...` | $0.000 | 0 |
| VP login wallet | `0x8824ADF8...` | $4.000 | - |

合計 ACP 内ロック額: 約 $4.22(うち取り戻したい主軸: buyer $1.85 + seller $2.27)

---

## 本セッションの変更ファイル

### 新規作成・削除
- なし(コード変更ゼロ)
- 白書のみ新規作成: `docs/GSD計画_v6_5bm_引き継ぎ白書.md`

### システム変更
- なし
- v2 seller (`neo-acp-seller-v2.service`): DRY_RUN=false のまま継続稼働中、Heartbeat 正常
- v1 seller (`neo-acp-seller.service`): 停止済(前セッションから変更なし)

### コスト
- 0 USDC
- 0 ETH(調査は eth_call などの read-only RPC のみ)

### 取引ロジック関連
- なし(claude.ai 戦略セッションのため、本体コードには一切触れていない)

---

## 残課題

### 即時(レス待ち)
- GitHub Issue #82 のレスポンス
  - 24時間後(2026/05/06 15:00 JST)にチェック、なければ Bump コメント1回のみ
  - 数日〜2週間以内のレスを想定

### 主戦線(本来の目的)
- **D3 Binance 移行条件達成に向けた取引改善**
  - Paper 勝率: 現在 49.4% → 目標 60%以上
  - 決済件数: 現在 77件 → 目標 100件
  - 期間: 2026/03/14〜 → 3ヶ月継続(最短達成 2026/06/14)
  - これが本来のプロジェクトの主目的

### やってはいけないこと
- ⚠️ 残り2つのウォレットの Withdraw 試行(凍結リスク)
- ⚠️ ACP 関連の追加投資・追加ジョブ発注(VP 側調査結果が出るまで)

---

## ロールバック手順

本セッションはコード変更ゼロのため、ロールバック対象なし。

参考(前セッションから引き継ぎ):
- アクティブエージェントを buyer に戻す場合:
  - `cd /docker/openclaw-taan/data/.openclaw/workspace/skills/acp-cli-v2`
  - `npx tsx bin/acp.ts agent use --agent-id 019d76d4-4e69-76c4-99d7-b90c64988af3`

---

## 自己採点詳細 (8/10)

### 良かった点
- 自前検証の最後のルート(Sandbox Butler)を1セッション内で完全に試し、結論を出した
- 副次的に Withdraw 異常を発見し、3症状を統合エビデンスとして整理できた
- GitHub Issue #82 として正式に投稿、フォーマットも明確で運営側が読みやすい構成
- 取引ロジックには一切触れていない(1ファイル1変更原則の維持)
- 残ウォレットの試行禁止判断が早かった(凍結リスクの拡大を防止)
- ACP 関連を「待ち」状態に確定させ、取引改善への戻り路を明確化

### 反省点
- 序盤で Butler の切替スイッチ位置を勘違い(画面右下のドロップダウンが切替だと推測したが、Butler 自身は「切替スイッチは持っていない」と回答)
- Withdraw 異常の発見は予定外で、1セッションでの作業量が膨らんだ
- ただし発見した内容は価値が高く、Issue の論拠強化に直結したので結果的にはプラス

### 次回への申し送り

**最優先**: 取引改善に集中(本来の主目的)

**並行作業**:
1. GitHub Issue #82 のレスポンス確認(毎日チェック)
2. 24時間レスがなければ Bump コメント1回(別投稿NG)
3. レスが来たら本文を claude.ai に貼って対応案を組み立てる

**現在状態**:
- v2 seller (`neo-acp-seller-v2.service`): DRY_RUN=false, 稼働中
- v1 seller (`neo-acp-seller.service`): 停止済
- ACP 関連: 待ち(Issue #82 レス待ち)
- 主戦線: 取引改善(D3 Binance移行 最短 2026/06/14)
