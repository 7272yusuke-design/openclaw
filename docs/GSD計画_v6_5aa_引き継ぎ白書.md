# 📐 GSD計画 v6.5aa 引き継ぎ白書

> **更新日時**: 2026/04/02 13:30 JST
> **セッション**: v6.5aa（Task 3.3 BTC/ETHペーパートレード開始セッション）
> **自己採点**: 92/100（Task 3.3全完了、Phase 3完了）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続（VP銘柄のみの実績） |
| Tier0勝率 | 0%（BTC/ETH取引開始待ち — 初回BTC Council完了→WAIT判断） |
| USDC | $87,979.91 |
| Holdings | なし |
| サービス | 全4サービス稼働中 |
| CFO L4 | ドローダウンブロック発動中（HWM $88,494） |
| Council | 2hローテーション: BTC → VIRTUAL → ETH → AIXBT（タイムスタンプベース） |

---

## ✅ 本セッション完了タスク

### Task 3.3a: 定期Councilタイムスタンプ化
- **旧**: cycle_count modulo方式（リスタートでリセット → Tier0未発火バグ）
- **新**: Blackboardに`last_unified_council_ts`を永続保存、2時間経過で発火
- 2a（Tier0）と2b（Tier1）を統合、BTC→VIRTUAL→ETH→AIXBTローテーション
- `UNIFIED_COUNCIL_INTERVAL_SEC = 7200`（旧: PERIODIC_COUNCIL_INTERVAL / TIER0_COUNCIL_INTERVAL 削除）

### Task 3.3b: BTC/ETH価格取得ローカルDB優先
- `check_tp_sl_all_positions()`（run_trigger.py）: BTC/ETHは`get_latest_price_from_db()`優先
- `trinity_council.py` Phase 1b: 同様にローカルDB優先
- CoinGecko APIレート制限回避 + 高速化

### Task 3.3c: 戦略別出口プロファイル
- `core/config.py` に `EXIT_PROFILES` / `STRATEGY_TO_EXIT_PROFILE` 追加
- 3カテゴリ: mean_reversion / trend_follow / evolved
  - mean_reversion: SL -5%, Trail +5%開始/-2.5%利確, Hard TP +14%, 時間 96h
  - trend_follow: SL -8%, Trail +10%開始/-4%利確, Hard TP +30%, 時間 336h（2週間）
  - evolved: trend_followと同一パラメータ
- `trinity_council.py`: BUY実行時に`strategy_tag`/`exit_profile`をholdingsに保存
- `run_trigger.py`: check_tp_slがexit_profileからパラメータ読み込み

### Task 3.3d: Tier別勝率カウント
- `performance_evaluator.py`: closed tradesをTier0/Tier1別に集計
- Blackboard `performance_summary` に `tier0_accuracy`/`tier1_accuracy` 追加
- 実取引移行条件はTier0勝率60%×3ヶ月で判定

---

## ⏭️ 次セッションの作業

### 短期（次回）
1. **2時間ローテーション観測**: BTC→VIRTUAL→ETH→AIXBT が正しく発火するか確認（数サイクル分のログ検証）
2. **BTC/ETH初BUY発生の確認**: Councilが実際にBUY判断を出したとき、strategy_tagが正しく保存されるか
3. **CFR急変時のポジション調整（Step 2設計）**: CFRレジーム急変時にexit_profileの動的上書き機能

### 中期
4. **Phase 4: 実取引エンジン（Binance Spot API）** — `tools/cex_executor.py` 新設
5. **Phase 5: 少額実取引** — $50テスト → 段階的引き上げ

### 設計メモ（将来のCFRポジション調整）
- CFR実行 → レジーム急変検知（Risk-On→Risk-Off）
- 保有ポジションのexit_profileを動的に引き締め（SL幅縮小 or 強制売却）
- config.pyのEXIT_PROFILESに`macro_override`キーを追加する設計で拡張可能

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `run_trigger.py` | 2a+2b統合→タイムスタンプベース2hローテーション、check_tp_sl戦略別プロファイル化、BTC/ETH価格ローカルDB優先 |
| `agents/trinity_council.py` | BTC/ETH価格ローカルDB優先、BUY時strategy_tag/exit_profile保存 |
| `core/config.py` | EXIT_PROFILES/STRATEGY_TO_EXIT_PROFILE/EXIT_PROFILE_DEFAULT追加 |
| `orchestration/performance_evaluator.py` | Tier別勝率カウント追加 |

---

## 🔧 システム構成（変更点のみ）
```
[neo-radar.service] — 変更あり
  2時間ごと → 統合Council召集（BTC→VIRTUAL→ETH→AIXBT ローテーション）
  ※旧: Tier0 cycle_count+240 / Tier1 cycle_count%480 → 廃止
  Blackboard "last_unified_council_ts" でリスタート耐性

[check_tp_sl] — 変更あり
  ポジションのexit_profileから戦略別SL/TP/時間上限を読み込み
  BTC/ETH: ローカルDB価格優先（Binance蓄積5分足）

[Phase 5 BUY] — 変更あり
  BUY後にholdings[symbol]["strategy_tag"]/["exit_profile"]を保存
```

---

## 📚 出口プロファイル一覧（config.py）

| カテゴリ | 戦略 | SL | Trail開始 | Trail幅 | Hard TP | 時間上限 |
|---|---|---|---|---|---|---|
| mean_reversion | rsi_bounce, bb_reversal, mean_reversion | -5% | +5% | -2.5% | +14% | 96h |
| trend_follow | macd_cross, ema_trend, momentum_breakout, vp_momentum, alpha_strategy | -8% | +10% | -4% | +30% | 2週間 |
| evolved | gplearn_evolved | -8% | +10% | -4% | +30% | 2週間 |
