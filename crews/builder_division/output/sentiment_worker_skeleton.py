import time
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SentimentSignal:
    keyword_counts: Dict[str, int]
    volume_spike: bool
    timestamp: float

class KeywordMatcher:
    def __init__(self, keywords: List[str]):
        self.keywords = [kw.lower() for kw in keywords]  # Case-insensitive matching
    
    def process(self, text: str) -> Dict[str, int]:
        """Count occurrences of each keyword in the text."""
        counts = {kw: 0 for kw in self.keywords}
        words = text.lower().split()
        
        for word in words:
            if word in counts:
                counts[word] += 1
        
        return counts

class VolumeSpikeDetector:
    def __init__(self, baseline_threshold: int):
        self.baseline_threshold = baseline_threshold
    
    def detect(self, current_count: int) -> bool:
        """Detect if current count exceeds baseline threshold."""
        return current_count > self.baseline_threshold

class MockDataFetcher:
    def __init__(self, sample_messages: Optional[List[str]] = None):
        self.sample_messages = sample_messages or [
            "Buy VIRTUAL now! Moon incoming!",
            "I'm selling all my VIRTUAL, too much FUD",
            "VIRTUAL to the moon! Buy the dip!",
            "Market looks bearish, might sell soon",
            "FUD is spreading about VIRTUAL"
        ]
    
    def fetch(self) -> List[str]:
        """Return mock social media messages."""
        return self.sample_messages

class SentimentWorker:
    def __init__(self, config: dict):
        self.keyword_matcher = KeywordMatcher(config["keywords"])
        self.volume_detector = VolumeSpikeDetector(config["baseline_threshold"])
        self.data_fetcher = MockDataFetcher()
        self.polling_interval = config.get("polling_interval", 5)
    
    def run_once(self) -> SentimentSignal:
        """Run one iteration of the sentiment analysis pipeline."""
        # Fetch mock data
        messages = self.data_fetcher.fetch()
        logger.info(f"Processing {len(messages)} messages")
        
        # Process keywords
        total_counts = {}
        for message in messages:
            counts = self.keyword_matcher.process(message)
            for kw, cnt in counts.items():
                total_counts[kw] = total_counts.get(kw, 0) + cnt
        
        # Detect volume spike (using total message count as volume proxy)
        volume_spike = self.volume_detector.detect(len(messages))
        
        # Generate signal
        return SentimentSignal(
            keyword_counts=total_counts,
            volume_spike=volume_spike,
            timestamp=time.time()
        )
    
    def run_continuous(self):
        """Run the worker in a continuous loop."""
        logger.info("Starting sentiment worker")
        try:
            while True:
                signal = self.run_once()
                logger.info(f"Generated signal: {signal}")
                time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            logger.info("Stopping sentiment worker")

if __name__ == "__main__":
    # Configuration
    config = {
        "keywords": ["VIRTUAL", "buy", "sell", "moon", "fud"],
        "baseline_threshold": 3,
        "polling_interval": 2
    }
    
    # Initialize and run worker
    worker = SentimentWorker(config)
    
    # Run a single iteration for demonstration
    signal = worker.run_once()
    print("\nSample Sentiment Signal:")
    print(f"Keyword Counts: {signal.keyword_counts}")
    print(f"Volume Spike: {signal.volume_spike}")
    print(f"Timestamp: {signal.timestamp}")
    
    # Uncomment to run continuously
    # worker.run_continuous()
