"""
FIN Centralized Security Configuration Model.
Enforces environment-specific security controls (DEVELOPMENT, TEST, PRODUCTION),
strict production fail-closed validation, credential strength policies,
CORS restrictions, rate limiting tiers, and resource exhaustion limits.
"""

from enum import Enum
import os
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

from src.utils.secret_redactor import mask_credential

# Load environment variables
load_dotenv()


class Environment(str, Enum):
    """Runtime operational environments."""
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, val: Optional[str]) -> "Environment":
        if not val:
            return cls.DEVELOPMENT
        normalized = val.strip().lower()
        if normalized in ("prod", "production"):
            return cls.PRODUCTION
        elif normalized in ("test", "testing"):
            return cls.TEST
        return cls.DEVELOPMENT


class SecurityConfigError(ValueError):
    """Raised when security configuration fails validation, especially in production."""
    pass


@dataclass
class SecuritySettings:
    """Centralized security configuration with strict production validation."""
    env: Environment = Environment.DEVELOPMENT
    
    # Internal service-to-service authentication
    service_api_key: str = "fin_internal_dev_key"
    header_name: str = "X-AI-Service-Key"
    min_key_length: int = 16

    # Model provider credentials
    gemini_api_key: Optional[str] = field(default=None, repr=False)
    openrouter_api_key: Optional[str] = field(default=None, repr=False)
    huggingface_token: Optional[str] = field(default=None, repr=False)
    allow_mock_fallback: bool = False
    
    # Network & CORS
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"])
    allow_all_cors: bool = False

    # Rate Limiting Tiers (requests per minute)
    rate_limit_enabled: bool = False
    rate_limit_public: int = 60
    rate_limit_protected: int = 120
    rate_limit_expensive: int = 20

    # Payload & File Upload Caps
    max_request_bytes: int = 30 * 1024 * 1024       # 30 MB global body limit
    max_upload_size_bytes: int = 25 * 1024 * 1024   # 25 MB document upload limit
    max_files_per_request: int = 10
    max_pdf_pages: int = 100
    max_image_pixels: int = 100_000_000             # 100 Megapixels
    max_docx_decompression_ratio: float = 50.0      # Zip bomb protection
    max_docx_uncompressed_bytes: int = 50 * 1024 * 1024  # 50 MB

    # Outbound HTTP & SSRF Timeouts
    http_connect_timeout: float = 5.0
    http_read_timeout: float = 20.0
    http_total_timeout: float = 30.0
    http_max_redirects: int = 3
    enforce_https_only: bool = True

    # Logging & Privacy
    enable_pii_redaction: bool = True
    enable_secret_redaction: bool = True
    log_level: str = "INFO"
    debug_mode: bool = False

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.env == Environment.TEST

    @property
    def is_development(self) -> bool:
        return self.env == Environment.DEVELOPMENT

    @classmethod
    def from_env(cls) -> "SecuritySettings":
        """Builds settings from environment variables."""
        raw_env = os.getenv("AI_ENV") or os.getenv("ENVIRONMENT") or "development"
        env = Environment.from_string(raw_env)

        # Service key
        raw_key = os.getenv("AI_SERVICE_API_KEY", "").strip()
        if not raw_key or raw_key.startswith("your_"):
            if env == Environment.PRODUCTION:
                raw_key = ""  # Will trigger fail-closed in validate()
            else:
                raw_key = "fin_internal_dev_key"

        # Model keys
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or None
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip() or None
        hf_token = os.getenv("HUGGINGFACE_API_TOKEN", "").strip() or None

        # CORS origins parsing
        raw_cors = os.getenv("AI_CORS_ORIGINS", "").strip()
        if raw_cors:
            cors_origins = [o.strip() for o in raw_cors.split(",") if o.strip()]
        else:
            if env == Environment.PRODUCTION:
                cors_origins = []  # Must be explicitly configured in production
            else:
                cors_origins = [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:5173",
                ]

        allow_all_cors = os.getenv("AI_ALLOW_ALL_CORS", "false").strip().lower() in ("true", "1", "yes")

        # Rate limits
        rl_enabled = os.getenv("AI_RATE_LIMIT_ENABLED", "").strip().lower()
        if rl_enabled:
            rate_limit_enabled = rl_enabled in ("true", "1", "yes")
        else:
            rate_limit_enabled = (env == Environment.PRODUCTION)

        rate_limit_pub = int(os.getenv("AI_RATE_LIMIT_PUBLIC", "60"))
        rate_limit_prot = int(os.getenv("AI_RATE_LIMIT_PROTECTED", "120"))
        rate_limit_exp = int(os.getenv("AI_RATE_LIMIT_EXPENSIVE", "20"))

        # Timeouts & payload sizes
        max_upload_mb = int(os.getenv("AI_MAX_UPLOAD_SIZE_MB", "25"))
        max_request_mb = int(os.getenv("AI_MAX_REQUEST_SIZE_MB", "30"))
        max_files = int(os.getenv("AI_MAX_FILES_PER_REQUEST", "10"))
        max_pages = int(os.getenv("AI_MAX_PDF_PAGES", "100"))

        debug_raw = os.getenv("AI_DEBUG", "false").strip().lower()
        debug_mode = debug_raw in ("true", "1", "yes")
        log_level = os.getenv("AI_LOG_LEVEL", "INFO").strip().upper()

        mock_fallback_raw = os.getenv("LLM_ALLOW_MOCK_FALLBACK", "false").strip().lower()
        allow_mock = (mock_fallback_raw in ("true", "1", "yes")) and (env != Environment.PRODUCTION)

        settings = cls(
            env=env,
            service_api_key=raw_key,
            header_name=os.getenv("AI_SERVICE_HEADER_NAME", "X-AI-Service-Key").strip(),
            gemini_api_key=gemini_key,
            openrouter_api_key=openrouter_key,
            huggingface_token=hf_token,
            allow_mock_fallback=allow_mock,
            cors_origins=cors_origins,
            allow_all_cors=allow_all_cors,
            rate_limit_enabled=rate_limit_enabled,
            rate_limit_public=rate_limit_pub,
            rate_limit_protected=rate_limit_prot,
            rate_limit_expensive=rate_limit_exp,
            max_request_bytes=max_request_mb * 1024 * 1024,
            max_upload_size_bytes=max_upload_mb * 1024 * 1024,
            max_files_per_request=max_files,
            max_pdf_pages=max_pages,
            log_level=log_level,
            debug_mode=debug_mode,
        )

        # Validate production environment configuration
        if env == Environment.PRODUCTION:
            settings.validate_production()

        return settings

    def validate_production(self) -> None:
        """
        FAIL CLOSED validation for production deployments.
        Ensures all security prerequisites are strictly satisfied before accepting traffic.
        """
        errors: List[str] = []

        # 1. Service key verification
        if not self.service_api_key:
            errors.append("Production requires AI_SERVICE_API_KEY to be set.")
        elif self.service_api_key == "fin_internal_dev_key":
            errors.append("Default development service key is strictly prohibited in production.")
        elif len(self.service_api_key) < self.min_key_length:
            errors.append(f"AI_SERVICE_API_KEY must be at least {self.min_key_length} characters (got {len(self.service_api_key)}).")

        # 2. CORS security
        if self.allow_all_cors or "*" in self.cors_origins:
            errors.append("Wildcard CORS origin ('*') is strictly forbidden in production.")
        if not self.cors_origins:
            errors.append("Production requires explicit AI_CORS_ORIGINS list.")

        # 3. Debug mode must be disabled
        if self.debug_mode:
            errors.append("AI_DEBUG must be false in production.")

        # 4. LLM Mock fallback disabled
        if self.allow_mock_fallback:
            errors.append("LLM mock fallback is strictly prohibited in production.")

        # 5. Model credentials: at least one real provider must be configured
        if not self.gemini_api_key and not self.openrouter_api_key:
            errors.append("Production requires at least GEMINI_API_KEY or OPENROUTER_API_KEY to be set.")

        # 6. Rate limiting must be enabled in production
        if not self.rate_limit_enabled:
            errors.append("Rate limiting must be enabled in production (AI_RATE_LIMIT_ENABLED=true).")

        if errors:
            raise SecurityConfigError(
                "Production Security Validation Failed:\n - " + "\n - ".join(errors)
            )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Returns safe telemetry metadata without exposing secrets."""
        return {
            "environment": self.env.value,
            "is_production": self.is_production,
            "service_header": self.header_name,
            "service_key_configured": bool(self.service_api_key and self.service_api_key != "fin_internal_dev_key"),
            "service_key_masked": mask_credential(self.service_api_key) if self.service_api_key else None,
            "has_gemini_key": bool(self.gemini_api_key),
            "has_openrouter_key": bool(self.openrouter_api_key),
            "has_hf_token": bool(self.huggingface_token),
            "allow_mock_fallback": self.allow_mock_fallback,
            "cors_origins_count": len(self.cors_origins),
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limits": {
                "public": self.rate_limit_public,
                "protected": self.rate_limit_protected,
                "expensive": self.rate_limit_expensive,
            },
            "limits": {
                "max_request_mb": self.max_request_bytes // (1024 * 1024),
                "max_upload_mb": self.max_upload_size_bytes // (1024 * 1024),
                "max_files": self.max_files_per_request,
                "max_pdf_pages": self.max_pdf_pages,
            },
            "timeouts": {
                "connect": self.http_connect_timeout,
                "read": self.http_read_timeout,
                "total": self.http_total_timeout,
            },
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
        }


# Global default security configuration
DEFAULT_SECURITY_SETTINGS = SecuritySettings.from_env()
