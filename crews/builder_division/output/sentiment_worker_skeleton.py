```python
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeywordMatcher:
    def __init__(self, keywords: List[str]):
        self.keywords = keywords

    def match(self, text: str) -> Dict[str, int]:
        keyword_counts = {keyword: text.lower().count(keyword) for keyword in self.keywords}
        return keyword_counts

class SentimentSignal:
    def __init__(self, keyword_counts: Dict[str, int], volume_spike: bool):
        self.keyword_counts = keyword_counts
        self.volume_spike = volume_spike

class SanityCheck:
    def check(self, signal: SentimentSignal) -> bool:
        # Rule 1: Empty Signal Check
        if all(count == 0 for count in signal.keyword_counts.values()):
            logger.warning("Signal rejected by SanityCheck: Empty Signal (Low Confidence)")
            return False
        
        # Rule 2: Volume Confirmation
        if not signal.volume_spike:
            logger.warning("Signal rejected by SanityCheck: Volume Spike is False (High Risk)")
            return False
        
        return True

class SentimentWorker:
    def __init__(self, keywords: List[str]):
        self.keyword_matcher = KeywordMatcher(keywords)
        self.sanity_check = SanityCheck()

    def run_once(self, text: str) -> SentimentSignal:
        keyword_counts = self.keyword_matcher.match(text)
        volume_spike = self._detect_volume_spike(text)
        signal = SentimentSignal(keyword_counts, volume_spike)
        
        # Perform sanity check
        if not self.sanity_check.check(signal):
            return None
        
        return signal

    def _detect_volume_spike(self, text: str) -> bool:
        # Placeholder for volume spike detection logic
        # In a real implementation, this would analyze the text volume/spike
        return True  # Assume volume spike is detected for this example

# Example usage
if __name__ == "__main__":
    keywords = ["bitcoin", "ethereum", "blockchain"]
    worker = SentimentWorker(keywords)
    text = "Bitcoin is rising, Ethereum is stable."
    
    signal = worker.run_once(text)
    if signal:
        logger.info(f"Valid Signal: {signal.keyword_counts}, Volume Spike: {signal.volume_spike}")
    else:
        logger.warning("No valid signal generated.")
```