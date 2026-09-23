"""
PolicySetu Data Quality Validation CLI.
Command: python -m src.data_pipeline.validate
Validates active snapshot or baseline dataset against all statutory quality constraints.
"""

from pathlib import Path
import sys

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.fetchers.local import BaselineSourceAdapter
from src.data_pipeline.validation import DataQualityValidator
from src.data_pipeline.snapshot import SnapshotManager
from src.data_pipeline.conflict import ConflictDetector


def run_validation(verbose: bool = True) -> bool:
    """Runs data quality validation and prints diagnostic report."""
    adapter = BaselineSourceAdapter()
    snapshot_mgr = SnapshotManager()

    if verbose:
        print("=" * 75)
        print("  PolicySetu Data Quality Validation Suite")
        print("=" * 75)

    schemes = adapter.load_baseline_schemes()
    faqs = adapter.load_baseline_faqs()
    supp = adapter.load_supplementary_schemes()

    conflicts = ConflictDetector.batch_detect_conflicts(
        primary_records=schemes,
        supplementary_records=supp,
        primary_source_id="myscheme_csv_baseline",
        supplementary_source_id="updated_data_supplementary",
    )

    report = DataQualityValidator.validate_corpus(
        schemes=schemes,
        faqs=faqs,
        conflicts=conflicts,
    )

    if verbose:
        print(f"Total Schemes Validated : {report.total_schemes_checked}")
        print(f"Total FAQs Validated    : {report.total_faqs_checked}")
        print(f"Quality Checks Passed   : {report.checks_passed}")
        print(f"Quality Checks Failed   : {report.checks_failed}")
        print(f"Critical Errors         : {len(report.critical_errors)}")
        print(f"Warnings (Non-critical) : {len(report.warnings)}")
        print(f"Overall Corpus Valid    : {report.is_valid}")
        print("=" * 75)

        if report.critical_errors:
            print("\n[CRITICAL VALIDATION ERRORS]")
            for err in report.critical_errors[:10]:
                print(f"  - {err}")

        if report.warnings:
            print("\n[AUDIT WARNINGS]")
            for w in report.warnings[:5]:
                print(f"  - {w}")

    return report.is_valid


if __name__ == "__main__":
    is_valid = run_validation(verbose=True)
    sys.exit(0 if is_valid else 1)
