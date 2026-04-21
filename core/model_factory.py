"""
ModelFactory — LLMモデルの一元管理（v6.5i）

用途別にモデルを使い分け:
  - critical: 三者協議の最終判断（Neo裁定者）→ 高品質モデル
  - standard: Bull/Bear議論、Scout偵察 → 標準モデル
  - fast: 要約、内省、ログ生成 → 軽量モデル

設定は.envのMODEL_*変数で上書き可能。
"""
import os
import litellm

# v6.5bd: litellm グローバルフォールバック設定
# 429時に自動で別モデルに切り替え
litellm.fallbacks = [
    {"openrouter/google/gemini-2.0-flash-001": ["openrouter/google/gemini-2.5-flash"]},
    {"openrouter/google/gemini-2.5-flash": ["openrouter/google/gemini-2.0-flash-001"]},
]
litellm.num_retries = 2
litellm.request_timeout = 60

# デフォルトモデル設定
_DEFAULTS = {
    "critical": "gemini-2.0-flash",    # 将来: gemini-2.0-pro等に変更可能
    "standard": "gemini-2.0-flash",
    "fast":     "gemini-2.0-flash",
}

class _GenaiModelWrapper:
    """google.genai SDK用ラッパー — 429リトライ+OpenRouterフォールバック付き (v6.5bd)"""
    def __init__(self, api_key: str, model_name: str):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._or_api_key = os.environ.get("OPENROUTER_API_KEY")

    def generate_content(self, prompt: str, **kwargs):
        import time, logging
        _log = logging.getLogger("neo.model_factory")
        # Try Gemini direct (up to 2 attempts)
        for attempt in range(2):
            try:
                return self._client.models.generate_content(
                    model=self._model_name, contents=prompt, **kwargs
                )
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "rate" in str(e).lower():
                    _log.warning(f"[ModelFactory] Gemini 429 (attempt {attempt+1}/2), retrying in 3s...")
                    time.sleep(3)
                    continue
                raise
        # Fallback: OpenRouter via litellm
        if self._or_api_key:
            _log.info(f"[ModelFactory] Gemini exhausted, falling back to OpenRouter/{self._model_name}")
            try:
                resp = litellm.completion(
                    model=f"openrouter/google/{ModelFactory._to_openrouter_id(self._model_name)}",
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self._or_api_key,
                    timeout=60,
                )
                return type("_FallbackResp", (), {"text": resp.choices[0].message.content})()
            except Exception as e2:
                _log.error(f"[ModelFactory] OpenRouter fallback also failed: {e2}")
                raise
        raise Exception("Gemini 429 and no OpenRouter key available")

class ModelFactory:
    """LLMモデルの一元管理"""

    @staticmethod
    def get_model_name(tier: str = "standard") -> str:
        """用途別モデル名を返す"""
        env_key = f"MODEL_{tier.upper()}"
        return os.environ.get(env_key, _DEFAULTS.get(tier, _DEFAULTS["standard"]))

    @staticmethod
    def get_langchain_model(tier: str = "standard"):
        """LangChain ChatGoogleGenerativeAIインスタンスを返す"""
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        model_name = ModelFactory.get_model_name(tier)
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    @staticmethod
    def get_genai_model(tier: str = "fast"):
        """google.genai SDK経由のGenerativeModelラッパーを返す（v6.5am移行）"""
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        model_name = ModelFactory.get_model_name(tier)
        return _GenaiModelWrapper(api_key=api_key, model_name=model_name)

    @staticmethod
    def get_openrouter_config(tier: str = "standard") -> dict:
        """OpenRouter用の設定を返す"""
        model_name = ModelFactory.get_model_name(tier)
        return {
            "model": f"openrouter/google/{model_name}",
            "api_key": os.environ.get("OPENROUTER_API_KEY"),
        }

    @staticmethod
    def _to_openrouter_id(model_name: str) -> str:
        """Geminiモデル名をOpenRouter IDに変換 (v6.5bd)"""
        # OpenRouterはバージョンサフィックス必須: gemini-2.0-flash → gemini-2.0-flash-001
        _or_map = {
            "gemini-2.0-flash": "gemini-2.0-flash-001",
            "gemini-2.5-flash": "gemini-2.5-flash",
        }
        return _or_map.get(model_name, model_name)

    @staticmethod
    def get_crewai_llm(tier: str = "standard"):
        """CrewAI LLM via OpenRouter (litellm経由 — 429フォールバック対応) v6.5bd"""
        from crewai import LLM
        model_name = ModelFactory.get_model_name(tier)
        or_api_key = os.environ.get('OPENROUTER_API_KEY')
        or_model = ModelFactory._to_openrouter_id(model_name)
        primary = f'openrouter/google/{or_model}'
        return LLM(
            model=primary,
            api_key=or_api_key,
            num_retries=2,
            timeout=60,
        )

    @staticmethod
    def summary() -> str:
        """現在のモデル設定サマリー"""
        return " / ".join(f"{t}={ModelFactory.get_model_name(t)}" for t in ["critical", "standard", "fast"])
