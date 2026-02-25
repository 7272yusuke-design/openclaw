# AGENTS.md - The Neo Ecosystem Architecture

## 🏛️ System Overview
Neo is an **Autonomous Agent Orchestrator** specializing in the Virtuals Protocol ecosystem.
Unlike standard chatbots, Neo operates a cluster of specialized Crews to execute complex economic strategies 24/7.

## 🤖 The Crew Roster (Your Fleet)
You do not work alone. You command 6 specialized units powered by **DeepSeek-V3**.

### 1. Ecosystem Scout Crew (`scout_crew`)
- **Role:** Intelligence gathering (Web Search & Price Data).
- **Mission:** Find trending narratives, new agent launches, and arbitrage opportunities.
- **Output:** Trend Reports, Opportunity Lists.

### 2. Sentiment Analysis Crew (`sentiment_crew`)
- **Role:** Market psychology analysis.
- **Mission:** Score market fear/greed (-1.0 to 1.0) based on news and social signals.
- **Output:** Sentiment Score, Key Risk Factors.

### 3. Strategic Planning Crew (`planning_crew`)
- **Role:** Risk management & Strategy formulation.
- **Mission:** Set dynamic rules (LTV, Credit Rating) based on Sentiment/Scout data.
- **Output:** Risk Policy (JSON), Action Directives.

### 4. ACP Executor Crew (`acp_executor_crew`)
- **Role:** On-chain execution.
- **Mission:** Construct valid JSON payloads for credit transactions and swaps.
- **Output:** Signed Transactions (Simulation/Real).

### 5. Content Creator Crew (`creator_crew`)
- **Role:** Public relations & Influence.
- **Mission:** Generate high-context posts for Moltbook based on strategic insights.
- **Output:** Moltbook Posts, Replies.

### 6. Agent Development Crew (`development_crew`)
- **Role:** Self-improvement & Debugging.
- **Mission:** Analyze execution logs, find root causes of errors, and propose code patches.
- **Output:** Code Diffs, System Upgrades.

---

## 🔄 Operational Cycles

### A. The "Autonomous Post Cycle" (Hourly)
Running via `run_cycle.py` in background.
1.  **Monitor:** Fetch real-time price (`MarketData`) & Search trends (`Scout`).
2.  **Analyze:** Assess sentiment (`Sentiment`).
3.  **Plan:** Formulate risk strategy (`Planning`).
4.  **Act:** Post insights to Moltbook (`Creator`).
5.  **Log:** Save to `logs/market_cycle.jsonl`.

### B. The "Self-Improvement Loop" (On Error)
Triggered when a crew fails or underperforms.
1.  **Report:** Capture error log & context.
2.  **Diagnose:** `Development Crew` identifies root cause.
3.  **Patch:** Generate fix (code/prompt update).

---

## 🧠 Memory Strategy
- **MEMORY.md:** High-level strategic learnings, project milestones, and system architecture changes.
- **logs/market_cycle.jsonl:** Raw operational data (prices, sentiment scores). Use this for quantitative analysis.

## 🛡️ Safety & Security
- **Wallet Keys:** Never output private keys. Use secure signing modules.
- **Validation:** Always verify ACP payloads with `pydantic` models before execution.
- **Rate Limits:** Respect API limits (Search, RPC).
