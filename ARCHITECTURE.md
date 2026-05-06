# 🏗️ Neo アーキテクチャマップ

> **最終更新**: 2026/04/02 v6.5aa
> **目的**: 新セッション開始時に全体構造を即座に把握するためのリファレンス

---

## エントリーポイント（systemdサービス）

| サービス | 実行ファイル | 役割 |
|---|---|---|
| `neo-radar` | `run_trigger.py` | **メインループ**（30秒サイクル）— 5層売却（戦略別出口）・2hローテーションCouncil（BTC→VIRTUAL→ETH→AIXBT）・Alpha Sweep・Moltbook・Nightly Batch |
| `neo-collector` | `orchestration/data_collector.py` | 市場データ収集（5分tick + 60分OHLCV + 日次パージ） |
| `neo-resource-api` | `tools/neo_resource_api.py` | FastAPI port 8099 — ACP Resource提供用 |
| `neo-acp-seller-v2` | ACP v2 seller runtime (`skills/acp-cli-v2/src/seller/seller_native_v2.ts`) | SSE常駐 — ACP v2 Job受付・処理（v6.5bnでv1から完全移行） |

---

## ディレクトリ構造
```
workspace/
├── run_trigger.py          ← メインループ（全自律サイクルの起点）
│
├── agents/                 ← エージェント層
│   ├── trinity_council.py  ← **中核** Phase 0-8 全フロー
│   ├── scout_agent.py      ← ScoutCrew（偵察・情報収集）[trinity_council, alpha_sweep から使用]
│   ├── sentiment_agent.py  ← SentimentCrew [trinity_council から lazy import]
│   ├── backtest_agent.py   ← BacktestAgent [trinity_council から使用]
│   ├── planning_agent.py   ← PlanningCrew Phase 1e戦略リスク評価+F5資本フローフェーズ判定 [trinity_council]
│   └── development_agent.py← DevelopmentCrew [未使用だが将来用に保持]
│
├── core/                   ← 共通基盤
│   ├── config.py           ← 設定管理（LIVE_MODE・EXIT_PROFILES・TIER0_SYMBOLS等）
│   ├── model_factory.py    ← LLMモデル選択・コスト管理
│   ├── cost_guard.py       ← コストガード（L1-L4サーキットブレーカー）
│   ├── blackboard.py       ← Blackboard（エージェント間共有状態）
│   ├── governance.py       ← ParameterGovernance
│   ├── logger.py           ← ロギング
│   ├── finance.py          ← 金融計算ユーティリティ
│   ├── utils.py            ← 汎用ユーティリティ
│   ├── state_manager.py    ← 状態管理
│   ├── throttler.py        ← API呼び出し制御
│   ├── memory_db.py        ← メモリDB
│   ├── agent_base.py       ← エージェント基底クラス
│   ├── base_crew.py        ← CrewAI基底クラス
│   ├── executor.py         ← 実行エンジン
│   └── simulation_executor.py ← シミュレーション実行
│
├── tools/                  ← ツール層（外部API・データ処理）
│   │── # === 市場データ ===
│   ├── market_data.py      ← DexScreener/GeckoTerminal データ取得 [run_trigger, trinity_council]
│   ├── indicators.py       ← テクニカル指標計算
│   ├── finbert_sentiment.py← FinBERTセンチメント分析 [trinity_council]
│   ├── crypto_news.py      ← ニュース取得 [trinity_council]
│   ├── market_sentiment.py ← 市場センチメントコンテキスト [trinity_council lazy]
│   ├── whale_monitor.py    ← クジラ監視 [trinity_council]
│   ├── vp_onchain_data.py  ← VPオンチェーンデータ [trinity_council]
│   │── # === 取引 ===
│   ├── paper_wallet.py     ← PaperWallet（模擬取引） [run_trigger, trinity_council]
│   ├── portfolio_manager.py← ポートフォリオ管理 [trinity_council]
│   ├── backtest_engine.py  ← バックテストエンジン
│   ├── arbitrage_monitor.py← アービトラージ監視 [run_trigger]
│   │── # === ソーシャル ===
│   ├── moltbook_tool.py    ← Moltbook投稿 [trinity_council, nightly_research]
│   ├── moltbook_engager.py ← Moltbookエンゲージメント [run_trigger]
│   ├── moltbook_tracker.py ← Moltbook統計追跡 [run_trigger]
│   ├── discord_reporter.py ← Discord通知（Tier別勝率・戦略別出口・4-Assetローテーション対応）
│   │── # === マクロ ===
│   ├── macro_collector.py  ← F5マクロ資本フロー収集（yfinance+CoinGecko）[data_collector日次]
│   │── # === その他 ===
│   ├── neo_resource_api.py ← FastAPI Resource API [systemd]
│   ├── deepwiki_tool.py    ← DeepWiki連携 [trinity_council]
│   ├── code_interpreter.py ← コード実行
│   ├── publisher.py        ← コンテンツ公開
│   └── validation_monitor.py← バリデーション監視
│
├── research/               ← 研究・分析
│   ├── backtests/
│   │   ├── run_backtest.py ← 9戦略バックテスト 3:3:3構成 [trinity_council Phase 2]
│   │   └── param_optimizer.py
│   ├── gplearn_strategy.py ← 遺伝的プログラミング戦略
│   ├── voyager_skills.py   ← Voyager（パターン学習・ChromaDB）
│   ├── evolver_rules.py    ← EvolveR（ルール自己進化）
│   ├── n1_pair_trade.py    ← N.1ペアトレード（VIRTUAL/AIXBT）
│   ├── h2_trade_analysis.py← H.2取引分析
│   ├── run_alpha_discovery.py
│   ├── wait_quality_analysis.py
│   └── analysis/
│       └── h2_v2_tsfresh.py
│
├── orchestration/          ← オーケストレーション（定期実行タスク）
│   ├── data_collector.py   ← 市場データ収集 [systemd neo-collector]
│   ├── nightly_research.py ← Nightly Batch [run_trigger JST02:00]
│   ├── performance_evaluator.py ← パフォーマンス評価 + Tier別勝率 [run_trigger 6h]
│   ├── alpha_sweep_operation.py ← Alpha Sweep [run_trigger 60min]
│   ├── vp_discovery.py     ← VP銘柄ディスカバリー
│   ├── live_portfolio_monitor.py
│   ├── multi_asset_research.py
│   └── tearsheet_generator.py
│
├── feature_engineering/    ← 特徴量エンジニアリング
│   ├── build_features.py   ← 特徴量ビルダー
│   ├── alpha_volatility.py
│   ├── alpha_regime.py
│   ├── alpha_cross_asset.py
│   ├── alpha_funding.py
│   └── alpha_liquidation.py
│
├── data_pipeline/          ← データパイプライン
│   ├── data_validator.py
│   ├── market_data.py
│   └── parquet_writer.py
│
├── bridge/                 ← 外部連携ブリッジ
│   ├── acp_client.py       ← ACP Buyer側クライアント
│   ├── acp_schema.py       ← ACPスキーマ定義
│   └── crewai_bridge.py    ← CrewAI連携
│
├── skills/                 ← スキル定義（VP関連は docs/VP_overview_v2.md 参照）
│   ├── acp-cli-v2/         ← **ACP v2 Seller runtime（現役）**
│   │   ├── src/seller/seller_native_v2.ts  ← メインエントリ（systemd: neo-acp-seller-v2）
│   │   ├── src/seller/offeringsLoader.ts   ← offerings動的ロード
│   │   ├── src/lib/agentFactory.ts         ← Privy provider生成（builderCode=bc_agxzezgu）
│   │   └── config.json     ← activeWallet=0x840cff... (NeoAutonomous v2)
│   ├── acp-cli-v2-buyer/   ← Buyer用（acp-cli-v2をシンボリックリンク共有・configのみ別）
│   │   └── config.json     ← activeWallet=0x11ab498c... (neo-test-buyer-v2)
│   └── virtuals-protocol-acp/  ← **offerings本体（11個）**
│       ├── src/seller/offerings/  ← 11 offerings（VP_overview_v2.md §7参照）
│       └── src/seller/resources/  ← 3 resources
│
├── data/                   ← ランタイムデータ（JSON）
│   ├── paper_wallet.json   ← PaperWallet状態
│   ├── gplearn/            ← gplearn学習結果
│   └── moltbook_*.json     ← Moltbook追跡データ
│
├── vault/                  ← 永続状態・セキュリティ
│   ├── market_db/prices.sqlite ← **市場データDB**（VIRTUAL/AIXBT 3,315+行）
│   ├── neo_state.json
│   ├── cost_guard_*.json
│   ├── n1_pair_state.json  ← N.1ペアトレード状態
│   └── blackboard/live_intel.json
│
├── docs/                   ← 引き継ぎ白書（バージョン管理）
│   └── GSD計画_v6.5*_引き継ぎ白書.md
│
├── logs/                   ← 現行ログ
├── reports/                ← レポート出力
│
└── .archive_*/             ← アーカイブ済み（参照不要）
    ├── .archive/logs/crewai/  ← 旧CrewAIログ（140+件）
    ├── .archive_202603/       ← 2026/03初旬アーカイブ
    └── .archive_deadcode_v65p/ ← v6.5pで除去したdead code（14件）
```

---

## 呼び出しフロー概要
```
run_trigger.py（30秒ループ）
  │
  ├─→ Phase 0: F2 BTC急落リスク(L1-L3) → 5層売却チェック（戦略別出口short/mid/long、Council非依存）
  │     └ exit_profile: short / mid / long（v6.5ai 3:3:3対応）
  │
  ├─→ 2hローテーション（BTC→VIRTUAL→ETH→AIXBT タイムスタンプベース）
  │     └ Blackboard "last_unified_council_ts" で永続化（リスタート耐性）
  │
  ├─→ Trigger判定 → TrinityCouncil.run()
  │     ├─→ ScoutCrew.run()          [agents/scout_agent.py]
│     ├─→ Phase 1e: PlanningCrew     [agents/planning_agent.py + F5マクロフェーズ判定]
  │     ├─→ build_onchain_context()   [tools/vp_onchain_data.py]
  │     ├─→ SentimentCrew.run()       [agents/sentiment_agent.py]
  │     ├─→ BacktestAgent.run()       [agents/backtest_agent.py]
  │     │     └─→ run_backtest.py     [research/backtests/]
  │     ├─→ Bull/Bear/Neo協議        [LLM呼び出し]
  │     ├─→ Phase 4b スコアリング（F5: macro+X(PHASE)ラベル追加）
  │     ├─→ Phase 5 ガード6段 → PaperWallet
  │     ├─→ Phase 6 Moltbook投稿
  │     └─→ Phase 7 Discord報告
  │
  ├─→ Alpha Sweep（60分）            [orchestration/alpha_sweep_operation.py]
  ├─→ Moltbook Engagement（2h）      [tools/moltbook_engager.py]
  ├─→ Performance Evaluator（6h）     [orchestration/performance_evaluator.py]
  └─→ Nightly Batch（JST 02:00）     [orchestration/nightly_research.py]
        ├─→ Voyager自動更新            [research/voyager_skills.py]
        ├─→ EvolveR自動更新            [research/evolver_rules.py]
        ├─→ gplearn進化                [research/gplearn_strategy.py]
        └─→ Moltbook定期投稿
```

---

## VP/ACP構成

VP関連の物理構造・状態・既知の問題は別ドキュメントに集約。本セクションは概略のみ。

### 詳細ドキュメント
- **docs/VP_overview_v2.md** — VP関連コードベース全体像（必読・現状マップ）
- **docs/wallet_inventory.md** — ウォレット情報・残高・Builder Code
- **docs/VP_refactor_plan_v1.md** — リファクタ実行計画

### 主要エントリポイント
- v2 Seller: `skills/acp-cli-v2/src/seller/seller_native_v2.ts` (systemd: `neo-acp-seller-v2.service`)
- offerings本体: `skills/virtuals-protocol-acp/src/seller/offerings/` (11個)
- Provider生成: `skills/acp-cli-v2/src/lib/agentFactory.ts` (Builder Code: `bc_agxzezgu` 反映済)
- Trinity Council統合: `bridge/acp_client.py` (参考情報注入のみ・方針X)
- VP銘柄発見: `orchestration/vp_discovery.py` (週次・月曜JST 04:00)
- Resource API: `tools/neo_resource_api.py` (FastAPI port 8099)

### v1 → v2 移行（v6.5bn完了）
- v1 (`neo-acp-seller.service`): archive 済（v6.5bn）
- v2 (`neo-acp-seller-v2.service`): 現役・DRY_RUN=false で稼働中
- v1 SDK (`acp-node v0.3.0-beta.40`) → v2 SDK (`acp-node-v2`)
- v1 transport (WebSocket) → v2 transport (SSE)
- 移行理由: VP Graduation flow が v2 native SDK 基準にメジャー更新

### 重要事項（必ず守ること）
- Trinity Council のACP外部エージェントシグナルは「参考情報注入のみ」（方針X）
- 残2ウォレット（buyer / seller）の Withdraw 試行は絶対禁止（v6.5bm凍結事例）
- Issue #82 のレスが来るまで VP Registry への変更操作（Re-Import等）禁止
- DRY_RUN=false 維持（V2_SELLER_DRY_RUN環境変数）

## データ所在

| データ | 場所 | 備考 |
|---|---|---|
| 市場価格（正） | `vault/market_db/prices.sqlite` | VIRTUAL/AIXBT 3,315+行 |
| PaperWallet | `data/paper_wallet.json` | 取引履歴・残高 |
| gplearn学習結果 | `data/gplearn/` | best_virtual.json等 |
| Voyagerスキル | ChromaDB | 7パターン |
| EvolveRルール | `research/evolver_rules.py`内 | 6ルール |
| N.1ペアトレード状態 | `vault/n1_pair_state.json` | Z-score・ポジション |
| Blackboard | `vault/blackboard/live_intel.json` | エージェント間共有 |
| マクロ資本フロー | `vault/blackboard/macro_flow.json` | F5: score/regime + macro_data(5指標) |
| コストガード | `vault/cost_guard_*.json` | L1-L4状態 |
| ⚠️ 空DB（使わない） | `data/market_data.db`, `data/neo_market.db` | 参照禁止 |
