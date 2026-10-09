"""
FIN Scheme Rule Registry and Immutable Versioning Subsystem.
Enforces that:
- Every active rule set has a deterministic identity, semantic version, and SHA256 integrity hash.
- Rule sets cannot be mutated once activated (immutability).
- Activation gates prevent invalid, contradictory, or ungrounded rules from activating.
- Rollback to prior versions is safe, deterministic, and preserves historical decision pinning.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from .candidate import RuleLifecycleStatus
from .exceptions import (
    ActivationGateError,
    ContradictoryRuleError,
    RuleVersionNotFoundError,
)
from .models import SchemeRuleSet
from .validator import RuleSetCompleteness, RuleValidator

logger = logging.getLogger("fin.rules.versioning")


def compute_ruleset_hash(ruleset: SchemeRuleSet) -> str:
    """
    Computes a deterministic SHA256 hash of a SchemeRuleSet.
    Sorts rules and keys to ensure identical AST structures yield identical hashes.
    """
    canonical_repr = {
        "scheme_id": ruleset.scheme_id,
        "scheme_slug": ruleset.scheme_slug,
        "version": ruleset.version,
        "root_logic": (ruleset.root_logic or "AND").upper(),
        "rules": sorted(
            [
                {
                    "rule_id": r.rule_id,
                    "field": r.field,
                    "operator": r.operator,
                    "expected_value": r.expected_value,
                    "value_type": r.value_type,
                    "hard_constraint": r.hard_constraint,
                    "logic_group": r.logic_group,
                }
                for r in ruleset.rules
            ],
            key=lambda x: x["rule_id"],
        ),
        "logic_groups": sorted(
            [
                {
                    "group_id": g.group_id,
                    "operator": g.operator,
                    "rule_ids": sorted(g.rule_ids),
                }
                for g in ruleset.logic_groups
            ],
            key=lambda x: x["group_id"],
        ),
    }

    serialized = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class SchemeRuleRegistry:
    """
    Multi-version registry managing SchemeRuleSets with activation gates and safe rollback.
    """

    def __init__(self, validator: Optional[RuleValidator] = None):
        self._validator = validator or RuleValidator()
        # Mapping: scheme_slug -> {version_str: SchemeRuleSet}
        self._versions: Dict[str, Dict[str, SchemeRuleSet]] = {}
        # Mapping: scheme_slug -> active_version_str
        self._active_versions: Dict[str, str] = {}
        # Mapping: scheme_id -> scheme_slug alias
        self._id_to_slug: Dict[str, str] = {}
        # Mapping: (scheme_slug, version) -> sha256_hash
        self._version_hashes: Dict[Tuple[str, str], str] = {}
        # Mapping: (scheme_slug, version) -> RuleLifecycleStatus
        self._version_statuses: Dict[Tuple[str, str], RuleLifecycleStatus] = {}
        # Audit log of activation and rollback events
        self._audit_log: List[Dict[str, Any]] = []

    def _resolve_slug(self, identifier: str) -> str:
        """Resolves either scheme_slug or scheme_id to canonical scheme_slug."""
        if identifier in self._versions:
            return identifier
        if identifier in self._id_to_slug:
            return self._id_to_slug[identifier]
        return identifier

    def register_ruleset(
        self,
        ruleset: SchemeRuleSet,
        activate: bool = False,
        validate: bool = True,
    ) -> SchemeRuleSet:
        """
        Registers a SchemeRuleSet version under its scheme slug.
        Computes its integrity hash and executes validation gates if requested.
        """
        slug = ruleset.scheme_slug
        ver = ruleset.version or "1.0.0"

        # Track scheme_id alias
        if ruleset.scheme_id:
            self._id_to_slug[ruleset.scheme_id] = slug

        if slug not in self._versions:
            self._versions[slug] = {}

        # Compute deterministic integrity hash
        ruleset_hash = compute_ruleset_hash(ruleset)
        self._version_hashes[(slug, ver)] = ruleset_hash

        # Run validation gates
        if validate:
            v_res = self._validator.validate_ruleset(ruleset)
            if v_res.contradictions:
                self._version_statuses[(slug, ver)] = RuleLifecycleStatus.REVIEW
                if activate:
                    raise ContradictoryRuleError(
                        f"Cannot activate contradictory ruleset '{slug}' v{ver}: {v_res.contradictions}"
                    )
            elif not v_res.is_valid:
                self._version_statuses[(slug, ver)] = RuleLifecycleStatus.REJECTED
                if activate:
                    raise ActivationGateError(
                        f"Cannot activate invalid ruleset '{slug}' v{ver}. Errors: {v_res.errors}"
                    )
            else:
                self._version_statuses[(slug, ver)] = RuleLifecycleStatus.VALIDATED
        else:
            self._version_statuses[(slug, ver)] = RuleLifecycleStatus.CANDIDATE


        # Store ruleset
        self._versions[slug][ver] = ruleset

        # If activation is requested, run activation gates
        if activate:
            self.activate_version(slug, ver)
        elif slug not in self._active_versions and self._version_statuses.get((slug, ver)) == RuleLifecycleStatus.VALIDATED:
            # Default auto-activate first validated version if none active
            self._active_versions[slug] = ver
            self._version_statuses[(slug, ver)] = RuleLifecycleStatus.ACTIVE

        return ruleset

    def activate_version(self, identifier: str, version: str) -> None:
        """
        Activates a specific registered version of a scheme's rule set.
        Enforces validation gates:
        - Version must exist
        - Must pass validation (zero fatal errors, zero contradictions)
        - Previous active version is retired.
        """
        slug = self._resolve_slug(identifier)
        if slug not in self._versions or version not in self._versions[slug]:
            raise RuleVersionNotFoundError(f"Version '{version}' for scheme '{identifier}' not found in registry.")

        ruleset = self._versions[slug][version]
        v_res = self._validator.validate_ruleset(ruleset)

        if not v_res.can_activate:
            raise ActivationGateError(
                f"Rule set '{slug}' v{version} failed activation gates. Errors: {v_res.errors}; Contradictions: {v_res.contradictions}"
            )

        prev_version = self._active_versions.get(slug)
        if prev_version and prev_version != version:
            self._version_statuses[(slug, prev_version)] = RuleLifecycleStatus.RETIRED

        self._active_versions[slug] = version
        self._version_statuses[(slug, version)] = RuleLifecycleStatus.ACTIVE

        event = {
            "event": "ACTIVATION",
            "scheme_slug": slug,
            "version": version,
            "previous_version": prev_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": self._version_hashes.get((slug, version)),
        }
        self._audit_log.append(event)
        logger.info("Activated scheme ruleset %s v%s (previous: %s)", slug, version, prev_version)

    def rollback_version(self, identifier: str, target_version: str) -> None:
        """
        Rolls back the active version to a specified prior version.
        Guarantees:
        - Target version exists and passes activation gates
        - Previous active version is retired
        - Historical decisions remain pinned and unaffected
        """
        slug = self._resolve_slug(identifier)
        if slug not in self._versions or target_version not in self._versions[slug]:
            raise RuleVersionNotFoundError(f"Cannot rollback: target version '{target_version}' does not exist for '{identifier}'.")

        current_ver = self._active_versions.get(slug)
        if current_ver == target_version:
            logger.info("Scheme %s is already at version %s. No rollback needed.", slug, target_version)
            return

        # Activate target version
        self.activate_version(slug, target_version)

        event = {
            "event": "ROLLBACK",
            "scheme_slug": slug,
            "rolled_back_from": current_ver,
            "rolled_back_to": target_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._audit_log.append(event)
        logger.warning("Rolled back scheme %s from v%s to v%s", slug, current_ver, target_version)

    def get_active_ruleset(self, identifier: str) -> SchemeRuleSet:
        """Returns the currently active SchemeRuleSet for a scheme."""
        slug = self._resolve_slug(identifier)
        if slug not in self._versions:
            raise KeyError(f"Scheme '{identifier}' is not registered.")
        active_ver = self._active_versions.get(slug)
        if not active_ver or active_ver not in self._versions[slug]:
            raise KeyError(f"No active rule version for scheme '{identifier}'.")
        return self._versions[slug][active_ver]

    def get_ruleset_version(self, identifier: str, version: str) -> SchemeRuleSet:
        """Retrieves a specific version of a SchemeRuleSet (supporting historical reproducibility)."""
        slug = self._resolve_slug(identifier)
        if slug not in self._versions:
            raise KeyError(f"Scheme '{identifier}' is not registered.")
        if version not in self._versions[slug]:
            raise RuleVersionNotFoundError(f"Version '{version}' for scheme '{identifier}' not found.")
        return self._versions[slug][version]

    def get_hash(self, identifier: str, version: Optional[str] = None) -> str:
        """Returns the SHA256 integrity hash for a scheme version."""
        slug = self._resolve_slug(identifier)
        ver = version or self._active_versions.get(slug, "")
        return self._version_hashes.get((slug, ver), "")

    def list_schemes(self) -> List[str]:
        """Returns a list of all registered scheme slugs."""
        return sorted(list(self._versions.keys()))

    def get_all_active_rulesets(self) -> List[SchemeRuleSet]:
        """Returns the active SchemeRuleSet for all registered schemes."""
        result = []
        for slug in sorted(self._versions.keys()):
            if slug in self._active_versions:
                ver = self._active_versions[slug]
                result.append(self._versions[slug][ver])
        return result

    def get_scheme_metadata(self, identifier: str) -> Dict[str, Any]:
        """Returns registry metadata for a scheme."""
        slug = self._resolve_slug(identifier)
        if slug not in self._versions:
            raise KeyError(f"Scheme '{identifier}' is not registered.")
        return {
            "scheme_slug": slug,
            "active_version": self._active_versions.get(slug),
            "versions": sorted(list(self._versions[slug].keys())),
            "version_statuses": {
                v: self._version_statuses.get((slug, v), RuleLifecycleStatus.DRAFT).value
                for v in self._versions[slug]
            },
            "version_hashes": {
                v: self._version_hashes.get((slug, v), "")
                for v in self._versions[slug]
            },
        }
