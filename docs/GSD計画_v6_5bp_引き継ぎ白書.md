# GSD計画 v6.5bp 引き継ぎ白書

- 更新日時: 2026/05/06 16:50 JST (07:50 UTC)
- セッション: v6.5bp (ACP真因再々調査 + 主役切替試行 + ロールバック)
- 自己採点: 7/10 (探索が深まったが、復旧自体は未達)
- 親コミット: 0a77eb12 (v6.5bo)

## このセッションの結論 (重要)

**v6.5bo の真因仮説「acpV2AgentId v1流用が原因」は誤りだった**ことを実証で確定。
新たに浮上した3つの仮説 (cluster=OPENCLAW説、SSE接続中=2999説、v2id=None説) はいずれも
他社v2 agent 15件のデータで否定された。

## 真の原因 (最有力仮説)

`lastActiveAt: 2999-12-31` は **agent が一度も Job を完走していない・activity 蓄積がない**
ことを示す sentinel 値。frozen は症状であり原因ではない。

| 状態 | 共通点 |
|---|---|
| 正常な lastActiveAt (実時刻) | 実 Job を完走済み・activity 蓄積あり |
| 2999-12-31 (frozen) | Job 完走実績ゼロ or backend に記録されていない |

→ **正しい復旧手順は「lastActiveAtを直す」ではなく「実 Job を完走させて backend に記録させる」**。
これは v6.5bo Phase 2 (Job #6407 vp_sentiment_scan $0.01 完走) で既にやっていた方向性。
ただし Job #6407 は完走したのに backend に反映されなかった = ここが本当の謎。

## やったこと

### 探索系
1. ACP CLI/SDK ソース (agentFactory.ts, seller_native_v2.ts, agent.ts, migration.md) を精読
2. 4 agents 全部の profile API 取得
3. 他社 v2 agent 15件を browse で取得し lastActiveAt パターン解析
4. v6.5bo の comparison_table.md は実は正しかった (chains[].acpV2AgentId は配列内の入れ子)

### 操作系 (ロールバック完了)
1. config.json バックアップ → .archive_deadcode_v65p/wallet_swap_20260506_072429/
2. 旧 Neo に主役切替試行 (acp agent use → builderCode bc_mvhyux4x → systemd restart)
   - 結果: 旧 Neo も同じく lastActiveAt=2999 になり、v1ID流用説が崩壊
3. ロールバック完了 (NeoAutonomous active, builderCode=bc_agxzezgu, systemd 再起動済)

### 副次成果 (旧 Neo に追加登録した3 offerings)
旧 Neo backend に以下3個が追加された (放置可・実害なし、削除も可):
- vp_market_analysis (ID: 019dfc2f-6e86-7467-a439-e970ddb1253d)
- vp_trade_evaluation (ID: 019dfc2f-d29e-7b05-a4ee-826a49324c79)
- vp_backtest_demand (ID: 019dfc30-b0c1-740f-886f-b8fca1bc5fc7)

## 否定された仮説リスト (再発防止用)

| 仮説 | 否定根拠 |
|---|---|
| acpV2AgentId v1流用が frozen 原因 | 他社 v2id=42091 (5桁) でも正常稼働、v2id=1011 (4桁) でも frozen |
| OPENCLAW cluster/tag が frozen 原因 | OPENCLAW 持ちで正常稼働: ClawSignal/Tricky/Connectouch/Ive/NOMIAI |
| SSE 接続中 seller は 2999 になる仕様 | ClawSignal は OPENCLAW + v2id=41066 で SSE 中だが 2026-05-05 14:23 |
| v2id=None が frozen 原因 | RAIVIN-V2 は v2id=None で正常 (2026-04-21) |
| migrate コマンドで再採番できる | migrationStatus=COMPLETED で全パス弾かれる |
| backend が自然回復した | ロールバック後再び 2999-12-31 に戻ることを確認 |

## 現在のシステム状態 (v6.5bo 末と同じ)

- neo-acp-seller-v2.service: active, NeoAutonomous (0x840cff90...)
- builderCode: bc_agxzezgu (元に戻し済)
- DRY_RUN: false
- 11 offerings ロード済 (ローカル)
- backend: 6 offerings 登録 (NeoAutonomous), 6 offerings 登録 (旧 Neo)
- 取引本線 (neo-radar 等): 完全に無傷

## 残課題 (次セッションで)

優先順位:
1. **Job #6407 が backend に記録されなかった理由の解明**
   (Job #6407 の event ログを精査、indexer に拾われなかったメカニズム特定)
2. 別の test Job をもう1件発注して、backend 反映の有無を再現テスト
3. もし依然として記録されないなら、setBudget や session.submit に未知のbug があるか
4. 旧 Neo に追加登録した3 offerings の処置 (削除 or 放置)

## やってはいけないこと (継続)

- 残2ウォレットの Withdraw 試行 (凍結リスク)
- VP Registry への破壊的変更
- 取引ロジック (TrinityCouncil, neo-radar) への副作用
- DRY_RUN=true への安易な戻し

## 主戦線 (継続)

D3 Binance 移行最短日 2026/06/14 に向けた取引改善が最優先。
Paper勝率 49% → 60% × 100件 × 3ヶ月達成が事業価値として最大。
ACP 復旧は副次的タスク。

## 親コミットからの変更ファイル

- 新規: docs/GSD計画_v6_5bp_引き継ぎ白書.md (本ファイル)
- 修正なし: 全ファイル v6.5bo 末状態に復元済
- 副次バックアップ: .archive_deadcode_v65p/wallet_swap_20260506_072429/
