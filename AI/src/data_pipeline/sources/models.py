"""
Source Registry models re-export and source-specific structures.
"""

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..models import SourceType, AuthorityTier, FreshnessStatus, SourceDefinition
except (ImportError, ValueError):
    from src.data_pipeline.models import SourceType, AuthorityTier, FreshnessStatus, SourceDefinition

__all__ = [
    "SourceType",
    "AuthorityTier",
    "FreshnessStatus",
    "SourceDefinition",
]