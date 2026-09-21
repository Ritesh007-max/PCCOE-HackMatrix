"""
PolicySetu Full Corpus Rebuild and Diagnostic Reporter.
Command: python -m src.data_pipeline.rebuild
Executes full baseline rebuild across all approved data sources and reports exact measured metrics.
"""

from collections import Counter
from pathlib import Path
import re
import sys
import pandas as pd

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.fetchers.local import BaselineSourceAdapter
from src.data_pipeline.conflict import ConflictDetector


def run_full_rebuild(verbose: bool = True) -> dict:
    """
    Scans all approved datasets and computes exact corpus statistics without fabrication.
    """
    adapter = BaselineSourceAdapter()

    if verbose:
        print("=" * 75)
        print("  PolicySetu Phase 7 Full Corpus Rebuild & Audit")
        print("  [Scanning all approved primary, supplementary, and archive datasets]")
        print("=" * 75)

    # 1. Primary Schemes
    primary_schemes = adapter.load_baseline_schemes()
    total_schemes = len(primary_schemes)

    # 2. Primary FAQs
    faqs = adapter.load_baseline_faqs()
    total_faqs = len(faqs)

    # 3. Supplementary Schemes
    supp_schemes = adapter.load_supplementary_schemes()
    total_supp_records = len(supp_schemes)
    raw_schemes_path = _AI_DIR / "data" / "raw" / "schemes.csv"
    if raw_schemes_path.exists():
        df_raw_p = pd.read_csv(raw_schemes_path, usecols=["slug"])
        raw_p_slugs = set(df_raw_p["slug"].dropna().str.strip().str.lower())
        supp_slugs = {str(s.get("slug", "")).strip().lower() for s in supp_schemes if s.get("slug")}
        distinct_supp_schemes = len(supp_slugs - raw_p_slugs)
    else:
        distinct_supp_schemes = sum(1 for s in primary_schemes if s.get("is_supplementary"))

    # 4. Local Bilingual QA Dataset (BharatSchemes local)
    bilingual_records = adapter.load_bilingual_qa()
    total_bilingual = len(bilingual_records)

    # 5. Archive Documents
    archive_docs = adapter.load_archive_docs(limit=2000)
    total_archive_docs = len(archive_docs)

    # 6. Central vs State breakdown
    levels = Counter([str(s.get("level", "Central")).strip().title() for s in primary_schemes])
    central_count = levels.get("Central", 0)
    state_count = levels.get("State", 0)

    # 7. Language detection across schemes
    languages = Counter()
    for s in primary_schemes:
        text = f"{s.get('scheme_name', '')} {s.get('brief_description', '')}"
        if re.search(r"[\u0900-\u097F]", text):
            languages["Hindi / Devanagari"] += 1
        else:
            languages["English"] += 1

    # Check bilingual records
    for b in bilingual_records:
        q_hi = str(b.get("question", ""))
        q_en = str(b.get("question_english", ""))
        if q_hi and re.search(r"[\u0900-\u097F]", q_hi):
            languages["Hindi (Bilingual)"] += 1
        if q_en:
            languages["English (Bilingual)"] += 1

    # 8. Duplicate Slugs Check
    slug_counts = Counter([str(s.get("slug", "")).strip().lower() for s in primary_schemes if s.get("slug")])
    duplicates_count = sum(1 for slug, cnt in slug_counts.items() if cnt > 1)

    # 9. Conflicts between Primary and Supplementary
    conflicts = ConflictDetector.batch_detect_conflicts(
        primary_records=primary_schemes,
        supplementary_records=supp_schemes,
        primary_source_id="myscheme_csv_baseline",
        supplementary_source_id="updated_data_supplementary",
    )
    conflicts_count = len(conflicts)

    # 10. Missing URLs & Missing Metadata
    missing_urls = sum(1 for s in primary_schemes if not s.get("source_url"))
    missing_ministry = sum(1 for s in primary_schemes if not s.get("ministry"))
    missing_eligibility = sum(1 for s in primary_schemes if not s.get("eligibility"))

    # 11. Total RAG Chunks
    rag_parquet = _AI_DIR / "data" / "processed" / "rag" / "rag_chunks.parquet"
    if rag_parquet.exists():
        df_chunks = pd.read_parquet(rag_parquet)
        total_chunks = len(df_chunks)
    else:
        total_chunks = 0

    stats = {
        "total_primary_schemes": total_schemes,
        "total_faqs": total_faqs,
        "supplementary_records": total_supp_records,
        "distinct_supplementary_schemes": distinct_supp_schemes,
        "total_supplementary_schemes": distinct_supp_schemes,
        "total_bilingual_records": total_bilingual,
        "total_archive_documents": total_archive_docs,
        "total_rag_chunks": total_chunks,
        "central_schemes": central_count,
        "state_schemes": state_count,
        "languages_distribution": dict(languages),
        "duplicates_count": duplicates_count,
        "conflicts_count": conflicts_count,
        "missing_urls": missing_urls,
        "missing_ministry": missing_ministry,
        "missing_eligibility": missing_eligibility,
        "source_distribution": {
            "schemes.csv (Primary)": total_schemes,
            "schemes_faqs.csv (Primary)": total_faqs,
            "updated_data.csv (Supplementary Records)": total_supp_records,
            "updated_data.csv (Distinct Supp Schemes)": distinct_supp_schemes,
            "indian government schemes bilingual (Supp)": total_bilingual,
            "archive (1).zip (Archive)": total_archive_docs,
        }
    }

    if verbose:
        print(f"Total Primary Schemes          : {total_schemes}")
        print(f"Total Authoritative FAQs       : {total_faqs}")
        print(f"Supplementary Records (Rows)   : {total_supp_records}")
        print(f"Distinct Supplementary Schemes : {distinct_supp_schemes}")
        print(f"Total Bilingual QA Records     : {total_bilingual}")
        print(f"Total Archive Documents (Zip)  : {total_archive_docs}")
        print(f"Total Processed RAG Chunks     : {total_chunks}")
        print(f"Central vs State Schemes       : Central: {central_count} | State: {state_count}")
        print(f"Languages Detected             : {dict(languages)}")
        print(f"Duplicate Slugs Detected       : {duplicates_count}")
        print(f"Audited Conflicts (Overlaps)   : {conflicts_count}")
        print(f"Missing Source URLs            : {missing_urls}")
        print(f"Missing Ministry Metadata      : {missing_ministry}")
        print(f"Missing Eligibility Clauses    : {missing_eligibility}")
        print("\nSource Distribution:")
        for src, count in stats["source_distribution"].items():
            print(f"  - {src:<42}: {count}")
        print("=" * 75)

    return stats


if __name__ == "__main__":
    run_full_rebuild(verbose=True)
