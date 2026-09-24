"""
FIN myScheme Source-Specific Parser.
Transforms raw web responses (HTML or API JSON) into canonical statutory scheme representations.
Preserves official first-party ministry/department URLs as authoritative references.
"""

from html.parser import HTMLParser
import json
import re
from typing import Any, Dict, List, Optional
import uuid


class _TextExtractor(HTMLParser):
    """Simple robust HTML text extractor without heavy external dependencies."""
    def __init__(self):
        super().__init__()
        self._tokens: List[str] = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style", "meta", "link"):
            self._in_script = True
        elif tag.lower() in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self._tokens.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style", "meta", "link"):
            self._in_script = False
        elif tag.lower() in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self._tokens.append("\n")

    def handle_data(self, data):
        if not self._in_script:
            self._tokens.append(data)

    def get_text(self) -> str:
        raw = "".join(self._tokens)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.split("\n")]
        return "\n".join([line for line in lines if line])


class MySchemeParser:
    """
    Specialized parser for national myScheme platform responses.
    Parses scheme sections, eligibility criteria, benefits, documents, and FAQs.
    """

    @classmethod
    def parse_raw_response(
        cls,
        raw_text: str,
        source_url: str,
        content_type: str = "text/html"
    ) -> Dict[str, Any]:
        """
        Parses web response (JSON or HTML) into canonical scheme format.
        """
        slug = cls._extract_slug(source_url)

        # 1. Try parsing as JSON (API endpoint or __NEXT_DATA__ payload)
        if "application/json" in content_type or raw_text.strip().startswith("{"):
            try:
                data = json.loads(raw_text)
                return cls._parse_json_payload(data, slug, source_url)
            except json.JSONDecodeError:
                pass

        # 2. Check for embedded Next.js JSON payload inside HTML
        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">({.*?})</script>', raw_text, re.DOTALL)
        if next_data_match:
            try:
                data = json.loads(next_data_match.group(1))
                page_props = data.get("props", {}).get("pageProps", {}).get("schemeData", {})
                if page_props:
                    return cls._parse_json_payload(page_props, slug, source_url)
            except Exception:
                pass

        # 3. Fallback to structured HTML text parsing
        return cls._parse_html_payload(raw_text, slug, source_url)

    @staticmethod
    def _extract_slug(url: str) -> str:
        """Extracts scheme slug from URL path."""
        clean = url.rstrip("/")
        parts = clean.split("/")
        return parts[-1].lower() if parts else "unknown-scheme"

    @classmethod
    def _parse_json_payload(cls, data: Dict[str, Any], slug: str, source_url: str) -> Dict[str, Any]:
        """Maps structured myScheme JSON to canonical schema."""
        scheme_name = (
            data.get("scheme_name")
            or data.get("schemeName")
            or data.get("title")
            or slug.replace("-", " ").title()
        )
        level = "State" if str(data.get("level", "")).lower() == "state" or data.get("state") else "Central"
        state = data.get("state") if level == "State" else None
        first_party_url = data.get("official_url") or data.get("application_url") or data.get("references")

        scheme_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source_url))

        return {
            "id": scheme_id,
            "slug": slug,
            "scheme_name": scheme_name,
            "short_title": data.get("short_title") or data.get("shortTitle"),
            "level": level,
            "state": state,
            "ministry": data.get("ministry"),
            "department": data.get("department"),
            "beneficiary_type": data.get("beneficiary_type"),
            "target_beneficiaries": data.get("target_beneficiaries", []),
            "benefit_type": data.get("benefit_type"),
            "categories": data.get("categories", []),
            "sub_categories": data.get("sub_categories", []),
            "tags": data.get("tags", []),
            "brief_description": data.get("brief_description") or data.get("description"),
            "detailed_description": data.get("detailed_description"),
            "benefits": data.get("benefits"),
            "eligibility": data.get("eligibility"),
            "exclusions": data.get("exclusions"),
            "application_mode": data.get("application_mode", ["Online"]),
            "application_process": data.get("application_process"),
            "documents_required": data.get("documents_required"),
            "dbt_scheme": data.get("dbt_scheme", False),
            "faq_count": len(data.get("faqs", [])),
            "source_url": source_url,
            "first_party_url": first_party_url,
            "faqs": data.get("faqs", []),
            "references": [first_party_url] if first_party_url else [],
            "provenance": {
                "source_type": "WEB_PAGE",
                "provider": "myScheme",
                "authority_tier": "PRIMARY_OFFICIAL",
            }
        }

    @classmethod
    def _parse_html_payload(cls, html: str, slug: str, source_url: str) -> Dict[str, Any]:
        """Extracts structured sections from raw HTML."""
        parser = _TextExtractor()
        parser.feed(html)
        full_text = parser.get_text()

        # Extract title from <title> or <h1>
        title_match = re.search(r"<title>(.*?)(?:\||-|—).*?</title>", html, re.IGNORECASE | re.DOTALL)
        if not title_match:
            title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)

        scheme_name = (
            re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
            if title_match
            else slug.replace("-", " ").title()
        )

        # Extract sections via regex headers
        eligibility = cls._extract_section(full_text, ["Eligibility Criteria", "Eligibility", "पात्रता"])
        benefits = cls._extract_section(full_text, ["Benefits", "Benefit Details", "लाभ"])
        exclusions = cls._extract_section(full_text, ["Exclusions", "Who is not eligible"])
        documents = cls._extract_section(full_text, ["Documents Required", "Required Documents", "दस्तावेज़"])
        process = cls._extract_section(full_text, ["Application Process", "How to apply", "आवेदन प्रक्रिया"])

        # Extract first party official portal link
        official_link = None
        link_matches = re.findall(r'href=[\'"](https?://[^\'"]+)[\'"]', html, re.IGNORECASE)
        for link in link_matches:
            if (".gov.in" in link or ".nic.in" in link) and "myscheme.gov.in" not in link:
                official_link = link
                break

        scheme_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source_url))

        return {
            "id": scheme_id,
            "slug": slug,
            "scheme_name": scheme_name,
            "short_title": None,
            "level": "Central",
            "state": None,
            "ministry": None,
            "department": None,
            "beneficiary_type": None,
            "target_beneficiaries": [],
            "benefit_type": None,
            "categories": [],
            "sub_categories": [],
            "tags": [],
            "brief_description": full_text[:400].strip() if full_text else None,
            "detailed_description": full_text[:2000].strip() if full_text else None,
            "benefits": benefits,
            "eligibility": eligibility,
            "exclusions": exclusions,
            "application_mode": ["Online"],
            "application_process": process,
            "documents_required": documents,
            "dbt_scheme": None,
            "faq_count": 0,
            "source_url": source_url,
            "first_party_url": official_link,
            "faqs": [],
            "references": [official_link] if official_link else [],
            "provenance": {
                "source_type": "WEB_PAGE",
                "provider": "myScheme",
                "authority_tier": "PRIMARY_OFFICIAL",
            }
        }

    @staticmethod
    def _extract_section(text: str, headers: List[str]) -> Optional[str]:
        """Extracts section text under one of the target header names."""
        for header in headers:
            pattern = re.compile(
                rf"(?:^|\n){re.escape(header)}[\s:]*\n(.*?)(?=\n[A-Z][A-Za-z\s]{{3,30}}[\s:]*\n|$)",
                re.IGNORECASE | re.DOTALL
            )
            match = pattern.search(text)
            if match:
                content = match.group(1).strip()
                if content and len(content) > 10:
                    return content
        return None
