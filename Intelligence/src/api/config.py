"""
FIN AI Microservice Configuration.
Handles environment configuration for HTTP service hosting, service-to-service
authentication, rate-limiting, and request size limits without leaking secrets.
Delegates to centralized SecuritySettings in src.config.security.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

from src.config.security import DEFAULT_SECURITY_SETTINGS, Environment, SecuritySettings

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
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"])
    default_provider_mode: str = "auto"

    # Service-to-service internal authentication
    service_api_key: str = "fin_internal_dev_key"
    header_name: str = "X-AI-Service-Key"
    min_key_length: int = 16

    # Rate limiting tiers (requests per minute)
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60
    rate_limit_public: int = 60
    rate_limit_protected: int = 120
    rate_limit_expensive: int = 20

    # Request size and file upload limits
    max_upload_size_mb: int = 25
    max_files_per_request: int = 10
    max_request_bytes: int = 30 * 1024 * 1024  # 30 MB total payload
    request_timeout_seconds: float = 60.0

    # Security settings reference
    security: SecuritySettings = field(default_factory=lambda: DEFAULT_SECURITY_SETTINGS)

    @property
    def environment(self) -> str:
        return self.env

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        """Loads service configuration from environment variables with safe defaults."""
        sec = DEFAULT_SECURITY_SETTINGS
        env = sec.env.value
        host = os.getenv("AI_HOST", "0.0.0.0").strip()
        try:
            port = int(os.getenv("AI_PORT", "8000").strip())
        except ValueError:
            port = 8000

        provider_mode = os.getenv("LLM_PROVIDER", "auto").strip().lower()

        return cls(
            env=env,
            host=host,
            port=port,
            log_level=sec.log_level,
            debug=sec.debug_mode,
            cors_origins=list(sec.cors_origins),
            default_provider_mode=provider_mode,
            service_api_key=sec.service_api_key,
            header_name=sec.header_name,
            min_key_length=sec.min_key_length,
            rate_limit_enabled=sec.rate_limit_enabled,
            rate_limit_per_minute=sec.rate_limit_protected,
            rate_limit_public=sec.rate_limit_public,
            rate_limit_protected=sec.rate_limit_protected,
            rate_limit_expensive=sec.rate_limit_expensive,
            max_upload_size_mb=sec.max_upload_size_bytes // (1024 * 1024),
            max_files_per_request=sec.max_files_per_request,
            max_request_bytes=sec.max_request_bytes,
            request_timeout_seconds=float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "60.0").strip()),
            security=sec,
        )


# Global default service configuration
DEFAULT_SERVICE_CONFIG = ServiceConfig.from_env()
