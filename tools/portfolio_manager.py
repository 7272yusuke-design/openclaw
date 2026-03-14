"""
PortfolioManager v2 — PaperWalletを正としたシングルウォレットシステム
旧: 2つの独立したウォレット（paper_balance.json + paper_wallet.json）
新: PaperWalletに統一し、PortfolioManagerはそのインターフェースとして機能
"""
import os
import json
import logging
from tools.paper_wallet import PaperWallet

logger = logging.getLogger("neo.portfolio")

# 統一ウォレットパス
WALLET_PATH = "/docker/openclaw-taan/data/.openclaw/workspace/data/paper_wallet.json"

class PortfolioManager:
    """PaperWalletへの統一インターフェース"""
    
    def __init__(self, mode=None):
        self.mode = mode or os.getenv("NEO_MODE", "PAPER")
        self.wallet = PaperWallet(data_path=WALLET_PATH, initial_balance=10000.0)
    
    def get_balance(self) -> dict:
        """統一フォーマットで残高を返す（旧互換: USDC, SOL等のキー）"""
        usd = self.wallet.get_balance()
        holdings = self.wallet.state.get("holdings", {})
        
        result = {"USDC": round(usd, 2)}
        for symbol, data in holdings.items():
            result[symbol] = round(data.get("amount", 0.0), 6)
        
        return result
    
    def get_full_state(self) -> dict:
        """ウォレットの完全な状態を返す"""
        return self.wallet.state
    
    def get_portfolio_value(self, prices: dict) -> float:
        """全資産のUSD評価額"""
        return self.wallet.get_portfolio_value(prices)
    
    def execute_trade(self, symbol: str, action: str, amount_usd: float, price: float, reason: str = "") -> dict:
        """取引実行のパススルー"""
        return self.wallet.execute_trade(symbol, action, amount_usd, price, reason)
    
    def calculate_position_size(self, confidence_score: float) -> float:
        """信頼度に基づく投入額の計算"""
        available = self.wallet.get_balance()
        max_risk_ratio = 0.10  # 残高の最大10%
        return round(available * max_risk_ratio * confidence_score, 2)
    
    def get_recent_trades(self, n: int = 5) -> list:
        """直近n件の取引履歴"""
        history = self.wallet.state.get("history", [])
        return history[-n:] if history else []
    
    def get_trade_count(self) -> int:
        """総取引回数"""
        return len(self.wallet.state.get("history", []))
