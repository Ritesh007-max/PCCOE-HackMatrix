"""
FIN Data Reconciliation Engine.
Audits live acquired government scheme content against pre-existing local baseline corpora.
Generates machine-readable diff reports tracking additions, removals, modifications, and statutory changes.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import Scheme


class CorpusReconciler:
    """
    Reconciles live acquired scheme corpora against existing baseline datasets.
    Does not delete or blindly overwrite existing data.
    """

    @classmethod
    def reconcile(
        cls,
        live_schemes: Dict[str, Scheme],
        baseline_schemes: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Computes fine-grained differences between live acquisition and baseline records.
        """
        live_slugs = set(live_schemes.keys())
        baseline_slugs = set(baseline_schemes.keys())

        added_slugs = sorted(list(live_slugs - baseline_slugs))
        removed_slugs = sorted(list(baseline_slugs - live_slugs))
        common_slugs = sorted(list(live_slugs & baseline_slugs))

        changed_schemes: List[Dict[str, Any]] = []
        renamed_schemes: List[Dict[str, Any]] = []
        changed_eligibility: List[Dict[str, Any]] = []
        changed_benefits: List[Dict[str, Any]] = []
        changed_documents: List[Dict[str, Any]] = []
        newly_discovered_sources: List[Dict[str, Any]] = []

        for slug in common_slugs:
            live = live_schemes[slug]
            base = baseline_schemes[slug]

            # 1. Name changes
            base_name = str(base.get("scheme_name") or base.get("Scheme_Name") or "").strip()
            if base_name and live.scheme_name.lower() != base_name.lower():
                renamed_schemes.append({
                    "slug": slug,
                    "baseline_name": base_name,
                    "live_name": live.scheme_name,
                })

            # 2. Eligibility changes
            base_elig = str(base.get("eligibility") or base.get("Eligibility") or "").strip()
            if base_elig and live.raw_eligibility_text.strip() != base_elig:
                changed_eligibility.append({
                    "slug": slug,
                    "baseline_eligibility_preview": base_elig[:120],
                    "live_eligibility_preview": live.raw_eligibility_text[:120],
                })

            # 3. Benefits changes
            base_ben = str(base.get("benefits") or base.get("Benefits") or "").strip()
            if base_ben and live.raw_benefits_text.strip() != base_ben:
                changed_benefits.append({
                    "slug": slug,
                    "baseline_benefits_preview": base_ben[:120],
                    "live_benefits_preview": live.raw_benefits_text[:120],
                })

            # 4. Document requirement changes
            base_docs = str(base.get("documents_required") or base.get("Documents_Required") or "").strip()
            if base_docs and live.raw_documents_text.strip() != base_docs:
                changed_documents.append({
                    "slug": slug,
                    "baseline_docs_preview": base_docs[:120],
                    "live_docs_preview": live.raw_documents_text[:120],
                })

            # 5. Newly discovered official sources
            base_source = str(base.get("source_url") or "").strip()
            if live.official_scheme_url and live.official_scheme_url != base_source:
                newly_discovered_sources.append({
                    "slug": slug,
                    "baseline_url": base_source,
                    "discovered_official_url": live.official_scheme_url,
                    "guideline_url": live.official_guideline_url,
                })

            # Check if any content changed
            if (
                live.scheme_name.lower() != base_name.lower()
                or live.raw_eligibility_text.strip() != base_elig
                or live.raw_benefits_text.strip() != base_ben
                or live.raw_documents_text.strip() != base_docs
            ):
                changed_schemes.append({
                    "slug": slug,
                    "scheme_name": live.scheme_name,
                    "content_hash": live.content_hash,
                })

        report = {
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
            "live_schemes_count": len(live_schemes),
            "baseline_schemes_count": len(baseline_schemes),
            "added_count": len(added_slugs),
            "removed_count": len(removed_slugs),
            "changed_count": len(changed_schemes),
            "renamed_count": len(renamed_schemes),
            "changed_eligibility_count": len(changed_eligibility),
            "changed_benefits_count": len(changed_benefits),
            "changed_documents_count": len(changed_documents),
            "newly_discovered_sources_count": len(newly_discovered_sources),
            "added_schemes_sample": added_slugs[:25],
            "removed_schemes_sample": removed_slugs[:25],
            "renamed_schemes": renamed_schemes[:25],
            "newly_discovered_sources": newly_discovered_sources[:25],
        }
        return report
