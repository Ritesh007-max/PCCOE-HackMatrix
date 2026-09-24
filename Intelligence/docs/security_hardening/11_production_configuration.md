# FIN Production Configuration & Deployment Hardening

## 1. Environment Topology
The system distinguishes three discrete runtime operational environments:
- `DEVELOPMENT` (Default local developer testing with safe fallback stubs)
- `TEST` (Automated CI/CD test runner with mocked offline network providers)
- `PRODUCTION` (Hardened, fail-closed production deployment)

---

## 2. Production Fail-Closed Requirements
When `AI_ENV=production` is active, `SecuritySettings.validate_production()` executes at startup and strictly aborts application boot if any of the following invariants fail:

1. **Service API Key**:
   - `AI_SERVICE_API_KEY` must be configured.
   - Must not equal default `"fin_internal_dev_key"`.
   - Must be $\ge 16$ characters in length.
2. **CORS Restrictions**:
   - Wildcard origin (`"*"`) is strictly prohibited.
   - Explicit approved origins must be declared in `AI_CORS_ORIGINS`.
3. **Debug Mode**:
   - `AI_DEBUG` must be `false`.
4. **Mock Fallback**:
   - `LLM_ALLOW_MOCK_FALLBACK` is strictly prohibited in production.
   - Provider mode `mock` is blocked.
5. **Real Model Credentials**:
   - At least one valid API credential (`GEMINI_API_KEY` or `OPENROUTER_API_KEY`) must be configured.
6. **Rate Limiting**:
   - `AI_RATE_LIMIT_ENABLED` must be set to `true`.

---

## 3. Recommended Container & Process Hardening

While container infrastructure is managed external to the AI microservice, production deployment should adhere to the following best practices:
- **Non-Root Execution**: Run the FastAPI process under a dedicated unprivileged user (`uid=10001, gid=10001`).
- **Read-Only Root Filesystem**: Mount the application container with `--read-only`, providing an explicit ephemeral tmpfs volume for `/tmp`.
- **Minimal Base Image**: Use `python:3.11-slim` or distroless images without shell utilities or package managers.
- **Dropped Capabilities**: Drop all Linux capabilities (`--cap-drop=ALL`).
- **Graceful Shutdown**: Handle SIGTERM cleanly through the FastAPI lifespan context manager.
