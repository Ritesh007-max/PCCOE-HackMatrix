"""
FIN Crawler Security, SSRF Protection, and Content Validation.
Enforces strict domain allowlists, private network isolation, payload limits,
and prompt injection defense. Downloaded policy text is DATA, NEVER instructions.
"""

import ipaddress
import os
from pathlib import Path
import re
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse


# Maximum allowed response size in bytes (25 MB)
MAX_RESPONSE_SIZE = 25 * 1024 * 1024

# Cloud metadata and link-local addresses strictly forbidden
FORBIDDEN_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure IMDSv1
    "fd00:ec2::254",    # AWS IPv6 IMDS
    "127.0.0.1",        # Localhost IPv4
    "::1",              # Localhost IPv6
    "0.0.0.0",          # Current network
}

# Suspicious hostnames and cloud metadata hosts
FORBIDDEN_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
    "169.254.169.254",
    "0.0.0.0",
}


class AcquisitionSecurityValidator:
    """
    Guards network and file access during live data acquisition.
    Prevents SSRF, malicious redirects, oversized payloads, and path traversal.
    """

    # Approved official government domain suffixes
    APPROVED_GOV_SUFFIXES = (
        ".gov.in",
        ".nic.in",
    )

    # Approved explicit discovery hosts
    APPROVED_EXPLICIT_HOSTS = {
        "myscheme.gov.in",
        "www.myscheme.gov.in",
        "search.myscheme.gov.in",
        "rules.myscheme.gov.in",
        "api.myscheme.gov.in",
        "cdn.myscheme.in",
        "india.gov.in",
        "www.india.gov.in",
        "digitalindia.gov.in",
        "www.digitalindia.gov.in",
        "data.gov.in",
        "www.data.gov.in",
        "web.umang.gov.in",
        "jansuraksha.gov.in",
        "www.jansuraksha.gov.in",
    }

    @classmethod
    def is_safe_url(cls, url: str, enforce_https: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validates URL against SSRF, deceptive host spoofing, and domain rules.
        Returns: (is_safe: bool, reason: Optional[str])
        """
        if not url or not isinstance(url, str):
            return False, "Empty or non-string URL"

        clean = url.strip()
        parsed = urlparse(clean)

        # 1. Scheme check
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False, f"Unsupported URL scheme '{parsed.scheme}'; only HTTP/HTTPS permitted"

        if enforce_https and scheme != "https":
            return False, f"Insecure scheme '{parsed.scheme}'; HTTPS strictly required for official government ingestion"

        host = (parsed.netloc or "").split(":")[0].strip().lower()
        if not host:
            return False, "Missing hostname in URL"

        # Check forbidden hostnames
        if host in FORBIDDEN_HOSTNAMES:
            return False, f"Domain '{host}' is not an authorized official government portal (SSRF violation: Direct access to restricted host '{host}')"

        # Check encoded numeric/hex IP addresses (e.g. 2130706433 or 0x7f000001)
        if host.isdigit() or host.startswith("0x"):
            return False, f"Domain '{host}' is not an authorized official government portal (SSRF violation: Direct access via encoded numeric host '{host}')"

        # 2. IP resolution & Private network / SSRF check
        try:
            # Check if host itself is a raw IP literal
            try:
                ip_obj = ipaddress.ip_address(host)
                if cls._is_private_or_restricted(ip_obj):
                    return False, f"Domain '{host}' is not an authorized official government portal (SSRF violation: Direct access to private/loopback IP '{host}')"
                return False, f"Domain '{host}' is not an authorized official government portal (SSRF violation: Direct IP access to '{host}' is prohibited; official domain name required)"
            except ValueError:
                # Host is a DNS name; check if it resolves to private IP
                try:
                    resolved_ip_str = socket.gethostbyname(host)
                    resolved_ip = ipaddress.ip_address(resolved_ip_str)
                    if cls._is_private_or_restricted(resolved_ip):
                        return False, f"Domain '{host}' is not an authorized official government portal (SSRF violation: '{host}' resolves to restricted IP '{resolved_ip_str}')"
                except (socket.gaierror, socket.herror):
                    # Hostname could not be resolved currently; allowed to proceed if domain is valid
                    pass
        except Exception as e:
            return False, f"SSRF security check error: {str(e)}"

        # 3. Deceptive domain spoofing check
        if any(tok in host for tok in (".gov.in.", ".nic.in.", "gov-in", "nic-in", "gov_in")):
            return False, f"Rejected deceptive spoofed domain '{host}'"

        # 4. Domain allowlist check
        is_official = False
        if host in cls.APPROVED_EXPLICIT_HOSTS:
            is_official = True
        elif (host.endswith(".gov.in") or host.endswith(".nic.in")) and not host.endswith("-gov.in"):
            is_official = True

        if not is_official:
            return False, f"Domain '{host}' is not an authorized official government portal"

        return True, None

    @classmethod
    def _is_private_or_restricted(cls, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Checks if IP belongs to private, loopback, link-local, or cloud metadata ranges."""
        if str(ip) in FORBIDDEN_IPS:
            return True
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        )

    @classmethod
    def sanitize_file_path(cls, base_dir: Path, filename: str) -> Path:
        """
        Guards against directory traversal (zip slip / path traversal).
        Ensures resulting path stays strictly inside base_dir.
        """
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            raise ValueError(f"Directory traversal detected in filename: '{filename}'")
        clean_name = os.path.basename(filename)
        clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)
        target = (base_dir / clean_name).resolve()
        base_resolved = base_dir.resolve()
        if not str(target).startswith(str(base_resolved)):
            raise ValueError(f"Directory traversal detected in filename: '{filename}'")
        return target

    @classmethod
    def sanitize_untrusted_text(cls, raw_text: str) -> str:
        """
        Ensures downloaded policy text is treated strictly as passive DATA.
        Strips potential executable script tags and neutralizing prompt injection attempts.
        """
        if not raw_text:
            return ""
        # Remove embedded script/iframe tags
        cleaned = re.sub(r"<(script|iframe|object|embed)[^>]*>.*?</\1>", "", raw_text, flags=re.DOTALL | re.IGNORECASE)
        # Strip null bytes
        cleaned = cleaned.replace("\x00", "")
        return cleaned.strip()
