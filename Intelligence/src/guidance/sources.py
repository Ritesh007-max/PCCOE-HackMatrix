"""
Source Metadata and Official URL Resolver.
Phase 11: Authoritative scheme metadata resolution, domain allowlist enforcement,
and deadline extraction.
"""

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .models import ApplicationMode, DeadlineGuidance, DeadlineStatus
from .exceptions import InvalidSourceURLError

logger = logging.getLogger("fin.guidance.sources")

# Strict authoritative Indian government domains and vetted official portals
TRUSTED_GOV_DOMAINS = (
    ".gov.in",
    ".nic.in",
    ".ac.in",
    ".res.in",
    "myscheme.gov.in",
    "pmkisan.gov.in",
    "scholarships.gov.in",
    "digitalgujarat.gov.in",
    "swayam.gov.in",
    "epfindia.gov.in",
    "pmjay.gov.in",
)

# Explicitly prohibited patterns (blogs, commercial aggregators, news, search engines)
UNTRUSTED_DOMAIN_PATTERNS = (
    "google.",
    "bing.",
    "yahoo.",
    "blogspot.",
    "wordpress.",
    "medium.com",
    "timesofindia.",
    "hindustantimes.",
    "ndtv.",
    "jagran.",
    "amarujala.",
    "cleartax.",
    "bankbazaar.",
    "policybazaar.",
    "sarkariyojana.",
    "yojana.",
)


class SourceMetadataResolver:
    """
    Resolves official metadata from the active Phase 7 snapshot.
    Enforces strict URL allowlisting and zero-hallucination deadlines.
    """

    def __init__(self, snapshots_root: Optional[Path] = None):
        self.snapshots_root = snapshots_root or Path(__file__).resolve().parents[2] / "data" / "snapshots"
        self._schemes_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _load_snapshot_schemes(self) -> Dict[str, Dict[str, Any]]:
        """Loads canonical scheme metadata index from the active snapshot."""
        if self._schemes_cache is not None:
            return self._schemes_cache

        cache: Dict[str, Dict[str, Any]] = {}
        active_json = self.snapshots_root / "active_version.json"
        snapshot_dir = None

        if active_json.exists():
            try:
                with open(active_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    snap_id = data.get("active_snapshot")
                    if snap_id:
                        snapshot_dir = self.snapshots_root / snap_id
            except Exception as e:
                logger.warning("Could not read active_version.json: %s", e)

        # Fallback to latest directory if active_version.json missing
        if snapshot_dir is None or not snapshot_dir.exists():
            snap_dirs = [d for d in self.snapshots_root.iterdir() if d.is_dir() and d.name.startswith("snapshot_")]
            if snap_dirs:
                snapshot_dir = sorted(snap_dirs)[-1]

        if snapshot_dir and snapshot_dir.exists():
            schemes_jsonl = snapshot_dir / "canonical" / "schemes.jsonl"
            if schemes_jsonl.exists():
                try:
                    with open(schemes_jsonl, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            rec = json.loads(line)
                            sid = rec.get("id") or rec.get("scheme_id")
                            slug = rec.get("slug") or rec.get("scheme_slug")
                            if sid:
                                cache[sid] = rec
                            if slug:
                                cache[slug] = rec
                except Exception as e:
                    logger.error("Failed to parse schemes.jsonl: %s", e)

        self._schemes_cache = cache
        return cache

    def get_scheme_metadata(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Lookup scheme metadata by scheme_id or slug."""
        schemes = self._load_snapshot_schemes()
        if identifier in schemes:
            return schemes[identifier]

        # Normalized slug attempt
        norm_id = identifier.lower().strip().replace("_", "-")
        if norm_id in schemes:
            return schemes[norm_id]

        norm_id_und = identifier.lower().strip().replace("-", "_")
        if norm_id_und in schemes:
            return schemes[norm_id_und]

        return None

    @classmethod
    def validate_official_url(cls, url: Optional[str]) -> Optional[str]:
        """
        Validates URL against trusted government domain allowlist.
        Returns sanitized URL if valid, or None if untrusted / invalid.
        """
        if not url or not isinstance(url, str):
            return None

        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            return None

        try:
            parsed = urlparse(clean_url)
            netloc = (parsed.netloc or "").lower()

            # Reject untrusted patterns
            for bad in UNTRUSTED_DOMAIN_PATTERNS:
                if bad in netloc:
                    logger.warning("Rejected non-authoritative URL domain '%s'", netloc)
                    return None

            # Verify trusted domain suffix or match
            is_trusted = False
            for trusted in TRUSTED_GOV_DOMAINS:
                if netloc == trusted or netloc.endswith(trusted):
                    is_trusted = True
                    break

            if is_trusted:
                return clean_url

            logger.warning("URL '%s' does not match trusted government domain patterns", clean_url)
            return None
        except Exception:
            return None

    def resolve_official_portal_url(self, scheme_id: str, default_fallback: Optional[str] = None) -> Optional[str]:
        """
        Resolves verified official portal URL for a scheme.
        Zero fabrication guarantee: returns None if no verified link exists.
        """
        meta = self.get_scheme_metadata(scheme_id)
        if meta:
            # Check source_url first
            s_url = self.validate_official_url(meta.get("source_url"))
            if s_url:
                return s_url

            # Check references list
            refs = meta.get("references", [])
            if isinstance(refs, list):
                for ref in refs:
                    ref_url = self.validate_official_url(ref if isinstance(ref, str) else ref.get("url"))
                    if ref_url:
                        return ref_url

        if default_fallback:
            return self.validate_official_url(default_fallback)

        return None

    def resolve_application_mode(self, scheme_id: str) -> ApplicationMode:
        """Determines official application mode from metadata."""
        meta = self.get_scheme_metadata(scheme_id)
        if not meta:
            return ApplicationMode.UNKNOWN

        mode_raw = meta.get("application_mode")
        if isinstance(mode_raw, list) and mode_raw:
            return ApplicationMode.from_string(" ".join(str(m) for m in mode_raw))
        if isinstance(mode_raw, str):
            return ApplicationMode.from_string(mode_raw)

        return ApplicationMode.UNKNOWN

    def resolve_deadlines(self, scheme_id: str, policy_version: str = "V1") -> DeadlineGuidance:
        """
        Extracts verified application opening and closing deadlines.
        Never hallucinates dates.
        """
        meta = self.get_scheme_metadata(scheme_id)
        if not meta:
            return DeadlineGuidance(
                status=DeadlineStatus.UNKNOWN,
                deadline_notes="Scheme metadata unavailable in active snapshot.",
                policy_snapshot_version=policy_version,
            )

        open_d = meta.get("scheme_open_date")
        close_d = meta.get("scheme_close_date")

        if open_d or close_d:
            notes = f"Application window: Open from {open_d or 'unspecified'} to {close_d or 'rolling / ongoing'}."
            return DeadlineGuidance(
                status=DeadlineStatus.KNOWN,
                open_date=str(open_d) if open_d else None,
                close_date=str(close_d) if close_d else None,
                deadline_notes=notes,
                policy_snapshot_version=policy_version,
            )

        return DeadlineGuidance(
            status=DeadlineStatus.UNKNOWN,
            deadline_notes="Application window is rolling or not explicitly scheduled in verified policy evidence.",
            policy_snapshot_version=policy_version,
        )
