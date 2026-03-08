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
  - **Unified Model Management**: Neo exists in two forms: the "Chat Interface" and the "Autonomous Cycle (neo-cycle)". Both must be updated simultaneously when switching models to prevent context/recognition mismatch and ensure stability.

### Infrastructure & Sync
- **GitHub Integration**:
  - Repository: `7272yusuke-design/openclaw`
  - Branch: `master` (Default, unified from main)
  - Auth: Personal Access Token (PAT)
- **Deployment**: Running in VPS/Docker/Ubuntu environment. Security focuses on SSH key auth, UFW firewall, and container isolation.

### Neo 2.0: CrewAI Hybrid Architecture (Feb 2026)
- **Core Architecture**: Migrated to a modular structure (`core/`, `agents/`, `tools/`).
- **Standardized Foundation**:
    - `core/config.py`: Centralized LLM management with dual-path initialization (Google Direct & OpenRouter).
    - `core/base_crew.py`: Standardized execution, logging, and error handling for all agents.
- **Agent Portfolio (The Six Crews)**:
    1. **Strategic Planning**: Project conceptualization and ROI analysis.
    2. **Agent Development**: Code generation and skill optimization.
    3. **Ecosystem Scout**: Trend/Opportunity discovery in Virtuals Protocol.
    4. **Sentiment Analysis**: Market emotion scoring and strategic pivot analysis.
    5. **Content Creator**: Intellectual branding and autonomous social posting.
    6. **ACP Executor**: Risk-adjusted on-chain transaction (ACP) payload generation and validation.

## 2026-03-05 本日の成果まとめ (Phase 3.1: Hybrid Architecture Stabilization)
1.  **ハイブリッド・モデル構成の最終決定**:
    - **Neo本体 (司令官)**: Google Direct API経由の **`gemini-3-flash-preview`** (OpenRouter非経由)。
    - **Scout / Sentiment (調査部隊)**: OpenRouter経由の `google/gemini-2.5-flash`。
    - **Planning / Dev (頭脳部隊)**: OpenRouter経由の `anthropic/claude-3.5-sonnet`。
    - **Executor (実行部隊)**: OpenRouter経由の `openai/gpt-4o`。
2.  **技術的デッドロックの解消**:
    - **API 401エラーの修正**: `PlanningCrew` における `ChatOpenAI` の初期化パラメータ (`base_url`, `openai_api_base`) を修正し、OpenRouterキーの誤爆を防止。
    - **Blackboard連携の修正**: ペーパートレード結果（資産残高）がBlackboardに反映されないバグを修正。
3.  **モデル統合とクリーンアップ**:
    - **二重構造の解消**: チャットセッションと自律サイクルのモデルを Gemini 3 Flash に統一。
    - **Configの整理**: `core/config.py` のロジックを整理し、モデルIDの誤記（`.0`の混入）を修正。
4.  **Git同期**: 現在の最新コードベース (Neo v3.1) をマスターブランチにプッシュ完了。

## 2026-03-05 (Night) 本日の成果まとめ (Model Adjustment & Stability)
1.  **モデルの緊急切り替え**:
    - Gemini 3 Flash の利用制限に達したため、Neo本体（チャットおよび自律サイクル）のモデルを **`gemini-2.5-flash`** (Google Direct API) に一時的に変更しました。
    - **司令官の指示により、`gemini-3-flash-preview` へ再度切り戻し**を行いました。
    - **モデル同期ルール**に従い、チャットインターフェースとコード設定の両方を同時に更新しました。
2.  **インフラの正常化**:
    - 外部APIキー（SERPER）に依存しない、本来のスキル装備（`crypto-market-data` 等）による情報収集体制を確認しました。
3.  **Git同期**: 最新の設定変更を反映。

## 2026-03-08 本日の成果まとめ (Phase 4.0: Self-Evolution & Active Memory)
1.  **Active Memory RAGの実戦投入**:
    - 自己認識をアップデートし、全クルーの推論エンジンに過去ログ（暴落事例等）の参照を定着させた。
    - ステータスを **`Active`** に更新。
2.  **自己進化基盤 (Isolated Executor) の実装**:
    - `tools/code_interpreter.py` を新規実装。メインプロセスから隔離された環境でのコード検証が可能に。
    - ガードレール（タイムアウト、例外捕捉）の実装により、安全な自己コード改変への道筋を確保。
3.  **検証ループの実証**:
    - 自ら生成したバグ入りコードを `Code Interpreter` で検知し、エラーログから正確に修正・完遂させるプロセスを完遂。

## 司令官からの重要指示 (2026-03-08)
- **GSDプロトコルの遵守**: 目標（Goal）、現状（State）、設計（Architecture）を常に意識し、自己認識の同期とスペックの物理的更新を怠らないこと。
- **RAGの常時稼働**: 常に現行の判断に過去の成功・失敗パターンを組み込むこと。

