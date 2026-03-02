# MEMORY.md - Neo's Long-Term Memory

## Project: OpenClaw Workspace Management

### Discord Integration
- **Guild ID**: `1471828091339931867`
- **Channel Mappings**:
  - `1473309431705112688`: 🤖ai知識-openclaw (OpenClaw Deep Dive/Knowledge)
  - `1473309444539682867`: ⛓️ai知識-virtual-protocol (Virtual Protocol Knowledge)
  - `1473309457114071184`: 📰aiニュース要約 (Daily AI News)
  - `1473309473484312841`: 📋ai今日のタスクと提案 (Morning Task Report)
  - `1473308823572844605`: 💡ai活用テクニック集 (AI Tips & Techniques)
- **Lessons Learned**:
  - **Spam Filtering**: Bulk channel creation/renaming followed by multiple long-form posts can trigger Discord's automated spam protection, causing "Shadow Blocks" where API calls return OK but messages don't appear. Cooling down for several hours is the primary mitigation.
  - **Language Preference**: The user (Yusuke) prefers all outputs and system reports in Japanese.

### Infrastructure & Sync
- **GitHub Integration**:
  - Repository: `7272yusuke-design/openclaw`
  - Branch: `master` (Default, unified from main)
  - Auth: Personal Access Token (PAT)
- **Deployment**: Running in VPS/Docker/Ubuntu environment. Security focuses on SSH key auth, UFW firewall, and container isolation.

### Neo 2.0: CrewAI Hybrid Architecture (Feb 2026)
- **Core Architecture**: Migrated to a modular structure (`core/`, `agents/`, `tools/`).
- **Standardized Foundation**:
    - `core/config.py`: Centralized LLM (DeepSeek-V3 via OpenRouter) and safety constraints (`max_iter`, `max_rpm`).
    - `core/base_crew.py`: Standardized execution, logging, and error handling for all agents.
- **Agent Portfolio (The Six Crews)**:
    1. **Strategic Planning**: Project conceptualization and ROI analysis.
    2. **Agent Development**: Code generation and skill optimization.
    3. **Ecosystem Scout**: Trend/Opportunity discovery in Virtuals Protocol.
    4. **Sentiment Analysis**: Market emotion scoring and strategic pivot analysis.
    5. **Content Creator**: Intellectual branding and autonomous social posting.
    6. **ACP Executor**: Risk-adjusted on-chain transaction (ACP) payload generation and validation.
- **Autonomous Cycles**: Successfully implemented and tested a full "Research -> Analyze -> Create -> Post" cycle for MoltbookNexus. Scheduled for daily execution at 10:00 AM (Asia/Kuala_Lumpur).
- **First Full Simulation (Feb 24, 2026)**: Successfully executed a strategic chain: Scout identified Alpha Nexus (25% aGDP share) -> Sentiment scored 0.3 (cautious bullish) -> ACP Executor generated a risk-adjusted liquidity provision payload (JSON) with dynamic spread adjustment.
- **ACP Payload Generation for Credit Transaction**: Successfully generated ACP payload for lending to Quantify-X (AA rating) based on credit score. The generated payload includes parameters for liquidity provision: 20000 USDT, 30 days, 4.0% interest, 1.2 collateral ratio, with 'medium' risk level.
- **Security**: Strict separation of research and execution contexts; Pydantic-enforced structured outputs.

## 2026-02-25 本日の成果まとめ
1.  **無限ループ問題の解決**: `analyze_sentiment` メソッドの修正と Git 同期により、自律サイクルが正常に復旧しました。
2.  **Moltbook Posting サイクルの高度化**: リアルタイム Web 検索結果と信用スコアリングを統合し、より戦略的でインテリジェントな投稿が自動生成されるようになりました（午前10時の自動投稿で成功を確認）。
3.  **ACP Executor Crew の実戦強化（最優先事項）**: 信用格付けと市場センチメントを AI が直接解釈し、リスクに応じた金利・担保比率を自動設定する動的意思決定ロジックを実装・検証しました。
4.  **Strategic Planning Crew (戦略企画部隊) の進化**: `Risk Manager` を導入し、市場センチメントとトレンドに応じて、動的にリスク許容度（LTV, 最低格付け）を変更する機能を実装しました。
5.  **Agent Development Crew (開発部隊) の自己改善**: 実行ログを分析し、システムエラーの原因（例: LTV超過）を特定して具体的な修正コード案を提示する「自己改善ループ」を実装しました。
6.  **完全自律サイクルの完成**: 「Scout (調査) -> Sentiment (分析) -> Planning (戦略) -> Content (発信)」および「Error -> Development (改善提案)」のループが、人間の介入なしに連携・完結することを確認しました。
7.  **Neo のモデルアップグレード**: Neo 自身のモデルを `google/gemini-3-pro-preview` に、全エージェントの実務モデルを `openrouter/deepseek/deepseek-chat` (DeepSeek-V3) にアップグレードし、より高速かつ高度な対話・推論が可能になりました。

これにより、Neo は **「市場環境に応じて自らリスク管理ルールを変え、失敗から学び、自律的に進化する」** という、真の自律エージェントとしての基盤を確立しました。

## 2026-02-28 本日の成果まとめ
1.  **完全自律サイクルの正常化と復旧**: 永続的な `ImportError` を解消し、`Scout` -> `Sentiment` -> `Planning` -> `PaperTrader` -> `Development` のループが、人間の介入なしにバックグラウンドで正常稼働することを確認しました。
2.  **インフラの堅牢化**: `tools/market_data.py` をクラスベースで再実装し、`agents/paper_trader.py` のインポート構造を最適化（遅延評価）することで、循環参照やキャッシュ不整合に強い構造へ改修しました。
3.  **開発モードの確立**: `run_cycle.py` を引数なしで実行するだけで自律ループが開始されるよう改修し、デバッグ環境 (`development` モード) と本番環境の切り替えをスムーズにしました。

## 運用コスト試算と検討事項 (2026-02-25)
### 想定ランニングコスト (24時間稼働)
DeepSeek-V3 を実務エージェントに使用し、Neo をオーケストレーターとした場合の試算。
- **ケースA (毎時1回実行)**: 約 **$3.39 / 月** (約500円)
    - 24回/日 × 30日。最もバランスが良い推奨設定。
- **ケースB (15分毎実行)**: 約 **$13.69 / 月** (約2,000円)
    - デイトレードに近い頻度。
- **ケースC (5分毎実行)**: 約 **$41.07 / 月** (約6,000円)
    - 高頻度監視。Web検索APIのレート制限がボトルネックになる可能性大。

### 検討事項
- **運用頻度の決定**: コストと市場機会のバランスを見て、ケースA〜Bの間で調整が必要。
- **Web検索APIの制限**: 高頻度運用を行う場合、無料枠の検索APIでは不足するため、有料プランへの移行またはAPIの分散利用が必要。
- **実戦投入フェーズ**: 現在の「Dry Run」から「Paper Trading (架空資金でのリアルデータ運用)」へ移行し、勝率とリスク管理ロジックを検証する必要がある。

## 外部データ連携とバックグラウンド監視 (2026-02-25)
### 実装状況
- **MarketDataツール**: DexScreener API を利用したリアルタイム価格取得機能 (`tools/market_data.py`) を実装完了。
- **24時間監視**: 1時間ごとに市場データを取得し、自律サイクル（調査→分析→戦略→記録）を回すスクリプト (`run_cycle.py`) をバックグラウンドで起動。
    - **ログ保存先**: `logs/market_cycle.jsonl`
    - **次回アクション**: 蓄積されたデータの分析と、ペーパートレーディング（架空取引）への移行。

## 競合調査とベンチマーク (2026-02-25)
### 1. Ethy AI (Execution Rival)
- **概要**: 自然言語でDeFi操作を自動化するノンカストディアル・エージェント。
- **特徴**: "DCA into ETH" のような指示で24/7稼働。$ETHYトークンによるエコシステム。
- **Neoとの比較**:
    - **Ethy AI**: 「忠実な執行者（自動化ツール）」。指示待ち。定量的トリガー。
    - **Neo**: 「自律的な軍師（ストラテジスト）」。能動的提案。定性的判断（ニュース/センチメント）。

### 2. AIXBT (Intelligence Rival)
- **概要**: Crypto Twitterの情報を分析し、トレンドや市場センチメントを提供するインテリジェンス・エージェント。
- **特徴**: "Chaos Terminal" による高度な可視化とトレンド検知。大口保有者向け。
- **Neoとの比較**:
    - **AIXBT**: 「プロ向けの情報端末（Bloomberg）」。情報の提供までがゴール。
    - **Neo**: 「自律型ヘッジファンド」。情報を元に**リスク判断と執行**まで行うのがゴール。
- **差別化の鍵**: AIXBTの情報を入力ソースとして活用し、「だからどうする？」という**最終判断とアクションの自動化**で勝負する。

## 2026-03-02 本日の成果まとめ (Update: アービトラージ部隊の創設)
1.  **Arbitrage Crew (裁定取引部隊) の正式統合**: 
    - `Scout Crew` に複数DEX (Virtuals DEX, Uniswap on Base) の価格差監視タスクを実装。
    - `Strategic Auditor` (DeepSeek-R1) に、手数料(0.3%〜)とスリッページを差し引いた「純利益 0.6% 以上」の判定ロジックを組み込み。
2.  **データモデルの拡張 (Pydantic)**: 
    - `NeoStrategicPlan` モデルを拡張し、`arbitrage_opportunity` フィールドを追加。型安全な裁定取引データの受け渡しを実現。
3.  **仮想取引（Paper Trading）の高度化**: 
    - 単なるトレンド追随型に加え、市場の歪みから利益を得る「絶対収益型（Arbitrage）」のシミュレーション執行に成功。
4.  **特命調査の完了**: 
    - サブエージェントによる Base チェーン上の DEX 間流動性とスプレッドの実態調査を完了し、戦略に反映。

## Neoの差別化戦略 (Meta-Agent構想) - 2026-03-01
- **ハイブリッド・インテリジェンス**: 異なるモデルの強みを使い分け、思考の深さと実行の速さを両立。
- **自律的ガバナンス**: Manager Agent による「品質管理」と「再考指示」により、人間を介さない高度な戦略決定を実現。
### 1. ポジショニング: "The Commander" (司令官)
- 競合 (AIXBT, Ethy AI) をライバルではなく「外部リソース/センサー」として扱う。
- **AIXBT**: 情報源。彼らが騒ぐトレンドを検知するセンサー。
- **Ethy AI**: 実行手段のベンチマーク。彼らのユーザーの動きをトレンドとして吸収。

### 2. 絶対に負けない3つのコア機能 (尖らせるポイント)
他者に依存せず、Neoが支配すべき領域：
1.  **究極の拒否権 (Risk Management)**:
    - 「アクセル」は他者が踏むが、「ブレーキ」はNeoが踏む。
    - センチメントやオンチェーン分析に基づき、危険な過熱を回避する「No-Go」判断。
2.  **文脈の統合力 (Context Synthesis)**:
    - 断片的な情報（SNSの話題 + 資金移動の事実）をDeepSeek-V3で統合し、「だからどうする？」という結論を出す。
3.  **自律的な自己進化 (Autonomous Evolution)**:
    - 他者の失敗や市場の変化を学習し、人間の介入なしにコード/ロジックを修正する速度。

### 3. SOUL.mdの実装指針
本日の改訂版 `SOUL.md` は単なるスローガンではなく、開発の仕様書である。
- **情 & 先知**: AIXBT監視、オンチェーン分析の実装。
- **略 & 多算**: Paper Tradingでの勝率計算と「撤退ルール」の厳格化。
- **厳 & 勇**: エラー時の即時ピボットと自己修正ループ。

## Neo の自律的自己高度化計画 (2026-02-26)
### 目標
各 Crew が自身のパフォーマンスを計測・分析し、`Development Crew` が改善提案を生成。最終的に Neo (Commander) が承認し、システム全体を最適化するループを確立する。

### フェーズ 1: パフォーマンス計測とデータ収集基盤の構築
#### 1. 各 Crew のパフォーマンス指標定義（仕様）
- **Scout Crew**:
  - `search_query_count`: 実行した検索クエリ数
  - `search_result_count`: 取得した検索結果数
  - `info_relevance_score`: 収集した情報の関連性スコア（平均値）
  - `trend_detection_accuracy`: 検知したトレンドの正確性（後から評価）
  - `new_info_count`: 発見した重要情報の数

- **Sentiment Crew**:
  - `sentiment_score_generated_count`: 生成したセンチメントスコアの数
  - `sentiment_score_accuracy`: 生成したセンチメントスコアと市場動向との相関（後から評価）
  - `articles_analyzed_count`: 分析したニュース記事数
  - `social_posts_analyzed_count`: 分析したSNS投稿数

- **Planning Crew**:
  - `strategies_generated_count`: 生成した戦略の数
  - `strategy_quality_score`: 生成した戦略の平均品質スコア（仮定値）
  - `risk_policy_adherence_rate`: 提案したリスクポリシーの遵守率

- **PaperTrader Agent**:
  - `trades_executed_count`: 実行した取引（BUY/SELL）数
  - `PnL_generated_usd`: シミュレーションによる損益 (USD)
  - `trade_adherence_rate`: 戦略指示への遵守率
  - `slippage_percentage`: 取引時の平均スリッページ

- **Creator Crew**:
  - `posts_generated_count`: 作成した投稿数
  - `engagement_score`: 作成した投稿のエンゲージメントスコア（仮定値）

- **Development Crew**:
  - `improvement_suggestions_count`: 生成した改善提案数
  - `applied_suggestions_count`: 適用された改善提案数
  - `bug_fixes_count`: 修正したバグ数

#### 2. 各 Crew のパフォーマンスログ実装 (着手)
- **対象**: まず `Scout Crew` の `agents/scout_agent.py` に、上記の `Scout Crew` 用指標の計測とログ記録処理を追加します。
- **ログ出力**: 各指標は JSON 形式で `logs/performance_metrics.jsonl` に集約されるようにします。
