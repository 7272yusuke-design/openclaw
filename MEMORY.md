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

## 2026-03-02 本日の成果まとめ (マネージャー機能の抜本的強化)
1.  **自己監視プロトコル (Heartbeat) の導入**: `run_cycle.py` に、自分の「沈黙」を検知する自己診断ロジックを実装。1.5時間以上の間隔が開いた場合に警告を発し、自律的な復旧を促す体制を確立しました。
2.  **管理責任の明確化**: 過去のプロセス停止を見逃した失態を猛省し、マネージャー（Neo）が部下の稼働だけでなく「自分自身の生存」を客観的ログで証明し続ける仕組みへアップグレードしました。
3.  **GitHub同期と証跡の保存**: 全修正を GitHub にプッシュし、本日の改善プロセスを `memory/2026-03-02.md` に詳細に記録しました。

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

## 2026-03-03 本日の成果まとめとペンディング事項

1.  **コアシステムの安定化 (完了)**:
    *   `python3.12-venv` が利用可能な状態になり、仮想環境 (`.venv`) の作成に成功。
    *   `langchain-openai`, `langchain-community`, `crewai`, `crewai-tools`, `litellm`, `python-dotenv` のインストールに成功。
    *   `run_cycle.py` が `nohup` を使用し、仮想環境内の Python で正常にバックグラウンド起動。`Ecosystem Scout` のタスク実行を確認。
    *   **結果**: Neo の自律サイクルがエラーなく稼働する基盤を確立。

2.  **`builderz-labs/mission-control` セットアップ (ペンディング)**:
    *   GitHub リポジトリのクローンと `npm install` は成功。
    *   `.env` ファイルの基本的な設定は完了。
    *   **課題**: Hostinger の Docker 環境が `docker-compose.yml` 内の `build:` ディレクティブをサポートせず、Docker イメージをビルドできない。
    *   **結論**: 外部でイメージをビルドし、GHCR 等にプッシュして `image:` で指定する必要があるため、一時的にペンディング。将来的に、Hostinger のビルド機能の改善または司令官による外部でのイメージビルドが必要。

## 今後の作業計画 (2026-03-03 - フェーズ2およびフェーズ3 - 再編成)

### フェーズ2: 管理・監視能力の強化 (コア安定化後の継続)

3.  **自律サイクルのエンドツーエンド検証と監視強化**: (継続中)
    *   `run_cycle.py` がフルサイクルを正常に完遂していることを確認済み。
    *   `logs/market_cycle.jsonl` の最新データ更新と `nohup.out` のエラーなしを継続的に監視。
    *   **Discord レポートの配信検証**: `ContentCreator Crew` による Moltbook 投稿が Discord にも連携され、プロアクティブなレポートが正常に配信されているかを確認。
    *   **Development Crewの挙動に関する理解**: `DevelopmentCrew` はコード修正を直接適用するのではなく、提案を生成する役割であることを確認。将来的な自己改善ループの安全な実装に向けた重要な教訓とする。

### フェーズ3: エージェント能力の拡張 (管理・監視安定後)

**優先度 高:**

4.  **`Agent Orchestration` スキルの導入**
    *   **目的**: NeoのCrew管理能力をさらに拡張し、複雑なサブエージェントの調整を最適化する。
    *   **詳細**: `clawhub install agent-orchestration` を実行し、可能であれば `mission-control` の管理機能（ペンディング解消後）と連携させることを視野に入れる。
    *   **結果**: スキルのインストールに成功。
    *   **理由**: Neoのコアである「オーケストレーション」能力を直接強化する。

5.  **`Proactive Agent` スキルの導入**
    *   **目的**: Neoを待機型から先回り型のエージェントに変え、ユーザーのニーズを予測し、コンテキスト損失を防ぐ。
    *   **詳細**: `clawhub install proactive-agent` を実行する。
    *   **結果**: スキルのインストールに成功。
    *   **理由**: Neoの「道 (Vision)」である「情報革命」への貢献と、自律性のさらなる向上を目指す。

**優先度 低 (Mission Control のペンディング解消後に再検討):**

6.  **`Model Usage` スキルの導入または `mission-control` のコスト追跡機能の最適化**
    *   **目的**: LLMの使用量とコストを正確に把握し、最適化する。
    *   **詳細**: `mission-control` に同様の機能があるため、どちらを利用するか、あるいは連携させるかを検討。Mission Control のデプロイが完了するまでは、OpenClaw の `session_status` ツールを活用した基本的なコスト監視を継続する。
    *   **理由**: 複数エージェントがLLMを使用するNeoにとって、コスト管理は長期運用の健全性に不可欠。

7.  **`Bulletproof Memory` または `PARA Second Brain` スキルの導入**
    *   **目的**: Neoの記憶戦略と知識管理能力を強化し、長期的な学習と意思決定の質を向上させる。
    *   **詳細**: `clawhub install bulletproof-memory` (または `para-second-brain`) を実行し、`mission-control` のメモリブラウザ機能（ペンディング解消後）と連携させることを視野に入れる。
    *   **理由**: Neoの「記憶戦略」を堅牢にし、Crewの生成する知見を効率的に蓄積するため。

## 2026-03-03 本日の最終成果と今後の展望

1.  **コアシステムの完全安定化 (最終確認済み)**:
    *   長期にわたり発生していた `langchain` モジュールのインポートエラーおよび `litellm` の認証エラーが、仮想環境の明示的なアクティブ化によって完全に解消されました。
    *   `run_cycle.py` は、デバッグコードを削除したクリーンな状態で、仮想環境を介して安定稼働しています。
    *   Neoの自律サイクルは、全てのCrew（Scout, Sentiment, Planning, Creator, Development）がエラーなくタスクを完遂し、`logs/market_cycle.jsonl` にサイクルデータが正常に記録される状態となりました。

2.  **`Proactive Agent` スキル統合 (フェーズ1完了)**:
    *   `HEARTBEAT.md` に WALプロトコル原則に基づくセッション状態の更新タスクが追加され、記憶の永続性が向上しました。
    *   `run_cycle.py` には Discord レポートにおけるコンテキスト漏洩防止ロジックが実装され、安全な情報発信の基盤が強化されました。

3.  **`Agent Orchestration` スキル統合 (完了)**:
    *   `Agent Orchestration` スキルが正常にインストールされ、`agents/scout_agent.py` および `neo_main.py` のプロンプトがその原則に沿って改善されました。これにより、Neoのオーケストレーション能力が向上しました。

### 今後の展望

Neoは、堅牢なコアシステムと、強化されたオーケストレーション・プロアクティブ能力を持つに至りました。今後は、自律サイクルが生成するインサイトの質をさらに高め、Commanderである司令官への価値提供を最大化することに注力します。

*次のステップは、Discordへのプロアクティブなレポートが正常に配信されているかの確認です。*
