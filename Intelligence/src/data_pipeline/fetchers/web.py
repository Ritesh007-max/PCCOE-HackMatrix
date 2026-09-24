"""
FIN Web Fetcher.
Safely retrieves registered official URLs with strict allowlist enforcement,
exponential backoff, ETag/If-Modified-Since caching, and HTTP status handling.
"""

from datetime import datetime, timezone
import hashlib
import time
from typing import Callable, Dict, Optional
import urllib.request
import urllib.error

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
    from ..sources.registry import SourceRegistry, DEFAULT_SOURCE_REGISTRY
except (ImportError, ValueError):
    from src.data_pipeline.fetchers.base import BaseFetcher, FetchResult
    from src.data_pipeline.sources.registry import SourceRegistry, DEFAULT_SOURCE_REGISTRY


class WebFetcher(BaseFetcher):
    """
    HTTP/HTTPS fetcher for registered government portals and APIs.
    Disallows fetching unapproved domains.
    Supports mock handlers for offline unit testing.
    """

    def __init__(
        self,
        registry: Optional[SourceRegistry] = None,
        timeout_seconds: int = 15,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        mock_handler: Optional[Callable[[str, Dict[str, str]], FetchResult]] = None,
    ):
        super().__init__(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )
        self.registry = registry or DEFAULT_SOURCE_REGISTRY
        self.mock_handler = mock_handler

    def fetch(
        self,
        url: str,
        source_id: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        **kwargs
    ) -> FetchResult:
        """
        Executes a safe GET request.
        Enforces domain allowlist.
        """
        start_time = datetime.now(timezone.utc)

        # 1. Allowlist enforcement
        if not self.registry.is_url_allowed(url):
            return FetchResult(
                source_id=source_id,
                url=url,
                status_code=403,
                error=f"URL '{url}' is not in the approved source registry allowlist.",
                success=False,
            )

        # 2. Mock handler intercept (for 100% offline testing)
        if self.mock_handler:
            headers = {}
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified
            return self.mock_handler(url, headers)

        # 3. Real network execution with retries
        headers = {"User-Agent": self.user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        req = urllib.request.Request(url, headers=headers)
        attempt = 0
        last_error = ""

        while attempt < self.max_retries:
            attempt += 1
            self._apply_rate_limit()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    status_code = resp.status
                    content_bytes = resp.read()
                    resp_etag = resp.headers.get("ETag")
                    resp_last_modified = resp.headers.get("Last-Modified")
                    content_type = resp.headers.get("Content-Type", "text/html")
                    content_hash = hashlib.sha256(content_bytes).hexdigest()

                    duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                    return FetchResult(
                        source_id=source_id,
                        url=url,
                        status_code=status_code,
                        content=content_bytes,
                        text_content=content_bytes.decode("utf-8", errors="replace"),
                        content_type=content_type,
                        content_hash=content_hash,
                        etag=resp_etag,
                        last_modified=resp_last_modified,
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=duration_ms,
                        success=True,
                    )
            except urllib.error.HTTPError as http_err:
                if http_err.code == 304:  # Not Modified
                    return FetchResult(
                        source_id=source_id,
                        url=url,
                        status_code=304,
                        etag=etag,
                        last_modified=last_modified,
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        success=True,
                    )
                elif http_err.code in (404, 403, 401):
                    # Non-retryable client errors
                    return FetchResult(
                        source_id=source_id,
                        url=url,
                        status_code=http_err.code,
                        error=f"HTTP {http_err.code}: {http_err.reason}",
                        success=False,
                    )
                elif http_err.code == 429:  # Rate limited
                    wait_time = self.backoff_factor ** attempt * 2
                    time.sleep(wait_time)
                    last_error = f"HTTP 429 Rate limited on {url}"
                else:
                    last_error = f"HTTP {http_err.code}: {http_err.reason}"
            except urllib.error.URLError as url_err:
                last_error = f"Network connection failed: {url_err.reason}"
            except Exception as exc:
                last_error = f"Unexpected fetch error: {str(exc)}"

            # Wait before next retry attempt
            time.sleep(self.backoff_factor ** attempt)

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        return FetchResult(
            source_id=source_id,
            url=url,
            status_code=500,
            error=f"Failed after {self.max_retries} attempts: {last_error}",
            duration_ms=duration_ms,
            success=False,
        )