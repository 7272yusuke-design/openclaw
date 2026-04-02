# 📐 GSD計画 v6.5z 引き継ぎ白書

> **更新日時**: 2026/04/02 12:30 JST
> **セッション**: v6.5z（BTC/ETH移行実装セッション）
> **自己採点**: 95/100（Phase1+2完了、Phase3の3.1+3.2完了、残りTask3.3のみ）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続 |
| USDC | $87,979.91 |
| Holdings | なし（AIXBT SL発火で全ポジション解消済み） |
| サービス | 全4サービス稼働中 |
| CFO L4 | ドローダウンブロック発動中（HWM $88,494） |
| Capital Flow | Score +14.04 / Neutral（Extreme Fear逆張り+VIX下落 vs ゴールド急騰） |

---

## ✅ 本セッション完了タスク

### Phase 1: データ基盤 — 全完了
- **Task 1.1+1.2**: Binance OHLCV+ティック取得関数を`data_collector.py`に追加。BTC/ETH 5分ティック+1h足OHLCV自動収集。`COLLECT_SYMBOLS`にBTC/ETH追加
- **Task 1.3**: `fetch_btc_trend()` CoinGecko→Binance API切替（klines 1d足+24hrティッカー）
- **Task 1.4**: `fetch_ohlcv_binance()` 新設 + `fetch_ohlcv_custom()` BTC/ETHフォールバック追加（LocalDB→Binance→CoinGecko）
- **Task 1.5**: 30日バックフィル完了（BTC 720本、ETH 720本）

### Phase 2: Capital Flow Radar — 全完了
- **Task 2.1**: `tools/capital_flow_radar.py` 新規作成。yfinance(VIX/DXY/S&P500/10Y/Gold) + alternative.me(F&G) + CoinGecko(/global)。重み付けz-score→-100〜+100スコア+レジーム判定
- **Task 2.2**: `run_trigger.py` CFR_INTERVAL=720（6時間サイクル）で自動実行
- **Task 2.3**: `trinity_council.py` Phase 4bスコアリングにマクロスコア注入（>=+50:+5, >=+20:+2, <=-20:-5, <=-50:-10）

### Phase 3: Council再編 — 3.1+3.2完了
- **Task 3.1**: `config.py` TIER0_SYMBOLS=[BTC,ETH]追加、COUNCIL_ELIGIBLE=TIER0+TIER1。`run_trigger.py` Tier0定期Council（4hサイクル、240オフセット→Tier0とTier1が2時間おきに交互召集）
- **Task 3.2**: バックテスト検証完了（BTC: 3/9有効 MED、ETH: 5/9有効 HIGH）

---

## ⏭️ 次セッションの作業（Task 3.3）

### Task 3.3: BTC/ETHペーパートレード開始
- PaperWalletがBTC/ETHポジションを管理できるか確認
- **勝率カウント**: BTC/ETH切替日からリセットするかどうかの判断
  - 現行勝率57.1%はVP銘柄のもの。BTC/ETH追加で混在する問題あり
  - 選択肢A: 全銘柄統合のまま（シンプルだが成績が混在）
  - 選択肢B: Tier0/Tier1別に勝率カウント（将来の実取引移行条件判定に有用）
- 学習モード: BTC/ETH用に新たにカウント開始するか検討
- **重要**: Council召集がBTC/ETHで初めて発火するのを確認（次の2hオフセットサイクル）

### その後: Phase 4（実取引エンジン）, Phase 5（少額実取引）
- 計画書参照: `docs/GSD計画_Phase1_BTC_ETH移行計画.md`

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `orchestration/data_collector.py` | +Binance関数3つ(ticks/ohlcv/backfill)+mainループ統合 |
| `tools/market_data.py` | fetch_btc_trend Binance化 + fetch_ohlcv_binance新設 |
| `tools/capital_flow_radar.py` | **新規** マクロ資金フロー分析モジュール |
| `vault/blackboard/macro_flow.json` | CFR出力（6hごと自動更新） |
| `run_trigger.py` | CFR 6hサイクル + Tier0 Council 4hサイクル(240 offset) |
| `agents/trinity_council.py` | Phase 4b マクロスコア注入 |
| `core/config.py` | TIER0_SYMBOLS + COUNCIL_ELIGIBLE拡張 |
| `docs/GSD計画_Phase1_BTC_ETH移行計画.md` | v3更新（進捗マーク+参考リポジトリURL確定） |

---

## 🔧 システム構成（変更点のみ）
```
[neo-collector.service] — 変更あり
  5分ごと → VIRTUAL/AIXBT/LUNA/BTC/ETH をDexScreener+Binanceから取得
  60分ごと → GeckoTerminal OHLCV + Binance 1h足OHLCV
  起動時   → BTC/ETH 30日バックフィル（既存データあればスキップ）

[neo-radar.service] — 変更あり
  6時間ごと → Capital Flow Radar（マクロ7指標）
  2時間おき → Council召集（Tier0 BTC/ETH ↔ Tier1 VIRTUAL/AIXBT 交互）

[Phase 4b スコアリング] — 変更あり
  既存項目 + cfr項目（macro_flow.json読み込み）
```

---

## 📚 参考リポジトリ（実際に参照・確認済み）

| 目的 | URL | 使用箇所 |
|---|---|---|
| マクロ指標統合 | https://github.com/shashankvemuri/economic-dashboard | CFR設計（指標ごと独立取得パターン） |
| HMMレジーム判定 | https://github.com/Poulami-Nandi/RegimeDetectionHMM | features.py参照（将来HMM化用） |
| F&G蓄積 | https://github.com/tomkenig/Application-Fear-and-greed-index-data | API取得パターン |
| 相関計算 | https://github.com/ranaroussi/quantstats | Rolling Correlation（将来） |
| HMM補助 | https://github.com/dhruvbelawat21/Market-Regime-Detection-Using-Hidden-Markov-Models | レジーム分類参考 |
| クロスアセット | https://github.com/Swiss-MQP-2022/Intermarket-ML-For-EMH | 跨資産分析フロー |
| 債券追跡 | https://github.com/DanTCIM/TreasuryYieldTracker | yfinance金利モジュール |
