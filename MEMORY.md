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
  - **New (Webhook)**: `DISCORD_WEBHOOK_URL` configured for autonomous reporting.
- **Lessons Learned**:
  - **Spam Filtering**: Bulk channel creation/renaming followed by multiple long-form posts can trigger Discord's automated spam protection, causing "Shadow Blocks" where API calls return OK but messages don't appear. Cooling down for several hours is the primary mitigation.
  - **Language Preference**: The user (Yusuke) prefers all outputs and system reports in Japanese.
  - **Proactive Reporting**: Background processes cannot initiate sessions; use Webhooks for "Push" notifications.
  - **Google Model IDs**: Correct ID for 3.0 Flash is `gemini-3-flash-preview` (not `3.0`). Incorrect IDs can trigger fallback to Pro models, causing rate limit/cost spikes. Always verify IDs in Google AI Studio.

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
7.  **Neo のモデルアップグレード**: Neo 自身のモデルを `google/gemini-3-flash-preview` に、全エージェントの実務モデルを `openrouter/deepseek/deepseek-chat` (DeepSeek-V3) にアップグレードし、より高速かつ高度な対話・推論が可能になりました。

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

## 2026-03-04 本日の成果まとめ (Neo v3.0 ハイブリッド・アーキテクチャ始動)
1.  **ハイブリッド・モデルへの移行**: 
    - 全CrewのDeepSeek縛りを撤廃し、適材適所の最強モデル構成へ換装。
    - Brain (Claude 3.5), Eyes (Gemini 2.0 Flash), Hands (GPT-4o) の役割分担を確立。
2.  **Paper Trading (仮想取引) の成功確認**: 
    - `PlanningCrew` からの「Risk On」シグナルに基づき、Neoが自律的にVIRTUALトークンを購入するプロセスを実証。
3.  **自律サイクルの堅牢化**: 
    - JSON抽出ロジックの強化と、PM2によるプロセス永続化により、エラー耐性と自律性が大幅に向上。
4.  **インフラの最適化**: 
    - Atomic Logging (`.jsonl`) の採用とGit同期により、データ整合性とコード管理を強化。
5.  **レポーティング機能の完全自動化 (Done)**:
    - `run_cycle.py` に Discord Webhook 送信機能を実装。
    - **フォーマット**: 4セクション（市場・戦略・資産・発信）構成のMarkdownレポートに標準化。
    - **言語設定**: 報告内容および戦略指示 (`action_directive`) を「完全日本語化」するようプロンプトを厳格化。

### 今後の展望（次期開発候補: Neo v3.1）
1.  **時間解像度の可変・イベント駆動化**:
    - 1時間ごとの定期実行に加え、価格急変やWhaleの動きを検知して即時実行する「Event-Driven」アーキテクチャの導入。
2.  **オンチェーン・インテリジェンスの深化**:
    - 「勝率の高いクジラ」を自動特定し、その動きをコピーする「Smart Money Tracking」機能の実装（自動検知と手動指定のハイブリッド）。
3.  **マルチ戦略マネジメント**:
    - トレンドフォロー、逆張り、アービトラージなど複数の戦略を並行稼働させ、相場環境に応じて資金配分を変える「Meta-Manager」の導入。

## 2026-03-05 本日の成果まとめ (Phase 3: Cost Guard & Self-Optimization)
1.  **Neoモデルのアップグレード**:
    - Neo本体（オーケストレーター）のモデルを `google/gemini-3-flash-preview` に換装し、圧倒的な高速性と最新の推論能力を確保。
2.  **Phase 3.1: The CFO Update (完了)**:
    - **Blackboard (共有メモリ)**: 各Crewが市場データや戦略をリアルタイムに共有する仕組み (`core/blackboard.py`) を実装。コンテキストの断絶を解消。
    - **Cost Guard (予算管理)**: タスク実行前に予算とループ回数をチェックするゲートキーパー (`core/cost_guard.py`) を実装。無駄なAPI消費をブロック。
3.  **Phase 3.2: Nightly Optimization (完了)**:
    - **日次バッチ (`batch/daily_optimize.py`)**: 毎晩ログを分析し、「改善パッチ」を自動生成するスクリプトを設置。
    - **Discord Reporting**: バッチ分析結果（修正案やエラー数）をDiscord Webhookに通知する機能を実装。
    - **Execution Logger**: 全エージェントの活動をJSONL形式で記録するロガーを `neo_main.py` に統合。

## 2026-03-05 (PM) 本日の成果まとめ (Phase 3.1: Hybrid Architecture Stabilization)
1.  **ハイブリッド・モデル構成の最終決定**:
    - **Neo本体 (司令官)**: Google Direct API経由の **`gemini/gemini-3.0-flash-preview`** (OpenRouter非経由)。
    - **Scout / Sentiment (調査部隊)**: OpenRouter経由の `google/gemini-2.5-flash`。
    - **Planning / Dev (頭脳部隊)**: OpenRouter経由の `anthropic/claude-3.5-sonnet`。
    - **Executor (実行部隊)**: OpenRouter経由の `openai/gpt-4o`。
2.  **技術的デッドロックの解消**:
    - **API 401エラーの修正**: `PlanningCrew` における API キー読み込みの不具合を修正し、戦略立案プロセスを正常化。
    - **Blackboard連携の修正**: ペーパートレード結果（資産残高）がBlackboardに反映されないバグを修正し、各Crewが最新の資産状況を参照可能に。
3.  **Git同期**: 現在の最新コードベース (Neo v3.1) をマスターブランチにプッシュ完了。

これにより、Neoは **「Google直のGemini 3.0 Flashが指揮し、OpenRouter経由の適材適所Crewが実務を行う」** という堅牢なハイブリッド体制で再始動しました。

## 司令官からの指示 (2026-03-05)
- **モデル設定**: Neo本体は `gemini/gemini-3.0-flash-preview` (Google Direct API) を使用すること。
