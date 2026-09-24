# FIN Phase 9 — Service Configuration

## 1. Environment Variable Reference

All microservice configuration settings are loaded via `ServiceConfig.from_env()`. Values are read from the environment or `.env` files with safe defaults for local development.

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `AI_ENV` | `string` | `development` | Environment mode (`development`, `staging`, `production`) |
| `AI_HOST` | `string` | `0.0.0.0` | Network interface to bind HTTP listener |
| `AI_PORT` | `integer` | `8000` | Port number for HTTP service |
| `AI_SERVICE_API_KEY` | `string` | `fin_internal_dev_key` | Shared internal authentication key |
| `AI_LOG_LEVEL` | `string` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `AI_DEBUG` | `boolean` | `false` | Enables debug telemetry when true |
| `AI_RATE_LIMIT_ENABLED`| `boolean` | `false` | Enables sliding window rate limiting (disabled in dev) |
| `AI_RATE_LIMIT_PER_MINUTE` | `integer` | `60` | Requests allowed per minute per client key |
| `AI_MAX_UPLOAD_SIZE_MB`| `integer` | `25` | Maximum upload size per file in megabytes |
| `AI_MAX_FILES_PER_REQUEST`| `integer` | `10` | Maximum number of files in a single request |
| `AI_REQUEST_TIMEOUT_SECONDS` | `float` | `60.0` | Maximum request duration before client timeout |
| `GEMINI_API_KEY` | `string` | `""` | Primary LLM provider key |
| `OPENROUTER_API_KEY` | `string` | `""` | Fallback LLM provider key |

---

## 2. Example Local Development `.env`

```ini
# Environment
AI_ENV=development
AI_HOST=0.0.0.0
AI_PORT=8000
AI_LOG_LEVEL=INFO

# Service Authentication (Matches Backend Caller)
AI_SERVICE_API_KEY=fin_internal_dev_key

# Rate Limiting (Disabled for local dev)
AI_RATE_LIMIT_ENABLED=false
AI_RATE_LIMIT_PER_MINUTE=60

# File Upload Thresholds
AI_MAX_UPLOAD_SIZE_MB=25
AI_MAX_FILES_PER_REQUEST=10

# AI Provider Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

---

## 3. Configuration Access in Code

Components access configuration through FastAPI's dependency injection provider:

```python
from src.api.config import ServiceConfig
from src.api.dependencies import get_service_config

@router.get("/example")
def example_endpoint(config: ServiceConfig = Depends(get_service_config)):
    return {"max_upload_size": config.max_upload_size_mb}
```
