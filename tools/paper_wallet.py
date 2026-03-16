import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class PaperWallet:
    """
    Manages a simulated crypto wallet for Paper Trading.
    Tracks USD balance, token holdings, and transaction history.
    """
    def __init__(self, data_path: str = "data/paper_wallet.json", initial_balance: float = 100000.0):
        self.data_path = data_path
        self.initial_balance = initial_balance
        self._load_wallet()

    def _load_wallet(self):
        """Loads wallet state from JSON or initializes a new one."""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    self.state = json.load(f)
            except json.JSONDecodeError:
                self._init_new_wallet()
        else:
            self._init_new_wallet()

    def _init_new_wallet(self):
        """Initializes a fresh wallet with starting capital."""
        self.state = {
            "usd_balance": self.initial_balance,
            "holdings": {},  # e.g., {"VIRTUAL": {"amount": 100, "avg_price": 2.5}}
            "history": [],
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        self._save_wallet()

    def _save_wallet(self):
        """Saves current state to JSON."""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        self.state["last_updated"] = datetime.utcnow().isoformat()
        with open(self.data_path, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_balance(self) -> float:
        return self.state["usd_balance"]

    def get_holding(self, symbol: str) -> float:
        return self.state["holdings"].get(symbol, {}).get("amount", 0.0)

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculates total value (USD + Value of Holdings)."""
        total = self.state["usd_balance"]
        for symbol, data in self.state["holdings"].items():
            price = current_prices.get(symbol, 0.0)
            total += data["amount"] * price
        return total

    def execute_trade(self, symbol: str, action: str, amount_usd: float, price: float, reason: str = "") -> Dict:
        """
        Executes a simulated trade.
        action: "BUY" or "SELL"
        amount_usd: Amount in USD to buy/sell
        price: Current token price
        """
        timestamp = datetime.utcnow().isoformat()
        token_amount = amount_usd / price

        if action.upper() == "BUY":
            if self.state["usd_balance"] < amount_usd:
                return {"status": "failed", "reason": "Insufficient USD funds"}
            
            # Update Balance
            self.state["usd_balance"] -= amount_usd
            
            # Update Holdings
            if symbol not in self.state["holdings"]:
                self.state["holdings"][symbol] = {"amount": 0.0, "avg_price": 0.0, "entry_time": timestamp}
            
            current_holding = self.state["holdings"][symbol]
            # Update Average Price (Weighted Average)
            total_cost = (current_holding["amount"] * current_holding["avg_price"]) + amount_usd
            new_amount = current_holding["amount"] + token_amount
            current_holding["avg_price"] = total_cost / new_amount
            current_holding["amount"] = new_amount
            current_holding["entry_time"] = current_holding.get("entry_time", timestamp)

        elif action.upper() == "SELL":
            current_holding = self.state["holdings"].get(symbol, {"amount": 0.0})
            if current_holding["amount"] < token_amount:
                # Sell all if not enough (simple logic for now, or fail)
                token_amount = current_holding["amount"]
                amount_usd = token_amount * price # Recalculate USD based on actual holdings
            
            if token_amount <= 0:
                 return {"status": "failed", "reason": "No holdings to sell"}

            # Update Balance
            self.state["usd_balance"] += amount_usd
            
            # Update Holdings
            current_holding["amount"] -= token_amount
            if current_holding["amount"] < 1e-6: # Cleanup dust
                del self.state["holdings"][symbol]

        # Log Transaction
        tx = {
            "timestamp": timestamp,
            "symbol": symbol,
            "action": action,
            "price": price,
            "amount_token": token_amount,
            "amount_usd": amount_usd,
            "reason": reason
        }
        self.state["history"].append(tx)
        self._save_wallet()
        
        return {"status": "success", "tx": tx}

    def get_unrealized_pnl(self, symbol: str, current_price: float) -> Dict:
        """Returns unrealized P&L for a position."""
        holding = self.state["holdings"].get(symbol)
        if not holding or holding["amount"] <= 0:
            return {"symbol": symbol, "amount": 0.0, "avg_price": 0.0, "current_price": current_price, "pnl_usd": 0.0, "pnl_pct": 0.0}
        amount = holding["amount"]
        avg_price = holding["avg_price"]
        pnl_usd = (current_price - avg_price) * amount
        pnl_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0.0
        return {
            "symbol": symbol,
            "amount": amount,
            "avg_price": avg_price,
            "current_price": current_price,
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct, 2),
            "entry_time": holding.get("entry_time", "")
        }

    def get_portfolio_summary(self, prices: Dict[str, float]) -> Dict:
        """Returns full portfolio P&L summary across all positions."""
        positions = []
        total_pnl_usd = 0.0
        total_value = self.state["usd_balance"]
        for symbol, holding in self.state["holdings"].items():
            price = prices.get(symbol, 0.0)
            pnl = self.get_unrealized_pnl(symbol, price)
            position_value = holding["amount"] * price
            total_value += position_value
            total_pnl_usd += pnl["pnl_usd"]
            positions.append({**pnl, "position_value_usd": round(position_value, 2)})
        return {
            "usd_balance": self.state["usd_balance"],
            "total_value_usd": round(total_value, 2),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "positions": positions
        }

    def should_take_profit(self, symbol: str, current_price: float, target_pct: float = 20.0) -> bool:
        """Returns True if position has reached take-profit threshold."""
        pnl = self.get_unrealized_pnl(symbol, current_price)
        return pnl["pnl_pct"] >= target_pct

    def should_stop_loss(self, symbol: str, current_price: float, stop_pct: float = 10.0) -> bool:
        """Returns True if position has hit stop-loss threshold."""
        pnl = self.get_unrealized_pnl(symbol, current_price)
        return pnl["pnl_pct"] <= -stop_pct

    def reset(self):
        """Resets the wallet to initial state."""
        self._init_new_wallet()
