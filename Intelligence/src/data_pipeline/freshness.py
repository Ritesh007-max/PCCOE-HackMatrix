"""
FIN Source Freshness Tracker.
Enforces that stale sources are quarantined and never silently treated as current.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .models import SourceDefinition, FreshnessStatus
except (ImportError, ValueError):
    from src.data_pipeline.models import SourceDefinition, FreshnessStatus


class FreshnessTracker:
    """
    Evaluates freshness health for data sources.
    Tracks refresh intervals and flags aging or stale policy data.
    """

    @classmethod
    def evaluate_freshness(
        cls,
        source: SourceDefinition,
        now: Optional[datetime] = None
    ) -> FreshnessStatus:
        """
        Determines current freshness status based on fetch history and freshness policy.
        """
        if not source.last_successful_fetch:
            return FreshnessStatus.UNKNOWN

        current_time = now or datetime.now(timezone.utc)

        try:
            fetch_time = datetime.fromisoformat(source.last_successful_fetch.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return FreshnessStatus.UNKNOWN

        age = current_time - fetch_time
        if age < timedelta(0):
            # Clock drift or future timestamp
            return FreshnessStatus.FRESH

        # Stale threshold check
        stale_threshold = timedelta(days=source.stale_after_days)
        if age > stale_threshold:
            return FreshnessStatus.STALE

        # Aging threshold check (past expected refresh interval)
        expected_interval = timedelta(hours=source.update_frequency_hours)
        if age > expected_interval:
            return FreshnessStatus.AGING

        return FreshnessStatus.FRESH

    @classmethod
    def is_quarantine_required(cls, source: SourceDefinition) -> bool:
        """
        Returns True if the source has become stale and should not be activated automatically.
        """
        status = cls.evaluate_freshness(source)
        return status in (FreshnessStatus.STALE, FreshnessStatus.FAILED)