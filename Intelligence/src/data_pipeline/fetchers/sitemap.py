"""
FIN Sitemap Fetcher and Inventory Diff Engine.
Parses XML sitemaps, extracts scheme URLs, compares against historical inventories,
and identifies added, removed, changed, and unchanged scheme URLs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Dict, List, Optional, Set
import xml.etree.ElementTree as ET

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .base import BaseFetcher, FetchResult
except (ImportError, ValueError):
    from src.data_pipeline.fetchers.base import BaseFetcher, FetchResult


@dataclass
class SitemapDiff:
    """Represents changes in sitemap URL inventory between runs."""
    added_urls: List[str] = field(default_factory=list)
    removed_urls: List[str] = field(default_factory=list)
    changed_urls: List[str] = field(default_factory=list)
    unchanged_urls: List[str] = field(default_factory=list)
    total_urls: int = 0
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


class SitemapFetcher(BaseFetcher):
    """
    Fetches and parses XML sitemaps.
    Maintains historical inventory to enable smart incremental crawling.
    """

    def __init__(
        self,
        scheme_url_pattern: str = r"/schemes?/[a-zA-Z0-9_-]+$",
        timeout_seconds: int = 30
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.scheme_url_regex = re.compile(scheme_url_pattern, re.IGNORECASE)

    def fetch(self, url: str, source_id: str, **kwargs) -> FetchResult:
        """Downloads the sitemap XML."""
        # Use LocalBaselineFetcher if url is a local file, otherwise simulated or WebFetcher
        if url.startswith("http://") or url.startswith("https://"):
            from .web import WebFetcher
            web_fetcher = WebFetcher(timeout_seconds=self.timeout_seconds)
            return web_fetcher.fetch(url=url, source_id=source_id, **kwargs)
        else:
            from .local import LocalBaselineFetcher
            local_fetcher = LocalBaselineFetcher()
            return local_fetcher.fetch(url=url, source_id=source_id, **kwargs)

    def parse_sitemap(self, xml_content: str) -> Dict[str, Optional[str]]:
        """
        Parses XML string and returns map of {url: lastmod}.
        Filters URLs matching the configured scheme pattern.
        """
        url_map: Dict[str, Optional[str]] = {}
        try:
            root = ET.fromstring(xml_content)
            # Handle XML namespaces
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            for url_elem in root.findall(f"{ns}url"):
                loc_elem = url_elem.find(f"{ns}loc")
                if loc_elem is not None and loc_elem.text:
                    loc = loc_elem.text.strip()
                    if self.scheme_url_regex.search(loc):
                        lastmod_elem = url_elem.find(f"{ns}lastmod")
                        lastmod = lastmod_elem.text.strip() if lastmod_elem is not None and lastmod_elem.text else None
                        url_map[loc] = lastmod
        except ET.ParseError:
            # Fallback regex extraction if XML is slightly malformed
            locs = re.findall(r"<loc>(.*?)</loc>", xml_content, re.IGNORECASE)
            for loc in locs:
                clean_loc = loc.strip()
                if self.scheme_url_regex.search(clean_loc):
                    url_map[clean_loc] = None

        return url_map

    def diff_inventories(
        self,
        current_inventory: Dict[str, Optional[str]],
        previous_inventory: Dict[str, Optional[str]]
    ) -> SitemapDiff:
        """
        Computes inventory delta between current and previous crawls.
        """
        curr_keys: Set[str] = set(current_inventory.keys())
        prev_keys: Set[str] = set(previous_inventory.keys())

        added = list(curr_keys - prev_keys)
        removed = list(prev_keys - curr_keys)

        changed = []
        unchanged = []

        for url in curr_keys & prev_keys:
            curr_mod = current_inventory.get(url)
            prev_mod = previous_inventory.get(url)
            if curr_mod and prev_mod and curr_mod != prev_mod:
                changed.append(url)
            else:
                unchanged.append(url)

        return SitemapDiff(
            added_urls=sorted(added),
            removed_urls=sorted(removed),
            changed_urls=sorted(changed),
            unchanged_urls=sorted(unchanged),
            total_urls=len(curr_keys),
        )