"""
PolicySetu Source Registry Manager.
Provides registration, lookup, authority precedence ordering,
URL allowlist validation, and source freshness tracking.
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..models import SourceDefinition, AuthorityTier, SourceType
    from .sources import APPROVED_SOURCES
except (ImportError, ValueError):
    from src.data_pipeline.models import SourceDefinition, AuthorityTier, SourceType
    from src.data_pipeline.sources.sources import APPROVED_SOURCES


class SourceRegistry:
    """
    Central registry for all statutory and supplementary data sources.
    Strictly forbids uncontrolled crawling by enforcing an explicit allowlist.
    """

    def __init__(self, initial_sources: Optional[Dict[str, SourceDefinition]] = None):
        self._sources: Dict[str, SourceDefinition] = {}
        sources_to_load = initial_sources if initial_sources is not None else APPROVED_SOURCES
        for sid, sdef in sources_to_load.items():
            self.register(sdef)

    def register(self, source: SourceDefinition) -> None:
        """Registers or updates a source definition."""
        self._sources[source.source_id] = source

    def get(self, source_id: str) -> Optional[SourceDefinition]:
        """Retrieves a source definition by ID."""
        return self._sources.get(source_id)

    def list_sources(self, enabled_only: bool = True) -> List[SourceDefinition]:
        """Lists all registered sources."""
        sources = list(self._sources.values())
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        return sources

    def list_by_tier(self, tier: AuthorityTier, enabled_only: bool = True) -> List[SourceDefinition]:
        """Filters sources by authority tier."""
        return [s for s in self.list_sources(enabled_only=enabled_only) if s.authority_tier == tier]

    def sorted_by_precedence(self, enabled_only: bool = True) -> List[SourceDefinition]:
        """
        Returns sources ordered from highest authority tier to lowest:
        PRIMARY_OFFICIAL (5) > PRIMARY_CANONICALIZED (4) > SUPPLEMENTARY (3) > ARCHIVE (2) > EVALUATION_ONLY (1)
        """
        sources = self.list_sources(enabled_only=enabled_only)
        return sorted(sources, key=lambda s: s.authority_tier.priority, reverse=True)

    # Approved exact government discovery hosts
    APPROVED_EXACT_HOSTS = {
        "www.myscheme.gov.in",
        "myscheme.gov.in",
        "india.gov.in",
        "www.india.gov.in",
    }

    # Approved external HuggingFace scheme dataset repository identifiers
    APPROVED_HF_REPOS = {
        "satyajitdas/bharatschemes-v1",
        "smartduketech/indian-government-schemes-2025",
        "shrijayan/gov_myscheme",
    }

    def is_url_allowed(self, url: str) -> bool:
        """
        Validates if a URL belongs to a registered official domain or path.
        Enforces strict host and path allowlists, forbidding uncontrolled crawling or
        arbitrary repo fetching from external hosting platforms (e.g. HuggingFace).
        """
        if not url:
            return False

        parsed_target = urlparse(url)
        scheme = parsed_target.scheme.lower()
        if scheme not in ("http", "https"):
            return False

        host = (parsed_target.netloc or "").lower().split(":")[0]
        path = parsed_target.path.strip("/")

        # 1. Official Indian government domains (.gov.in, .nic.in)
        if host == "gov.in" or host.endswith(".gov.in") or host == "nic.in" or host.endswith(".nic.in"):
            return True

        # 2. Approved exact discovery portal hosts
        if host in self.APPROVED_EXACT_HOSTS:
            return True

        # 3. Third-party repository hardening (e.g. huggingface.co):
        # Strictly require exact approved repo IDs in URL path rather than blanket host or suffix matching
        if host in ("huggingface.co", "www.huggingface.co"):
            parts = [p for p in path.split("/") if p]
            if parts and parts[0] == "datasets":
                parts = parts[1:]
            if len(parts) >= 2:
                repo_id = f"{parts[0]}/{parts[1]}"
                if repo_id in self.APPROVED_HF_REPOS:
                    return True
            return False

        # 4. Check against explicitly registered source definitions
        for s in self.list_sources(enabled_only=True):
            if s.url:
                parsed_source = urlparse(s.url)
                if parsed_source.netloc and parsed_source.netloc.lower() == host:
                    if url.startswith(s.url):
                        return True

        return False

    def update_fetch_status(
        self,
        source_id: str,
        timestamp: str,
        content_hash: str
    ) -> None:
        """Updates the last successful fetch timestamp and content hash."""
        if source_id in self._sources:
            src = self._sources[source_id]
            src.last_successful_fetch = timestamp
            src.last_content_hash = content_hash


# Global default instance
DEFAULT_SOURCE_REGISTRY = SourceRegistry()