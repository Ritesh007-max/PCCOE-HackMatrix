"""
PolicySetu Structured Output Validator.
Extracts, cleans, and validates JSON payloads from LLM responses into typed data structures.
"""

import json
import re
from typing import Any, Dict, Optional, Type, TypeVar, cast
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .errors import MalformedOutputError, SchemaValidationError
except (ImportError, ValueError):
    from src.llm.errors import MalformedOutputError, SchemaValidationError

T = TypeVar("T")


def clean_json_text(text: str) -> str:
    """
    Extracts JSON from text containing markdown code blocks, conversational prefixes,
    or trailing formatting.
    """
    if not text or not isinstance(text, str):
        raise MalformedOutputError("Empty or non-string LLM output received.")

    cleaned = text.strip()

    # 1. Strip markdown code fences (```json ... ``` or ``` ... ```)
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(code_block_pattern, cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    else:
        # Fallback: find outermost curly braces or square brackets
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        first_bracket = cleaned.find("[")
        last_bracket = cleaned.rfind("]")

        if first_brace != -1 and last_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            cleaned = cleaned[first_brace : last_brace + 1]
        elif first_bracket != -1 and last_bracket != -1:
            cleaned = cleaned[first_bracket : last_bracket + 1]

    # Remove trailing commas before closing braces/brackets (common LLM JSON issue)
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    return cleaned


def parse_structured_json(text: str) -> Any:
    """Parses cleaned text into a dictionary or list, raising MalformedOutputError on failure."""
    cleaned = clean_json_text(text)
    try:
        data = json.loads(cleaned)
        if not isinstance(data, (dict, list)):
            raise MalformedOutputError(f"Expected JSON object or array, got {type(data).__name__}")
        return data
    except json.JSONDecodeError as exc:
        raise MalformedOutputError(f"Failed to parse LLM JSON: {exc.msg} at line {exc.lineno} col {exc.colno}") from exc


def validate_and_instantiate(data: Dict[str, Any], target_cls: Type[T]) -> T:
    """
    Instantiates target dataclass from parsed JSON data using its from_dict() or constructor,
    raising SchemaValidationError if required fields are missing or invalid.
    """
    if not isinstance(data, dict):
        raise SchemaValidationError(f"Expected dict for {target_cls.__name__}, got {type(data).__name__}")

    try:
        from_dict_fn = getattr(target_cls, "from_dict", None)
        if callable(from_dict_fn):
            return cast(T, from_dict_fn(data))
        return target_cls(**data)
    except (TypeError, ValueError, KeyError) as exc:
        raise SchemaValidationError(f"Schema validation failed for {target_cls.__name__}: {exc}") from exc