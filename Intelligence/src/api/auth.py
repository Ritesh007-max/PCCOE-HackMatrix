"""
FIN Hardened Internal Service Authentication.
Enforces service-to-service authentication using X-AI-Service-Key header
with timing-attack resistant constant-time comparison, minimum key length
validation, production fail-closed behavior, and zero secret leakage.
"""

import hmac
import logging
from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import DEFAULT_SERVICE_CONFIG
from src.utils.secret_redactor import mask_credential

logger = logging.getLogger("fin.api.auth")

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
    Enforces:
      1. Missing-key rejection (401 Unauthorized)
      2. Production fail-closed validation
      3. Minimum key length validation
      4. Constant-time comparison (hmac.compare_digest)
      5. Zero key material reflected in logs or error messages
    """
    expected_key = DEFAULT_SERVICE_CONFIG.service_api_key

    # Production fail-closed check
    if DEFAULT_SERVICE_CONFIG.is_production:
        if not expected_key or expected_key == "fin_internal_dev_key":
            logger.critical("Authentication failure: Production service key is unconfigured or default.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security configuration error: Service authentication is unconfigured.",
            )

    if not x_ai_service_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required service key in header '{DEFAULT_SERVICE_CONFIG.header_name}'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    clean_key = x_ai_service_key.strip()

    # Minimum key length check (reject trivial/empty keys)
    min_length = DEFAULT_SERVICE_CONFIG.min_key_length
    if len(clean_key) < min_length:
        logger.warning(
            "Rejected service key: length %d is below minimum required length %d.",
            len(clean_key), min_length
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison preventing side-channel timing attacks
    is_valid = hmac.compare_digest(clean_key, expected_key.strip())
    if not is_valid:
        logger.warning("Invalid service API key attempt rejected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return clean_key


# Alias for dependency injection
verify_api_key = verify_service_api_key
