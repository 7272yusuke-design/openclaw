# 📋 ACP v2 Graduation 実行計画書

> **作成日**: 2026/04/22
> **対象**: Neo ACP v2 seller (NeoAutonomous v2, `0x840cff9032a4ce29845e05aed510f0ca4ea16cab`)
> **目的**: DRY_RUN 解除 → 本番稼働 → 10 jobs完走 → Graduation 申請までの具体的手順
> **想定実行環境**: Claude Code on VPS (`/docker/openclaw-taan/data/.openclaw/workspace`)
> **想定所要時間**: 合計2〜4時間（ただし小分け実行推奨）

---

## 前提条件（着手前の確認）

- [ ] Paper勝率改善タスクが一段落している、または並行作業で影響が許容される
- [ ] `neo-acp-seller-v2.service` が稼働中である（`systemctl status neo-acp-seller-v2.service`）
- [ ] `skills/acp-cli-v2/config.json` の `activeWallet` が `0x840cff90...` である
- [ ] v2 seller 本体 (`skills/acp-cli-v2/src/seller/seller_native_v2.ts`) が最終修正から変更されていない
- [ ] 本番稼働中にバグが出た場合、即座に `V2_SELLER_DRY_RUN=true` に戻せる準備がある

---

## Phase 0: 事前調査（危険がないか最終確認）

### 0.1 v2 seller 実装の完全性確認

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 1. seller_native_v2.ts の TODO / FIXME / 未実装箇所を確認
grep -nE "TODO|FIXME|XXX|HACK|未実装|not implemented" skills/acp-cli-v2/src/seller/seller_native_v2.ts

# 2. 実装行数とハンドラ関数の完全性
wc -l skills/acp-cli-v2/src/seller/seller_native_v2.ts
grep -nE "^(async )?function |const .* = (async )?\(" skills/acp-cli-v2/src/seller/seller_native_v2.ts | head -20

# 3. DRY_RUNフラグの使用箇所を全部洗い出す
grep -nE "DRY_RUN|dryRun|V2_SELLER_DRY_RUN" skills/acp-cli-v2/src/seller/seller_native_v2.ts
```

**判断基準**:
- TODO/FIXMEが致命的な処理に残っていないか
- DRY_RUNチェックが署名・送信の直前で入っているか（解除で本当にライブ送信される設計か）

### 0.2 過去5日間の"擬似処理ログ"を確認

```bash
# DRY_RUN中に「本来なら処理するはずだった」ジョブがあるかログ確認
journalctl -u neo-acp-seller-v2.service --since "7 days ago" --no-pager 2>/dev/null | \
  grep -iE "job|offering|requirement|funded|submit|error|dry" | tail -50
```

**判断基準**:
- ジョブを受諾したがDRY_RUNで止まった痕跡があるか
- エラーや例外が継続発生していないか

### 0.3 既存の jobRegistry 34件の状態確認

```bash
# jobRegistry の全件状態
python3 -c "
import json
with open('skills/acp-cli-v2/config.json') as f:
    c = json.load(f)
jr = c.get('jobRegistry', {})
print(f'jobRegistry総数: {len(jr)}')
print('=== 全件 ===')
for jid, info in sorted(jr.items(), key=lambda x: int(x[0])):
    print(f'  Job {jid}: legacy={info.get(\"legacy\")} chainId={info.get(\"chainId\")}')"
```

**判断基準**:
- 34件全てが `legacy: false` / `chainId: 8453` か
- 何らかのエラー状態のジョブが含まれていないか

### 0.4 config.json の他ウォレットの状態確認

```bash
# 他の3つのウォレット (0x75e65..., 0x11ab498..., 0x131d3ff...) の実体確認
# activeWallet 以外のウォレットがVirtuals上で稼働中でないか
for addr in 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a \
           0x11ab498cea003b73b66ab48222cb240fe7a9ee82 \
           0x131d3ff8250b00da4753b06317d826ffefde5912; do
    echo "=== $addr ==="
    # Privyの walletId が生きているか確認（acp-cli の whoami 等、存在すれば）
    # 必要に応じて acp-cli コマンドで確認
done
```

**判断基準**:
- 他ウォレットを誤って operation 対象に含めないよう `activeWallet` が固定されているか

---

## Phase 1: 安全ネット構築

### 1.1 緊急ロールバック手順の確認

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# ロールバック用スクリプトを事前作成
cat > scripts/rollback_v2_seller.sh <<'EOF'
#!/bin/bash
# 緊急ロールバック: v2 seller を DRY_RUN に戻して再起動
set -e
echo "[ROLLBACK] V2 seller を DRY_RUN に戻します"
sed -i 's/^Environment=V2_SELLER_DRY_RUN=false$/Environment=V2_SELLER_DRY_RUN=true/' \
    /etc/systemd/system/neo-acp-seller-v2.service
systemctl daemon-reload
systemctl restart neo-acp-seller-v2.service
sleep 5
systemctl status neo-acp-seller-v2.service --no-pager | head -10
echo "[ROLLBACK] 完了。ログ確認: journalctl -u neo-acp-seller-v2.service -f"
EOF
chmod +x scripts/rollback_v2_seller.sh
```

### 1.2 現状の service ファイルをバックアップ

```bash
cp /etc/systemd/system/neo-acp-seller-v2.service \
   /etc/systemd/system/neo-acp-seller-v2.service.bak_$(date +%Y%m%d)
ls -la /etc/systemd/system/neo-acp-seller-v2.service*
```

### 1.3 seller本体もバックアップ

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace
cp skills/acp-cli-v2/src/seller/seller_native_v2.ts \
   skills/acp-cli-v2/src/seller/seller_native_v2.ts.bak_$(date +%Y%m%d)

# .archive_deadcode_v65p/ に移動（再開手順ルール）
mkdir -p .archive_deadcode_v65p
mv skills/acp-cli-v2/src/seller/seller_native_v2.ts.bak_* .archive_deadcode_v65p/
```

---

## Phase 2: 少額ジョブで DRY_RUN 解除テスト（1件のみ）

### 2.1 testnet か mainnet かの確認

```bash
# jobRegistry の chainId=8453 = Base mainnet → 本番環境
# acp-cli-v2/.env.example の IS_TESTNET= が空 → production
grep -E "IS_TESTNET" skills/acp-cli-v2/.env 2>/dev/null
```

**判断基準**: Base mainnet運用になっている。testnet選択肢があれば先にそちらで試したいが、config.jsonの実績からそのまま本番Testへ進む方針。

### 2.2 DRY_RUN を解除

```bash
# service ファイルを書き換え
sed -i 's/^Environment=V2_SELLER_DRY_RUN=true$/Environment=V2_SELLER_DRY_RUN=false/' \
    /etc/systemd/system/neo-acp-seller-v2.service

# 確認
grep -E "V2_SELLER_DRY_RUN|WorkingDirectory|ExecStart" /etc/systemd/system/neo-acp-seller-v2.service

# daemon-reload + restart
systemctl daemon-reload
systemctl restart neo-acp-seller-v2.service
sleep 10

# 起動直後のログ確認（5分間ほど眺める）
journalctl -u neo-acp-seller-v2.service --since "1 minute ago" --no-pager | head -30
```

**判断基準**:
- `✅ Connected to ACP v2 server` が出ているか
- `DRY_RUN=false` または `live mode` 的なログがあるか
- エラー（例：private key not found, signing error）が出ていないか

**問題が出たら**: `scripts/rollback_v2_seller.sh` を即実行

### 2.3 NeoTestBuyer v2 からテストジョブ1件送信

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 既存のバイヤースクリプトが v2対応しているか確認
ls skills/acp-cli-v2/src/ 2>/dev/null | grep -i buyer
ls skills/virtuals-protocol-acp/src/ 2>/dev/null | grep -i buyer

# v2バイヤースクリプトが無ければ作る必要あり（Phase 2.3a）
# あれば → 1件だけ offering_audit などの安い offering を発注
```

**発注内容の推奨**:
- offering: `offering_audit` ($0.30、最安)
- evaluator: 自分自身のアドレス (0x840cff...) または固定 `0x0000` (skip-evaluation)
- wait for: job.funded → session.submit → session.complete

### 2.4 1件ジョブの完走確認

```bash
# リアルタイムログ監視（別ターミナル推奨）
journalctl -u neo-acp-seller-v2.service -f &

# ジョブ発注後、以下のイベントが順に出るはず:
# 1. [v2-seller] Job received: jobId=XX
# 2. [v2-seller] Phase: job.created → budget.set
# 3. [v2-seller] Phase: budget.set → funded (client側の処理待ち)
# 4. [v2-seller] Phase: job.funded → executing offering
# 5. [v2-seller] Executing offering_audit...
# 6. [v2-seller] Phase: submitted
# 7. [v2-seller] Phase: job.completed ✅
```

**判断基準**:
- 1件が最後まで `job.completed` まで到達するか
- 途中で例外やタイムアウトが起きないか
- Base mainnet上でトランザクションが記録されているか（Basescanで確認）

### 2.5 成功したら Discord 通知確認

Discordに以下が届いているはず:
```
🔔 ACP Job (Native v2)
Offering: offering_audit
Job ID: XX
Phase: job.completed
```

---

## Phase 3: 10件バッチ実行 → Graduation 条件達成

### 3.1 バッチ発注スクリプトの準備

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# v1の buyer_batch.ts を参考に v2版を作成（または既存なら修正）
# 基本フロー:
#  - 10件のjobを offering を分散して発注
#  - 各job間に30秒〜1分のスリープ
#  - 結果を Discord に報告
```

**推奨 offering 分散**:
- offering_audit × 4件
- profile_seo × 3件
- graduation_boost × 2件
- graduation_complete × 1件

合計: 約 $5〜$10 のUSDC投入が必要（test buyerウォレットの残高確認必須）

### 3.2 バッチ実行

```bash
# 実行前: ログ監視を立ち上げておく
journalctl -u neo-acp-seller-v2.service -f > /tmp/v2_seller_batch.log &

# バッチ発注
cd /docker/openclaw-taan/data/.openclaw/workspace
npx tsx skills/acp-cli-v2/src/buyer_batch_v2.ts

# 完走まで約10〜30分
# 各ジョブが funded → submitted → completed となるのを監視
```

### 3.3 10件完走の確認

```bash
# completed件数のカウント
grep -c "Phase: job.completed" /tmp/v2_seller_batch.log

# VP APIで確認（登録されていれば）
# 現時点で acpx/acp-x402 がウォレット検索に応答しないので、Platform UI での確認が確実
```

**目視確認ポイント** (app.virtuals.io/acp/agents/<v2-agent-id>):
- Graduation Progress: 100%
- Successful Transactions: 10+
- Consecutive Successful: 3+（自分のtest buyerから）

---

## Phase 4: Graduation 申請

### 4.1 Platform UI から申請

ブラウザで:
1. https://app.virtuals.io/acp/agents を開く
2. NeoAutonomous v2 (0x840cff...) を選択
3. 以下のいずれかが表示されているはず:
   - **"Congratulations" modal**
   - **"Proceed to Graduation" button**
   - **"Graduate Agent" button**
4. クリックして Graduation Submission Form に進む

### 4.2 Submission Form への入力内容（事前準備）

- Agent Description: "Autonomous crypto trading AI with 11 ACP offerings"
- Service offerings詳細
- Video recordings（offerings動作確認の動画）← **事前撮影必要**
- 技術スタック（acp-node-v2 + native SDK）

### 4.3 Submission後のフロー

Virtuals側での Manual Review（通常1〜2週間）:
1. **Stage 1**: 書類審査（説明の十分性）
2. **Stage 2**: Functional test（サポートチームが各offeringをテスト）
3. **Stage 3**: Final approval

結果は Telegram で通知される。

---

## Phase 5: 万一失敗した場合のフォールバック

### シナリオ A: Phase 2 で1件ジョブが失敗

**対処**:
1. `scripts/rollback_v2_seller.sh` を実行して DRY_RUN に戻す
2. journalctl でエラーを特定
3. よくある原因:
   - P256キーが無効 → `skills/acp-cli-v2/bin/acp-cli-signer-*` の権限確認
   - Privy walletId 不一致 → config.json と実際のウォレットの一致確認
   - USDC残高不足 → test buyerへの入金確認

### シナリオ B: Phase 3 でバッチ途中で失敗

**対処**:
1. 失敗したジョブの phase を記録
2. 残りのジョブを個別発注で補完（5件+5件等に分けて段階実行）
3. Rate limit の可能性もあるため間隔を広げる

### シナリオ C: Phase 4 で Graduation ボタンが出ない

**対処**:
1. 24時間待つ（VP側のメトリクス反映ラグの可能性）
2. acp-cli v2 で `agent status` 等を叩いて successful_jobs の数を確認
3. それでもダメなら Discord @ team に報告（このドキュメントをエビデンスとして添付）

---

## Phase 6: 完了後の後始末

### 6.1 旧v1 seller の停止

```bash
# v2 で graduation が通ったら、v1 seller は役目終了
systemctl stop neo-acp-seller.service
systemctl disable neo-acp-seller.service
```

### 6.2 再開手順の更新

- `saikai_tejun_v6_5ak.md` の ACP構成セクションを v2主体に書き換え
- ARCHITECTURE.md の更新

### 6.3 白書更新

- Graduation完了を白書に記載
- `graduation_history_v2.md` に実行結果を追記

---

## 実行判断チェックリスト（着手前）

- [ ] Phase 0 の調査を全て完了し、実装に致命的な穴がないことを確認した
- [ ] ロールバックスクリプトを準備済み
- [ ] Test buyerウォレットに最低$10のUSDC残高がある
- [ ] Discord webhookが動作している（通知受信可能）
- [ ] Basescanで v2ウォレット (`0x840cff...`) のBase mainnet残高を確認した
- [ ] 作業中に取引ロジックの変更は行わない（1ファイル1変更原則）
- [ ] Paper運用には影響を与えない（v1 seller はそのまま維持、運用本体はv1主体）

---

## タイムライン目安

```
Phase 0 (事前調査):         30分〜1時間
Phase 1 (安全ネット):       15分
Phase 2 (1件テスト):        30分〜1時間（ジョブ完走待ち含む）
Phase 3 (10件バッチ):       1〜2時間
Phase 4 (申請):             30分（UI操作 + 申請フォーム記入）
Phase 5 (レビュー待ち):     1〜2週間（Virtuals側）
Phase 6 (後始末):           30分
```

**合計の実作業時間**: 3〜5時間
**カレンダー時間**: 2〜3週間（Virtualsレビュー待ちを含む）

---

## 備考

- 本計画書は「v2 seller実装が Phase 7 (v6.5ba) で完了している」前提で書かれている。もし実装に未完成部分が見つかった場合、Phase 0 の時点で中断して再設計が必要。
- Virtuals Protocol側のAPI/UIは継続的に変更されるため、Phase 4 の申請UIが本計画書と異なる可能性がある。最新は whitepaper.virtuals.io で確認のこと。
- 本計画書は `Claude Code on VPS` 環境での実行を想定。claude.ai 側では計画策定までで、実装はClaude Codeに任せる設計。
