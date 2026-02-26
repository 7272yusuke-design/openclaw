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
                self.state["holdings"][symbol] = {"amount": 0.0, "avg_price": 0.0}
            
            current_holding = self.state["holdings"][symbol]
            # Update Average Price (Weighted Average)
            total_cost = (current_holding["amount"] * current_holding["avg_price"]) + amount_usd
            new_amount = current_holding["amount"] + token_amount
            current_holding["avg_price"] = total_cost / new_amount
            current_holding["amount"] = new_amount

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

    def reset(self):
        """Resets the wallet to initial state."""
        self._init_new_wallet()
