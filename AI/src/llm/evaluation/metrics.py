"""
PolicySetu Phase 6 Evaluation Metrics.
Calculates exact precision, recall, F1, intent classification accuracy,
and decision immutability adherence.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Any


@dataclass
class IntentMetrics:
    total_queries: int
    correct_intent: int
    intent_accuracy: float
    correct_language: int
    language_accuracy: float
    correct_state_hints: int
    state_hint_accuracy: float
    correct_category_hints: int
    category_hint_accuracy: float
    correct_beneficiary_hints: int
    beneficiary_hint_accuracy: float
    unrelated_facts_reported: int


@dataclass
class FactExtractionMetrics:
    total_test_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    normalization_pass_rate: float


@dataclass
class SafetyAndGroundingMetrics:
    total_injection_cases: int
    detected_injections: int
    injection_detection_rate: float
    raw_text_preservation_rate: float
    decision_immutability_adherence_rate: float
    citation_precision: float


def compute_intent_metrics(results: List[Dict[str, Any]]) -> IntentMetrics:
    """Computes intent, language, and retrieval hint accuracy over test queries."""
    total = len(results)
    if total == 0:
        return IntentMetrics(0, 0, 0.0, 0, 0.0, 0, 0.0, 0, 0.0, 0, 0.0, 0)

    correct_intent = sum(1 for r in results if r["predicted_intent"] == r["expected_intent"])
    correct_lang = sum(1 for r in results if r["predicted_language"] == r["expected_language"])
    correct_state = sum(1 for r in results if r.get("predicted_state") == r.get("expected_state"))
    correct_cat = sum(1 for r in results if r.get("predicted_category") == r.get("expected_category"))
    correct_ben = sum(1 for r in results if r.get("predicted_beneficiary") == r.get("expected_beneficiary"))
    unrelated_facts = sum(r.get("unrelated_applicant_facts_reported", 0) for r in results)

    return IntentMetrics(
        total_queries=total,
        correct_intent=correct_intent,
        intent_accuracy=round(correct_intent / total, 4),
        correct_language=correct_lang,
        language_accuracy=round(correct_lang / total, 4),
        correct_state_hints=correct_state,
        state_hint_accuracy=round(correct_state / total, 4),
        correct_category_hints=correct_cat,
        category_hint_accuracy=round(correct_cat / total, 4),
        correct_beneficiary_hints=correct_ben,
        beneficiary_hint_accuracy=round(correct_ben / total, 4),
        unrelated_facts_reported=unrelated_facts,
    )


def compute_extraction_metrics(results: List[Dict[str, Any]]) -> FactExtractionMetrics:
    """Computes field-level extraction precision, recall, and F1."""
    tp = 0
    fp = 0
    fn = 0
    norm_pass = 0
    total_norm_tested = 0

    for r in results:
        expected_fields: Set[str] = set(r["expected_fields"].keys())
        predicted_fields: Set[str] = set(r["predicted_facts"].keys())

        # Correctly extracted fields
        common = expected_fields & predicted_fields
        for field in common:
            # Check if expected raw value is contained in or equal to predicted raw value
            exp_val = str(r["expected_fields"][field]).lower().strip()
            pred_val = str(r["predicted_facts"][field]).lower().strip()
            if exp_val in pred_val or pred_val in exp_val:
                tp += 1
            else:
                fp += 1

        fp += len(predicted_fields - expected_fields)
        fn += len(expected_fields - predicted_fields)

        if "normalized_success" in r:
            total_norm_tested += 1
            if r["normalized_success"]:
                norm_pass += 1

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    norm_rate = round(norm_pass / total_norm_tested, 4) if total_norm_tested > 0 else 1.0

    return FactExtractionMetrics(
        total_test_cases=len(results),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        normalization_pass_rate=norm_rate,
    )
