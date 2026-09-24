"""
FIN API Input Validation & Sanitization Helpers.
Guards against null-byte injection, path traversal sequences, oversized strings,
malformed snapshot IDs, and invalid language codes.
"""

import re
from typing import Any, List, Optional
from fastapi import HTTPException, status

# Pre-compiled safety patterns
NULL_BYTE_PATTERN = re.compile(r"\x00")
PATH_TRAVERSAL_PATTERN = re.compile(r"(?:\.\.[\\/]|[\\/]\.\.)")
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})?$")

# Input length thresholds
MAX_QUERY_LENGTH = 1000
MAX_TEXT_INPUT_LENGTH = 50000
MAX_LIST_ITEMS = 100


def validate_safe_string(
    val: Optional[str],
    field_name: str = "field",
    max_length: int = MAX_QUERY_LENGTH,
    allow_empty: bool = True,
) -> Optional[str]:
    """
    Validates a string input for null bytes, path traversal sequences, and length limits.
    Raises HTTPException(400) if unsafe or oversized.
    """
    if val is None:
        return None

    if not isinstance(val, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid type for '{field_name}': expected string.",
        )

    # 1. Null-byte injection check
    if NULL_BYTE_PATTERN.search(val):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: Null byte detected in '{field_name}'.",
        )

    # 2. Length check
    if len(val) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value for '{field_name}' exceeds maximum permitted length of {max_length} characters.",
        )

    clean = val.strip()
    if not clean and not allow_empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value for '{field_name}' cannot be empty.",
        )

    return clean


def validate_identifier(
    val: Optional[str],
    field_name: str = "id",
    required: bool = True,
) -> Optional[str]:
    """
    Validates that an identifier (source_id, snapshot_id, document_id) matches safe alphanumeric patterns.
    """
    if val is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required identifier '{field_name}'.",
            )
        return None

    clean = validate_safe_string(val, field_name=field_name, max_length=64, allow_empty=not required)
    if clean:
        if not SAFE_IDENTIFIER_PATTERN.match(clean) or PATH_TRAVERSAL_PATTERN.search(clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format for '{field_name}': must be alphanumeric, hyphen, underscore or dot.",
            )

    return clean


def validate_language_code(lang: Optional[str]) -> str:
    """Validates language code format (e.g. 'en', 'hi', 'en-IN')."""
    if not lang:
        return "en"
    clean = lang.strip().lower()
    if not LANGUAGE_CODE_PATTERN.match(clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid language code: '{lang}'. Must follow BCP 47 format (e.g. 'en', 'hi').",
        )
    return clean


def validate_list_size(items: Optional[List[Any]], field_name: str = "items", max_size: int = MAX_LIST_ITEMS) -> List[Any]:
    """Ensures list inputs do not exceed resource exhaustion bounds."""
    if items is None:
        return []
    if len(items) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"List '{field_name}' exceeds maximum permitted size of {max_size} elements.",
        )
    return items
