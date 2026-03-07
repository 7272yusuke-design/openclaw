# Roadmap: Neo Sentiment Logic Fix

## Phase 1: Debug & Diagnostics
- [x] Trace `neo_main.py` execution flow to capture exact payload sent to SentimentCrew.
- [x] Document the expected vs. actual schema for SentimentCrew input power.
- [x] Reproduce the hallucination error in a controlled local environment.

## Phase 2: Implementation & Hardening
- [x] Refactor Argument Passing in neo_main.py
- [x] Enforce Pydantic Output Schema in SentimentCrew (Implicitly handled by bridge, extraction hardened)
- [x] Harden Sentiment Extraction Logic
- [x] Integrate Loguru Telemetry for Data Flow (Verified via test script)

## Phase 3: Validation & CI
- [x] Create unit tests for argument mapping logic (tests/test_fix_verification.py).
- [ ] Run an end-to-end integration test of the autonomous cycle.
- [ ] Deploy fix and monitor logs for "hallucination" signatures or argument errors.