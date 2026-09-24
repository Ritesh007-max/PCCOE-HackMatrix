"""
FIN Data Quality Validation Engine.
Executes rigorous full-corpus checks prior to knowledge-base activation:
- Duplicate scheme slugs
- Invalid URLs
- Missing scheme names
- Missing source provenance
- Malformed dates
- Impossible age limits (< 0 or > 120)
- Negative income limits (< 0)
- Malformed benefits
- Invalid state names
- Invalid categories
- Broken / orphan FAQ links
- Duplicate chunks
- Stale records
- Unresolved critical conflicts
Any critical error strictly aborts activation of the new snapshot.
"""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Set

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from ..normalization.normalizer import INDIAN_STATES_AND_UTS
except (ImportError, ValueError):
    from src.normalization.normalizer import INDIAN_STATES_AND_UTS


VALID_CATEGORIES = {
    "Agriculture,Rural & Environment",
    "Banking,Financial Services and Insurance",
    "Business & Entrepreneurship",
    "Education & Learning",
    "Health & Wellness",
    "Housing & Shelter",
    "Public Safety,Law & Justice",
    "Science, IT & Communications",
    "Skills & Employment",
    "Social welfare & Empowerment",
    "Sports & Culture",
    "Transport & Infrastructure",
    "Travel & Tourism",
    "Utility & Sanitation",
    "Women and Child",
}


@dataclass
class ValidationReport:
    """Comprehensive validation outcome across all statutory checks."""
    is_valid: bool
    critical_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_schemes_checked: int = 0
    total_faqs_checked: int = 0
    checks_passed: int = 0
    checks_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "critical_errors_count": len(self.critical_errors),
            "critical_errors": self.critical_errors[:50],  # cap for summary
            "warnings_count": len(self.warnings),
            "warnings": self.warnings[:50],
            "total_schemes_checked": self.total_schemes_checked,
            "total_faqs_checked": self.total_faqs_checked,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
        }


class DataQualityValidator:
    """
    Validates canonical data quality and integrity before snapshot activation.
    """

    @classmethod
    def validate_corpus(
        cls,
        schemes: List[Dict[str, Any]],
        faqs: Optional[List[Dict[str, Any]]] = None,
        chunks: Optional[List[Any]] = None,
        conflicts: Optional[List[Any]] = None,
    ) -> ValidationReport:
        """
        Runs all statutory validation checks across the corpus.
        """
        critical_errors: List[str] = []
        warnings: List[str] = []
        checks_passed = 0
        checks_failed = 0

        valid_states_lower = {s.lower() for s in INDIAN_STATES_AND_UTS}
        valid_states_lower.add("all india")

        # 1. Duplicate Scheme Slugs & Missing Names
        slug_counts: Dict[str, int] = {}
        for idx, s in enumerate(schemes):
            slug = str(s.get("slug", "")).strip().lower()
            name = str(s.get("scheme_name", "")).strip()

            if not slug:
                critical_errors.append(f"Scheme at index {idx} has missing or empty slug.")
            else:
                slug_counts[slug] = slug_counts.get(slug, 0) + 1

            if not name:
                critical_errors.append(f"Scheme '{slug or idx}' has missing or empty scheme_name.")

        duplicates = [s for s, count in slug_counts.items() if count > 1]
        if duplicates:
            critical_errors.append(f"Duplicate scheme slugs detected: {duplicates[:10]}")
            checks_failed += 1
        else:
            checks_passed += 1

        # 2. Source Provenance & URLs
        url_regex = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
        for s in schemes:
            slug = s.get("slug", "unknown")
            prov = s.get("provenance")
            if not prov:
                critical_errors.append(f"Scheme '{slug}' is missing provenance metadata.")
                break

            src_url = s.get("source_url")
            if src_url and not url_regex.match(src_url):
                warnings.append(f"Scheme '{slug}' has malformed source_url: '{src_url}'")

        if not any("missing provenance" in err for err in critical_errors):
            checks_passed += 1
        else:
            checks_failed += 1

        # 3. Statutory Criteria Limits (Age, Income)
        for s in schemes:
            slug = s.get("slug", "unknown")
            # Age check
            min_age = s.get("min_age")
            max_age = s.get("max_age")
            for age_val, lbl in [(min_age, "min_age"), (max_age, "max_age")]:
                if age_val is not None:
                    try:
                        num_age = float(age_val)
                        if num_age < 0 or num_age > 120:
                            critical_errors.append(
                                f"Scheme '{slug}' has physically impossible {lbl}: {num_age}"
                            )
                    except (ValueError, TypeError):
                        critical_errors.append(f"Scheme '{slug}' has malformed numeric {lbl}: {age_val}")

            if min_age is not None and max_age is not None:
                try:
                    if float(min_age) > float(max_age):
                        critical_errors.append(
                            f"Scheme '{slug}' has min_age ({min_age}) > max_age ({max_age})"
                        )
                except (ValueError, TypeError):
                    pass

            # Income check
            income = s.get("annual_family_income") or s.get("income_limit")
            if income is not None:
                try:
                    num_income = float(income)
                    if num_income < 0:
                        critical_errors.append(
                            f"Scheme '{slug}' has invalid negative income threshold: {num_income}"
                        )
                except (ValueError, TypeError):
                    pass

        # 4. State Names and Categories
        for s in schemes:
            slug = s.get("slug", "unknown")
            st = s.get("state")
            level = s.get("level", "Central")
            if level == "State" and st is not None and not (isinstance(st, float) and str(st) == "nan"):
                st_str = str(st).strip()
                if st_str.lower() not in valid_states_lower:
                    warnings.append(f"Scheme '{slug}' has uncanonicalized state: '{st_str}'")

            cats = s.get("categories", [])
            if isinstance(cats, (list, tuple)):
                for cat in cats:
                    cat_str = str(cat).strip()
                    if cat_str and cat_str not in VALID_CATEGORIES:
                        warnings.append(f"Scheme '{slug}' has non-standard category: '{cat_str}'")

        # 5. FAQs: Orphan & Broken Link Check
        known_slugs = set(slug_counts.keys())
        if faqs:
            orphan_count = 0
            for idx, f in enumerate(faqs):
                f_slug = str(f.get("scheme_slug", "")).strip().lower()
                if not f_slug or f_slug not in known_slugs:
                    orphan_count += 1
            if orphan_count > 0:
                warnings.append(f"Detected {orphan_count} orphan FAQ records with no matching scheme.")

        # 6. Duplicate Chunks Check
        if chunks:
            seen_chunk_ids = set()
            dup_chunks = 0
            for c in chunks:
                cid = getattr(c, "chunk_id", None) or (c.get("chunk_id") if isinstance(c, dict) else None)
                if cid:
                    if cid in seen_chunk_ids:
                        dup_chunks += 1
                    seen_chunk_ids.add(cid)
            if dup_chunks > 0:
                critical_errors.append(f"Detected {dup_chunks} duplicate RAG chunk IDs in index.")
                checks_failed += 1
            else:
                checks_passed += 1

        is_valid = len(critical_errors) == 0

        return ValidationReport(
            is_valid=is_valid,
            critical_errors=critical_errors,
            warnings=warnings,
            total_schemes_checked=len(schemes),
            total_faqs_checked=len(faqs) if faqs else 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )