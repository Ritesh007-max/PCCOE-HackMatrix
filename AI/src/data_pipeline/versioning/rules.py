"""
PolicySetu Rule Versioning Engine.
Tracks compiled Rule AST versions tied directly to policy source versions.
Suppresses unnecessary rule regeneration when only benefits or descriptions change.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..models import RuleVersionMetadata, RecordDiff
except (ImportError, ValueError):
    from src.data_pipeline.models import RuleVersionMetadata, RecordDiff


class RuleVersionManager:
    """
    Manages statutory eligibility rule AST versions.
    Enforces that eligibility changes trigger new rule versions,
    while non-eligibility changes preserve existing compiled rule representations.
    """

    def __init__(self):
        self._rules_by_slug: Dict[str, List[RuleVersionMetadata]] = {}

    def should_rebuild_rules(self, diff: Optional[RecordDiff]) -> bool:
        """
        Determines whether eligibility rules must be recompiled.
        Returns False if only benefits, descriptions, or non-statutory metadata changed.
        """
        if diff is None:
            return True
        if diff.change_type.value == "ADDED":
            return True
        if diff.change_type.value == "REMOVED":
            return False
        # For MODIFIED records: inspect field diffs
        return diff.has_eligibility_change

    def register_rule_version(
        self,
        scheme_slug: str,
        policy_version_id: str,
        rule_set_data: Dict[str, Any],
        raw_source_text: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> RuleVersionMetadata:
        """
        Registers a newly compiled or migrated rule version.
        """
        now = datetime.now(timezone.utc)
        rule_hash = hashlib.sha256(
            json.dumps(rule_set_data, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        existing = self._rules_by_slug.get(scheme_slug, [])
        version_num = len(existing) + 1
        rule_version_id = f"rules_v{version_num}_{rule_hash[:10]}"

        meta = RuleVersionMetadata(
            rule_version_id=rule_version_id,
            policy_version_id=policy_version_id,
            scheme_slug=scheme_slug,
            rule_hash=rule_hash,
            extraction_timestamp=now.isoformat(),
            source_url=source_url,
            raw_source_text=raw_source_text,
        )

        if scheme_slug not in self._rules_by_slug:
            self._rules_by_slug[scheme_slug] = []
        self._rules_by_slug[scheme_slug].append(meta)

        return meta

    def get_latest_rule_version(self, scheme_slug: str) -> Optional[RuleVersionMetadata]:
        """Returns the most recent compiled rule version for a scheme."""
        versions = self._rules_by_slug.get(scheme_slug, [])
        return versions[-1] if versions else None