"""
PolicySetu Internal Service Authentication.
Enforces service-to-service authentication using X-AI-Service-Key header
with timing-attack resistant verification. Never logs key material.
"""

import hmac
from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import DEFAULT_SERVICE_CONFIG, ServiceConfig

# APIKeyHeader for OpenAPI specification integration
_api_key_header = APIKeyHeader(
    name=DEFAULT_SERVICE_CONFIG.header_name,
    auto_error=False,
    description="Internal service authentication key provided by backend callers."
)


def verify_service_api_key(
    x_ai_service_key: Optional[str] = Security(_api_key_header),
) -> str:
    """
    Verifies that the incoming request contains a valid internal service key.
    Uses hmac.compare_digest to prevent side-channel timing attacks.
    """
    expected_key = DEFAULT_SERVICE_CONFIG.service_api_key

    if not x_ai_service_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required service key in header 'X-AI-Service-Key'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison
    is_valid = hmac.compare_digest(x_ai_service_key.strip(), expected_key.strip())
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_ai_service_key


# Alias for dependency injection
verify_api_key = verify_service_api_key
