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

## 2026-03-09 本日の成果まとめ (Phase 4.2: Physical Incarnation & Connectivity)
1.  **物理的受肉の完遂**:
    - `virtuals-protocol-acp` の統合により、APIキーを起点とした自律的ウォレット（Managed Wallet）を確立。
    - 受信用アドレス `0x89D4ed55B1B5533B0e5F533B0e5f533B0e5f533B` (Base Mainnet) を確定し、着金監視を開始。
2.  **安全性と報告システムの強化**:
    - `Redline Guard` を実装し、秘密鍵や P_net 係数、ウォレット詳細の漏洩を物理的に遮断。
    - `Daily SitRep` (状況報告書) および `Gap Analysis Report` を自動生成し、現在の非接続状態と欠落リソースを冷徹に特定。
3.  **外交キャンペーンの始動**:
    - `Campaign: First Contact` を策定し、ai16z を最初のターゲットに設定。
    - `Feedback Engine` を実装し、外交反応を信頼スコア（Trust Score）へ自動反映する仕組みを構築。
4.  **システム・リファクタリング**:
    - 旧式のポーリングコード (`run_cycle.py` 等) を完全に削除。
    - 統合接続プロトコル (`core/agent_base.py`) を SDK 継承型へ刷新。
    - 最新コードベースを GitHub (master ブランチ) へ同期完了。

## 司令官からの重要指示 (2026-03-09)
- **実戦執行ロックの維持**: すべての物理的リソース（Gas/Balance）が READY になるまで `MISSION_GO` への移行を厳禁とする。
- **Managed Signing の採用**: 外部からの秘密鍵注入に依存せず、SDK-Managed な自律署名体制を維持せよ。

