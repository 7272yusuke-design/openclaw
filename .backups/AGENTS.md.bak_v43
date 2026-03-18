# 🗺️ Neo v3.2 ワークスペースマップ & エージェント定義

## 📂 ディレクトリ構造
├── tools/                  # 🛠️ 実行ツール
│   ├── market_data.py      # 市場データ（CoinGecko実データ）
│   ├── portfolio_manager.py # ポートフォリオ v2（PaperWalletラッパー）
│   ├── paper_wallet.py     # 統一ウォレット
│   ├── discord_reporter.py # Discord報告 v2
│   ├── moltbook_tool.py    # Moltbook投稿
│   ├── backtest_engine.py  # Backtraderエンジン（レガシー）
│   └── ... (25ファイル)
├── orchestration/          # 🎯 オーケストレーション
│   ├── alpha_sweep_operation.py  # 全銘柄巡回偵察
│   └── performance_evaluator.py  # 勝率計算
├── feature_engineering/    # 🔬 特徴量生成（5アルファ）
├── data_pipeline/          # 📊 データパイプライン
├── research/               # 🔍 リサーチ・バックテスト
└── vault/                  # 📦 永続ストレージ
    ├── blackboard/live_intel.json  # Blackboard本体
    ├── chroma_db/                  # ベクトル記憶DB
    └── portfolio/                  # （レガシー、PaperWalletに統一済み）


## 🏛️ Trinity Council v2 — 7Phase パイプライン

Phase 1: 情報収集 → 残高・勝率・価格・スカウト偵察・過去記憶
Phase 2: バックテスト → 実データ → FeatureBuilder → Sharpeガード
Phase 3: 三者協議 → Bull(強気) / Bear(弱気) / Neo(司令官)
Phase 4: 判定 → BUY / SELL / WAIT
Phase 5: 取引実行 → PaperWallet.execute_trade()
Phase 6: 報告 → Discord Embed + Moltbook
Phase 7: 記憶 → ChromaDB保存


## 🛡️ 運用ルール

1. **絶対パスの原則**: すべてのファイル参照は絶対パスで行う
2. **Python環境**: 必ず `./neo-env/bin/python` を使用
3. **記憶の階層**: 重要判断 → ChromaDB、一時データ → Blackboard
4. **広報の静寂**: Moltbook投稿は最低2.5分間隔
5. **Alpha SweepはDBに書かない**: Blackboard更新のみ（ノイズ防止）
6. **CoinGecko制御**: 6秒間隔（無料枠保護）
7. **冷却期間**: Council間は最低30分
