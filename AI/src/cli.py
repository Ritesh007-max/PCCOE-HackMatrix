"""
PolicySetu AI Subsystem Command-Line Interface (CLI).
Provides developer and administrative access to the document intelligence
and application evaluation pipelines.

Usage Examples:
    # Run from AI/ directory:
    python -m src.cli --document tests/fixtures/sample_income_cert.pdf --query "scholarship for SC students in Gujarat"

    # Run from project root directory:
    python -m AI.src.cli --document AI/tests/fixtures/sample_income_cert.pdf --provider auto --json
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import List, Optional

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.documents.pipeline import DocumentPipeline
from src.documents.models import DocumentContent
from src.llm.config import LLMConfig
from src.llm.client import LLMClient
from src.pipelines.application_pipeline import ApplicationPipeline, ApplicationResult


def resolve_file_path(path_str: str) -> Path:
    """
    Multi-root path resolver.
    Attempts to resolve paths relative to current working directory,
    relative to AI/, and relative to project root.
    """
    p = Path(path_str)
    if p.is_file():
        return p.resolve()

    # Try relative to AI dir
    candidate_ai = _AI_DIR / path_str
    if candidate_ai.is_file():
        return candidate_ai.resolve()

    # Try stripping leading "AI/" if in AI dir
    if path_str.startswith("AI/") or path_str.startswith("AI\\"):
        sub = path_str[3:]
        candidate_sub = _AI_DIR / sub
        if candidate_sub.is_file():
            return candidate_sub.resolve()

    # Try relative to project root
    project_root = _AI_DIR.parent
    candidate_root = project_root / path_str
    if candidate_root.is_file():
        return candidate_root.resolve()

    # Return as-is (will be caught by validator)
    return p.resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="policysetu-ai",
        description="PolicySetu Document Intelligence & Eligibility Pipeline CLI",
    )
    parser.add_argument(
        "--document", "-d",
        action="append",
        dest="documents",
        help="Path to citizen document (PDF, DOCX, PNG, JPG). Can be specified multiple times.",
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Citizen natural-language query or search request.",
    )
    parser.add_argument(
        "--scheme", "-s",
        type=str,
        default=None,
        help="Target scheme identifier (e.g., 'sc_post_matric_scholarship', 'pm_kisan').",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["auto", "gemini", "openrouter", "mock"],
        default="auto",
        help="LLM provider routing mode (default: auto).",
    )
    parser.add_argument(
        "--ocr-only",
        action="store_true",
        help="Only run document parsing, scan detection, and OCR extraction.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Run deterministic pipeline using mock provider (offline).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON response.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging output.",
    )
    return parser


def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    # Configure logging
    log_level = logging.DEBUG if parsed_args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    doc_paths = []
    if parsed_args.documents:
        for d in parsed_args.documents:
            resolved = resolve_file_path(d)
            if not resolved.exists():
                sys.stderr.write(f"Error: Document not found: {d} (resolved: {resolved})\n")
                return 1
            doc_paths.append(resolved)

    # 1. OCR-Only execution
    if parsed_args.ocr_only:
        pipeline = DocumentPipeline()
        results = []
        for path in doc_paths:
            content: DocumentContent = pipeline.process(path)
            results.append(content.to_dict())

        if parsed_args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"=== Document: {r['file_name']} ===")
                print(f"Type: {r['document_type']}")
                print(f"Extraction Method: {r['extraction_method']}")
                print(f"Scanned: {r['is_scanned']}")
                print(f"Pages: {r['page_count']}")
                print(f"Text Preview: {r['full_text'][:200]}...")
                print()
        return 0

    # 2. End-to-End Application Pipeline execution
    provider_mode = "mock" if parsed_args.no_llm else parsed_args.provider
    config = LLMConfig.from_env()
    config.provider = provider_mode

    app_pipeline = ApplicationPipeline(llm_config=config)
    result = app_pipeline.process_application(
        documents=doc_paths,
        user_query=parsed_args.query,
        target_scheme=parsed_args.scheme,
    )

    if parsed_args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("=" * 60)
        print("POLICYSETU APPLICATION EVALUATION RESULT")
        print("=" * 60)
        print(f"Application ID: {result.application_id}")
        print(f"Steps Completed: {result.steps_completed} / 21")
        print(f"Status: {result.processing_status}")
        print(f"Documents Processed: {len(result.documents_processed)}")
        for d in result.documents_processed:
            print(f"  - {d['file_name']}: {d['document_type']} ({d['extraction_method']})")

        print("\nApplicant Profile Extracted:")
        for k, v in result.applicant_profile.items():
            print(f"  - {k}: {v}")

        if result.conflicts_detected:
            print(f"\n[!] Conflicts Detected: {', '.join(result.conflicts_detected)}")

        if result.query_intent:
            print(f"\nQuery Intent: {result.query_intent.get('intent')} (state: {result.query_intent.get('state')})")

        print(f"\nEligibility Decision ({result.eligibility_decision.get('scheme_name')}):")
        print(f"  Outcome: {result.eligibility_decision.get('status')}")
        print(f"  Is Eligible: {result.eligibility_decision.get('is_eligible')}")

        if result.benefit_calculation:
            bc = result.benefit_calculation
            print(f"\nBenefit Calculation:")
            print(f"  Amount: Rs {bc.get('amount')}")
            print(f"  Type: {bc.get('benefit_type')}")
            print(f"  Status: {bc.get('status')}")
            print(f"  Reasoning: {bc.get('reasoning')}")

        if result.missing_information.get("has_missing_info"):
            print(f"\nMissing Information:")
            for mf in result.missing_information.get("missing_fields", []):
                print(f"  - Field required: {mf}")

        summary = (
            result.explanation.get("answer")
            or result.explanation.get("plain_language_summary")
            or "Decision evaluated successfully."
        )
        print(f"\nExplanation Summary:")
        print(f"  {summary}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
