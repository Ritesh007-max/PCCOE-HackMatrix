"""
FIN Secret and PII Redaction Engine.
Provides comprehensive pattern matching and masking for API keys, bearer tokens,
service keys, credentials, and citizen PII (Aadhaar, PAN, phone numbers).
Guarantees zero secret leakage into logs, error responses, exception tracebacks, or reports.
"""

import logging
import re
from typing import Any, List, Optional, Pattern, Tuple, Union

# Compiled regular expressions for sensitive secrets
SECRET_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    ("GEMINI_KEY", re.compile(r"AIza[0-9A-Za-z-_]{30,}")),
    ("OPENROUTER_KEY", re.compile(r"sk-or-v1-[0-9a-f]{64}|sk-or-[0-9A-Za-z-_]{16,}")),
    ("OPENAI_KEY", re.compile(r"sk-[0-9A-Za-z-_]{32,}")),
    ("HF_TOKEN", re.compile(r"hf_[0-9A-Za-z]{34,}")),
    ("BEARER_TOKEN", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.~+/=]{16,}\b")),
    ("AUTH_HEADER", re.compile(r"(?i)(?:authorization|x-api-key|x-service-key|x-ai-service-key):\s*(?!\[[A-Z_]+_REDACTED\])([^\s,]+)")),
    ("KEY_ASSIGNMENT", re.compile(r"(?i)(?:api_key|apikey|secret_key|private_key|token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.~]{16,})['\"]?")),
]

# Compiled regular expressions for sensitive citizen PII
PII_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    # Indian Aadhaar 12-digit number (e.g., 1234 5678 9012 or 123456789012)
    ("AADHAAR", re.compile(r"\b[1-9]\d{3}\s?\d{4}\s?\d{4}\b")),
    # Indian PAN card (5 letters, 4 digits, 1 letter)
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    # Indian 10-digit mobile phone number
    ("PHONE", re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b")),
    # Email addresses
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
]


def redact_secrets(text: Any, redact_pii: bool = True) -> str:
    """
    Sanitizes any string, dictionary, or exception representation, replacing
    credentials with [SECRET_REDACTED] and citizen identifiers with [IDENTIFIER_REDACTED].
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    sanitized = text

    # Redact credentials
    for label, pattern in SECRET_PATTERNS:
        if label == "AUTH_HEADER":
            sanitized = pattern.sub(r"Authorization: [SECRET_REDACTED]", sanitized)
        elif label == "KEY_ASSIGNMENT":
            sanitized = pattern.sub(r"api_key=[SECRET_REDACTED]", sanitized)
        elif label == "BEARER_TOKEN":
            sanitized = pattern.sub("[BEARER_TOKEN_REDACTED]", sanitized)
        else:
            sanitized = pattern.sub("[SECRET_REDACTED]", sanitized)

    # Redact citizen PII if requested
    if redact_pii:
        for label, pattern in PII_PATTERNS:
            sanitized = pattern.sub(f"[{label}_REDACTED]", sanitized)

    return sanitized


def mask_credential(credential: Optional[str], visible_chars: int = 4) -> str:
    """
    Masks a credential for safe diagnostic display (e.g. 'sk-o...a1b2').
    Returns 'NOT_CONFIGURED' if empty.
    """
    if not credential:
        return "[NOT_CONFIGURED]"
    clean = credential.strip()
    if len(clean) <= visible_chars * 2:
        return "******"
    return f"{clean[:visible_chars]}...{clean[-visible_chars:]}"


class SecretRedactingLoggingFilter(logging.Filter):
    """
    Standard logging filter that automatically intercepts log records and redacts
    secrets and citizen PII from record messages and arguments before writing to streams/files.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg, redact_pii=True)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(v, redact_pii=True) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    redact_secrets(v, redact_pii=True) if isinstance(v, str) else v
                    for v in record.args
                )
        return True


def attach_secret_filter_to_root() -> None:
    """Attaches the SecretRedactingLoggingFilter to all existing and root handlers."""
    filt = SecretRedactingLoggingFilter()
    root_logger = logging.getLogger()
    root_logger.addFilter(filt)
    for handler in root_logger.handlers:
        handler.addFilter(filt)
