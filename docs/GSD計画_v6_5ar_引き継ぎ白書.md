# 📐 GSD計画 v6.5ar 引き継ぎ白書

> **更新日時**: 2026/04/08 11:00 JST
> **セッション**: v6.5ar（二重発火修正・売却根拠充実・Moltbook karma復旧・Swap追加）
> **自己採点**: 85/100（安全性・可観測性の大幅改善。効果検証は次セッション）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | リセット後 **55.6%**（9ペア決済） |
| USDC | $61,472 |
| Holdings | BTC(0.1177) / ETH(5.8726) / VIRTUAL(6425) |
| サービス | 全4サービス稼働中 |
| CFO L4 | DD4.87% — ✅ OK |
| Council | **1h**ローテーション: BTC → VIRTUAL → ETH |
| Swap | **2GB追加済み**（OOM防止） |
| Moltbook | karma=97, followers=13 |

---

## ✅ 本セッション完了タスク

### Task 1: 二重発火防止（P0）
- **問題**: Exit Stage(sell 50%)発火後、30秒後にRSI Exitで同ポジション再発火
- **原因**: `check_tp_sl_all_positions`にシンボル別冷却がなかった
- **修正**: `_sell_cooldown`辞書でシンボル別5分冷却。SELL成功後にセット、ループ先頭でチェック

### Task 2: 売却根拠スナップショット（P1）
- **問題**: SELL時のログが「RSI=79.8, +2.0%」だけで市場コンテキストなし
- **修正**: 全SELL時に`[SELL根拠]`ログ出力（RSI遷移・BTC24h・保有時間・戦略thesis・entry_conf）
- `vault/sell_tracker.json`に売却記録を保存

### Task 3: 売却後価格追跡（P1）
- **問題**: 「売った後に上がった/下がった」の学習がなかった
- **修正**: `check_sell_aftermath()`関数を新設。1h/6h/24h後に現在価格を取得し「正解/早すぎ/中立」判定をログ出力
- メインループの0-pre位置で毎サイクル実行（軽量）

### Task 4: Phase 3bシナリオ具体性制約（P2）
- **問題**: bull/bear narrativeが「底値圏で反発」等の抽象表現ばかり
- **修正**: プロンプトに具体性ルール追加
  - narrative内に数値2つ以上必須
  - 抽象表現禁止（例を明記）
  - evidence形式「データソース:値→解釈」必須
  - bull/bearは対立する具体的条件で記述

### Task 5: Moltbook karma追跡（P3）
- **問題**: karma取得コードがなかった
- **修正**: `post()`メソッドのレスポンスから`author.karma`をログ出力
- 動作確認済み: karma=97, followers=13

### Task 6: Moltbook verification失敗デバッグ（A）
- **問題**: verification失敗率18%（81成功/18失敗）だがエラー内容が空
- **修正**: moltbook_tool.py/moltbook_engager.pyにchallenge内容と回答のデバッグログ追加
- 次の失敗時に原因特定可能

### Task 7: Nightly moltbook tracker復旧（B）
- **問題**: `data/moltbook_stats.json`が3/30で更新停止。nightlyでrun_tracking()が呼ばれていなかった
- **修正**: nightly Step 7bの前に`run_tracking()`呼び出しを追加
- Discordレポートが最新データを反映するように

### Task 8: Discord SELL報告に売却根拠表示（D）
- **問題**: SELL時のDiscord通知がstatus行のみ
- **修正**: RSI遷移・BTC24h・保有時間・confidence・戦略thesisをstatus欄に追記

### Task 9: ハートビートVIRTUAL表示修正
- **問題**: ハートビートにBTC/ETHのみ表示、VIRTUALが欠落
- **原因**: GeckoTerminal失敗時にexcept:passで無言スキップ
- **修正**: BTC/ETHはローカルDB優先、VIRTUALはGeckoTerminal→fetch_token_dataフォールバック

### Task 10: Swap 2GB追加
- **問題**: メモリ7.8GB中4.2GB使用、Swap 0 → OOM killer直撃リスク
- **修正**: `/swapfile` 2GB作成・fstab登録済み

---

## ⏭️ 次セッションの作業

### 最優先 — 本セッション修正の効果検証
1. `grep "SELL根拠" radar_output.log | tail -5` → 市場コンテキスト付きか
2. `grep "売却追跡" radar_output.log | tail -5` → 1h/6h/24h判定出るか
3. `cat vault/sell_tracker.json | python3 -m json.tool | tail -20` → 追跡データ蓄積確認
4. `grep "📊 VIRTUAL" radar_output.log | tail -3` → ハートビートVIRTUAL表示
5. Phase 3b戦略書のnarrative/evidenceが具体的数値入りか確認
6. `grep "🧮 Challenge\|🧮 Answer" radar_output.log | tail -10` → verification失敗原因特定
7. `cat data/moltbook_stats.json | python3 -m json.tool | tail -20` → nightly tracker更新確認

### 重要
8. Verification失敗原因に基づく修正（デバッグログ分析後）
9. 勝率改善分析（決済ペア蓄積後）
10. sell_tracker.jsonの蓄積データを使った売却判断パターン分析

### 検証待ち（v6.5aqから継続）
11. S2/S3: 戦略書モニタリング・動的出口の動作確認
12. E1検証: SL発火でscenario_outcome+strategy_quality_score確認
13. exit_stages: 部分売却後のcompleted_stages永続化確認

### 短期
14. パターンマイニング（50件蓄積後）
15. VP/Graduation: Discord返答確認
16. E3拡張: 戦略パターンルール自動生成

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| run_trigger.py | 二重発火防止(_sell_cooldown) / 売却根拠スナップショット+sell_tracker.json / check_sell_aftermath()追跡関数 / Discord SELL根拠表示 / ハートビートVIRTUAL修正 / Nightly tracker呼び出し |
| agents/trinity_council.py | Phase 3b: シナリオ具体性ルール追加 |
| tools/moltbook_tool.py | karma追跡ログ + verification デバッグログ |
| tools/moltbook_engager.py | verification デバッグログ |
| /swapfile | 2GB Swap追加（fstab登録済み） |

---

## 📢 Discord報告体系（SELL報告改善）

| 報告 | タイミング | 内容 |
|---|---|---|
| Council Minutes | BUY/SELL時 | 市況+ポジション+戦略書+スコアリング内訳+判断+取引結果+出口プロファイル |
| **SELL Alert** | **SELL時** | **RSI遷移・BTC24h・保有時間・confidence・戦略thesis（v6.5ar追加）** |
| Performance Dashboard | 6h毎 | 勝率+Tier別+ポートフォリオ+直近決済5件 |
| Nightly Batch Report | JST 02:00 | 自己進化日報 |
| Moltbook活動レポート | JST 02:00 | **karma推移（tracker復旧）**+エンゲージメント |

---

## 🛡️ リスクヘッジ全レイヤー（二重発火防止追加）

| 検知対象 | 仕組み | 頻度 | 対応速度 |
|---|---|---|---|
| BTC急落 | F2（L1-L3） | 30秒 | 即時 |
| マクロ急変（SPY/Gold） | F2b（L1-L3） | 30分 | 先回り |
| マクロ環境悪化 | F5 capital_flow_phase | 1h | Council時 |
| 戦略書exit_stages | Phase 0第0層 | 30秒 | 即時 |
| ポジション個別 | Phase 0 5層出口 | 30秒 | 即時 |
| **二重発火防止** | **_sell_cooldown 5分** | **30秒** | **即時** |
| 戦略前提崩壊 | Phase S invalidation | 30秒 | 即時 |
| ポートフォリオ全体 | CostGuard L1-L4 | Council時 | 1h |
| ポートフォリオ集中 | Phase 5ガード6段 | BUY時 | 即時 |
| **OOMリスク** | **Swap 2GB** | **常時** | **自動** |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152+件 | 構造化済み |
| voyager_skill | 42件 | データ不足待機中 |
| evolver_rule | 36件 | データ不足待機中 |
| sell_tracker | **新設** | 売却後1h/6h/24h追跡 |
| moltbook_stats | **復旧** | nightly自動更新 |
| gplearn | 動作中 | VIRTUAL/AIXBT |
