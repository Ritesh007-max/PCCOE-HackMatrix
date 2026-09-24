"""
FIN Phase 13 Evaluation Metrics Framework.
Calculates mathematical metrics across retrieval, extraction, grounding, eligibility, security, and operations.
Provides JSON and Markdown report generation.
"""

from typing import Any, Dict, List, Optional
import math


def _norm_slug(s: str) -> str:
    return str(s).replace("_", "-").strip().lower()


def compute_hit_at_k(retrieved: List[str], expected: str, k: int) -> float:
    """Computes Hit@K binary metric (1.0 if expected is in top-k, else 0.0)."""
    norm_exp = _norm_slug(expected)
    norm_ret = [_norm_slug(x) for x in retrieved[:k]]
    return 1.0 if norm_exp in norm_ret else 0.0


def compute_mrr(retrieved: List[str], expected: str) -> float:
    """Computes Mean Reciprocal Rank (1.0 / rank of first match, else 0.0)."""
    norm_exp = _norm_slug(expected)
    norm_ret = [_norm_slug(x) for x in retrieved]
    try:
        rank = norm_ret.index(norm_exp) + 1
        return 1.0 / float(rank)
    except ValueError:
        return 0.0


def compute_precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Computes Precision@K: fraction of retrieved top-k items that are relevant."""
    if k <= 0:
        return 0.0
    norm_rel = {_norm_slug(r) for r in relevant}
    top_k = [_norm_slug(x) for x in retrieved[:k]]
    matches = sum(1 for item in top_k if item in norm_rel)
    return matches / float(k)


def compute_recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Computes Recall@K: fraction of relevant items that are in top-k."""
    if not relevant:
        return 1.0
    norm_rel = {_norm_slug(r) for r in relevant}
    top_k = [_norm_slug(x) for x in retrieved[:k]]
    matches = sum(1 for item in top_k if item in norm_rel)
    return matches / float(len(relevant))


def compute_f1(precision: float, recall: float) -> float:
    """Computes harmonic mean F1 score."""
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def compute_percentile(values: List[float], p: float) -> float:
    """Computes p-th percentile from a list of numerical values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)


class MetricAggregator:
    """Aggregates metrics for a full evaluation or red-team run."""

    @staticmethod
    def aggregate_retrieval(query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates Hit@1, Hit@3, Hit@5, MRR, Precision, Recall across query results."""
        total = len(query_results)
        if total == 0:
            return {"total_queries": 0, "hit@1": 0.0, "hit@3": 0.0, "hit@5": 0.0, "mrr": 0.0}

        h1 = sum(r.get("hit@1", 0.0) for r in query_results) / total
        h3 = sum(r.get("hit@3", 0.0) for r in query_results) / total
        h5 = sum(r.get("hit@5", 0.0) for r in query_results) / total
        mrr = sum(r.get("mrr", 0.0) for r in query_results) / total
        prec = sum(r.get("precision@5", 0.0) for r in query_results) / total
        rec = sum(r.get("recall@5", 0.0) for r in query_results) / total

        return {
            "total_queries": total,
            "hit@1": round(h1, 4),
            "hit@3": round(h3, 4),
            "hit@5": round(h5, 4),
            "mrr": round(mrr, 4),
            "precision@5": round(prec, 4),
            "recall@5": round(rec, 4),
        }

    @staticmethod
    def aggregate_extraction(field_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Computes field precision, recall, and F1 across document extractions."""
        total_expected = sum(f.get("expected_count", 0) for f in field_evals)
        total_extracted = sum(f.get("extracted_count", 0) for f in field_evals)
        total_correct = sum(f.get("correct_count", 0) for f in field_evals)

        precision = total_correct / total_extracted if total_extracted > 0 else 1.0
        recall = total_correct / total_expected if total_expected > 0 else 1.0
        f1 = compute_f1(precision, recall)

        return {
            "total_fields_evaluated": total_expected,
            "field_precision": round(precision, 4),
            "field_recall": round(recall, 4),
            "field_f1": round(f1, 4),
        }

    @staticmethod
    def aggregate_grounding(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates supported claim rate, unsupported claim rate, and contradiction rate."""
        total = len(claims)
        if total == 0:
            return {"total_claims": 0, "supported_rate": 1.0, "unsupported_rate": 0.0, "contradiction_rate": 0.0}

        supported = sum(1 for c in claims if c.get("status") == "SUPPORTED")
        partially = sum(1 for c in claims if c.get("status") == "PARTIALLY_SUPPORTED")
        unsupported = sum(1 for c in claims if c.get("status") == "UNSUPPORTED")
        contradicted = sum(1 for c in claims if c.get("status") == "CONTRADICTED")

        return {
            "total_claims": total,
            "supported_count": supported,
            "partially_supported_count": partially,
            "unsupported_count": unsupported,
            "contradicted_count": contradicted,
            "supported_rate": round(supported / total, 4),
            "unsupported_rate": round(unsupported / total, 4),
            "contradiction_rate": round(contradicted / total, 4),
            "citation_coverage": round((supported + partially) / total, 4),
        }

    @staticmethod
    def aggregate_decisions(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates accuracy for PASS, FAIL, UNKNOWN, REVIEW decisions."""
        total = len(decisions)
        if total == 0:
            return {"total_decisions": 0, "overall_accuracy": 1.0}

        matches = sum(1 for d in decisions if d.get("expected") == d.get("actual"))
        by_status: Dict[str, Dict[str, int]] = {}

        for d in decisions:
            exp = d.get("expected", "UNKNOWN")
            act = d.get("actual", "UNKNOWN")
            if exp not in by_status:
                by_status[exp] = {"total": 0, "correct": 0}
            by_status[exp]["total"] += 1
            if exp == act:
                by_status[exp]["correct"] += 1

        accuracy_by_status = {
            s: round(v["correct"] / v["total"], 4) if v["total"] > 0 else 1.0
            for s, v in by_status.items()
        }

        return {
            "total_decisions": total,
            "overall_accuracy": round(matches / total, 4),
            "accuracy_by_status": accuracy_by_status,
        }

    @staticmethod
    def aggregate_security(security_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates security red-team outcomes."""
        total = len(security_results)
        if total == 0:
            return {"total_security_cases": 0, "injection_neutralized_rate": 1.0, "secrets_leaked": 0}

        neutralized = sum(1 for s in security_results if s.get("blocked_or_neutralized", True))
        secrets_leaked = sum(s.get("secrets_leaked", 0) for s in security_results)
        pii_leaked = sum(s.get("pii_leaked", 0) for s in security_results)
        unauthorized_mutations = sum(1 for s in security_results if s.get("unauthorized_mutation", False))

        return {
            "total_security_cases": total,
            "injection_neutralized_count": neutralized,
            "injection_neutralized_rate": round(neutralized / total, 4) if total > 0 else 1.0,
            "secrets_leaked": secrets_leaked,
            "pii_leaked": pii_leaked,
            "unauthorized_mutations": unauthorized_mutations,
        }

    @staticmethod
    def format_markdown_report(run_data: Dict[str, Any]) -> str:
        """Formats an EvaluationRun dictionary into a clean GitHub Flavored Markdown report."""
        run_id = run_data.get("run_id", "unknown")
        suite = run_data.get("suite_name", "full")
        total = run_data.get("total_cases", 0)
        passed = run_data.get("passed", 0)
        failed = run_data.get("failed", 0)
        skipped = run_data.get("skipped", 0)
        metrics = run_data.get("metrics", {})

        md = [
            f"# FIN Evaluation & Benchmark Report: {suite.upper()}",
            f"**Run ID**: `{run_id}`  ",
            f"**Generated At**: {run_data.get('completed_at', run_data.get('started_at', ''))}  ",
            f"**Policy Snapshot**: `{run_data.get('policy_snapshot_version', 'N/A')}`  ",
            f"**Rule Version**: `{run_data.get('rule_version', 'N/A')}`  ",
            f"**RAG Version**: `{run_data.get('rag_version', 'N/A')}`  ",
            "",
            "## 1. Executive Summary",
            "",
            f"| Total Cases | Passed | Failed | Skipped | Pass Rate |",
            f"|---|---|---|---|---|",
            f"| {total} | {passed} | {failed} | {skipped} | {round((passed / total) * 100, 2) if total > 0 else 100.0}% |",
            "",
            "## 2. Key Metrics by Layer",
            "",
        ]

        if "retrieval" in metrics:
            r = metrics["retrieval"]
            md.extend([
                "### Retrieval Quality (Layer 2)",
                f"- **Hit@1**: {r.get('hit@1', 0.0)}",
                f"- **Hit@3**: {r.get('hit@3', 0.0)}",
                f"- **Hit@5**: {r.get('hit@5', 0.0)}",
                f"- **MRR**: {r.get('mrr', 0.0)}",
                f"- **Precision@5**: {r.get('precision@5', 0.0)}",
                f"- **Recall@5**: {r.get('recall@5', 0.0)}",
                "",
            ])

        if "eligibility" in metrics:
            e = metrics["eligibility"]
            md.extend([
                "### Eligibility Determinism (Layer 4)",
                f"- **Overall Accuracy**: {e.get('overall_accuracy', 0.0)}",
                f"- **Breakdown by Status**: `{e.get('accuracy_by_status', {})}`",
                "",
            ])

        if "extraction" in metrics:
            ex = metrics["extraction"]
            md.extend([
                "### Document Fact Extraction (Layer 3)",
                f"- **Field Precision**: {ex.get('field_precision', 0.0)}",
                f"- **Field Recall**: {ex.get('field_recall', 0.0)}",
                f"- **Field F1**: {ex.get('field_f1', 0.0)}",
                "",
            ])

        if "grounding" in metrics:
            g = metrics["grounding"]
            md.extend([
                "### Evidence Grounding (Layer 5)",
                f"- **Supported Claim Rate**: {g.get('supported_rate', 0.0)}",
                f"- **Unsupported Claim Rate**: {g.get('unsupported_rate', 0.0)}",
                f"- **Contradiction Rate**: {g.get('contradiction_rate', 0.0)}",
                f"- **Citation Coverage**: {g.get('citation_coverage', 0.0)}",
                "",
            ])

        if "security" in metrics:
            s = metrics["security"]
            md.extend([
                "### Red Team & Security (Layer 8)",
                f"- **Injection Neutralization Rate**: {s.get('injection_neutralized_rate', 0.0)}",
                f"- **Secrets Leaked**: {s.get('secrets_leaked', 0)}",
                f"- **PII Leaked**: {s.get('pii_leaked', 0)}",
                f"- **Unauthorized Mutations**: {s.get('unauthorized_mutations', 0)}",
                "",
            ])

        return "\n".join(md)
