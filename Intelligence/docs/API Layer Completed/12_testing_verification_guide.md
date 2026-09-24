# FIN Phase 9 — Testing & Verification Guide

## 1. Test Architecture & Structure

Phase 9 implements a multi-tier testing strategy ensuring 100% offline regression safety alongside environment-gated live provider tests.

```
Intelligence/tests/api/
├── __init__.py                     # Package definition
├── test_health.py                  # GET /health/live, /health/ready, /version
├── test_auth.py                    # X-AI-Service-Key & X-Request-ID middleware
├── test_documents.py               # POST /v1/documents/process
├── test_schemes.py                 # POST /v1/schemes/search
├── test_eligibility.py             # POST /v1/eligibility/check (deterministic, zero LLM)
├── test_chat.py                    # POST /v1/chat (grounding, citations, injection defense)
├── test_applications.py            # POST /v1/applications/analyze (21-step pipeline)
├── test_e2e_api.py                 # Complete multi-step citizen workflow
├── test_api_real_gemini.py         # Live Gemini test (environment-gated)
└── test_api_real_openrouter.py     # Live OpenRouter fallback test (environment-gated)
```

---

## 2. Running Verification Commands

All commands MUST be executed from the `Intelligence/` directory.

### Command 1: Fast Offline API Regression Suite
Runs in under 1 second without downloading large embedding models or making remote LLM calls:
```powershell
python -m unittest tests/api/test_health.py tests/api/test_auth.py tests/api/test_documents.py tests/api/test_schemes.py tests/api/test_eligibility.py tests/api/test_chat.py tests/api/test_applications.py tests/api/test_e2e_api.py
```

### Command 2: Complete AI Repository Test Suite
Runs all 263 unit and integration tests across the complete codebase:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### Command 3: Static Type Checking
Strict type verification with zero errors:
```powershell
npx pyright src/api tests/api
```

### Command 4: Live Provider Integration Tests
Explicitly executes live Gemini and OpenRouter API endpoints:
```powershell
python -m unittest tests/api/test_api_real_gemini.py tests/api/test_api_real_openrouter.py
```

---

## 3. Real-Provider Separation Contract

In alignment with Phase 8 guardrails:
- The standard regression suite uses mocks and offline deterministic stubs to execute in seconds without consuming API credits or failing when offline.
- Real provider tests check for `GEMINI_API_KEY` and `OPENROUTER_API_KEY`. If keys are absent or default placeholders, tests gracefully skip via `self.skipTest()`.
