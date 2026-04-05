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
    # --- v6.5ai F1: short/mid/long 3プロファイル ---
    "short": {
        "sl_pct": 3.0,           # 損切り幅
        "trailing_start": 5.0,   # トレーリング開始
        "trailing_drop": 2.5,    # HWMからの下落で利確
        "hard_tp_pct": 14.0,     # 絶対上限TP
        "rsi_exit": 65,          # RSI出口閾値
        "time_limit_hours": 192, # 8日（短期戦略2-8日）
    },
    "mid": {
        "sl_pct": 5.0,
        "trailing_start": 10.0,
        "trailing_drop": 4.0,
        "hard_tp_pct": 25.0,
        "rsi_exit": 72,
        "time_limit_hours": 408, # 17日（中期戦略8-17日）
    },
    "long": {
        "sl_pct": 8.0,
        "trailing_start": 15.0,
        "trailing_drop": 6.0,
        "hard_tp_pct": 50.0,
        "rsi_exit": None,        # 長期はRSI出口無効
        "time_limit_hours": 1080, # 45日（長期戦略17-50日）
    },
}
EXIT_PROFILE_DEFAULT = "short"  # 未タグ時のフォールバック

# 戦略名 → 出口プロファイル マッピング（v6.5ai 3:3:3対応）
STRATEGY_TO_EXIT_PROFILE = {
    # 短期（2-8日）
    "macd_cross": "short",
    "mean_reversion": "short",
    "gplearn_evolved": "short",
    # 中期（8-17日）
    "triple_ma_cross": "mid",
    "ichimoku_cloud": "mid",
    "atr_breakout": "mid",
    # 長期（17-50日）
    "macro_value": "long",
    "golden_cross": "long",
    "dca_accumulation": "long",
}

# ============================================================
# 学習モード設定（Task F.1）
# ============================================================
LEARNING_MODE = True           # 100回取引達成まで有効
LEARNING_TARGET_TRADES = 100   # 目標取引数
LEARNING_SHARPE_THRESHOLD = 0.5  # 学習モード中の緩和Sharpeしきい値（通常5.0）

# ============================================================
# 相関分析ベース設定（v6.5ag — データ駆動型調整）
# ============================================================
# confidence→サイズ連動を無効化（データ: 高conf=47%勝率 vs 低conf=83%勝率）
FLAT_POSITION_SIZE = True      # True=全BUY一律5%, False=従来のconf連動(3-10%)
FLAT_SIZE_PCT = 0.05           # FLAT_POSITION_SIZE=True時のサイズ

# 時間帯スコア修正（データ: Asia67% > EU62% > US33%）
# 旧: Asia-10, EU+10, US+0 → 新: Asia+5, EU+5, US-10
TZ_SCORE_ASIA = 3              # v6.5an: 振れ幅縮小（出口防御で管理）
TZ_SCORE_EU = 3                # v6.5an: 振れ幅縮小（出口防御で管理）
TZ_SCORE_US = -3               # v6.5an: -10→-3 リスクは出口側で管理（二重減点排除）
