import math
import logging

logger = logging.getLogger(__name__)

class NeoFinance:
    @staticmethod
    def calculate_slippage(amount_in: float, pool_liquidity: float) -> float:
        """注文サイズに基づくスリッページ影響の近似計算: Δx / (L + Δx)"""
        if pool_liquidity <= 0:
            return 1.0  # 流動性ゼロなら100%インパクト
        return amount_in / (pool_liquidity + amount_in)

    @staticmethod
    def estimate_net_profit(
        amount_in_usd: float,
        amount_out_usd: float,
        gas_cost_usd: float,
        dex_fee_rate: float = 0.003,
        pool_liquidity_usd: float = 0.0
    ) -> dict:
        """
        純利益 (P_net) の算出
        P_net = Amount_out_usd - Amount_in_usd - Gas_cost - Fees_dex - Slippage_impact
        """
        # 1. DEX手数料 (通常 0.3%)
        dex_fees = amount_out_usd * dex_fee_rate
        
        # 2. スリッページ影響の算出 (USDベースの流動性を使用)
        slippage_rate = NeoFinance.calculate_slippage(amount_in_usd, pool_liquidity_usd)
        slippage_impact_usd = amount_out_usd * slippage_rate
        
        # 3. 純利益の算出
        net_profit = amount_out_usd - amount_in_usd - gas_cost_usd - dex_fees - slippage_impact_usd
        
        return {
            "net_profit_usd": round(net_profit, 4),
            "is_profitable": net_profit > 0,
            "breakdown": {
                "amount_in_usd": round(amount_in_usd, 4),
                "amount_out_usd": round(amount_out_usd, 4),
                "dex_fees_usd": round(dex_fees, 4),
                "gas_cost_usd": round(gas_cost_usd, 4),
                "slippage_impact_usd": round(slippage_impact_usd, 4),
                "slippage_rate": round(slippage_rate, 6)
            }
        }
