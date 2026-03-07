import sys
import os
import re

# パスを通す
sys.path.append(os.getcwd())

from tools.data_fetcher import DataFetcher

class MockCrewOutput:
    def __init__(self, raw, pydantic=None, json_dict=None):
        self.raw = raw
        self.pydantic = pydantic
        self.json_dict = json_dict

class MockPydanticModel:
    def __init__(self, payload):
        self.virtuals_payload = payload

def test_fixed_logic():
    print("--- Test: Fixed Data Flow and Score Extraction ---")
    
    # 1. Data Flow Test
    goal = "Analyze This"
    market_data = "Price is up" # context
    raw_sns_data = [{"title": "Test", "snippet": "Snippet", "url": "URL"}]
    context = market_data
    constraints = "Strict constraints"
    
    # 修正後の neo_main.py ロジック
    formatted_sns = DataFetcher.format_for_crew(raw_sns_data)
    inputs = DataFetcher.create_sentiment_input(goal, context, formatted_sns)
    
    print(f"Fixed Inputs Context:\n{inputs['context'][:100]}...")
    if "Snippet" in inputs['context']:
        print("✅ Success: SNS Data is present in Context!")
    else:
        print("❌ Failure: SNS Data is missing!")

    # 2. Score Extraction Test
    print("\n--- Test: Score Extraction Robustness ---")
    
    # Case A: Pydantic Model (CrewResult)
    print("Case A: Pydantic Model")
    payload_a = {"market_sentiment_score": 0.8}
    analysis_a = MockPydanticModel(payload_a)
    score_a = extract_score(analysis_a)
    print(f"Score: {score_a} (Expected: 0.8)")
    
    # Case B: CrewOutput with JSON Dict
    print("Case B: CrewOutput JSON")
    payload_b = {"virtuals_payload": {"market_sentiment_score": -0.5}}
    analysis_b = MockCrewOutput(raw="...", json_dict=payload_b)
    score_b = extract_score(analysis_b)
    print(f"Score: {score_b} (Expected: -0.5)")
    
    # Case C: Raw Text Fallback
    print("Case C: Raw Text Fallback")
    raw_text = "Analysis complete. \"market_sentiment_score\": 0.3."
    analysis_c = MockCrewOutput(raw=raw_text)
    score_c = extract_score(analysis_c)
    print(f"Score: {score_c} (Expected: 0.3)")

def extract_score(analysis):
    # Copy-paste logic from neo_main.py (simplified for test)
    sentiment_score = 0.0
    try:
        payload = None
        if hasattr(analysis, 'virtuals_payload'):
            payload = analysis.virtuals_payload
        elif hasattr(analysis, 'json_dict') and analysis.json_dict:
            payload = analysis.json_dict.get('virtuals_payload')
        
        if payload:
            if isinstance(payload, dict):
                sentiment_score = float(payload.get('market_sentiment_score', 0.0))
        
        if sentiment_score == 0.0:
            raw_text = str(getattr(analysis, 'raw', analysis))
            match = re.search(r"['\"]market_sentiment_score['\"]:\s*([+-]?\d*\.\d+|[+-]?\d+)", raw_text)
            if match:
                sentiment_score = float(match.group(1))
    except Exception:
        pass
    return sentiment_score

if __name__ == "__main__":
    test_fixed_logic()
