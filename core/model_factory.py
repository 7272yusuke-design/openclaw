"""
ModelFactory — LLMモデルの一元管理（v6.5i）

用途別にモデルを使い分け:
  - critical: 三者協議の最終判断（Neo裁定者）→ 高品質モデル
  - standard: Bull/Bear議論、Scout偵察 → 標準モデル
  - fast: 要約、内省、ログ生成 → 軽量モデル

設定は.envのMODEL_*変数で上書き可能。
"""
import os

# デフォルトモデル設定
_DEFAULTS = {
    "critical": "gemini-2.0-flash",    # 将来: gemini-2.0-pro等に変更可能
    "standard": "gemini-2.0-flash",
    "fast":     "gemini-2.0-flash",
}

class _GenaiModelWrapper:
    """google.genai SDK用ラッパー — 旧generate_content()インターフェースを維持"""
    def __init__(self, api_key: str, model_name: str):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def generate_content(self, prompt: str, **kwargs):
        return self._client.models.generate_content(
            model=self._model_name, contents=prompt, **kwargs
        )

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
    def summary() -> str:
        """現在のモデル設定サマリー"""
        return " / ".join(f"{t}={ModelFactory.get_model_name(t)}" for t in ["critical", "standard", "fast"])
