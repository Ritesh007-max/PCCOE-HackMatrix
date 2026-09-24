"""
FIN Resilient Acquisition HTTP Client.
Features safe rate limiting, bounded retries with exponential backoff,
SSRF filtering, size limits, and auditable CrawlFailure tracking.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import socket
import ssl
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request
import uuid

from .models import CrawlFailure, HttpRequestRecord, EndpointType
from .security import AcquisitionSecurityValidator, MAX_RESPONSE_SIZE


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Validates redirect targets against SSRF and domain policies after every redirect.
    Limits maximum redirection depth to prevent infinite redirect loops.
    """
    def __init__(self, max_redirects: int = 3, enforce_https: bool = False):
        super().__init__()
        self.max_redirects = max_redirects
        self.enforce_https = enforce_https
        self._redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._redirect_count += 1
        if self._redirect_count > self.max_redirects:
            raise urllib.error.HTTPError(newurl, 400, f"Max redirects ({self.max_redirects}) exceeded", headers, fp)

        is_safe, reason = AcquisitionSecurityValidator.is_safe_url(newurl, enforce_https=self.enforce_https)
        if not is_safe:
            raise urllib.error.HTTPError(newurl, 403, f"SSRF Security Violation on redirect: {reason}", headers, fp)

        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SafeHttpClient:
    """
    Polite and secure HTTP client for government portal data acquisition.
    Enforces concurrency caps, rate limiting, and failure recording.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 FIN-DataAcquisition/1.0"
    )

    def __init__(
        self,
        requests_per_second: float = 6.0,
        timeout: float = 15.0,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        user_agent: Optional[str] = None,
    ):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / max(0.1, requests_per_second)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

        self._last_request_time: float = 0.0
        self._lock = threading.Lock()
        self.failures: List[CrawlFailure] = []
        self.request_ledger: List[HttpRequestRecord] = []
        self.total_requests: int = 0
        self.total_latency_ms: float = 0.0

        # Standard SSL context
        self._ssl_ctx = ssl.create_default_context()

    def _rate_limit(self) -> None:
        """Enforces inter-request delay to protect server stability without thread starvation."""
        if self.requests_per_second <= 0:
            return
        sleep_time = 0.0
        with self._lock:
            now = time.time()
            if self._last_request_time > now:
                scheduled_time = self._last_request_time + self.min_interval
            else:
                scheduled_time = now + self.min_interval
            self._last_request_time = scheduled_time
            sleep_time = scheduled_time - now - self.min_interval
        if sleep_time > 0:
            time.sleep(sleep_time)

    def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes | str] = None,
        scheme_id: Optional[str] = None,
        slug: Optional[str] = None,
        endpoint_type: str = EndpointType.OTHER.value,
        batch_id: Optional[str] = None,
        batch_size: int = 1,
        page: Optional[int] = None,
        language: str = "en",
        run_id: str = "",
    ) -> Tuple[Optional[bytes], Optional[str], Optional[int]]:
        """
        Executes a network request with security validation, bounded retries,
        and request-level instrumentation into request_ledger.
        Returns: (response_bytes, content_sha256, http_status_code)
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        req_timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Validate URL security (SSRF, domain allowlist, deceptive hosts)
        is_safe, reason = AcquisitionSecurityValidator.is_safe_url(url)
        if not is_safe:
            now_iso = datetime.now(timezone.utc).isoformat()
            with self._lock:
                self.failures.append(
                    CrawlFailure(
                        url=url,
                        scheme_id=scheme_id,
                        http_status=403,
                        error_type="SSRF_SECURITY_REJECTION",
                        retry_count=0,
                        first_failure=now_iso,
                        latest_failure=now_iso,
                        reason=reason or "Security validation failed",
                        next_action="REJECT_URL",
                    )
                )
                self.request_ledger.append(
                    HttpRequestRecord(
                        request_id=request_id,
                        endpoint=url,
                        method=method,
                        run_id=run_id,
                        scheme_id=scheme_id,
                        slug=slug,
                        endpoint_type=endpoint_type,
                        batch_id=batch_id,
                        batch_size=batch_size,
                        page=page,
                        language=language,
                        response_size=0,
                        status_code=403,
                        latency_ms=0.0,
                        retry_count=0,
                        success=False,
                        timestamp=req_timestamp,
                        error=f"SSRF_SECURITY_REJECTION: {reason or 'Security validation failed'}",
                    )
                )
            return None, None, 403

        # Prepare headers
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
        }
        if headers:
            req_headers.update(headers)

        payload_bytes: Optional[bytes] = None
        if data is not None:
            if isinstance(data, str):
                payload_bytes = data.encode("utf-8")
            else:
                payload_bytes = data

        first_failure_time: Optional[str] = None
        last_error_reason = ""
        last_status: Optional[int] = None
        duration_ms: float = 0.0

        for attempt in range(self.max_retries + 1):
            self._rate_limit()
            start_t = time.time()
            with self._lock:
                self.total_requests += 1

            req = urllib.request.Request(url, data=payload_bytes, headers=req_headers, method=method)
            try:
                redirect_handler = SafeRedirectHandler(max_redirects=3)
                https_handler = urllib.request.HTTPSHandler(context=self._ssl_ctx)
                opener = urllib.request.build_opener(redirect_handler, https_handler)
                with opener.open(req, timeout=self.timeout) as resp:
                    resp_bytes = resp.read(MAX_RESPONSE_SIZE + 1)
                    duration_ms = (time.time() - start_t) * 1000.0
                    with self._lock:
                        self.total_latency_ms += duration_ms

                    if len(resp_bytes) > MAX_RESPONSE_SIZE:
                        # Exceeded size limit
                        now_iso = datetime.now(timezone.utc).isoformat()
                        with self._lock:
                            self.failures.append(
                                CrawlFailure(
                                    url=url,
                                    scheme_id=scheme_id,
                                    http_status=resp.status,
                                    error_type="PAYLOAD_OVERSIZE",
                                    retry_count=attempt,
                                    first_failure=first_failure_time or now_iso,
                                    latest_failure=now_iso,
                                    reason=f"Response exceeded maximum allowed size of {MAX_RESPONSE_SIZE} bytes",
                                    next_action="DROP_RESPONSE",
                                )
                            )
                            self.request_ledger.append(
                                HttpRequestRecord(
                                    request_id=request_id,
                                    endpoint=url,
                                    method=method,
                                    run_id=run_id,
                                    scheme_id=scheme_id,
                                    slug=slug,
                                    endpoint_type=endpoint_type,
                                    batch_id=batch_id,
                                    batch_size=batch_size,
                                    page=page,
                                    language=language,
                                    response_size=len(resp_bytes),
                                    status_code=resp.status,
                                    latency_ms=round(duration_ms, 2),
                                    retry_count=attempt,
                                    success=False,
                                    timestamp=req_timestamp,
                                    error="PAYLOAD_OVERSIZE",
                                )
                            )
                        return None, None, resp.status

                    content_hash = hashlib.sha256(resp_bytes).hexdigest()
                    with self._lock:
                        self.request_ledger.append(
                            HttpRequestRecord(
                                request_id=request_id,
                                endpoint=url,
                                method=method,
                                run_id=run_id,
                                scheme_id=scheme_id,
                                slug=slug,
                                endpoint_type=endpoint_type,
                                batch_id=batch_id,
                                batch_size=batch_size,
                                page=page,
                                language=language,
                                response_size=len(resp_bytes),
                                status_code=resp.status,
                                latency_ms=round(duration_ms, 2),
                                retry_count=attempt,
                                success=True,
                                timestamp=req_timestamp,
                                error=None,
                            )
                        )
                    return resp_bytes, content_hash, resp.status

            except urllib.error.HTTPError as e:
                duration_ms = (time.time() - start_t) * 1000.0
                with self._lock:
                    self.total_latency_ms += duration_ms
                last_status = e.code
                last_error_reason = f"HTTP {e.code}: {e.reason}"
                now_iso = datetime.now(timezone.utc).isoformat()
                if not first_failure_time:
                    first_failure_time = now_iso

                # Special handling for HTTP 429 (Rate Limit): cooperative backoff
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After")
                    try:
                        base_wait = float(retry_after) if retry_after else 4.0 * (1.5 ** attempt)
                    except Exception:
                        base_wait = 4.0 * (1.5 ** attempt)
                    backoff_delay = base_wait + random.uniform(1.0, 3.0)
                    with self._lock:
                        now_t = time.time()
                        if self._last_request_time < now_t + backoff_delay:
                            self._last_request_time = now_t + backoff_delay
                    time.sleep(backoff_delay)
                    continue

                # Don't retry client 404 or 403
                if e.code in (404, 403, 401, 410):
                    with self._lock:
                        self.failures.append(
                            CrawlFailure(
                                url=url,
                                scheme_id=scheme_id,
                                http_status=e.code,
                                error_type="CLIENT_ERROR",
                                retry_count=attempt,
                                first_failure=first_failure_time,
                                latest_failure=now_iso,
                                reason=last_error_reason,
                                next_action="FLAG_MISSING_OR_FORBIDDEN",
                            )
                        )
                        self.request_ledger.append(
                            HttpRequestRecord(
                                request_id=request_id,
                                endpoint=url,
                                method=method,
                                run_id=run_id,
                                scheme_id=scheme_id,
                                slug=slug,
                                endpoint_type=endpoint_type,
                                batch_id=batch_id,
                                batch_size=batch_size,
                                page=page,
                                language=language,
                                response_size=0,
                                status_code=e.code,
                                latency_ms=round(duration_ms, 2),
                                retry_count=attempt,
                                success=False,
                                timestamp=req_timestamp,
                                error=last_error_reason,
                            )
                        )
                    return None, None, e.code

            except (urllib.error.URLError, TimeoutError, socket.timeout, Exception) as e:
                duration_ms = (time.time() - start_t) * 1000.0
                with self._lock:
                    self.total_latency_ms += duration_ms
                last_error_reason = f"{type(e).__name__}: {str(e)}"
                now_iso = datetime.now(timezone.utc).isoformat()
                if not first_failure_time:
                    first_failure_time = now_iso

            # Exponential backoff before retry
            if attempt < self.max_retries:
                sleep_secs = self.backoff_factor * (2 ** attempt)
                time.sleep(sleep_secs)

        # Retries exhausted
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.failures.append(
                CrawlFailure(
                    url=url,
                    scheme_id=scheme_id,
                    http_status=last_status,
                    error_type="RETRIES_EXHAUSTED",
                    retry_count=self.max_retries,
                    first_failure=first_failure_time or now_iso,
                    latest_failure=now_iso,
                    reason=last_error_reason,
                    next_action="MANUAL_AUDIT_REQUIRED",
                )
            )
            self.request_ledger.append(
                HttpRequestRecord(
                    request_id=request_id,
                    endpoint=url,
                    method=method,
                    run_id=run_id,
                    scheme_id=scheme_id,
                    slug=slug,
                    endpoint_type=endpoint_type,
                    batch_id=batch_id,
                    batch_size=batch_size,
                    page=page,
                    language=language,
                    response_size=0,
                    status_code=last_status,
                    latency_ms=round(duration_ms, 2),
                    retry_count=self.max_retries,
                    success=False,
                    timestamp=req_timestamp,
                    error=last_error_reason,
                )
            )
        return None, None, last_status

    def export_request_ledger(self, filepath: Path) -> Path:
        """Exports complete HTTP request ledger to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            records = [r.to_dict() for r in self.request_ledger]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        return filepath
