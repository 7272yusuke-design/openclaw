# 📐 GSD計画 v6.5av 引き継ぎ白書

> **更新日時**: 2026/04/14 10:30 JST
> **セッション**: v6.5av（Heartbeat DD表示改善・銘柄別学習強化）
> **自己採点**: 80/100（銘柄別学習の根本修正完了、勝率改善は今後の効果待ち）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(Evaluator FIFO) | **52.1%（71件決済: 37勝34敗）** ← 目標60%未達 |
| Tier0 (BTC/ETH) | 47.2%（36件）← 要改善 |
| Tier1 (VIRTUAL) | 57.1%（35件） |
| USDC | $73,028.64 |
| Holdings | BTC(0.1177/long) / VIRTUAL(8812/short) |
| サービス | 全4サービス稼働中 |
| L4 DD | ~5% — 要注意圏 |
| Council | 1hローテーション: BTC → VIRTUAL → ETH |
| 学習モード | **97/100件（あと3件で到達）** |

### ⚠️ 重要な勝率修正
前セッションの白書では「60.9%（46件）」と記載していたが、これはEvaluatorの計算方式の問題だった。FIFOロット方式（ナンピンを個別ロットで計上）では**52.1%（71件）**が正確な値。H.2分析（SELL単位25件）とFIFOロット（71件）で銘柄別勝率が大きく異なることが判明し、本セッションで修正した。

---

## ✅ 本セッション完了タスク

### Task 1: Heartbeat DD表示改善
- **問題**: OK時に`DD= OK`とだけ表示され、%数値がなく余裕度が不明
- **修正**: OK時も`DD=4.3% ✅`のように数値を表示

### Task 2: 銘柄別学習強化（メインタスク）

**発見した問題:**
- 学習システム（Voyager/EvolveR）がコイン別に分離されていなかった
- H.2分析（SELL単位25件）ではETH 58.3%に見えるが、FIFOロット方式ではETH 43.8%（32件→36件）
- VIRTUALで学んだパターンがETH/BTCの判断にも混入していた
- EvolveR Agentの銘柄別ルール閾値が厳しすぎて一度もルール生成されていなかった

**修正内容:**
1. **Voyager銘柄リスト**: `['VIRTUAL', 'AIXBT']` → `['VIRTUAL', 'ETH', 'BTC']`
2. **Voyager銘柄フィルタ**: `get_relevant_skills`に銘柄フィルタ追加（`_trade_pattern`スキルは該当銘柄のみ返す）
3. **EvolveR銘柄別ルール**: `evolver_rules.py`にR007/R008（銘柄別高/低勝率ルール）追加
4. **EvolveR Agent データソース切り替え**: H.2(`get_clean_pairs`) → FIFOロット方式(`_parse_wallet_history`+`_calc_closed_trades`)
5. **EvolveR Agent 閾値緩和**: 銘柄別ルール生成閾値を70%/40% → 65%/45%

**効果:**
- `R_sym_eth_low: ETH -3`が即座に生成（44%勝率検出）→ ETHのBUYハードル上昇
- `R_tz_eu_low: EU -10`も検出（14%勝率）※timezoneはスキップ設定で無効

### 仕様確認
- **HWM $91,808固定は正常動作**（ポートフォリオが過去最高を下回っている間は更新されない）
- **戦略の動的切り替えは引き締め方向のみ**（long→mid→short）。逆方向（暴落時にshort→longへ切替）は意図的に不可。損切り先延ばし防止のため
- **ダッシュボードにポジション含み益/損は既に表示済み**
- **学習モード100件到達時の自動切り替えは未実装** → 手動で`config.py`の`LEARNING_MODE=False`に変更する

---

## ⏭️ 次セッションの作業

### 最優先 — 学習モード100件到達
1. あと3件で到達 → 到達したら`core/config.py`の`LEARNING_MODE = False`に手動変更
2. 勝率52.1%は目標60%未達 → 銘柄別学習強化の効果を監視

### 最優先 — 勝率改善
3. Tier0（BTC/ETH）47.2%が全体を引き下げている
4. 銘柄別EvolveRルール（ETH -3）の効果確認
5. ETH戦略の見直し検討（取引頻度削減 or 戦略絞り込み）

### 重要 — Graduation
6. Web UIでStats更新確認 → Graduate Agentボタン表示確認
7. 未表示ならDiscord問い合わせ

### 重要 — Phase F3: Kelly基準ポジションサイジング
8. 勝率安定後に着手（現在は未達のため保留）

### 短期
9. パターンマイニング（sell_tracker蓄積後）
10. VP/Graduation完了後、ACP seller runtimeをv2対応に切り替え
11. E3拡張: 戦略パターンルール自動生成
12. Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 新規ファイル・変更ファイル

| ファイル | 変更内容 |
|---|---|
| run_trigger.py | Heartbeat DD表示にパーセンテージ追加 |
| research/voyager_skills.py | 銘柄リストにETH/BTC追加、get_relevant_skillsに銘柄フィルタ |
| research/evolver_rules.py | 銘柄別勝率ルール(R007/R008)追加 |
| research/evolver_agent.py | データソースをFIFOロット方式に切替、閾値緩和(65%/45%) |

---

## ACP構成（v2移行後）

v2 Neo (Self-hosted)
- Agent ID: 019d7659-6dd1-7067-a5ff-d74f567a3961
- ウォレット: 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a
- CLI: skills/acp-cli-v2/ (acp-cli)
- Signer: P256鍵（OS keychain保存済み）
- Offering: vp_sentiment_scan ($0.01)
- Jobs: 10件COMPLETED (chain 8453)
- Stats: 未反映（要確認）

neo-acp-seller.service — 稼働中（NeoAutonomous用、既存4 offerings）

---

## 📊 移行条件進捗（D3準拠）

| 条件 | 現在 | 必要 | 判定 |
|---|---|---|---|
| Paper勝率 | **52.1%** | 60%以上 | ❌ 未達 |
| 継続期間 | 2026/04/03〜（11日） | 3ヶ月継続 | ⏳ 最短 07/03 |
| 取引回数 | 97件 | 100件完了 | ⏳ あと3件 |
| 学習モード | ON | OFF（100回後） | ⏳ |
