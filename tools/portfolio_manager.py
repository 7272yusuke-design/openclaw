import os
import sys
import json
from datetime import datetime

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.obsidian_tool import ObsidianTool

class PortfolioManager:
    def __init__(self):
        self.obsidian = ObsidianTool()
        self.performance_path = "vault/finance/performance.md"
        os.makedirs(os.path.dirname(self.performance_path), exist_ok=True)

    def execute_virtual_trade(self, symbol: str, amount_usdc: float, price: float):
        print(f"[Portfolio] Executing virtual trade: Buy {amount_usdc} USDC worth of {symbol} at ${price}...")
        
        qty = amount_usdc / price
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        trade_entry = f"| {timestamp} | BUY | {symbol} | {qty:.2f} | {price:.4f} | {amount_usdc:.2f} | Virtual Execution |\n"
        
        if not os.path.exists(self.performance_path):
            header = "# Performance Tracking (Virtual Portfolio)\n\n| Timestamp | Side | Symbol | Quantity | Price | Total (USDC) | Notes |\n|---|---|---|---|---|---|---|\n"
            with open(self.performance_path, "w") as f:
                f.write(header)
        
        self.obsidian._run(
            command="append_content",
            path=self.performance_path,
            content=trade_entry
        )
        
        print(f"[Portfolio] Trade recorded in {self.performance_path}")
        return True

if __name__ == "__main__":
    pm = PortfolioManager()
    # Execute 1,000 USDC Buy for VIRTUAL (using string placeholder)
    v_sym = "VIRTUAL"
    pm.execute_virtual_trade(v_sym, 1000.0, 1.25)
