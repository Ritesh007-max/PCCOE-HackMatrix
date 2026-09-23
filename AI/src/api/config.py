"""
PolicySetu AI Microservice Configuration.
Handles environment configuration for HTTP service hosting, service-to-service
authentication, rate-limiting, and request size limits without leaking secrets.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# Auto-load local environment if present
load_dotenv()
if not os.getenv("AI_SERVICE_API_KEY") and os.path.exists(".env.example"):
    load_dotenv(".env.example")


@dataclass
class ServiceConfig:
    """Production-oriented service configuration settings."""
    env: str = "development"
    api_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    default_provider_mode: str = "auto"

    # Service-to-service internal authentication
    service_api_key: str = "policysetu_internal_dev_key"
    header_name: str = "X-AI-Service-Key"

    # Rate limiting (configurable, dev-friendly)
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60

    # Request size and file upload limits
    max_upload_size_mb: int = 25
    max_files_per_request: int = 10
    max_request_bytes: int = 30 * 1024 * 1024  # 30 MB total payload
    request_timeout_seconds: float = 60.0

    @property
    def environment(self) -> str:
        return self.env

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        """Loads service configuration from environment variables with safe defaults."""
        env = os.getenv("AI_ENV", "development").strip().lower()
        host = os.getenv("AI_HOST", "0.0.0.0").strip()
        try:
            port = int(os.getenv("AI_PORT", "8000").strip())
        except ValueError:
            port = 8000

        log_level = os.getenv("AI_LOG_LEVEL", "INFO").strip().upper()
        debug_raw = os.getenv("AI_DEBUG", "false").strip().lower()
        debug = debug_raw in ("true", "1", "yes")

        # Internal service key (safe dev fallback if empty or placeholder)
        raw_key = os.getenv("AI_SERVICE_API_KEY", "").strip()
        api_key = "policysetu_internal_dev_key" if (not raw_key or raw_key.startswith("your_")) else raw_key

        # Rate limiting: disabled by default in development unless explicitly enabled
        rl_env = os.getenv("AI_RATE_LIMIT_ENABLED", "").strip().lower()
        if rl_env:
            rate_limit_enabled = rl_env in ("true", "1", "yes")
        else:
            rate_limit_enabled = (env == "production")

        try:
            rate_limit_per_minute = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "60").strip())
        except ValueError:
            rate_limit_per_minute = 60

        try:
            max_upload_size_mb = int(os.getenv("AI_MAX_UPLOAD_SIZE_MB", "25").strip())
        except ValueError:
            max_upload_size_mb = 25

        try:
            max_files = int(os.getenv("AI_MAX_FILES_PER_REQUEST", "10").strip())
        except ValueError:
            max_files = 10

        try:
            timeout_s = float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "60.0").strip())
        except ValueError:
            timeout_s = 60.0

        return cls(
            env=env,
            host=host,
            port=port,
            log_level=log_level,
            debug=debug,
            service_api_key=api_key,
            rate_limit_enabled=rate_limit_enabled,
            rate_limit_per_minute=rate_limit_per_minute,
            max_upload_size_mb=max_upload_size_mb,
            max_files_per_request=max_files,
            max_request_bytes=max_upload_size_mb * 1024 * 1024,
            request_timeout_seconds=timeout_s,
        )


# Global default service configuration
DEFAULT_SERVICE_CONFIG = ServiceConfig.from_env()
