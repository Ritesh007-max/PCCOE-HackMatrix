"""
PolicySetu Dataset Diffing CLI.
Command: python -m src.data_pipeline.diff
Compares active snapshot with baseline dataset and displays field-level changes.
"""

from pathlib import Path
import sys

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(_reconfigure):
    try:
        _reconfigure(encoding="utf-8")
    except Exception:
        pass

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.fetchers.local import BaselineSourceAdapter
from src.data_pipeline.change_detection import ChangeDetector
from src.data_pipeline.snapshot import SnapshotManager


def run_diff(verbose: bool = True) -> None:
    """Computes and prints dataset differences."""
    adapter = BaselineSourceAdapter()
    snapshot_mgr = SnapshotManager()

    if verbose:
        print("=" * 75)
        print("  PolicySetu Dataset Change Detection and Diff Inspection")
        print("=" * 75)

    primary = adapter.load_baseline_schemes()
    supplementary = adapter.load_supplementary_schemes()

    summary = ChangeDetector.diff_datasets(
        old_records=primary,
        new_records=supplementary,
        key_field="slug"
    )

    if verbose:
        print(f"Primary Schemes (Baseline)     : {summary.total_old_records}")
        print(f"Comparison Schemes (Target)    : {summary.total_new_records}")
        print(f"Added Schemes                  : {summary.added_count}")
        print(f"Modified Schemes               : {summary.modified_count}")
        print(f"Removed Schemes                : {summary.removed_count}")
        print(f"Unchanged Schemes              : {summary.unchanged_count}")
        print(f"Eligibility Criteria Changes   : {summary.has_eligibility_changes}")
        print("=" * 75)

        # Show sample field diffs
        modified_diffs = [d for d in summary.diffs if d.change_type.value == "MODIFIED"]
        if modified_diffs:
            print("\nSample Field-Level Changes:")
            for d in modified_diffs[:5]:
                print(f"\n  Scheme: {d.scheme_slug}")
                for fd in d.field_diffs[:3]:
                    print(f"    - {fd.description}")


if __name__ == "__main__":
    run_diff(verbose=True)
