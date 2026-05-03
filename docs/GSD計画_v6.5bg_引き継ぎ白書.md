# GSD計画 v6.5bg 引き継ぎ白書

- 更新日時: 2026/05/03 08:31 JST
- セッション: v6.5bg(VP Graduation問題 方針再検証 + Phase 0/1完了)
- 自己採点: 7/10

---

## このセッションの主題

**「VP Graduation問題を解決したい」という主訴に対し、ACP_v2_Graduation実行計画書 Phase 0(事前調査)と Phase 1(安全ネット構築)を完了し、計画書の前提自体を公式仕様で検証した。**

- 取引ロジックには一切手を入れていない(claude.aiでの戦略セッションのため)
- v2 seller の DRY_RUN は今も true のまま(計画書通り、Phase 2以降の判断は次回)

---

## Phase 0 事前調査 結果(全項目合格)

### 0.1 v2 seller 実装の完全性
- TODO/FIXME: なし
- ファイル規模: 312行
- 主要関数 7個(notifyDiscord, log, resolveOfferingName, extractRequirements, handleEntry, main, shutdown)
- DRY_RUNフラグ使用箇所 7つ(reject直前/submit直前の理想配置)
- handleEntry関数(109-241行)の処理フロー: fetchJob -> validateRequirements -> executeJob -> session.submit、各段階で try/catch リカバリ完備

### 0.2 過去ログの異常確認
- 過去7日間のイベント: たった2行(起動時のDRY_RUN確認とofferingsロード)
- エラーログ: ゼロ
- 受諾ジョブ: ゼロ(5日間ジョブが1件も来ていない)
- DRY_RUNで止まったジョブ: ゼロ

### 0.3 jobRegistry 34件の状態
- chainId: 全34件が 8453 (Base mainnet)
- legacy=false: 32件
- legacy=true: 2件 (Job 1003409529 / 1003409552)
- legacy=trueはJobIDが10桁の古いID。v1時代の歴史的記録で無害

### 0.4 ウォレット状態
- activeWallet: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab で固定
- 他3ウォレット(0x75e65.../0x11ab49.../0x131d3ff8...)は誤動作不可能な状態
- 0x131d3ff8... は publicKey が空 -> 署名そのものができない

**結論: DRY_RUN解除しても問題ない技術状態。**

---

## Phase 1 安全ネット構築 完了

| 項目 | パス |
|---|---|
| ロールバックスクリプト | scripts/rollback_v2_seller_dryrun.bash |
| systemd unit バックアップ | /etc/systemd/system/neo-acp-seller-v2.service.bak_20260503 |
| seller本体バックアップ | .archive_deadcode_v65p/seller_native_v2.ts.bak_20260503 |

ロールバックは `bash scripts/rollback_v2_seller_dryrun.bash` で一発で DRY_RUN=true に戻る。

---

## 計画書 vs 公式仕様 の検証結果(最重要)

ACP_v2_Graduation実行計画書は概ね正しいが、Virtuals Protocol公式仕様の検証で4点の修正・追加が必要と判明した。

### 修正点1: 連続成功条件
- 計画書: 「10件成功」
- 公式: 「10件中3件連続成功」
- 出典: whitepaper.virtuals.io graduation-process

### 修正点2: Evaluator設定
- 計画書: evaluator=0x0000 (skip-evaluation)
- 公式推奨: evaluatorAddress = buyerAddress (self_evaluation)
- 出典: SDK README Buyer Quick Start, ACP Current Status

### 修正点3: テスト価格
- 計画書: offering_audit $0.30 を使う
- 公式推奨: テスト用は $0.01 で可
- 出典: ACP Current Status「For testing purposes, you can always set your test Provider agent service at $0.01」

### 修正点4: 動画録画の重要度
- 計画書: Phase 4で軽く言及
- 公式: 申請時必須(各 service offering に対して)。「If any single service offering fails, the review will stop, the submission will be rejected, and future submissions may experience delays」
- 出典: agent-graduation-submission-guide

---

## v1で14件COMPLETEDだったがGraduateボタンが出なかった謎の説明

公式仕様 ACP Changelog より:
- 「Congratulations modal」と「Graduate Agent ボタン」は2026/02頃の新機能
- メトリクスは「直近10分以内に活動があったagent」のみ更新される
- v1の14件は古い時代の実績で、新しい判定ロジックでカウントされていない可能性が高い
- v2 seller DRY_RUN期間は実activityがゼロなのでメトリクスにも反映されない

---

## acp-cli-v2 の構造調査結果

| ディレクトリ | 内容 |
|---|---|
| src/commands/ | CLI コマンド (job/agent/browse/wallet等) |
| src/lib/ | 共通ライブラリ |
| src/seller/ | seller_native_v2.ts + offeringsLoader.ts |

- **Buyer専用ディレクトリは存在しない**
- src/commands/job.ts には list/history/watch のみ。**job create コマンドはない**
- 計画書 Phase 2.3a「v2バイヤースクリプトを作る」は必要

### Buyer実装の道筋(公式SDK README より確認済)
- @virtuals-protocol/acp-node-v2 の Buyer Quick Start に約50行の完全動作コード
- buyer.on("entry") で budget.set -> session.fund / job.submitted -> session.complete / job.completed -> 終了
- buyer.createJobByOfferingName() で1関数で job作成 + メッセージ送信

### SDK公式 examples 一覧(GitHub上に存在、要確認)
- examples/buyer.ts (基本)
- examples/seller.ts (基本)
- examples/buyer-fund.ts (fund transfer)
- examples/buyer-llm.ts (LLM駆動 with Claude)

---

## 次セッションの作業

### Claude Code 側で実施すべき内容

1. **Buyer実装** (skills/acp-cli-v2/src/buyer/buyer_test_v2.ts として新規作成)
   - SDK Quick Start の Buyer コードをベースに作成
   - .env の BUYER_* 環境変数を読み込む(BUYER_AGENT_WALLET_ADDRESS, BUYER_WHITELISTED_WALLET_PRIVATE_KEY等)
   - evaluatorAddress = buyerAddress (self_evaluation)
   - chainId = 8453 (Base mainnet)
   - createJobByOfferingName で 0x840cff90... に発注
   - 最初は1件のテスト発注のみ(連続発注ループは後日)

2. **Buyer/Sellerウォレットの残高確認**
   - Buyer (0x3E3E4345...): USDC残高 (Base mainnet)
   - Seller (0x840cff90...): ガス代用ETH (Base mainnet) ※x402モードならガスはsponsorかも

3. **offering 価格の調整(必要なら)**
   - 現行 offerings の価格を確認
   - テスト用に $0.01 に下げる選択肢も検討

4. **動画録画の事前準備リスト作成**
   - 11 offerings 全てが対象?それともテストに使う1〜2offeringsだけ?
   - 公式申請フォームの要件を別途確認

### 実行順序(計画書 Phase 2 改訂版)
1. Buyer実装完了 + 1件テスト発注成功(DRY_RUN中)
2. DRY_RUN解除 + 1件本番テスト発注($0.01)
3. 残り9件発注、うち3件は連続成功になるよう間隔調整
4. Graduateボタン出現を確認
5. 動画録画
6. 申請フォーム送信

### 重要な並行作業候補(計画書通り)
- D3 Binance移行準備(2026/06/14以降の本番移行に向けて)
- Voyager V2 Phase B (検証層への進化)
- EvolveR V2 Phase A (観測の集中化)

---

## 戦略的優先順位の更新(memory/計画書から変化)

| 項目 | v1版(graduation_history_v2) | 本セッション | 理由 |
|---|---|---|---|
| Paper勝率 | 49.4%(77件) | 75.8%(33件) | ウォレットリセット後改善 |
| VP Graduation優先度 | 副次的 | **やや上昇** | 取引改善のプレッシャー低下 + Phase 0/1完了で着手障壁が低い |
| D3 Binance移行 | 最優先 | 引き続き重要 | 本番取引のための条件達成は変わらず |

→ **取引改善が一段落した今、VP Graduation を「副次的」から「次の小目標」へ格上げ可能。ただし取引ロジックへの影響ゼロを大原則とする。**

---

## 本セッション変更ファイル

- 新規: scripts/rollback_v2_seller_dryrun.bash (ロールバックスクリプト)
- バックアップ: /etc/systemd/system/neo-acp-seller-v2.service.bak_20260503
- バックアップ: .archive_deadcode_v65p/seller_native_v2.ts.bak_20260503
- 新規: docs/GSD計画_v6.5bg_引き継ぎ白書.md (本ファイル)

### 取引ロジック関連の変更
- **なし**(claude.aiでの戦略セッションのため、本体コードに一切触れていない)

---

## ロールバック手順

このセッションで作ったものを全て元に戻す手順(必要時のみ実行):
cd /docker/openclaw-taan/data/.openclaw/workspace
rm -f scripts/rollback_v2_seller_dryrun.bash
rmdir scripts 2>/dev/null
rm -f /etc/systemd/system/neo-acp-seller-v2.service.bak_20260503
rm -f .archive_deadcode_v65p/seller_native_v2.ts.bak_20260503
DRY_RUNは元から true のままなので追加の操作は不要。

---

## 自己採点詳細(7/10)

### 良かった点
- 計画書を盲信せず公式仕様で検証した
- Phase 0/1 を抜かりなく完遂
- ターミナルUIの自動リンク化問題に複数回対応(.bash 拡張子に変更で解決)
- ユーザーの「自分でバイヤー作るのは違うのでは?」という疑問を真摯に受け止め公式仕様を再検証

### 反省点
- 序盤で計画書の前提検証を後回しにした(本来 Phase 0 着手前にやるべきだった)
- Buyer実装の道筋まで来たがコード生成までは進めなかった
- 動画録画準備という重要要件を見落としていた(計画書も簡略すぎた)

### 次回への申し送り
- Buyer実装は claude.ai で設計済み、Claude Code側で実装するのが効率的
- DRY_RUN解除は Phase 2.1 の「1件発注テスト」と同時実行が望ましい(連続作業)
- 動画録画準備はGraduate申請の数日前から着手
