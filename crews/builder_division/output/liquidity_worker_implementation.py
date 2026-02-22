```python
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class ProtocolBridge:
    """Mock ProtocolBridge class for blockchain interactions"""
    
    def add_liquidity(self, token_pair: str, amount: float) -> Dict:
        """Simulate adding liquidity to a pool"""
        return {
            'status': 'success',
            'transaction_hash': f'0x{token_pair[:8]}{int(time.time())}',
            'amount': amount
        }
    
    def remove_liquidity(self, token_pair: str, amount: float) -> Dict:
        """Simulate removing liquidity from a pool"""
        return {
            'status': 'success',
            'transaction_hash': f'0x{token_pair[:8]}{int(time.time())}',
            'amount': amount
        }
    
    def get_portfolio_value(self) -> float:
        """Simulate getting current portfolio value"""
        return 10000.0  # Mock value
    
    def get_liquidity(self, token_pair: str) -> float:
        """Simulate getting current pool liquidity"""
        return 50000.0  # Mock value


class LiquidityWorker:
    """Automated liquidity management with safety controls"""
    
    def __init__(self, protocol_bridge: ProtocolBridge, config: Dict):
        """
        Initialize the liquidity worker with safety parameters.
        
        Args:
            protocol_bridge: ProtocolBridge instance for blockchain interactions
            config: Dictionary containing:
                - max_daily_spend: Maximum daily liquidity addition (USD)
                - stop_loss_threshold: Portfolio value threshold to halt trading (USD)
                - min_liquidity: Minimum required pool liquidity (USD)
                - base_amount: Base trade size (USD)
                - max_amount: Maximum trade size (USD)
        """
        self.bridge = protocol_bridge
        self.max_daily_spend = config['max_daily_spend']
        self.stop_loss_threshold = config['stop_loss_threshold']
        self.min_liquidity = config['min_liquidity']
        self.base_amount = config['base_amount']
        self.max_amount = config['max_amount']
        
        # Tracking state
        self.daily_spend = 0.0
        self.last_reset_time = datetime.now()
        self.trading_active = True
        
    def _check_daily_limit(self) -> bool:
        """Check if daily spending limit is reached and reset if needed"""
        now = datetime.now()
        if now - self.last_reset_time > timedelta(days=1):
            self.daily_spend = 0.0
            self.last_reset_time = now
            return True
        return self.daily_spend < self.max_daily_spend
    
    def _check_stop_loss(self) -> bool:
        """Check if portfolio has hit stop loss threshold"""
        portfolio_value = self.bridge.get_portfolio_value()
        return portfolio_value >= self.stop_loss_threshold
    
    def _check_liquidity(self, token_pair: str) -> bool:
        """Check if pool has sufficient liquidity"""
        liquidity = self.bridge.get_liquidity(token_pair)
        return liquidity >= self.min_liquidity
    
    def _calculate_trade_size(self, confidence: float) -> float:
        """Calculate trade size based on confidence score"""
        return self.base_amount + (self.max_amount - self.base_amount) * confidence
    
    def process_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Process a trading signal and execute liquidity action if conditions are met.
        
        Args:
            signal: Dictionary containing:
                - action: 'BUY' or 'SELL'
                - token_pair: Trading pair (e.g., 'ETH-USDC')
                - confidence: Confidence score (0.0 to 1.0)
        
        Returns:
            Dictionary with transaction details or None if trade was blocked
        """
        # Check safety conditions
        if not self.trading_active:
            print("Trading halted due to safety conditions")
            return None
            
        if not self._check_stop_loss():
            self.trading_active = False
            print("Stop loss triggered! Trading halted")
            return None
            
        if not self._check_daily_limit():
            print("Daily spending limit reached")
            return None
            
        if not self._check_liquidity(signal['token_pair']):
            print("Insufficient pool liquidity")
            return None
            
        # Calculate trade size
        trade_size = self._calculate_trade_size(signal['confidence'])
        
        # Execute trade
        if signal['action'] == 'BUY':
            if self.daily_spend + trade_size > self.max_daily_spend:
                trade_size = self.max_daily_spend - self.daily_spend
                if trade_size <= 0:
                    return None
                    
            result = self.bridge.add_liquidity(signal['token_pair'], trade_size)
            self.daily_spend += trade_size
            return result
            
        elif signal['action'] == 'SELL':
            result = self.bridge.remove_liquidity(signal['token_pair'], trade_size)
            return result
            
        else:
            raise ValueError(f"Invalid action: {signal['action']}")


# Demonstration
if __name__ == "__main__":
    # Configuration
    config = {
        'max_daily_spend': 10000.0,
        'stop_loss_threshold': 5000.0,
        'min_liquidity': 10000.0,
        'base_amount': 100.0,
        'max_amount': 1000.0
    }
    
    # Initialize
    bridge = ProtocolBridge()
    worker = LiquidityWorker(bridge, config)
    
    # Simulate signals
    signals = [
        {'action': 'BUY', 'token_pair': 'ETH-USDC', 'confidence': 0.7},
        {'action': 'SELL', 'token_pair': 'ETH-USDC', 'confidence': 0.8},
        {'action': 'BUY', 'token_pair': 'ETH-USDC', 'confidence': 0.9},
    ]
    
    # Process signals
    for signal in signals:
        print(f"\nProcessing signal: {signal}")
        result = worker.process_signal(signal)
        if result:
            print("Trade executed:", result)
        else:
            print("Trade blocked by safety controls")
            
    # Print daily spend tracking
    print(f"\nDaily spend so far: ${worker.daily_spend:.2f} of ${worker.max_daily_spend:.2f}")
```