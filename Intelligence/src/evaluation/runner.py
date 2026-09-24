"""
FIN Phase 13 Evaluation & Red Team Runner.
CLI and programmatic interface to run evaluation suites and export JSON/Markdown benchmark reports.
Usage:
    python -m src.evaluation.runner --suite all
    python -m src.evaluation.runner --suite retrieval
    python -m src.evaluation.runner --suite eligibility
    python -m src.evaluation.runner --suite red-team
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationRun
from src.evaluation.retrieval_eval import RetrievalEvaluator
from src.evaluation.eligibility_eval import EligibilityEvaluator
from src.evaluation.extraction_eval import DocumentExtractionEvaluator
from src.evaluation.grounding_eval import GroundingEvaluator
from src.evaluation.multilingual_eval import MultilingualEvaluator
from src.evaluation.red_team import RedTeamEvaluator
from src.evaluation.security_eval import APISecurityEvaluator
from src.evaluation.reports import ReportManager


def load_dataset(filename: str) -> List[EvaluationCase]:
    """Loads a JSONL dataset from Intelligence/data/evaluation/."""
    file_path = _INTELLIGENCE_DIR / "data" / "evaluation" / filename
    cases: List[EvaluationCase] = []
    if not file_path.exists():
        return cases
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(EvaluationCase.from_dict(json.loads(line)))
    return cases


class EvaluationSuiteRunner:
    """Orchestrates test suites across the 10 evaluation pyramid layers."""

    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()
        self.eligibility_eval = EligibilityEvaluator()
        self.extraction_eval = DocumentExtractionEvaluator()
        self.grounding_eval = GroundingEvaluator()
        self.multilingual_eval = MultilingualEvaluator()
        self.red_team_eval = RedTeamEvaluator()
        self.api_eval = APISecurityEvaluator()
        self.report_mgr = ReportManager()

    def run_suite(self, suite_name: str = "all") -> Dict[str, Any]:
        """Runs the requested evaluation suite and produces aggregated metrics."""
        start_time = datetime.now(timezone.utc)
        run_id = f"eval_{start_time.strftime('%Y%m%d_%H%M%S')}"

        suite_results: Dict[str, Any] = {}
        total_cases = 0
        total_passed = 0
        total_failed = 0
        combined_metrics: Dict[str, Any] = {}

        # 1. Retrieval Suite
        if suite_name in ("all", "retrieval"):
            cases = load_dataset("golden_retrieval.jsonl")
            res = self.retrieval_eval.evaluate_suite(cases)
            suite_results["retrieval"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]
            combined_metrics["retrieval"] = res["metrics"]

        # 2. Eligibility Suite
        if suite_name in ("all", "eligibility"):
            cases = load_dataset("golden_eligibility.jsonl")
            res = self.eligibility_eval.evaluate_suite(cases)
            suite_results["eligibility"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]
            combined_metrics["eligibility"] = res["metrics"]

        # 3. Extraction Suite
        if suite_name in ("all", "extraction"):
            cases = load_dataset("golden_extraction.jsonl")
            res = self.extraction_eval.evaluate_suite(cases)
            suite_results["extraction"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]
            combined_metrics["extraction"] = res["metrics"]

        # 4. Grounding Suite
        if suite_name in ("all", "grounding"):
            cases = load_dataset("golden_grounding.jsonl")
            res = self.grounding_eval.evaluate_suite(cases)
            suite_results["grounding"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]
            combined_metrics["grounding"] = res["metrics"]

        # 5. Multilingual Suite
        if suite_name in ("all", "multilingual"):
            cases = load_dataset("golden_multilingual.jsonl")
            res = self.multilingual_eval.evaluate_suite(cases)
            suite_results["multilingual"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]

        # 6. Red Team Suite (Prompt Injections + Policy Poisoning + HF Red Team)
        if suite_name in ("all", "red-team", "red_team"):
            cases = (
                load_dataset("red_team_injections.jsonl")
                + load_dataset("red_team_policy_poisoning.jsonl")
                + load_dataset("red_team_hf.jsonl")
                + load_dataset("red_team_documents.jsonl")
            )
            res = self.red_team_eval.evaluate_suite(cases)
            suite_results["red_team"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]
            combined_metrics["security"] = res["metrics"]

        # 7. Security & API Suite
        if suite_name in ("all", "security"):
            cases = load_dataset("red_team_api.jsonl")
            res = self.api_eval.evaluate_suite(cases)
            suite_results["api_security"] = res
            total_cases += res["total_cases"]
            total_passed += res["passed"]
            total_failed += res["failed"]

        end_time = datetime.now(timezone.utc)

        run_record = {
            "run_id": run_id,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "suite_name": suite_name,
            "total_cases": total_cases,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": 0,
            "metrics": combined_metrics,
            "suites": suite_results,
            "policy_snapshot_version": "snapshot_20260921_193823",
            "rule_version": "1.0.0",
            "rag_version": "1.0.0",
            "model_provider_metadata": {"primary": "gemini-1.5-flash", "fallback": "openrouter"},
        }

        # Persist reports
        saved = self.report_mgr.persist_run(run_record, suite_name=suite_name)
        run_record["report_paths"] = {k: str(v) for k, v in saved.items()}
        return run_record


def main():
    parser = argparse.ArgumentParser(description="FIN Phase 13 Evaluation & Red Team Runner")
    parser.add_argument(
        "--suite",
        choices=["all", "retrieval", "eligibility", "extraction", "grounding", "multilingual", "security", "red-team"],
        default="all",
        help="Evaluation suite to execute (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Report output format to display (default: both)",
    )

    args = parser.parse_args()
    runner = EvaluationSuiteRunner()
    print(f"[*] Starting FIN Phase 13 Evaluation Suite: '{args.suite}'...")
    res = runner.run_suite(args.suite)

    print("\n============================================================")
    print(f"EXECUTION SUMMARY: {res['suite_name'].upper()}")
    print("============================================================")
    print(f"Total Cases: {res['total_cases']}")
    print(f"Passed:      {res['passed']}")
    print(f"Failed:      {res['failed']}")
    print(f"Pass Rate:   {round((res['passed'] / res['total_cases']) * 100, 2) if res['total_cases'] > 0 else 100.0}%")
    print(f"Reports Saved:")
    for fmt, p in res.get("report_paths", {}).items():
        print(f"  - {fmt.upper()}: {p}")
    print("============================================================\n")


if __name__ == "__main__":
    main()
