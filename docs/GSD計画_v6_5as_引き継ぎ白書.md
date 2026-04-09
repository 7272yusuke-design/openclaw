# 📐 GSD計画 v6.5as 引き継ぎ白書

> **更新日時**: 2026/04/09 16:00 JST
> **セッション**: v6.5as（AI主導化・SELL根拠実装・N.1削除・出口パラメータ動的化）
> **自己採点**: 80/100（AI主導化の大幅改善。効果は次セッション以降で検証）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(Evaluator) | **43.75%（32件決済）** ← 目標60%を大幅下回る |
| USDC | $48,446 |
| Holdings | BTC(0.1177/long) / VIRTUAL(19745/mid) / ETH(7.4574/short) |
| サービス | 全4サービス稼働中 |
| L4 DD | 6.26% — ⚠️ 上限8%に接近 |
| Council | 1hローテーション: BTC → VIRTUAL → ETH |
| Moltbook | karma=97, followers=13 |

### ⚠️ 勝率急落の原因（v6.5ar→as間で判明）
- **利小損大**: 勝ち+1.6〜2.4%(RSI Exit) vs 負け-1.8〜3.9%(Bear Stage/SL)
- RSI Exit閾値(mid=72)が低すぎ → AI戦略のbull_stageに到達する前に利確
- 本セッションで根本修正済み（効果検証は次セッション）

---

## ✅ 本セッション完了タスク

### バグ修正（3件）

#### Task 1: SELL根拠+sell_tracker.json書き込み実装
- **問題**: v6.5arで設計されたSELL根拠ログとsell_tracker.json書き込みが未実装だった
- **修正**: SELL成功後に`[SELL根拠]`ログ出力+`vault/sell_tracker.json`に書き込み
- 変数未定義バグも同時修正（`rsi_val`/`_btc_24h_change`がスコープ外）

#### Task 2: Discord SELL報告の未定義変数修正
- **問題**: `_sell_ctx_ec`/`_sell_ctx_rsi`/`_sell_ctx_thesis`が未定義で毎回exceptで握りつぶし
- **修正**: スナップショット変数（`_rsi_snap`/`_entry_ctx`等）に統一

#### Task 3: N.1ペアトレード削除
- **問題**: AIXBT除外済みでペア崩壊（相関0.5-0.6）、ロングオンリーでペアトレード不適、ノイズ源
- **修正**: `research/n1_pair_trade.py`をarchive移動、trinity_councilから全参照除去（Phase 1-P/Phase 4bスコアリング/報告）

### AI主導化（5件）

#### Task 4: RSI Exit改善
- **問題**: 含み益1.5%+RSI>72で一律利確 → AIのbull_stage(例:+4%半利確)に到達する前に売却
- **修正**: AI戦略のbull_stage1のtrigger_pct未到達ならRSI Exit発火しない。最低利益条件3%
- RSI閾値引上げ: short 65→75、mid 72→78

#### Task 5: 出口パラメータ動的化
- **問題**: rsi_exit/trailing_start/trailing_dropがconfig固定値。全トレード一律
- **修正**: Phase 3b戦略書JSONに`exit_params`フィールド追加。AIが相場ボラ・timeframeに応じて指定。config値はフォールバック
- run_trigger.pyでentry_context.exit_profileのAI値を優先使用

#### Task 6: exit_profile決定のAI主導化
- **問題**: `STRATEGY_TO_EXIT_PROFILE`が戦略名→profile固定マッピング。AIが`thesis_timeframe: short`と判断しても`atr_breakout→mid`で上書き
- **修正**: AIのthesis_timeframe(short/mid/long)を優先、STRATEGY_TO_EXIT_PROFILEはフォールバック

#### Task 7: AIポジションサイズ
- **問題**: confidence→%の固定ブラケット(50-59→3%等)。AIが相場判断してもサイズに反映されない
- **修正**: Phase 3b戦略書に`position_size_pct`(1-15%)追加。AIが確信度・ボラ・RR比から推奨。ハードキャップ15%は安全装置として維持。AI値がない場合は従来ブラケットにフォールバック

---

## ⏭️ 次セッションの作業

### 最優先 — 本セッション修正の効果検証
1. 新規BUYログで「📐 AI推奨サイズ: X%」が出るか
2. exit_profileがAI timeframeで決まっているか（ログ確認）
3. entry_context.exit_profileにAI指定rsi_exit値が入っているか
4. RSI Exitが`min_profit`条件で抑制されたログがあるか
5. `grep "SELL根拠" radar_output.log` — ログ出力されるか
6. `cat vault/sell_tracker.json` — 追跡データ書き込みされるか
7. Discord SELL通知にRSI/BTC24h/保有時間/戦略が表示されるか

### 重要
8. 勝率・RR比の推移（利小損大パターン改善の確認）
9. sell_tracker.jsonの蓄積データを使った売却判断パターン分析
10. Verification失敗原因分析（デバッグログ確認）

### 検証待ち（v6.5arから継続）
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
| run_trigger.py | SELL根拠スナップショット+sell_tracker.json書き込み / Discord SELL報告変数修正 / RSI Exit改善(min_profit+bull_stage連動) / AI出口パラメータ優先使用 |
| agents/trinity_council.py | N.1全参照除去 / Phase 3bにexit_params+position_size_pct追加 / exit_profileをAI timeframe優先 / AIポジションサイズ / AI出口パラメータをentry_contextに保存 |
| core/config.py | RSI閾値引上げ(short 65→75, mid 72→78) |
| research/n1_pair_trade.py | → .archive_deadcode_v65p/に移動 |

---

## 🧬 AI主導化の現在地

| 判断項目 | v6.5ar以前 | v6.5as以降 |
|---|---|---|
| BUY/SELL判断 | ✅ AI（Council三者協議） | 変更なし |
| 戦略thesis/シナリオ | ✅ AI（Phase 3b） | 変更なし |
| exit_stages(段階売却) | ✅ AI（Phase 3b） | 変更なし |
| SL/TP価格 | ✅ AI（ATR基準） | 変更なし |
| **exit_profile** | ❌ 戦略名→固定マッピング | ✅ AI thesis_timeframe優先 |
| **RSI Exit閾値** | ❌ config固定(65/72) | ✅ AI exit_params指定 |
| **トレーリング開始/幅** | ❌ config固定 | ✅ AI exit_params指定 |
| **ポジションサイズ** | ❌ conf→%固定ブラケット | ✅ AI推奨(キャップ15%) |
| RSI Exit発火条件 | ❌ 含み益1.5%で一律 | ✅ AI bull_stage1連動(最低3%) |
| F2/F2b BTC急落閾値 | ❌ 固定(-5/-8/-12%) | 固定のまま（安全装置） |
| Phase 4bスコアリング基点 | ❌ 固定(base=50) | 固定のまま（基準点） |
| CostGuard L1-L4 | ❌ 固定 | 固定のまま（安全装置） |

---

## 🛡️ リスクヘッジ全レイヤー

| 検知対象 | 仕組み | 頻度 | 備考 |
|---|---|---|---|
| BTC急落 | F2（L1-L3） | 30秒 | 固定閾値（安全装置） |
| マクロ急変 | F2b（L1-L3） | 30分 | 固定閾値（安全装置） |
| 戦略書exit_stages | Phase 0第0層 | 30秒 | AI設計 |
| ポジション個別 | Phase 0 5層出口 | 30秒 | AI出口パラメータ反映 |
| 二重発火防止 | _sell_cooldown 5分 | 30秒 | |
| 戦略前提崩壊 | Phase S invalidation | 30秒 | AI設計 |
| ポートフォリオ全体 | CostGuard L1-L4 | Council時 | 固定（安全装置） |
| ポートフォリオ集中 | Phase 5ガード6段 | BUY時 | |
| ポジションサイズ | ハードキャップ15% | BUY時 | AI推奨+キャップ |
| OOMリスク | Swap 2GB | 常時 | |
