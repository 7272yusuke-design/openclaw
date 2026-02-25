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
