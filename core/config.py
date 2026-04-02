import os
from crewai import LLM

class NeoConfig:
    DEFAULT_AGENT_MODEL = "openrouter/google/gemini-2.0-flash-001"
    MODEL_EYES = DEFAULT_AGENT_MODEL
    MODEL_BRAIN = DEFAULT_AGENT_MODEL
    MODEL_CREATIVE = DEFAULT_AGENT_MODEL
    MODEL_HANDS = DEFAULT_AGENT_MODEL

    @staticmethod
    def setup_env():
        pass

def get_agent_llm(name=None):
    # すべてのエージェントに OpenRouter 経由の LLM を強制配布
    return LLM(
        model=NeoConfig.DEFAULT_AGENT_MODEL,
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )

def get_neo_llm():
    return get_agent_llm()

# ============================================================
# VP銘柄監視 3層設定（Task A.1）
# ============================================================
TIER0_SYMBOLS    = ["BTC", "ETH"]              # Tier0: メイン取引対象（Binance）
VP_TIER1_SYMBOLS = ["VIRTUAL", "AIXBT"]       # 常時監視 + Sweep最優先
VP_TIER2_SYMBOLS = ["TIBBIR", "ROBO"]          # Tier2: VP経済圏銘柄（60分Sweep対象）
VP_TIER3_SYMBOLS = ["ETH", "SOL", "BNB"]      # 日次Nightlyのみ

SWEEP_SYMBOLS         = VP_TIER1_SYMBOLS + VP_TIER2_SYMBOLS   # 通常Sweep
SWEEP_SYMBOLS_NIGHTLY = VP_TIER1_SYMBOLS + VP_TIER2_SYMBOLS + VP_TIER3_SYMBOLS  # Nightly
VOLATILITY_WATCH_SYMBOLS = VP_TIER1_SYMBOLS   # ボラティリティ監視
COUNCIL_ELIGIBLE_SYMBOLS = TIER0_SYMBOLS + VP_TIER1_SYMBOLS  # Council召集可能（Tier0+Tier1）

# ============================================================
# 学習モード設定（Task F.1）
# ============================================================
LEARNING_MODE = True           # 100回取引達成まで有効
LEARNING_TARGET_TRADES = 100   # 目標取引数
LEARNING_SHARPE_THRESHOLD = 0.5  # 学習モード中の緩和Sharpeしきい値（通常5.0）
