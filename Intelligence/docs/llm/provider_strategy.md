# FIN Phase 6: Provider Strategy & Configuration

## 1. Provider Abstraction Model

FIN enforces strict decoupling between application business logic and specific LLM vendors. The provider layer defines an abstract base interface:

```python
class LLMProvider(ABC):
    @property
    def provider_name(self) -> str: ...
    @property
    def model_name(self) -> str: ...
    def is_available(self) -> bool: ...
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str: ...
    def generate_structured(self, prompt: str, schema_cls: Type[T], system_prompt: Optional[str] = None, **kwargs) -> T: ...
```

---

## 2. Implemented Providers in Phase 6

### A. `MockLLMProvider` (100% Offline Testing Foundation)
- Default provider when `LLM_PROVIDER=mock` or when running unit/benchmark tests.
- Backed by high-precision deterministic NLP:
  - `LanguageDetector`: classifies English, Hindi (Devanagari), and Hinglish (Romanized Hindi).
  - `IntentClassifier`: regex patterns for common governance query intents.
  - `QueryParser`: parses Indian states, categories, and beneficiaries.
  - `AmbiguityDetector`: identifies approximate amounts, missing units, and family references.
- Operates 100% locally with zero network calls, zero API keys, and deterministic output.

### B. `OpenAICompatibleProvider` (Production API Endpoint)
- Compatible with any OpenAI-standard endpoint (`/chat/completions`), including:
  - OpenAI (`gpt-4o-mini`, `gpt-4o`)
  - Local inference engines (vLLM, Ollama, LocalAI)
  - Hosted OpenAI-compatible proxies
- Configured via `OPENAI_API_BASE` and `OPENAI_API_KEY`.

---

## 3. Critical Failure Isolation (No Silent Mock Fallback)

> [!IMPORTANT]
> **Production LLM failure MUST NOT silently fall back to MockLLMProvider.**
>
> In production mode (`provider="openai"`):
> - Network timeouts, HTTP 429 (rate limits), or HTTP 500 errors will **raise explicit exceptions** (`ProviderUnavailableError` or `ProviderTimeoutError`).
> - The system will NEVER secretly switch to mock data in production.
> - Mock provider execution is permitted solely when explicitly configured (`LLM_PROVIDER=mock`).

---

## 4. Configuration Reference (`LLMConfig`)

| Setting | Default | Environment Variable | Description |
| :--- | :--- | :--- | :--- |
| `provider` | `"mock"` | `LLM_PROVIDER` | Active provider (`mock`, `openai`) |
| `model` | `"mock-governance-v1"` | `LLM_MODEL` | Underlying model identifier |
| `temperature` | `0.0` | `LLM_TEMPERATURE` | Sampling temperature (0.0 for deterministic extraction) |
| `max_tokens` | `2048` | `LLM_MAX_TOKENS` | Maximum tokens in generation |
| `timeout_seconds` | `30.0` | `LLM_TIMEOUT` | Request timeout |
| `allow_mock_fallback`| `False` | `LLM_ALLOW_MOCK_FALLBACK` | Strict failure isolation switch |
| `api_key` | `None` | `OPENAI_API_KEY` | Vendor secret key (redacted in logs) |
| `api_base` | `None` | `OPENAI_API_BASE` | Endpoint URL |
