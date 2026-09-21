"""
PolicySetu Eligibility Subsystem.
Provides the deterministic eligibility evaluation engine and decision representations.
"""

from .decision import EligibilityDecision
from .engine import EligibilityEngine

__all__ = [
    "EligibilityEngine",
    "EligibilityDecision",
]
