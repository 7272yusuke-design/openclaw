# 📋 VP関連リファクタ実行計画書 v1

> **作成日**: 2026/05/06
> **作成セッション**: claude.ai リファクタ調査セッション
> **対象**: 次回以降のセッション(claude.ai または Claude Code on VPS)
> **前提読書**: `docs/VP_overview_v2.md`(必須)
> **想定スコープ**: 中規模リファクタ(v1停止・コード統合・ドキュメント整備)

---

## 🎯 このドキュメントの目的

VP関連のリファクタを **次のセッションで安全に実行できるよう**、調査結果に基づいた具体的な手順を残す。本セッション(2026/05/06)では調査と計画策定までを実施し、**実際のコード変更は次セッション以降に持ち越す**。

理由:

1. 主戦線はD3 Binance移行(Paper勝率改善)であり、VP関連は副次的
2. Issue #82 のVP側レスポンス次第で計画が変わる可能性
3. 本セッションは長く、疲労によるミスを避けたい

---

## 🚦 大原則(必ず守ること)

このリファクタを実行するセッションは、以下を必ず守ること:

1. **本ドキュメントを実行する前に `docs/VP_overview_v2.md` を必ず読む**
2. **本番取引(Paper運用、TrinityCouncil、neo-radar)には一切影響を与えない**
3. **Issue #82 のステータスを最初に確認する**(Open/Closed/レスありで方針が変わる)
4. **1ファイル1変更ずつ進め、毎回構文チェック**
5. **バックアップは `.archive_deadcode_v65p/refactor_<日付>/` に集約**
6. **`V2_SELLER_DRY_RUN=false` を維持**(白書v6.5bm時点ですでに解除済)
7. **Withdraw操作は絶対禁止**(残2ウォレットの凍結リスク)

---

## 📦 リファクタ全体像

| Phase | 内容 | リスク | 推定時間 | 前提 |
|---|---|---|---|---|
| **0** | 事前確認 | なし | 15分 | なし |
| **1** | バックアップ作成 | なし | 10分 | Phase 0 |
| **2** | デッドコード整理 | 低 | 30分 | Phase 1 |
| **3** | Builder Code反映 + seller再起動 | **中** | 30分 | Phase 2、Issue #82要確認 |
| **4** | wallet_inventory.md 作成 | なし | 15分 | Phase 1 |
| **5** | ARCHITECTURE.md / 再開手順 更新 | なし | 30分 | Phase 2-4 |
| **6** | git commit + 白書更新 | なし | 15分 | 全Phase完了 |

合計: **約2時間半**(集中して実施した場合)

---

## Phase 0: 事前確認

### 0.1 Issue #82 のステータス確認

ブラウザで以下を開く:
https://github.com/Virtual-Protocol/openclaw-acp/issues/82

判定:

| ステータス | 影響 |
|---|---|
| Open + レスなし | このリファクタを通常通り実行可 |
| Open + Virtuals側からレスあり | **本リファクタ中断**、レス内容を白書に反映してから対応再検討 |
| Closed (resolved) | 喜ばしい状況。Phase 3後に Re-Import 検討を追加 |

### 0.2 サービス稼働確認

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

for svc in neo-radar neo-collector neo-resource-api neo-acp-seller neo-acp-seller-v2; do
    active=$(systemctl is-active $svc.service 2>&1)
    enabled=$(systemctl is-enabled $svc.service 2>&1)
    printf "%-25s active=%-12s enabled=%s\n" "$svc" "$active" "$enabled"
done
```

期待値(白書v6.5bm時点):

```
neo-radar                 active=active       enabled=enabled
neo-collector             active=active       enabled=enabled
neo-resource-api          active=active       enabled=enabled
neo-acp-seller            active=inactive     enabled=disabled
neo-acp-seller-v2         active=active       enabled=enabled
```

ズレがあれば原因を特定してから先に進む。

### 0.3 Paper運用への影響範囲チェック

```bash
ls -la data/paper_wallet.json
tail -5 radar_output.log
```

paper_wallet.jsonが直近で更新されていることを確認。Council判断が止まっていないこと。

---

## Phase 1: バックアップ作成

### 1.1 作業用バックアップディレクトリ作成

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

BACKUP_DIR=".archive_deadcode_v65p/refactor_$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
echo "Backup dir: $BACKUP_DIR"
```

### 1.2 これから触るファイルを全部バックアップ

```bash
# v2 seller本体(Phase 3でBuilder Code反映時に変更)
cp skills/acp-cli-v2/src/seller/seller_native_v2.ts "$BACKUP_DIR/seller_native_v2.ts.bak"

# systemd unit(参考)
cp /etc/systemd/system/neo-acp-seller-v2.service "$BACKUP_DIR/neo-acp-seller-v2.service.bak"
cp /etc/systemd/system/neo-acp-seller.service "$BACKUP_DIR/neo-acp-seller.service.bak"

# config.json(参考)
cp skills/acp-cli-v2/config.json "$BACKUP_DIR/acp-cli-v2-config.json.bak"

# ARCHITECTURE.md と 再開手順
cp ARCHITECTURE.md "$BACKUP_DIR/ARCHITECTURE.md.bak"

ls -la "$BACKUP_DIR"
```

### 1.3 緊急ロールバック手順をメモ

```bash
cat > "$BACKUP_DIR/ROLLBACK.md" <<EOF
# 緊急ロールバック手順

## seller_native_v2.ts を戻す
cp $BACKUP_DIR/seller_native_v2.ts.bak skills/acp-cli-v2/src/seller/seller_native_v2.ts
systemctl restart neo-acp-seller-v2.service
sleep 5
journalctl -u neo-acp-seller-v2.service --since "1 minute ago" --no-pager | head -20

## DRY_RUNに戻す(緊急時)
sed -i 's/V2_SELLER_DRY_RUN=false/V2_SELLER_DRY_RUN=true/' /etc/systemd/system/neo-acp-seller-v2.service
systemctl daemon-reload
systemctl restart neo-acp-seller-v2.service

## git stash で全変更を退避
git stash
git stash list
EOF

cat "$BACKUP_DIR/ROLLBACK.md"
```

---

## Phase 2: デッドコード整理

### 2.1 systemd .bak ファイルを移動

```bash
# 現状確認
ls -la /etc/systemd/system/neo-acp-seller*.service*

# bakファイルを.archive_deadcode_v65p/ に移動
mv /etc/systemd/system/neo-acp-seller-v2.service.bak_20260503 \
   .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/
mv /etc/systemd/system/neo-acp-seller-v2.service.bak_before_live_20260505_0131 \
   .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/

# 確認
ls -la /etc/systemd/system/neo-acp-seller*.service*
```

期待: `neo-acp-seller.service` と `neo-acp-seller-v2.service` の2つだけ残る。

### 2.2 v1 seller を archive(任意・残しても害はない)

`neo-acp-seller.service` は disabled 済みで害はないが、再開手順.mdの整理ルール上は archive 推奨。

```bash
# disabledかつ inactive を再確認
systemctl is-active neo-acp-seller.service
systemctl is-enabled neo-acp-seller.service

# 安全のため stop & disable を再実行(冪等)
systemctl stop neo-acp-seller.service 2>/dev/null
systemctl disable neo-acp-seller.service 2>/dev/null

# unit本体を移動
mv /etc/systemd/system/neo-acp-seller.service \
   .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/

systemctl daemon-reload

# 確認
ls -la /etc/systemd/system/neo-acp-seller*.service*
systemctl status neo-acp-seller.service 2>&1 | head -5
```

期待: `neo-acp-seller-v2.service` のみ残る。`neo-acp-seller.service` は「Unit not found」になる。

### 2.3 skills/openclaw-acp-v2/ の判定

参照ゼロのデッドコードだが、独立Gitリポジトリのため慎重に。

**判断材料**:

```bash
# 最後にコミットがあったか確認
cd skills/openclaw-acp-v2
git log -1 --format="%h %ad %s" 2>/dev/null
cd ../..

# 全体コードベースでの参照チェック(再確認)
grep -rn "openclaw-acp-v2" \
    --include="*.py" --include="*.ts" --include="*.json" --include="*.service" \
    --exclude-dir=node_modules --exclude-dir=.git \
    --exclude-dir=.archive_deadcode_v65p \
    /docker/openclaw-taan/data/.openclaw/workspace/ \
    /etc/systemd/system/ \
    2>/dev/null | head -5
```

**判定方針**:

- 参照ゼロが確認できれば、**ディレクトリごと `.archive_deadcode_v65p/` に移動**
- 削除ではなく移動するのは、後で「やっぱり要る」となった時の保険
- 独立gitリポジトリなので `.git` も含めて移動

```bash
# まだ参照がないことを確認したら実行
mv skills/openclaw-acp-v2 .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/

# 確認
ls -la skills/ | grep -i openclaw
```

### 2.4 agents/acp_executor_agent.py の判定

参照ゼロ(自分自身しかimportしていない)。

```bash
# 再確認
grep -rln "acp_executor_agent\|ACPExecutorCrew" \
    --include="*.py" \
    --exclude-dir=.archive_deadcode_v65p \
    --exclude-dir=__pycache__ \
    2>/dev/null

# 該当が agents/acp_executor_agent.py 自身だけなら archive
mv agents/acp_executor_agent.py .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/

# Pythonの構文を壊していないか確認(import側のチェック)
python3 -c "from agents.trinity_council import TrinityCouncil; print('OK')" 2>&1 | head -5
```

期待: `OK` が表示される。エラーが出たらすぐに戻す:

```bash
mv .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/acp_executor_agent.py agents/
```

### 2.5 v1 seller のソースコードを archive

```bash
# 該当ファイル確認
ls skills/virtuals-protocol-acp/src/seller/runtime/seller_native.ts

# v2 seller がこのファイルを参照していないか確認
grep -rn "runtime/seller_native\|seller_native\.ts" \
    skills/acp-cli-v2/ \
    --exclude-dir=node_modules \
    2>/dev/null | head -5
```

参照がないことを確認したら:

```bash
# ディレクトリごと archive
mv skills/virtuals-protocol-acp/src/seller/runtime \
   .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/v1_seller_runtime

# 確認
ls skills/virtuals-protocol-acp/src/seller/
```

期待: `offerings/` ディレクトリだけ残る。

### 2.6 docs/graduation_history.md を archive

旧版(2026/04/01)。最新は claude.ai プロジェクトファイル `graduation_history_v2.md` にある。

```bash
mv docs/graduation_history.md .archive_deadcode_v65p/refactor_$(date +%Y%m%d)/
```

---

## Phase 3: Builder Code反映 + seller再起動

⚠️ **このPhaseはリスク中。慎重に実施**

### 3.1 事前確認

```bash
# 現在のseller稼働状態
systemctl status neo-acp-seller-v2.service --no-pager | head -10

# 直近のログでエラーがないか
journalctl -u neo-acp-seller-v2.service --since "1 hour ago" --no-pager 2>/dev/null | \
    grep -iE "error|fail|warn" | head -10
```

エラーが出ていなければ続行。

### 3.2 seller_native_v2.ts に Builder Code を組み込む

**目的**: VP UIで登録済みの `bc_agxzezgu` を、実際の取引データに付加する。

**実装方針**: Base Builder Codes の標準仕様 ERC-8021 に従い、`dataSuffix` を全トランザクションに付加する。

**Builder Code**: `bc_agxzezgu`

#### Step 3.2.1: 現在の seller_native_v2.ts の構造を確認

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 主要なimport文と構造を把握
head -50 skills/acp-cli-v2/src/seller/seller_native_v2.ts

# AcpAgent や createAgentFromConfig の使い方を確認
grep -nE "createAgentFromConfig|AcpAgent|new Agent|signTransaction" \
    skills/acp-cli-v2/src/seller/seller_native_v2.ts | head -10
```

#### Step 3.2.2: ACP v2 SDK が dataSuffix オプションを持つか確認

```bash
# acp-node-v2 のドキュメント・型定義を確認
find skills/acp-cli-v2/node_modules/@virtuals-protocol/acp-node-v2 \
    -name "*.d.ts" 2>/dev/null | head -5
grep -rn "dataSuffix\|builderCode\|attribution" \
    skills/acp-cli-v2/node_modules/@virtuals-protocol/acp-node-v2/ \
    2>/dev/null | head -10
```

判定:

- **dataSuffixオプションあり**: AcpAgent初期化時に渡すだけで完了
- **dataSuffixオプションなし**: ERC-8021の `Attribution.toDataSuffix` をimportして手動付加

このPhase 3は **判定結果次第で具体的なコード変更が変わる**ため、上記確認後に詳細実装を別途計画する必要がある。

#### Step 3.2.3: コード変更の指針(参考)

```typescript
// ファイル冒頭のimport追加
import { Attribution } from "ox/erc8021";

// Builder Code定義(コメント付き)
// VP UIで登録済み: bc_agxzezgu (2026/05/06設定)
const BASE_BUILDER_CODE = "bc_agxzezgu";
const DATA_SUFFIX = Attribution.toDataSuffix({
  codes: [BASE_BUILDER_CODE],
});

// AcpAgent初期化箇所に dataSuffix を渡す(SDKのAPI次第)
```

実際の差分は Step 3.2.1-3.2.2 の結果に依存するので、その時点で具体化する。

### 3.3 構文チェック

```bash
cd skills/acp-cli-v2
npx tsc --noEmit src/seller/seller_native_v2.ts 2>&1 | head -20
```

エラーゼロを確認してから次へ。

### 3.4 seller再起動とログ確認

```bash
# 再起動
systemctl restart neo-acp-seller-v2.service
sleep 10

# 起動確認
systemctl is-active neo-acp-seller-v2.service

# 起動ログ(11 offerings ロード確認)
journalctl -u neo-acp-seller-v2.service --since "30 seconds ago" --no-pager 2>/dev/null | \
    grep -iE "loaded|connect|error" | head -20
```

期待:

- `Loaded 11 offerings: ...` のメッセージ
- `Connected to ACP v2 server` 等の接続成功メッセージ
- エラーなし

### 3.5 失敗時のロールバック

エラーが出た or 起動しない場合:

```bash
# ロールバック手順をすぐ実行
BACKUP_DIR=".archive_deadcode_v65p/refactor_$(date +%Y%m%d)"
cp $BACKUP_DIR/seller_native_v2.ts.bak \
   skills/acp-cli-v2/src/seller/seller_native_v2.ts
systemctl restart neo-acp-seller-v2.service
sleep 5
journalctl -u neo-acp-seller-v2.service --since "1 minute ago" --no-pager | head -20
```

ロールバックして安定したら、エラー内容を白書に記録して次セッションへ持ち越し。

### 3.6 Builder Code帰属の検証

`https://builder-code-checker.vercel.app/` で、新規発生したジョブのトランザクションが `8021 attributed` になっているか確認。

ただし、**新規ジョブを発注しないと検証できない**ため、Issue #82 解決待ちの間は実取引で検証することはせず、コード変更のみで完了とする。

---

## Phase 4: wallet_inventory.md 作成

ウォレット情報を1箇所に集約する `docs/wallet_inventory.md` を作成。

```bash
cat > docs/wallet_inventory.md <<'EOF'
# 💰 Neo VP Wallet Inventory

> **最終更新**: <作業日に書き換える>
> **目的**: VP関連ウォレット4個 + ログイン用ウォレット1個の正体・残高・状態を1箇所にまとめる

---

## エージェントウォレット (skills/acp-cli-v2/config.json で管理)

| アドレス | 名前 | 役割 | activeWallet | USDC残高 | ETH | 状態 |
|---|---|---|---|---|---|---|
| 0x840cff9032a4ce29845e05aed510f0ca4ea16cab | NeoAutonomous v2 | seller本体 | acp-cli-v2 側 active | $2.268 | 0 | 🟢 現役 |
| 0x11ab498cea003b73b66ab48222cb240fe7a9ee82 | neo-test-buyer-v2 | テストバイヤー | acp-cli-v2-buyer 側 active | $1.853 | 0 | 🟢 現役 |
| 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a | ECONOMYOS | 旧テストエージェント | なし | $0.099 | 0 | 🔴 凍結 (Withdraw失敗) |
| 0x131d3ff8250b00da4753b06317d826ffefde5912 | (空ウォレット) | 作成途中 | なし | $0.000 | 0 | ⚫ publicKey空・署名不可 |

## ブラウザログイン用 (config.json外)

| アドレス | 役割 | USDC残高 |
|---|---|---|
| 0x8824ADF8e...ABFFC8f3870 | VP login wallet (MetaMask等) | $4.000 |

## Privy walletId 一覧

```
0x840cff90... → fjw429slut1eygk4gipj7y6d
0x11ab498c... → ebwhtj033sjo8cfx17fdlm86
0x75e65397... → q6819z8fmd2ios2l6nnrf505
0x131d3ff8... → (空)
```

## Agent ID 一覧

```
0x840cff90... → 019d7b3f-c2d8-7a52-839c-9629f4abb5dc (NeoAutonomous v2)
0x11ab498c... → 019d76d4-4e69-76c4-99d7-b90c64988af3 (neo-test-buyer-v2)
0x75e65397... → 019d7659-6dd1-7067-a5ff-d74f567a3961 (ECONOMYOS)
0x131d3ff8... → 019d7bb4-d669-7809-a171-e6996c632eea (空ウォレット)
```

## 重要事項

### 認証構造
- 全ウォレットは Privy 管理 (P256キー + walletId)
- privateKey フィールドはconfig.jsonに存在しない = サーバー側に秘密鍵なし
- 通常のweb3スクリプトでは送金不可能
- ガス代は Virtuals 側がスポンサー

### Withdraw禁止事項 (白書v6.5bm)
- 残2ウォレット (buyer / seller) のWithdraw試行は絶対禁止
- 理由: ECONOMYOSの$0.10が1ヶ月凍結状態 (Withdrawで$0.001消費後・送金未完了)
- Issue #82 のVP側調査結果待ち

### activeWallet 切替について
- skills/acp-cli-v2/config.json の activeWallet が seller側を決定
- skills/acp-cli-v2-buyer/config.json の activeWallet が buyer側を決定
- 切替は config.json を直接編集 + サービス再起動

## 残高更新履歴

| 日付 | アドレス | 変動 | 理由 |
|---|---|---|---|
| 2026/05/05 | 全ウォレット | スナップショット | 白書v6.5bm |

---

## 改訂履歴

| 日付 | 変更内容 | 担当 |
|---|---|---|
| <作業日> | 初版作成 | <セッションID> |
EOF

# 作成日を埋める
sed -i "s/<作業日に書き換える>/$(date +%Y/%m/%d)/" docs/wallet_inventory.md
sed -i "s/<作業日>/$(date +%Y\/%m\/%d)/g" docs/wallet_inventory.md

# 確認
cat docs/wallet_inventory.md | head -20
```

---

## Phase 5: ARCHITECTURE.md / 再開手順 更新

### 5.1 ARCHITECTURE.md にVPセクションへのポインタ追加

```bash
# 現状確認
grep -n "VP\|ACP\|virtuals" ARCHITECTURE.md | head -10
```

ARCHITECTURE.md の適切な箇所に以下のセクションを追加(具体位置はファイル構造を見て決定):

```markdown
## VP/ACP関連

VP関連の物理構造・状態は別ドキュメントに集約しています:

- **`docs/VP_overview_v2.md`** — VP関連コードベース全体像マップ(必読)
- **`docs/wallet_inventory.md`** — ウォレット情報
- **`docs/VP_refactor_plan_v1.md`** — リファクタ実行計画

主要エントリポイント:
- v2 seller: `skills/acp-cli-v2/src/seller/seller_native_v2.ts` (systemd: neo-acp-seller-v2.service)
- offerings本体: `skills/virtuals-protocol-acp/src/seller/offerings/` (11個)
- Trinity Council統合: `bridge/acp_client.py` 経由(参考情報注入のみ)
- VP銘柄発見: `orchestration/vp_discovery.py` (週次)
```

### 5.2 再開手順.md にVPドキュメントへのポインタ追加

`saikai_tejun_v6_5ak.md` の冒頭「最初にやること」セクション周辺に追記:

```markdown
## VP/ACP関連の作業を始める前に

VP/ACP関連の作業を行う場合は、必ず以下を順に読む:

1. `docs/VP_overview_v2.md` — 現状マップ(物理構造・既知の問題)
2. `docs/wallet_inventory.md` — ウォレット情報
3. `docs/VP_refactor_plan_v1.md` — 残作業の計画書(該当する場合)

重要な禁止事項:
- Issue #82 のレスが来るまで、VP Registryへの変更操作(Re-Import等)禁止
- 残2ウォレットの Withdraw 試行は絶対禁止
```

### 5.3 docs/ 内のVP関連ドキュメント整理状況

整理後の docs/ 内VP関連ファイル一覧(期待):

```
docs/VP_overview_v2.md         <- 新規・現状マップ
docs/VP_refactor_plan_v1.md    <- 新規・本ドキュメント
docs/wallet_inventory.md       <- 新規・ウォレット情報
docs/graduation_boost_design.md <- 残す(設計書)
docs/GSD計画_v6_5bm_引き継ぎ白書.md <- 残す(最新白書)
```

`docs/graduation_history.md`(旧版)は Phase 2.6 で archive 済。

---

## Phase 6: git commit + 白書更新

### 6.1 変更ファイル一覧の確認

```bash
git status --short | head -30
```

期待される変更:

- 新規: `docs/VP_overview_v2.md`
- 新規: `docs/VP_refactor_plan_v1.md`
- 新規: `docs/wallet_inventory.md`
- 削除/移動: `agents/acp_executor_agent.py`
- 削除/移動: `skills/openclaw-acp-v2/`
- 削除/移動: `skills/virtuals-protocol-acp/src/seller/runtime/`
- 削除/移動: `docs/graduation_history.md`
- 修正: `skills/acp-cli-v2/src/seller/seller_native_v2.ts` (Builder Code反映 - Phase 3実施した場合)
- 修正: `ARCHITECTURE.md`
- 修正: `saikai_tejun_v6_5ak.md`(オプショナル)

### 6.2 git commit

```bash
git add -A
git status --short

# 適切なコミットメッセージで commit
git commit -m "v6.5bn: VP関連リファクタ実施 - デッドコード整理 + ドキュメント整備

主な変更:
- VP関連の現状マップ作成 (docs/VP_overview_v2.md)
- リファクタ実行計画書作成 (docs/VP_refactor_plan_v1.md)
- ウォレット情報集約 (docs/wallet_inventory.md)
- v1 seller archive (skills/virtuals-protocol-acp/src/seller/runtime/)
- デッドコード archive (skills/openclaw-acp-v2/, agents/acp_executor_agent.py)
- systemd .bak整理 (.archive_deadcode_v65p/refactor_YYYYMMDD/)
- ARCHITECTURE.md / 再開手順 にVPセクションへのポインタ追加
- Builder Code (bc_agxzezgu) を seller_native_v2.ts に反映 (Phase 3実施した場合)

注意:
- 取引ロジックには一切触れていない
- VP Registry側の状態は変更していない (Issue #82レス待ち)
- DRY_RUN=false 維持"
```

### 6.3 白書 v6.5bn 作成

```bash
NEW_WHITEPAPER="docs/GSD計画_v6_5bn_引き継ぎ白書.md"

cat > $NEW_WHITEPAPER <<EOF
# GSD計画 v6.5bn 引き継ぎ白書

- 更新日時: $(date +%Y/%m/%d) <時刻>
- セッション: v6.5bn (VP関連リファクタ実施)
- 自己採点: <作業後に記入>

---

## このセッションの主題

(claude.aiの計画書 docs/VP_refactor_plan_v1.md に基づくVP関連リファクタの実施)

主な変更:
- VPに関する現状を docs/VP_overview_v2.md として集約
- リファクタ実行計画 docs/VP_refactor_plan_v1.md を確定
- ウォレット情報 docs/wallet_inventory.md を作成
- デッドコード(skills/openclaw-acp-v2/, agents/acp_executor_agent.py, v1 seller runtime)を archive
- systemd .bak ファイルを .archive_deadcode_v65p/ に移動
- ARCHITECTURE.md / 再開手順 にVPセクションを統合

(以下、実際の作業内容に基づいて記入)

EOF

echo "$NEW_WHITEPAPER created"
```

白書本文は実施結果を見て手動で完成させる。

### 6.4 最終 commit

```bash
git add -A
git commit -m "docs: v6.5bn 白書追加 (VP関連リファクタ完了)"
```

---

## チェックリスト(完了判定)

このリファクタが完了したと言える基準:

### Phase 0
- [ ] Issue #82 のステータス確認済
- [ ] 全サービス稼働確認済
- [ ] Paper運用への影響なしを確認

### Phase 1
- [ ] バックアップディレクトリ作成
- [ ] seller_native_v2.ts バックアップ済
- [ ] systemd unit バックアップ済
- [ ] config.json バックアップ済
- [ ] ROLLBACK.md 作成済

### Phase 2
- [ ] systemd .bak 2個 archive 済
- [ ] v1 seller unit archive 済
- [ ] skills/openclaw-acp-v2/ archive 済
- [ ] agents/acp_executor_agent.py archive 済
- [ ] v1 seller runtime ディレクトリ archive 済
- [ ] docs/graduation_history.md archive 済
- [ ] python3 -c "from agents.trinity_council import TrinityCouncil" 成功

### Phase 3 (オプション・リスク中)
- [ ] seller_native_v2.ts に Builder Code (bc_agxzezgu) 反映
- [ ] tsc --noEmit でエラーなし
- [ ] seller再起動成功
- [ ] 起動ログで「Loaded 11 offerings」確認
- [ ] 直近1分間にエラーログなし

### Phase 4
- [ ] docs/wallet_inventory.md 作成

### Phase 5
- [ ] ARCHITECTURE.md にVPセクションへのポインタ追加
- [ ] 再開手順.md にVPドキュメントへのポインタ追加

### Phase 6
- [ ] git add -A 後、変更内容が想定通り
- [ ] git commit 成功
- [ ] 白書 v6.5bn 作成

---

## トラブルシューティング

### Q: Phase 3でseller再起動後にジョブが入らない

A: 直近のログを確認:
```bash
journalctl -u neo-acp-seller-v2.service -f
```

`Connected to ACP v2 server` が出ていない場合、ネットワーク or Privy認証問題。

### Q: agents/acp_executor_agent.py を archive 後、Pythonがimportエラー

A: ロールバック:
```bash
mv .archive_deadcode_v65p/refactor_*/acp_executor_agent.py agents/
python3 -c "from agents.trinity_council import TrinityCouncil; print('OK')"
```

### Q: VP UIで何も表示が変わらない

A: VP Registry層は本リファクタの対象外。Issue #82 のレス待ち状態の継続。

---

## このドキュメントの更新ルール

- 実施完了後、該当Phaseのチェックリストにチェックを入れる
- 実施中にトラブルや想定外があれば、本ドキュメントの末尾「実施記録」に追記する
- リファクタ完了後、新たな課題が発生したら新しい計画書 v2 を作成する

---

## 実施記録

(リファクタ実施時に追記する欄)

| 日付 | Phase | 内容 | 結果 | 備考 |
|---|---|---|---|---|
| - | - | - | - | - |

---

## 改訂履歴

| 日付 | バージョン | 変更概要 | 担当 |
|---|---|---|---|
| 2026/05/06 | v1.0 | 初版作成(claude.aiリファクタ調査セッション) | claude.ai |
