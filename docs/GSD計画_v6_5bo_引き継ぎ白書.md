# GSD計画 v6.5bo 引き継ぎ白書

- 更新日時: 2026/05/06 16:00 JST
- セッション: v6.5bo (VP/ACP問題の真因再調査)
- 自己採点: 9/10
- 親コミット: 957e1157 (v6.5bn) からの追加調査セッション

## このセッションの主題

claude.ai セッションで「Issue #82レス待ちで何もできない」と即時判断したのを覆し、ユーザーから「過去のことを疑って再調査せよ」の指示を受けて深掘り。
結果、ACP backend のデータ不整合 (migrationStatus=COMPLETED でありながら lastActiveAt=2999、acpV2AgentId=41437=v1流用) が真因と確定。

## 達成したこと

- API直叩きで seller (broken) と buyer (working) の profile 比較完了
- `acp agent migrate --complete` 試行 (COMPLETED で弾かれて書き込みなし、安全)
- `acp agent update` で description 1文字変更 → updatedAt 更新成功、lastActiveAt は frozen のまま
- Issue #82 への追加投稿用 comparison_table.md 生成
- snapshot保存: .archive_deadcode_v65p/profile_snapshot_20260506/{before_update,after_update,buyer_profile}.json

## 副次発見

- ACP backend 上の seller offerings は 6個 (ローカル 11個との差5個は未登録)
- Builder Code (bc_agxzezgu) が seller profile レコードに反映されていない (buyer には bc_zwlc4yf7 が登録されている)
- v6.5bn で agentFactory.ts に追加した builderCode はトランザクション送信時の dataSuffix のみで、profile API レコードには別途登録が必要だった可能性

## 残課題 (次セッションで)

優先順位:
1. Issue #82 に comparison_table.md の内容をコメント追加 (公式の動きを促す)
2. 24h後 lastActiveAt の自然回復を再確認
3. 残5 offerings の `acp offering create` 試行 (graduation_boost / graduation_complete / vp_correlation_risk / vp_market_intelligence / vp_whale_alert)
4. Builder Code を profile API で正式登録できるか調査 (acp agent コマンド一覧を再確認)

## やってはいけないこと (継続)

- 残2ウォレットの Withdraw 試行 (凍結リスク)
- VP Registry への破壊的変更 (現在のIssue #82文脈で証拠が変わる)
- 取引ロジック (TrinityCouncil, neo-radar) への副作用

## 主戦線

D3 Binance 移行最短日 2026/06/14 に向けた取引改善が依然として最優先。
本セッションは「ACP問題の証拠固め」が完了したことで、以後 ACP は完全に Issue #82 待ちに移行可能。

