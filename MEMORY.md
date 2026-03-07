
4.  **Dual LLM Architecture (2026-03-07)**:
    - オーケストレーター (Neo) とサブエージェント (CrewAI) のLLMプロバイダを分離し、API競合とコストを最適化。
        - **Neo (Orchestrator)**: Google公式API (Gemini 2.0 Flash) を直接使用。`get_neo_llm()`
        - **Agents (Workers)**: OpenRouter経由 (Google Gemini 3 Flash Preview) を使用。`get_agent_llm()`
    - `core/config.py` に `get_neo_llm()` と `get_agent_llm()` を実装し、システム全体で使い分けを徹底。
