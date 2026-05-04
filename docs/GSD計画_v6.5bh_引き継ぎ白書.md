# GSD計画 v6.5bh 引き継ぎ白書

- 更新日時: 2026/05/04 11:55 JST
- セッション: v6.5bh(VP Graduation問題 Phase 2 着手 + setBudget実装欠落の発見・修正)
- 自己採点: 8/10

---

## このセッションの主題

**「VP Graduation問題」を進めるため、Phase 2(buyer実装+1件発注テスト)に着手。途中で複数の重大事実が判明し、計画書 Phase 0 の前提が部分的に誤っていたことが発覚。最終的にseller-v2の致命的な実装欠落を発見・修正し、buyer→seller通信の動作確認まで完了した。**

- 取引ロジック(neo-radar / TrinityCouncil等)には一切手を入れていない
- v2 seller は今もDRY_RUN=trueで稼働中(計画書 Phase 2.1 の動作確認まで完了、本番テストは次回)

---

## 本セッションで判明した重大事実

### 重大事実1: ECONOMYOS(`0x75e65397...`)は卒業対象にできない

- 当初ユーザー意向は「最古の本命エージェント `0x75e65397...`(Agent ID `019d7659-6dd1-7067-a5ff-d74f567a3961`、VP上の表示名「Neo」/ECONOMYOS)を卒業させたい」
- しかしVP UI上で確認したところ、このエージェントは:
  - **ACPタブが存在しない**(他のv2エージェントには存在する)
  - Runtime空、Revenue $0、Spend $0、Wallet残高 $0.099
  - Setup/Activate ボタンもない、ポップアップに「We'll guide you through setup once your agent is ready」とだけ表示
  - VPプラットフォーム側がこのエージェント枠を有効化していない殻状態
- → **戦略的妥協案を採用**: まず `0x840cff90...` を卒業させて実績を作り、その後VPサポートに ECONOMYOS の有効化を相談する流れに方針転換

### 重大事実2: v2 buyer は既に存在していた(neo-test-buyer-v2)

- これまでの白書・graduation_history_v2.md では「buyerは NeoTestBuyer (`0x9999c67a...`, Agent ID 41440, v1扱い)のみ」とされていた
- しかし実際には **`neo-test-buyer-v2` (`0x11ab498c...`, Agent ID `019d76d4-4e69-76c4-99d7-b90c64988af3`)** がVP上に Self-hosted Pro として存在
- このエージェントは **既に config.json に登録済み**(publicKey, walletId 揃い)、Wallet残高も $1.97 USDC ある状態
- → **NeoTestBuyer の v2 アップグレード作業は不要**だったことが判明

### 重大事実3: seller_native_v2.ts に setBudget 実装が欠落していた

**最大の発見**。Phase 0(v6.5bg)で「seller-v2は完全実装済み」と評価していたが、これが誤りだった。

実装の問題点:
- 現seller_native_v2.ts は `event.type === "job.funded"` をトリガーに処理開始する設計
- しかしv2 SDKのフローでは `requirement → setBudget → fund → submit → complete` の順で進む
- **setBudget を呼ぶコードが完全に欠如していた**ため、buyerが発注しても永遠に進まない
- これがv6.5ba以降の5日間「DRY_RUN中で0 jobs」だった真の原因の片割れ
  - 表面的原因: buyer未稼働 / DRY_RUN
  - 真因: 仮に DRY_RUN を解除しても、setBudgetがないため永遠にジョブが流れない設計だった

修正内容:
- import 文に `AssetToken` 追加(1行)
- `budgetSetJobs` Set 宣言追加(1行)
- handleEntry の冒頭に message:requirement を受信した際の setBudget 発射ロジック追加(約36行)
- DRY_RUN時はログ出力のみ、本番時は `session.setBudget(AssetToken.usdc(jobFee, chainId))` を呼ぶ

---

## 本セッションで実施したこと(時系列)

### Phase A: 状況の再調査
1. v6.5bg白書の確認、計画書 Phase 0/1完了状態の確認
2. acp-cli-v2 のディレクトリ構成、agentFactory.ts、config.json、SDK README の Buyer/Seller Quick Start を読み込み
3. **重要発見**: SDK の `PrivyAlchemyEvmProviderAdapter` は signerPrivateKey または signFn を選択でき、Paymaster (Alchemy ガスsponsor) で ETH 残高ゼロでも動作する設計
4. .env と config.json の突き合わせで全 wallet を洗い出し

### Phase B: ECONOMYOS問題の発覚と方針転換
1. ユーザーが「最古の本命エージェントを卒業させたい」と希望
2. ブラウザで `0x75e65397...` (ECONOMYOS) のページ確認
3. **ACPタブなし、Runtime空、設定ボタンなし** → VP側で有効化されていない殻状態と判明
4. 戦略的妥協案として `0x840cff90...` ルートで先に1体卒業させる方針に確定

### Phase C: buyer の選定と実装
1. ユーザーから「他にも buyer がいるのでは?」との示唆
2. VP UI の My Agents 一覧をユーザーから取得 → **`neo-test-buyer-v2` (`0x11ab498c...`)** が v2 として存在することを発見
3. config.json でこの buyer の publicKey/walletId が既に揃っていることを確認
4. 残高確認: USDC 1.97(発注 197 回分)
5. buyer 用に別ディレクトリ `skills/acp-cli-v2-buyer/` を作成(node_modules等はsymlinkで共有、config.json だけ別)
6. buyer 用 config.json を作成(activeWallet=`0x11ab498c...`、jobRegistry空)
7. `buyer_test_v2.ts` を新規作成(SDK Quick Start ベース、self_evaluation、createJobByOfferingName で発注)

### Phase D: 1件テスト発注と問題発覚
1. 初回実行: `vp_sentiment_scan` の symbol enum で BTC が許可されておらず却下
2. symbol を VIRTUAL に修正 → **Job 5708 が発行成功**
3. seller側ログ確認: `New job created: 8453:5708 (provider role)` と requirement message までは到達
4. しかしジョブが進まない → seller の handleEntry を精査
5. **setBudget が呼ばれていない**ことを発見

### Phase E: setBudget 修正と動作確認
1. seller_native_v2.ts のバックアップ取得 → `.archive_deadcode_v65p/` に格納
2. import文に AssetToken 追加(str.replace)
3. handleEntry の冒頭に message:requirement → setBudget ブロック追加(str.replace)
4. budgetSetJobs Set 宣言追加(str.replace)
5. tsx 起動テスト → import OK、offerings 11件ロード OK
6. systemctl restart で本番反映
7. **再起動直後にキューに残っていた Job 5708 を即座に拾い**、`💵 Setting budget for 8453:5708: vp_sentiment_scan = $0.01 USDC` → `[DRY_RUN] Would setBudget(USDC 0.01) for 8453:5708` をログ出力。**動作確認完了**

---

## 残課題(計画書 Phase 2.2以降)

### すぐ着手できる作業
1. **DRY_RUN 解除 → Job 5708 または新規 Job で 1件本番完走**
   - DRY_RUN=false に切替 → systemctl restart
   - buyer から(または既存 Job 5708 を活用)1件処理を完走させる
   - 期待USDC消費: $0.01 + ガス代(Paymaster sponsor のはずなので実質 $0.01のみ)
2. **10件バッチ発注 → 3件連続成功を確保**
   - Phase 2.3 改訂版に従う
   - 各offeringを分散してバッチ発注
3. **動画録画準備**(Graduation 申請に必須、各 service offering ごと)
4. **Graduation Submission Form 提出**

### 中長期
- 並行作業: D3 Binance移行準備、取引戦略の継続改善
- ECONOMYOS(`0x75e65397...`)の有効化を VP に問い合わせる(`0x840cff90...` 卒業実績が出てから)

---

## 戦略的優先順位の更新

| 項目 | v6.5bg時点 | v6.5bh時点 |
|---|---|---|
| Paper勝率改善 | 75.8%(33ペア) | 引き続き重要 |
| VP Graduation優先度 | やや上昇 | **さらに上昇**(Phase 2.1まで完了、残り作業が見える形になった) |
| D3 Binance移行 | 引き続き重要 | 引き続き重要 |
| ECONOMYOS卒業 | 副次的目標 | **後回し**(`0x840cff90...` 卒業実績後に再検討) |

→ **次回セッションの主題は「Phase 2.2 = DRY_RUN解除 + 1件本番テスト」になる見込み**。本セッションで土台が整ったため、次回は数十分で完了するはず。

---

## 本セッションの変更ファイル

### 修正
- `skills/acp-cli-v2/src/seller/seller_native_v2.ts`
  - import文に `AssetToken` 追加
  - `budgetSetJobs` Set 宣言追加
  - handleEntry に message:requirement → setBudget 発射ブロック追加
  - 全行数: 350行(変更前 312行)

### 新規
- `skills/acp-cli-v2-buyer/`(buyer専用ディレクトリ)
  - `node_modules/`, `bin/`, `src/`, `package.json`, `tsconfig.json` は symlink (acp-cli-v2 から共有)
  - `config.json` は独立(activeWallet=`0x11ab498c...`, jobRegistry空)
  - `buyer_test_v2.ts` 新規作成(SDK Quick Start ベース、1件発注テスト用)

### バックアップ
- `.archive_deadcode_v65p/seller_native_v2.ts.bak_setbudget_20260504_0251`
- `.archive_deadcode_v65p/buyer_test_v2.ts.bak_20260504_0247`(symbol BTC→VIRTUAL 変更前)

### 取引ロジック関連の変更
- **なし**(claude.aiでの戦略セッションのため、本体コードには一切触れていない)

---

## ロールバック手順

このセッションで作ったものを全て元に戻す手順(必要時のみ実行):

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 1. seller_native_v2.ts を元に戻す
cp .archive_deadcode_v65p/seller_native_v2.ts.bak_setbudget_20260504_0251 \
   skills/acp-cli-v2/src/seller/seller_native_v2.ts

# 2. seller-v2 サービス再起動(DRY_RUN=true は維持)
systemctl restart neo-acp-seller-v2.service

# 3. buyer ディレクトリを削除(必要時のみ)
rm -rf skills/acp-cli-v2-buyer/
```

DRY_RUNは元から true のままなので追加の操作は不要。

---

## 自己採点詳細(8/10)

### 良かった点
- Phase 0 の白書評価を盲信せず、テスト実行で setBudget 欠落を発見できた
- ECONOMYOS の調査で「殻状態」を見抜き、戦略的妥協案にスムーズに切替えた
- ユーザーの「他にも buyer がいる」発言を真摯に受け止め、neo-test-buyer-v2 の存在に気づけた
- buyer-seller 分離設計(別ディレクトリ + 別 config.json)で seller を一切止めずに作業
- 1ファイル1変更原則をほぼ守れた(seller への変更は一括だがロジック単位)
- バックアップを毎回 `.archive_deadcode_v65p/` に格納

### 反省点
- Phase 0 で seller_native_v2.ts の handleEntry を読んでいたが「setBudget欠落」に気づけなかった。SDK READMEのSeller例と比較するという視点が抜けていた
- 序盤、ECONOMYOSの件で時間を使いすぎた(ユーザーの意向確認を早めに通すべきだった)
- buyer USDC残高確認時、最初に試したRPC(mainnet.base.org)が403を返した時にもう少し早く別RPCを試せたはず

### 次回への申し送り
- **次回セッションでまず確認すべき**: Job 5708 がまだPENDINGか、それともexpire/rejectされたか
- DRY_RUN 解除前にもう一度 seller_native_v2.ts のバックアップを取得すべき
- 本番1件成功後、Graduation条件「10件中3件連続」のためのバッチ実行は慎重に(間隔30秒以上、既存Job 5708 は10件カウントに含めるか別途判断)
- 動画録画は11 offerings 全てか申請に使う代表数件かを VP の最新申請ガイドで再確認
