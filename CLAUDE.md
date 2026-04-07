# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neo is an autonomous cryptocurrency trading agent for the Virtuals Protocol ecosystem. It runs a 30-second market monitoring loop, executes simulated trades via PaperWallet, and self-improves through memory-driven learning (ChromaDB). Current version: **v6.5aq**.

**Language**: All code comments, logs, docs, and commit messages are in **Japanese**. Follow this convention.

## Running Services

Neo runs as 4 systemd services on a Hostinger VPS:

| Service | Entry Point | Purpose |
|---------|-------------|---------|
| `neo-radar` | `run_trigger.py` | Main 30s loop (market monitoring, TP/SL, Council calls) |
| `neo-collector` | `orchestration/data_collector.py` | 5min tick + 60min OHLCV market data collection |
| `neo-resource-api` | `tools/neo_resource_api.py` | FastAPI on port 8099 for ACP resources |
| `neo-acp-seller` | `skills/virtuals-protocol-acp/` | ACP WebSocket seller (Node.js) |

```bash
# Check logs
tail -f logs/radar_output.log

# Restart service
sudo systemctl restart neo-radar

# Run main loop manually (foreground, unbuffered)
python3 -u run_trigger.py
```

## Architecture

### Decision Pipeline: Trinity Council (`agents/trinity_council.py`)

The core decision engine runs 8 phases per cycle:

1. **Scout reconnaissance** — market data, whale monitoring
2. **Planning & onchain analysis** — VP data from DexScreener, macro flow
3. **Bull/Bear/Neo debate** — 3-agent consensus via LLM
4. **Scoring & gate application** — 6-layer risk gates (Sharpe, MaxDD, RR, etc.)
5. **PaperWallet execution** — simulated BUY/SELL with confidence-driven sizing
6. **Moltbook posting** — data-driven social posts
7. **Discord reporting** — structured alerts via webhooks
8. **Memory storage** — trade lessons to ChromaDB

### Main Loop (`run_trigger.py`)

Each 30-second tick checks:
- **Phase 0**: BTC risk (F2 levels L1-L3) with 5-layer exit stages
- **TP/SL**: Profit-taking and stop-loss on all holdings (Council-independent)
- **2h rotation**: Council召集 for BTC → VIRTUAL → ETH
- **60min**: Alpha sweep across SWEEP_SYMBOLS
- **6h**: Performance evaluation
- **JST 02:00**: Nightly batch (research, learning, content posting)

### Tier System (`core/config.py`)

- **Tier0** (BTC, ETH): Council-eligible, Binance data
- **Tier1** (VIRTUAL): Council-eligible, highest sweep priority
- **Tier2** (AIXBT, TIBBIR, ROBO): Sweep-only, VP ecosystem tokens
- **Tier3** (SOL, BNB): Nightly-only

Only `COUNCIL_ELIGIBLE_SYMBOLS` (Tier0 + Tier1) can trigger Trinity Council.

### Exit Profiles (`core/config.py`)

Strategy-tagged positions use profile-specific TP/SL:
- **short** (2-8d): SL -3%, TP +14%, trailing from 5%
- **mid** (8-17d): SL -5%, TP +25%, trailing from 10%
- **long** (17-50d): SL -8%, TP +50%, no RSI exit

### Self-Evolution Stack

8-layer learning pipeline: E1 (post-trade lessons) → E2 (Reflexion bias detection) → E3 (EvolveR rule generation) → Phase 1e (Voyager skill storage) → F5 (macro regime) → S1-S4 (strategy monitoring) → F2b (BTC macro cache)

## Key Modules

| Module | Path | Notes |
|--------|------|-------|
| Config | `core/config.py` | Tier definitions, exit profiles, learning mode thresholds |
| Blackboard | `core/blackboard.py` | Pydantic shared state → `vault/blackboard/live_intel.json` |
| Memory DB | `core/memory_db.py` | ChromaDB at `vault/chroma_db/` (write-only via Council Phase 8) |
| PaperWallet | `tools/paper_wallet.py` | Simulated trading, 100K USDC start, state at `data/paper_wallet.json` |
| Cost Guard | `core/cost_guard.py` | L1-L4 circuit breaker, daily $5 LLM spend limit |
| Market Data | `tools/market_data.py` | CoinGecko → Binance → DexScreener fallback chain |
| Model Factory | `core/model_factory.py` | LLM selection + cost tracking |

## LLM Configuration

- **Primary model**: `openrouter/google/gemini-2.0-flash-001` (via OpenRouter)
- **Fast model**: `gemini-2.5-flash` (MODEL_FAST)
- All agents share the same model; cost tracked per-call through `core/cost_guard.py`

## Data Persistence

| Data | Location | Format |
|------|----------|--------|
| Market prices | `vault/market_db/prices.sqlite` | SQLite (OHLCV + hourly) |
| Shared state | `vault/blackboard/live_intel.json` | JSON |
| Macro flow | `vault/blackboard/macro_flow.json` | JSON (SPY/Gold/DXY/Rates) |
| Trade memory | `vault/chroma_db/` | ChromaDB vector store |
| Paper positions | `data/paper_wallet.json` | JSON |
| Pair trade state | `vault/n1_pair_state.json` | JSON |
| API cost tracking | `vault/cost_guard_*.json` | JSON |

## External Integrations

- **Discord**: 4 webhooks (Report, Log, Dashboard, Nightly) — `tools/discord_reporter.py`
- **Moltbook**: Social posting with spam filters (2.5min interval) — `tools/moltbook_tool.py`
- **ACP**: 9 offerings in `skills/virtuals-protocol-acp/src/seller/offerings/`
- **Base Chain**: RPC via `BASE_RPC_URL` env var

## Environment Variables

All secrets in `.env` (not committed): `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, `DISCORD_WEBHOOK_*`, `BASE_RPC_URL`, `MOLTBOOK_*`, `GITHUB_TOKEN`, ACP wallet keys.

## Versioned Handoff Whitepapers

Each session produces a handoff doc at `docs/GSD計画_v6.5XX_引き継ぎ白書.md`. The latest (`v6_5aq`) contains current status, completed tasks, and next priorities. **Always read the latest whitepaper** before starting work to understand current state.

## Git Conventions

- Remote: `https://github.com/7272yusuke-design/openclaw` (master branch)
- Commit messages: version prefix + Japanese description (e.g., `v6.5aq: Moltbook投稿をデータ駆動に刷新`)
- 100MB file limit: keep `neo-env/` and large binaries in `.gitignore`

## Current Operating Mode

- **Learning Mode**: ON (target: 100 trades, Sharpe threshold ≥ 0.5)
- **Paper Trading**: Active (not live trading)
- **Live Trading**: NOT active (requires 60%+ win-rate sustained 3 months)

## 禁止事項

- CostGuardをreturn Trueで無効化しない
- Discovery銘柄でCouncil召集しない（バックテストデータ不足で常にWAITになる）
- Moltbookに取引推奨投稿（BUY/SELL/$金額）をしない（スパム判定される）
- system pythonでパッケージをインストールしない（`./neo-env/bin/python`を使う）
- Phase 3bの戦略書でrisk_pct > 6%のSL設定を許可しない

## 設計方針（変更不可）

- TrinityCouncilのBull/Bear/Neo三者構造は変えない
- ACP外部エージェントのシグナルは「参考情報注入のみ」（方針X）
- LLMのconfidenceは参考値のみ → Phase 4bルールベースで常に上書き
- AIXBTは取引対象外

## ファイル編集ルール

- 編集前に必ずバックアップを取る（`cp file.py file.py.bak_taskXX`）
- Python編集後は必ず構文チェック（`python -c "import ast; ast.parse(open('file.py').read())"`）
- 変更後はgit commitする
- バックアップファイルは`.archive_deadcode_v65p/`に移動する

## 環境ルール

- 作業ディレクトリ: `/config/workspace/neo`（code-server内パス。ホスト上は `/docker/openclaw-taan/data/.openclaw/workspace`）
- Python: `./neo-env/bin/python`（system pythonは不可）
- ACP CLI: `skills/virtuals-protocol-acp/` から `npx tsx bin/acp.ts`
- `.env`はgitにコミットしない

## 過去の重大バグ（再発防止）

- `fetch_ohlcv_custom`が合成データを返していた → Sharpe常時5.0超え → 修正済み
- TrinityCouncilがBUY後にテキスト生成のみで取引未実行 → 修正済み
- ChromaDBがAlpha Sweepノイズで汚染（59件→17件）→ 書き込みルール制定済み
- ACP `handlers.ts`が`request.requirements.X`で参照 → 全ジョブreject → v6.5j修正済み
- streak連敗ペナルティが48h経過後も残存 → v6.5rで48h完全解除に修正
- L4 DD計算が`holding.get("current_value",0)`でポジション評価額が常に0 → v6.5akで時価計算に修正
- `capital_flow_radar.py`が`macro_flow.json`を全上書き → macro_dataフィールド消失 → v6.5akでread-modify-write修正
- Phase 3bが`self.pro_model`（CrewAI用LangChain）の`generate_content()`を呼び出し → `ModelFactory.get_genai_model("critical")`に修正

## 重要なデータパス

- 市場データSQLite: `vault/market_db/prices.sqlite`（正規パス）
- `data/market_data.db` と `data/neo_market.db` は空。使わない
- Paper Wallet: `data/paper_wallet.json`
- マクロフロー: `vault/blackboard/macro_flow.json`

## セッション開始時

最新の引き継ぎ白書を読むこと:
```bash
cat "$(ls -t docs/GSD計画*.md | head -1)"
```
