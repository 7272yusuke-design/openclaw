# 📐 GSD計画: BTC/ETH移行 + マクロ分析 + 実取引準備

> **作成日**: 2026/04/02
> **最終更新**: 2026/04/02 v3（Phase1+2完了、Phase3途中）
> **ステータス**: Phase 3 Task 3.3 着手前
> **目的**: Neoの分析能力を最大活用できる市場(BTC/ETH)へ主戦場を移行し、実取引を目指す

---

## 背景

VP銘柄(VIRTUAL/AIXBT)は時価総額が小さく、大口売買に支配されるためNeoの9戦略バックテスト・
gplearn・FinBERTセンチメント等の分析能力が活きない。BTC/ETHはデータ量・流動性・パターンの
統計的有意性が桁違いに優れており、Neoの強みを最大限発揮できる。

併せてマクロ資金フロー分析（Capital Flow Radar）を導入し、株式→暗号資産等の
資金ローテーションを先読みする能力を追加する。

**「お盆の上のビー玉」理論**: 資金は株式・債券・不動産・暗号資産等の間を移動する。
株式下落→暗号資産への資金流入等のパターンを先読みするための機能。

---

## データソース方針（重要決定事項）

| 銘柄 | データソース | 理由 |
|---|---|---|
| **BTC/ETH** | **Binance API** | 無料・APIキー不要・1分足〜日足対応・数年分の履歴・将来の実取引と一致 |
| VP銘柄 | DexScreener + GeckoTerminal | DEX専用トークンのため変更なし |
| マクロ指標 | **yfinance + alternative.me + CoinGecko /global** | 軽量・APIキー不要・信頼性高い |

**却下**: OpenBB（依存関係が重い）、ccxt（Binance直接の方がシンプル）、Glassnode（有料）

---

## Tier構成の変更

| Tier | 変更前 | 変更後 | 監視頻度 | 取引対象 |
|---|---|---|---|---|
| **Tier0（新設）** | — | **BTC, ETH** | 常時（Binance 1時間OHLCV + 5分ティック） | ✅ メイン |
| **Tier1（縮小）** | VIRTUAL, AIXBT | VIRTUAL, AIXBT | 5分ティック（既存） | 段階的縮小 |
| **Tier2** | LUNA | LUNA（監視のみ） | 60分 | ❌ |
| **Tier3** | ETH, SOL, BNB | SOL, BNB | 日次Sweep | ❌ |

---

## Phase 1: データ基盤（今週）

### Task 1.1: Binance OHLCV取得関数の追加 ✅
- **ファイル**: `orchestration/data_collector.py`
- **内容**: `collect_binance_ohlcv()` 関数を新設
  - BTC/USDT, ETH/USDT の1時間足を取得
  - Binance API (`api.binance.com/api/v3/klines`) — APIキー不要
  - 同じSQLite (prices.sqlite) に蓄積（既存テーブル互換）
  - 5分ティックも Binance ticker API から取得
- **呼び出し**: mainループで60分ごと
- **初回**: 過去30日分を一括取得（limit=720 = 30日×24h）

### Task 1.2: COLLECT_SYMBOLSにBTC/ETH追加 ✅
- **ファイル**: `orchestration/data_collector.py`
- **内容**: COLLECT_SYMBOLSに "BTC", "ETH" 追加
- **5分ティック**: Binance ticker API (`api.binance.com/api/v3/ticker/price`)
- **異常値フィルター**: 既存の50%乖離フィルターはそのまま使える

### Task 1.3: market_data.py fetch_btc_trend をBinance化 ✅
- **ファイル**: `tools/market_data.py`
- **内容**: fetch_btc_trend() の実装をCoinGecko → Binance klines APIに切替
- **戻り値**: 既存フォーマット維持（price, change_24h, change_30d, change_180d, trend）

### Task 1.4: market_data.py OHLCV取得のBinance対応 ✅
- **ファイル**: `tools/market_data.py`
- **新規**: `fetch_ohlcv_binance(symbol, days=30)` メソッド追加
- **fetch_ohlcv_custom 優先順位変更**:
  - BTC/ETH → ローカルDB（Binance蓄積分）→ Binance API直接フォールバック
  - VP銘柄 → 既存のまま（ローカルDB → GeckoTerminal → CoinGecko）

### Task 1.5: 初期データバックフィル ✅
- BTC/ETHの過去30日分OHLCVをBinanceから一括取得してDB蓄積
- バックテストエージェントがBTC/ETHデータで動作することを確認

---

## Phase 2: Capital Flow Radar（来週前半）

### アーキテクチャ
```
capital_flow_radar.py — 6時間ごと実行

[データ取得層]
├── yfinance: ^GSPC, ^VIX, ^TNX, DX-Y.NYB, GC=F
├── CoinGecko: /global（Total MCap, BTC Dominance）
└── alternative.me: Fear & Greed Index

[スコアリング層] ← 初版はルールベース、後にHMM置換可能
├── 各指標を正規化（z-score）
├── 重み付け合算 → 資金フロースコア (-100〜+100)
│   VIX変化率:        重み 25%（急騰→大幅マイナス）
│   DXY変化率:        重み 20%（ドル高→マイナス）
│   S&P500変化率:     重み 15%（上昇→プラス）
│   10年債利回り変化:  重み 15%（上昇→マイナス）
│   ゴールド変化率:    重み 10%（急騰→マイナス=逃避）
│   Fear&Greed:       重み 10%（Extreme Fear→逆張りプラス）
│   BTC Dominance変化: 重み 5%
└── レジーム判定: Risk-On / Neutral / Risk-Off

[出力層]
├── Blackboard (vault/blackboard/macro_flow.json)
├── Council Phase 4b スコア注入
└── Discord定期レポート
```

### Task 2.1: マクロ指標収集モジュール ✅
- **新規ファイル**: `tools/capital_flow_radar.py`
- **依存**: `pip install yfinance`（要インストール確認）
- **取得対象**: VIX, DXY, S&P500, 米10年債, ゴールド, BTC Dominance, Fear&Greed
- **出力**: 資金フロースコア (-100〜+100) + レジーム判定

### Task 2.2: radarサイクル統合 ✅
- run_trigger.pyに6時間ごとのCapital Flow Radar呼び出し追加
- Discord定期レポート

### Task 2.3: Council統合 ✅
- Phase 4bスコアリングテーブルにマクロスコア項目追加
- マクロスコア +50以上: BUY判断 +5pt
- マクロスコア -50以下: BUY判断 -10pt

### 参考リポジトリ（確認済みURL）

| 目的 | リポジトリ | URL | 実装参照箇所 |
|---|---|---|---|
| マクロ指標統合 | economic-dashboard | https://github.com/shashankvemuri/economic-dashboard | data_functions.py: yfinance各指標独立取得パターン → CFR設計に採用 |
| HMMレジーム判定 | RegimeDetectionHMM | https://github.com/Poulami-Nandi/RegimeDetectionHMM | features.py: ret/vol/z_ret/momentum/drawdown特徴量設計 → 将来HMM化時に参照 |
| F&Gデータ蓄積 | Application-Fear-and-greed-index-data | https://github.com/tomkenig/Application-Fear-and-greed-index-data | fear_and_greed_index.py: alternative.me API取得パターン |
| 相関計算 | QuantStats | https://github.com/ranaroussi/quantstats | Rolling Correlation実装（将来使用） |
| HMM補助 | Market-Regime-Detection-HMM | https://github.com/dhruvbelawat21/Market-Regime-Detection-Using-Hidden-Markov-Models | 資産リターン平均・分散・共分散モデル |
| クロスアセット | Intermarket-ML-For-EMH | https://github.com/Swiss-MQP-2022/Intermarket-ML-For-EMH | 株/金/BTC跨資産分析フロー |
| パイプライン設計 | finance-data-pipeline | https://github.com/nicholashook/finance-data-pipeline | 複数API→DB保存の構造 |
| 債券追跡 | TreasuryYieldTracker | https://github.com/DanTCIM/TreasuryYieldTracker | yfinanceベース金利モジュール |

---

## Phase 3: Council再編 + BTC/ETHペーパー取引（来週後半）

### Task 3.1: Tier0のCouncil召集ロジック ✅
- run_trigger.pyにTier0サイクル追加
- BTC/ETH: 4時間ごとCouncil召集（VP銘柄と独立して実行）

### Task 3.2: バックテスト対応確認 ✅
- 9戦略バックテストがBTC/ETHデータで正常動作するか検証
- gplearn: BTC/ETHでの進化サイクル追加

### Task 3.3: ペーパートレード開始
- PaperWallet: BTC/ETHポジション管理
- **勝率カウント: BTC/ETH切替日からリセット**
- 学習モード: BTC/ETH用に新たにカウント開始

---

## Phase 4: 実取引エンジン（3週目）

### Task 4.1: Binance Spot API実行エンジン
- **新規ファイル**: `tools/cex_executor.py`
- Binance Spot APIでBTC/ETH売買（CEXの方がDEXよりスリッページ・手数料で有利）
- D2設計書の安全装置を流用（最大取引額$500、日次上限$2000、緊急停止等）

### Task 4.2: APIキー管理
- Binance APIキー（Read + Spot Trading権限）
- .envに `BINANCE_API_KEY` / `BINANCE_API_SECRET` 追加
- IP制限設定

### Task 4.3: DRY_RUNモード
- トランザクション生成のみ、送信しない
- PaperWalletとの比較検証

---

## Phase 5: 少額実取引（4週目〜）

### Task 5.1: $50少額テスト
### Task 5.2: 1週間検証 → $200引き上げ
### Task 5.3: PaperWallet並行稼働で比較

---

## 移行条件

| 条件 | 基準 |
|---|---|
| BTC/ETH Paper勝率 | 60%以上 |
| 期間 | BTC/ETHペーパー開始から3ヶ月 |
| 取引回数 | 100回完了 |
| Capital Flow Radar | 正常稼働確認 |
| DRY_RUNテスト | 10回以上エラーなし |

---

## VP銘柄の扱い

- VIRTUAL/AIXBTは**監視継続**（データ蓄積、Alpha Sweep）
- Council召集はTier1として維持（頻度は据え置き）
- ポジションサイズを段階的に縮小（現行 → 50% → 監視のみ）
- ACP offeringのmarket_analysisはBTC/ETH対応に拡張

---

## リスクと注意事項

| リスク | 対策 |
|---|---|
| Binance API障害 | CoinGeckoフォールバック維持 |
| BTC/ETH競争激しい | 勝率目標60%は保守的で達成可能 |
| VP経済圏との乖離 | Tier1で監視継続、ACP offeringsは拡張 |
| 実取引での損失 | D2設計書の安全装置+段階的引き上げ |
| yfinance API変更 | シンプルなラッパーなので差し替え容易 |
