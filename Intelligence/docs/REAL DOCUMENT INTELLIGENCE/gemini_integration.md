# FIN Gemini Integration Specification (Primary Provider)

## 1. Official Google GenAI SDK

FIN uses the official `google-genai` Python SDK (`import google.genai`).
No third-party wrappers or deprecated libraries (`google-generativeai`) are used.

### Client Initialization
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=config.gemini_api_key)
```

## 2. Model Selection & Configuration

- **Primary Model**: `gemini-2.5-flash`
- **Fallback Models**: `gemini-2.5-pro` (for complex multilingual multi-page documents)
- **Temperature**: `0.0` (Mandatory for deterministic applicant fact candidate extraction)
- **Max Output Tokens**: `2048`
- **Safety Settings**: Standard enterprise content filter settings with explicit prompt injection defense wrappers.

## 3. Strict Operational Scope

Gemini acts strictly as an **intelligence assistant**:
- Performs multimodal document understanding.
- Extracts raw candidate applicant facts (`raw_value` only, e.g. "4.2 lakh").
- Formats structured responses into strict JSON conforming to target schemas (`QueryIntent`, `FactExtractionResult`, `GroundedExplanation`).
- Explains deterministic eligibility outcomes with citations to verified policy chunks.

### Strict Negative Invariants
1. Gemini **NEVER** decides whether an applicant is eligible.
2. Gemini **NEVER** extracts or invents mathematical benefit formulas from narrative text.
3. Gemini **NEVER** normalizes values (Phase 4 owns 100% of normalization).
4. Gemini **NEVER** overrides or contradicts the Phase 3 `RuleEvaluator` decision.

## 4. Structured Output Enforcement

Structured generation enforces JSON formatting:
```python
json_instruction = (
    f"\nYou must output your response STRICTLY as a valid JSON object conforming to "
    f"the {schema_cls.__name__} schema. Do not include markdown preamble or conversational text. "
    f"Enclose strictly in ```json ```."
)
```
The output is extracted via `parse_structured_json` (robust against markdown fences, stray preamble, and json decode errors) and instantiated into typed dataclasses (`validate_and_instantiate`).

## 5. Error Classification & Non-Fallback Guarantees

Exceptions from Google Gemini are strictly translated into typed FIN errors:
- `401 / 403 / API_KEY_INVALID` → `ProviderAuthenticationError` (**NEVER** falls back to OpenRouter).
- `429 / RESOURCE_EXHAUSTED` → `ProviderRateLimitError` (triggers operational fallback).
- `500 / 502 / 503 / 504 / UNAVAILABLE` → `ProviderUnavailableError` (triggers operational fallback).
- `DEADLINE_EXCEEDED / TIMEOUT` → `ProviderTimeoutError` (triggers operational fallback).
