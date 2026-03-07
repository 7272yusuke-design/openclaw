<phase name="Phase 2: Implementation & Hardening">
  <task id="P2-01">
    <name>Refactor Argument Passing in neo_main.py</name>
    <description>
      Align the call site of SentimentCrew in `neo_main.py` with the expected schema identified in Phase 1. 
      Ensure that all required context variables (e.g., raw_data, social_context) are passed as a single dictionary or specific keyword arguments matching the Crew's `kickoff(inputs={...})` structure.
    </description>
    <files>
      <file>neo_main.py</file>
    </files>
    <verification>
      Run `python neo_main.py --dry-run` (or equivalent) to ensure no TypeError or ArgumentMismatch errors occur during initialization.
    </verification>
  </task>

  <task id="P2-02">
    <name>Enforce Pydantic Output Schema in SentimentCrew</name>
    <description>
      Modify the SentimentCrew task definition to use `output_json` or `output_pydantic`. 
      Define a `SentimentResult` class with fields: `score` (float), `label` (string), and `reasoning` (string). 
      This prevents the LLM from returning conversational text instead of structured data.
    </description>
    <files>
      <file>src/crews/sentiment_crew.py</file>
      <file>src/models/schemas.py</file>
    </files>
    <verification>
      Run a standalone script invoking SentimentCrew and verify that the output is a valid instance of SentimentResult.
    </verification>
  </task>

  <task id="P2-03">
    <name>Harden Sentiment Extraction Logic</name>
    <description>
      Update the utility function responsible for extracting scores from the Crew output. 
      Implement wrap-around logic that handles cases where the LLM might return a null value or an out-of-bounds score. 
      Add default values (e.g., 0.5/neutral) if extraction fails despite the schema enforcement.
    </description>
    <files>
      <file>src/utils/sentiment_parser.py</file>
    </files>
    <verification>
      Run `pytest tests/test_sentiment_parser.py` using a suite of malformed JSON strings to ensure the parser does not raise exceptions.
    </verification>
  </task>

  <task id="P2-04">
    <name>Integrate Loguru Telemetry for Data Flow</name>
    <description>
      Add trace-level logging in `neo_main.py` and `sentiment_crew.py` to log the exact JSON payload before and after the Crew execution. 
      This ensures that if a hallucination occurs, we have a clear audit trail of the input that caused it.
    </description>
    <files>
      <file>neo_main.py</file>
      <file>src/crews/sentiment_crew.py</file>
    </files>
    <verification>
      Execute a test cycle and check `logs/neo.log` (or stdout) to confirm that "Payload Sent" and "Payload Received" entries are visible and correctly formatted.
    </verification>
  </task>
</phase>