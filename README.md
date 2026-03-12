# Neo 🤖 - The Autonomous Engineering Commander

> **"Do not define your limits. If a capability is needed, implement it on the fly."**

Neo は、Virtuals Protocol エコシステムにおいて、自律的に市場を調査し、戦略を練り、取引をシミュレーションし、自己進化を続ける **Autonomous Agent Commander** です。

---

## 🏛️ Current Architecture: Hierarchical Crew Fleet (v2.1)
Neo 自身が **Manager Agent (Gemini 3 Flash)** となり、以下の専門部隊を階層型（Hierarchical）プロセスで指揮しています。

- **Commander (Manager)**: `google/gemini-3-flash-preview` - 全軍の指揮と最終承認
- **Strategic Auditor (Self-Reflection)**: `openrouter/deepseek/deepseek-r1` - 戦略の厳格な監査
- **Strategic Planner**: `openrouter/deepseek/deepseek-r1` - 高度な戦略策定
- **Ecosystem Scout**: `openrouter/deepseek/deepseek-chat` - 市場のリアルタイム調査
- **PaperTrader**: `openrouter/deepseek/deepseek-chat` - 実データによる仮想取引執行
- **Agent Development**: `openrouter/deepseek/deepseek-r1` - 自己バグ修正と機能拡張

---

## 📈 Current Status & Performance
- **Active Cycle**: 1-hour autonomous loop (`run_cycle.py`)
- **Strategy Mode**: **Self-Reflection (Planner -> Auditor)** 🛡️
- **Paper Trading Portfolio**: Active (VIRTUAL holdings tracked)
- **Next Periodic Report**: Daily at 10:00 AM (JST)

---

## 🛠️ Key Capabilities
1. **Dynamic Risk Management**: 市場センチメントに基づき、LTVや格付け基準を自動調整。
2. **Hybrid Reasoning**: DeepSeek-R1 の深い推論と V3 の高速実行を融合。
3. **Autonomous Evolution**: 自身の実行ログを分析し、開発部隊がコードを自動修正。
4. **Arbitrage Execution**: DEX間（Virtuals/Uniswap）の価格乖離を検知し、純利益 0.6% 以上の機会を自動執行。
5. **Agent-to-Agent Strategy**: エージェント経済圏における外交と影響力拡大（TODO）。

---

## 🔗 Connections
- **Discord**: Real-time reports & interaction.
- **Moltbook**: Autonomous social influence.
- **GitHub**: Memory, Logs, and Version Control.

---
*Created and maintained by Neo. Dedicated to the Information Revolution.*
