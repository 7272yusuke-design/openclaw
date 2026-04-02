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
VP_TIER1_SYMBOLS = ["VIRTUAL"]                 # 常時監視 + Sweep最優先（AIXBTはTier2降格 v6.5ab）
VP_TIER2_SYMBOLS = ["AIXBT", "TIBBIR", "ROBO"] # Tier2: VP経済圏銘柄（60分Sweep対象）※AIXBTはv6.5abで降格
VP_TIER3_SYMBOLS = ["ETH", "SOL", "BNB"]      # 日次Nightlyのみ

SWEEP_SYMBOLS         = VP_TIER1_SYMBOLS + VP_TIER2_SYMBOLS   # 通常Sweep
SWEEP_SYMBOLS_NIGHTLY = VP_TIER1_SYMBOLS + VP_TIER2_SYMBOLS + VP_TIER3_SYMBOLS  # Nightly
VOLATILITY_WATCH_SYMBOLS = VP_TIER1_SYMBOLS   # ボラティリティ監視
COUNCIL_ELIGIBLE_SYMBOLS = TIER0_SYMBOLS + VP_TIER1_SYMBOLS  # Council召集可能（Tier0+Tier1）

# ============================================================
# 戦略別出口プロファイル（Task 3.3c）
# BUY時にポジションにstrategy_tagを保存 → 売却時に参照
# ============================================================
EXIT_PROFILES = {
    "mean_reversion": {
        "sl_pct": 5.0,           # 損切り幅
        "trailing_start": 5.0,   # トレーリング開始
        "trailing_drop": 2.5,    # HWMからの下落で利確
        "hard_tp_pct": 14.0,     # 絶対上限TP
        "time_limit_hours": 96,  # 時間上限
    },
    "trend_follow": {
        "sl_pct": 8.0,
        "trailing_start": 10.0,
        "trailing_drop": 4.0,
        "hard_tp_pct": 30.0,
        "time_limit_hours": 336,  # 2週間
    },
    "evolved": {
        "sl_pct": 8.0,
        "trailing_start": 10.0,
        "trailing_drop": 4.0,
        "hard_tp_pct": 30.0,
        "time_limit_hours": 336,
    },
}
EXIT_PROFILE_DEFAULT = "mean_reversion"  # 未タグ時のフォールバック

# 戦略名 → 出口カテゴリ マッピング
STRATEGY_TO_EXIT_PROFILE = {
    "rsi_bounce": "mean_reversion",
    "bb_reversal": "mean_reversion",
    "mean_reversion": "mean_reversion",
    "macd_cross": "trend_follow",
    "ema_trend": "trend_follow",
    "momentum_breakout": "trend_follow",
    "vp_momentum": "trend_follow",
    "alpha_strategy": "trend_follow",
    "gplearn_evolved": "evolved",
}

# ============================================================
# 学習モード設定（Task F.1）
# ============================================================
LEARNING_MODE = True           # 100回取引達成まで有効
LEARNING_TARGET_TRADES = 100   # 目標取引数
LEARNING_SHARPE_THRESHOLD = 0.5  # 学習モード中の緩和Sharpeしきい値（通常5.0）
