# LLM Infrastructure Specification

## 1. Orchestrator (Neo Main Brain)
- **Model**: Gemini 3 Flash
- **Connection**: Direct Google AI API (Native)
- **Primary Key**: GEMINI_API_KEY

## 2. Worker Agents (CrewAI)
- **Model**: Gemini 3 Flash
- **Connection**: OpenRouter (OpenAI-compatible)
- **Primary Key**: OPENROUTER_API_KEY

## 3. Note
- 司令官（Neo自身）はGoogle公式APIを直接叩いています。
- 裏側のエージェントたちはOpenRouterを経由して並列実行されています。
