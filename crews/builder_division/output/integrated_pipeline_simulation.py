import logging
from typing import Optional
from dataclasses import dataclass
import random
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data classes for signals and configurations
@dataclass
class SentimentSignal:
    symbol: str
    sentiment_score: float
    confidence: float
    timestamp: datetime

@dataclass
class LiquiditySignal:
    symbol: str
    action: str  # "BUY", "SELL", or "HOLD"
    amount: float
    reason: str

class ProtocolBridge:
    def __init__(self):
        self.safety_checks_enabled = True
    
    def perform_safety_checks(self, signal: SentimentSignal) -> bool:
        """Simulate safety checks"""
        if not self.safety_checks_enabled:
            return True
            
        # Basic sanity checks
        if abs(signal.sentiment_score) > 1.0:
            logger.warning(f"Invalid sentiment score {signal.sentiment_score} for {signal.symbol}")
            return False
        if signal.confidence < 0 or signal.confidence > 1:
            logger.warning(f"Invalid confidence {signal.confidence} for {signal.symbol}")
            return False
        return True

class SentimentWorker:
    def __init__(self, symbols: list[str]):
        self.symbols = symbols
    
    def run_once(self) -> Optional[SentimentSignal]:
        """Simulate fetching sentiment data"""
        symbol = random.choice(self.symbols)
        sentiment_score = round(random.uniform(-1, 1), 2)
        confidence = round(random.uniform(0.5, 1.0), 2)
        
        # Occasionally return None to simulate no signal
        if random.random() < 0.1:
            return None
            
        return SentimentSignal(
            symbol=symbol,
            sentiment_score=sentiment_score,
            confidence=confidence,
            timestamp=datetime.now()
        )

class LiquidityWorker:
    def __init__(self, protocol_bridge: ProtocolBridge):
        self.protocol_bridge = protocol_bridge
        self.min_confidence = 0.7
        self.min_abs_score = 0.3
    
    def process_signal(self, signal: SentimentSignal) -> Optional[LiquiditySignal]:
        """Process sentiment signal and generate liquidity action"""
        logger.info(f"Processing sentiment signal: {signal}")
        
        # Perform safety checks
        if not self.protocol_bridge.perform_safety_checks(signal):
            logger.warning(f"Safety checks failed for {signal.symbol}")
            return None
        
        # Check if signal meets minimum thresholds
        if abs(signal.sentiment_score) < self.min_abs_score or signal.confidence < self.min_confidence:
            logger.info(f"Signal below thresholds (score: {signal.sentiment_score}, confidence: {signal.confidence})")
            return None
        
        # Determine action based on sentiment
        action = "BUY" if signal.sentiment_score > 0 else "SELL"
        amount = abs(signal.sentiment_score) * signal.confidence * 1000  # Simulate amount calculation
        
        return LiquiditySignal(
            symbol=signal.symbol,
            action=action,
            amount=amount,
            reason=f"Strong {action} signal (score: {signal.sentiment_score}, confidence: {signal.confidence})"
        )

def main():
    # Configuration
    symbols = ["BTC", "ETH", "SOL", "AVAX", "BNB"]
    
    # Instantiate workers
    protocol_bridge = ProtocolBridge()
    sentiment_worker = SentimentWorker(symbols)
    liquidity_worker = LiquidityWorker(protocol_bridge)
    
    # Run pipeline for 5 iterations
    for i in range(1, 6):
        print(f"\n=== Iteration {i} ===")
        
        # Step 1: Generate sentiment signal
        sentiment_signal = sentiment_worker.run_once()
        if sentiment_signal is None:
            print("No sentiment signal generated this iteration")
            continue
            
        print(f"Generated sentiment signal: {sentiment_signal}")
        
        # Step 2: Process signal through liquidity worker
        liquidity_signal = liquidity_worker.process_signal(sentiment_signal)
        
        if liquidity_signal:
            print(f"Liquidity action: {liquidity_signal.action} {liquidity_signal.amount} {liquidity_signal.symbol}")
            print(f"Reason: {liquidity_signal.reason}")
        else:
            print("No liquidity action taken (signal filtered by safety checks or thresholds)")

if __name__ == "__main__":
    main()
