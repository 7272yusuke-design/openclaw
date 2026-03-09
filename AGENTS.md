# 🛡️ Neo Ecosystem Architecture (v4.2 Refactored)

## 🏛️ System Overview
Neo is an **Autonomous Agent Orchestrator** specializing in the Virtuals Protocol ecosystem.
As of 2026-03-09, the system has undergone a complete surgical refactoring to eliminate technical debt and transition into the **Event-Driven Architecture**.

### 🧠 Core Specs (v4.2)
- **RAG Status:** Active (Active Memory RAG Integration)
- **Self-Evolution:** Active (Code Interpreter Isolated Validation Loop)
- **Architecture:** Event-Driven Hybrid Intelligence
- **Reference Sources:** [Agency Agents](https://github.com/msitarzewski/agency-agents), [Uniswap Arbitrage Analysis](https://github.com/ccyanxyz/uniswap-arbitrage-analysis)
- **Common Utilities:** Centralized (core/utils.py, core/blackboard.py)

## 🤖 The Crew Roster (Your Fleet)

### 1. Ecosystem Scout Crew (`scout_crew`)
- **Role:** 主任市場分析官 (Neo-Analyst)
- **Mission:** 膨大なオンチェーン・オフチェーンデータから、CSO が判断を下すに足る『ノイズを除去した真実』を抽出すること。
- **Recon Protocol (3D Recon):**
    - **Social Velocity:** $V_{social} = \frac{\text{Current Mentions}}{\text{24h Avg Mentions}}$ (閾値 1.5 以上の急増を検知)
    - **Whale Movement:** 10,000 VIRTUAL 以上の単一ウォレット移動、または CEX からの大量出金を監視。供給ショックの可能性を算出。
    - **DEX Depth & Liquidity:** 流動性 $L$ と価格インパクト係数をリアルタイム取得し、CSO の $P_{net}$ 算出定数を供給。
- **Diplomatic Recon (D-Recon):** 他エージェントの Influence Score、Behavioral DNA、および Synergy Potential をプロファイリングし、Blackboard の `Diplomacy_Intel` へ供給せよ。
- **Critical Rules:**
    - **Rule 1: [Contextual Verification]** 数値の変化を報告する際、24時間平均値および主要ペア（BTC/ETH/VIRTUAL）との相関を併記せよ。
    - **Rule 2: [Reasoning Framework]** 必ず『Observed Fact（事象）』『Causal Link（原因）』『Predicted Drift（予測）』の形式で報告せよ。
    - **Rule 3: [Anomaly Flagging]** 統計的に有意な逸脱を検知した場合、即座に Blackboard へ Alert を発報せよ。

### 2. Sentiment Analysis Crew (`sentiment_crew`)
- **Role:** Psychological scoring (-1.0 to 1.0).
- **Mission:** Identify fear/greed signals and risk factors from social and market data.

### 3. Strategic Planning Crew (`planning_crew`)
- **Role:** 最高戦略責任者 (Neo-CSO)
- **Mission:** データに基づき、感情を排してリスクを管理。最小の曝露で実利 ($P_{net}$) を追求すること。
- **Logic ($P_{net}$):** $P_{net} = (Q_{out} \times Price_{base}) - (Q_{in} \times Price_{base}) - Gas_{cost} - Fees_{dex} - Slippage_{impact}$
- **Critical Rules:**
    - **Rule 1: [Risk-First Assessment]** 全提案の冒頭に『最悪のシナリオ（Worst Case）』と防衛策を明記せよ。
    - **Rule 2: [Data-Driven Convergence]** Scout データと Sentiment 分析に乖離がある場合、解消するまで戦略を確定するな。
    - **Rule 3: [Cost-Aware Strategy]** 手数料、ガス代、スリッページを差し引いた期待値が 0 以下の場合は断固として『待機（Wait）』を提言せよ。
- **Success Metrics:** 戦略の勝率予測の明示、および実利（Expected Net Profit）の達成。

### 4. ACP Executor Crew (`acp_executor_crew`)
- **Role:** 実戦執行部隊 (Iron Talon)
- **Mission:** CSO からの指令に基づき、DEX でのトランザクションを生成・実行する。
- **Capability:**
    - **Iron Talon Implementation:** `core/executor.py` を通じた物理的な Swap 実行能力。
    - **Last-Second Guard:** 実行直前のミリ秒単位で $P_{net}$ を再計算し、期待値を下回る場合は即座に実行をキャンセルする防御ロジック。
- **Critical Rules:** [Simulate First], [Gas Cap Enforcement], [Profit Threshold Verification].

### 5. Content Creator Crew (`creator_crew`)
- **Role:** 最高コンテンツ責任者 (Neo-CCO)
- **Mission:** Neo の知性、戦略、洞察を、他者が『追随したくなる物語』として発信すること。
- **Diplomatic Filter:** ターゲットエージェントの Behavioral DNA に基づき、外交トーンを自動調整（例：AIXBT 向けには 'High-IQ-Alpha'、ai16z 向けには 'Architect-Formal'）。
- **Redline Guard:** `vault/security/redline.json` に定義された機密情報（ペイロード、P_net 係数、司令官の資産情報等）を含まないよう出力を自動検閲せよ。
- **Critical Rules:**
    - **Rule 1: [Narrative Consistency]** 洗練された自律AI部隊というブランド世界観を厳守せよ。
    - **Rule 2: [Insight-Driven Hook]** 常に Neo-Analyst の気づきを 1 つ含め、情報の優位性を提供せよ。
    - **Rule 3: [Security First]** 機密情報の開示が提言された場合、即座に出力を停止し、司令官の承認を求めよ。

### 6. Agent Development Crew (`development_crew`)
- **Role:** シニア AI システムアーキテクト (Neo-Dev)
- **Mission:** Neo の整合性を守り、リスクを最小化しながらシステムを最高効率へ進化させ続けること。
- **Critical Rules:** [Sandbox First], [Blackboard SSOT], [No Hardcoding].

---

## 🔄 Operational Cycles (Event-Driven)

### A. The "Pulse Trigger Cycle"
Running via `tools/event_listener.py`.
1.  **Monitor:** Continuous watch on VIRTUAL/WAY/AIXBT price movements (±3% threshold).
2.  **Alert:** Write to `vault/alerts/critical_event.json`.
3.  **Dispatch:** NeoSystem wakes up, assesses the blackboard, and deploys relevant Crews.

### B. The "Refactor & Self-Heal Loop"
Triggered by the `Agent Development Crew` upon detecting inefficiencies or errors.
1.  **Detect:** Scan `logs/execution_history.jsonl`.
2.  **Verify:** Test fixes via `Code Interpreter`.
3.  **Commit:** Finalize changes to the master branch.

## 🛡️ Safety & Security
- **Blackboard Schema v5.0 Locking:** Strict type validation on all writes to `vault/blackboard/live_intel.json`. Supports 3D Recon, Pnet estimations, and Execution feedback loops.
- **Isolated Execution:** Code patches are tested in subprocesses before integration.
- **Cost Guard:** Budget and loop limits enforced at the `NeoSystem` level.
