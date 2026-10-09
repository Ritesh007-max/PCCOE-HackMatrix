"""
FIN Scheme Recommendation Service.
Coordinates personalized policy discovery by combining:
1. Canonical ApplicantContext facts and conflict tracking (Phase 17)
2. Query understanding and semantic intent (Phase 18)
3. Parameterized hybrid retrieval (BM25 + FAISS + rerank)
4. Deterministic applicant-scheme compatibility scoring
5. Per-scheme statutory missing-field gap analysis
6. Optional deterministic eligibility evaluation via registered rule sets

CRITICAL ARCHITECTURAL PRINCIPLE:
AI interprets
-> Retrieval finds relevant policy candidates
-> Rules decide statutory eligibility
-> Evidence proves the information
-> Human reviews uncertainty
"""

import logging
from typing import Any, Dict, List, Optional

from src.context.models import ApplicantContext, SYSTEM_METADATA_KEYS
from src.context.fact_mapper import canonicalize_fact_key
from src.extraction.models import ApplicantFact, FactSourceType, FactVerificationStatus
from src.normalization.normalizer import normalize_field_value
from src.context.service import ApplicantContextService
from src.query.models import CanonicalIntent, QueryUnderstandingResult
from src.query.service import QueryUnderstandingService
from src.rag.models import RetrievalQuery, SchemeRetrievalResult, SourceTier
from src.rag.retriever import HybridRetriever
from src.eligibility.engine import EligibilityEngine
from src.rules.models import RuleStatus
from src.recommendation.bridge import ContextRetrievalBridge
from src.recommendation.compatibility import CompatibilityAnalyzer
from src.recommendation.gap_analysis import MissingFieldGapAnalyzer
from src.recommendation.models import (
    CompatibilityState,
    RecommendationEvidence,
    SchemeRecommendationItem,
    SchemeRecommendationResult,
)

logger = logging.getLogger("fin.recommendation.service")


class SchemeRecommendationService:
    """
    Authoritative service orchestrating personalized scheme recommendations.
    Enforces strict boundaries: retrieval finds candidates; deterministic rules evaluate eligibility.
    """

    def __init__(
        self,
        context_service: Optional[ApplicantContextService] = None,
        query_service: Optional[QueryUnderstandingService] = None,
        retriever: Optional[HybridRetriever] = None,
        eligibility_engine: Optional[EligibilityEngine] = None,
        compatibility_analyzer: Optional[CompatibilityAnalyzer] = None,
        gap_analyzer: Optional[MissingFieldGapAnalyzer] = None,
    ):
        self.context_service = context_service or ApplicantContextService()
        self.query_service = query_service or QueryUnderstandingService(applicant_context_service=self.context_service)
        self.retriever = retriever or HybridRetriever()
        self.eligibility_engine = eligibility_engine
        self.compatibility_analyzer = compatibility_analyzer or CompatibilityAnalyzer(
            eligibility_engine=self.eligibility_engine
        )
        self.gap_analyzer = gap_analyzer or MissingFieldGapAnalyzer(
            eligibility_engine=self.eligibility_engine
        )

    def recommend_schemes(
        self,
        applicant_id: str,
        query: str,
        top_k: int = 10,
        language: str = "en",
        include_eligibility: bool = True,
        include_missing_fields: bool = True,
        state_override: Optional[str] = None,
        category_override: Optional[str] = None,
        query_understanding: Optional[QueryUnderstandingResult] = None,
        applicant_facts: Optional[Dict[str, Any]] = None,
        document_facts: Optional[List[Dict[str, Any]]] = None,
    ) -> SchemeRecommendationResult:
        """
        Executes end-to-end personalized scheme recommendation.

        1. Loads applicant context snapshot for the specified applicant_id.
        2. Obtains QueryUnderstandingResult (Phase 18).
        3. Builds RetrievalQuery with deterministic metadata filters.
        4. Invokes HybridRetriever.retrieve_schemes().
        5. Computes deterministic applicant-scheme compatibility.
        6. Identifies missing statutory fields.
        7. Optionally evaluates deterministic eligibility via EligibilityEngine.
        8. Synthesizes policy evidence & provenance.
        9. Ranks candidates deterministically.
        10. Returns structured SchemeRecommendationResult.
        """
        if not applicant_id or not applicant_id.strip():
            raise ValueError("applicant_id is required for personalized recommendations.")
        if not query or not query.strip():
            raise ValueError("query string is required.")

        clean_applicant_id = applicant_id.strip()
        clean_query = query.strip()
        clamped_top_k = max(1, min(50, top_k))

        # 1. Load canonical ApplicantContext snapshot. Request facts are added
        # with source-level provenance before reconciliation; discordant document
        # values are therefore REVIEW/CONFLICTED, never "latest wins".
        context: Optional[ApplicantContext] = None
        try:
            context = self.context_service.get_applicant_context(clean_applicant_id)
        except Exception as e:
            logger.warning("Could not load ApplicantContext for %s: %s", clean_applicant_id, e)
            context = None

        context = context or ApplicantContext(applicant_id=clean_applicant_id)
        for key, value in (applicant_facts or {}).items():
            if not key or key in SYSTEM_METADATA_KEYS:
                continue
            if value is None or isinstance(value, (dict, list)):
                continue
            canonical_key = canonicalize_fact_key(key)
            if canonical_key in SYSTEM_METADATA_KEYS:
                continue
            try:
                normalized = normalize_field_value(canonical_key, value, validate=False)
            except Exception:
                normalized = value
            fact = ApplicantFact(
                applicant_id=clean_applicant_id, field=canonical_key, value=value,
                normalized_value=normalized, data_type="string", confidence=1.0,
                source_document="authenticated_profile", source_type=FactSourceType.PROFILE,
                extraction_method="PROFILE", verification_status=FactVerificationStatus.SELF_REPORTED,
            )
            context.add_fact(fact)
            try:
                self.context_service.repository.save_fact(fact)
            except Exception:
                pass
        for document in (document_facts or []):
            document_id = str(document.get("document_id") or "unknown_document")
            document_type = document.get("document_type")
            file_name = document.get("file_name") or ""
            doc_fields = document.get("fields") or {}

            # Determine whether this document describes family/household income
            has_fam = (
                any(k in doc_fields for k in ("annual_family_income", "family_income", "father_income", "mother_income", "household_income", "parivar_aay"))
                or "income" in (document_type or "").lower()
                or "income" in file_name.lower()
            )

            for key, value in doc_fields.items():
                if not key or key in SYSTEM_METADATA_KEYS:
                    continue
                if value is None or isinstance(value, (dict, list)):
                    continue
                canonical_key = canonicalize_fact_key(key, document_type, has_family_income=has_fam, file_name=file_name)
                if canonical_key in SYSTEM_METADATA_KEYS:
                    continue
                try:
                    normalized = normalize_field_value(canonical_key, value, validate=False)
                except Exception:
                    normalized = value
                context.add_fact(ApplicantFact(
                    applicant_id=clean_applicant_id, document_id=document_id,
                    field=canonical_key, value=value, normalized_value=normalized,
                    data_type="string", confidence=0.95, source_document=document_id,
                    source_type=FactSourceType.DOCUMENT, extraction_method="OCR_OR_EXTRACTION",
                    verification_status=FactVerificationStatus.EXTRACTED,
                    metadata={"document_type": document_type, "file_name": file_name, "uploaded_at": document.get("uploaded_at"),
                              "document_verification_status": document.get("verification_status")},
                ))

        conflicts_detected = [
            c for c in sorted(list(context.conflicts))
            if c not in SYSTEM_METADATA_KEYS
        ]

        # 2. Phase 18 Query Understanding
        qu_result = query_understanding
        if qu_result is None:
            try:
                qu_result = self.query_service.understand_query(clean_applicant_id, clean_query)
            except Exception as e:
                logger.warning("QueryUnderstanding failed for query '%s': %s", clean_query, e)
                qu_result = None

        # 3. Deterministic Context -> RetrievalQuery Bridge
        retrieval_query, filter_audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=context,
            user_query=clean_query,
            query_understanding=qu_result,
            top_k=clamped_top_k,
            language=language,
            state_override=state_override,
            category_override=category_override,
        )

        # 4. Hybrid Scheme Retrieval (BM25 + FAISS + fusion + rerank + scheme dedup)
        retrieved_schemes: List[SchemeRetrievalResult] = []
        try:
            retrieved_schemes = self.retriever.retrieve_schemes(retrieval_query)
        except Exception as e:
            logger.error("HybridRetriever.retrieve_schemes failed: %s", e)
            retrieved_schemes = []

        total_candidates = len(retrieved_schemes)

        # 5. Process Each Candidate Scheme
        recommendation_items: List[SchemeRecommendationItem] = []

        for candidate in retrieved_schemes:
            slug = candidate.scheme_slug
            primary_chunk = candidate.best_matching_chunks[0] if candidate.best_matching_chunks else None
            scheme_id = (
                primary_chunk.scheme_id
                if primary_chunk and primary_chunk.scheme_id
                else slug
            )
            scheme_name = candidate.scheme_name or slug
            relevance_score = float(candidate.aggregate_score)

            # Compatibility Analysis
            compat_res = self.compatibility_analyzer.analyze(candidate, context)
            compatibility_score = float(compat_res.overall_compatibility_score)

            # Missing Fields Analysis
            missing_fields: List[Dict[str, Any]] = []
            missing_fields_status = "UNKNOWN"
            if include_missing_fields:
                mf_objs, missing_fields_status = self.gap_analyzer.analyze(candidate, context)
                missing_fields = [m.to_dict() for m in mf_objs]

            # Deterministic Eligibility Evaluation (Phase 20 integration)
            eligibility_status: Optional[str] = None
            is_eligible: Optional[bool] = None

            if include_eligibility:
                if self.eligibility_engine and (slug in self.eligibility_engine._rulesets or scheme_id in self.eligibility_engine._rulesets):
                    try:
                        profile = context.to_applicant_profile() if context else {}
                        rule_id_target = slug if slug in self.eligibility_engine._rulesets else scheme_id
                        decision = self.eligibility_engine.evaluate(rule_id_target, profile)
                        eligibility_status = decision.status.value
                        is_eligible = decision.eligible
                    except Exception as e:
                        logger.warning("Eligibility evaluation failed for scheme %s: %s", slug, e)
                        eligibility_status = RuleStatus.UNKNOWN.value
                        is_eligible = None
                else:
                    # Unregistered scheme -> UNKNOWN (never guess PASS or FAIL!)
                    eligibility_status = RuleStatus.UNKNOWN.value
                    is_eligible = None

            # Evidence & Provenance Preservation
            snippets = [c.content for c in candidate.best_matching_chunks[:3]]
            chunk_ids = [c.chunk_id for c in candidate.best_matching_chunks]
            highest_tier = (
                candidate.source_metadata.get("highest_source_tier")
                or (primary_chunk.source_tier if primary_chunk else SourceTier.PRIMARY_SCHEME.value)
            )
            source_url = (
                candidate.source_metadata.get("source_url")
                or (primary_chunk.metadata.get("source_url") if primary_chunk else None)
            )

            # Gather applicant fact evidence IDs that influenced this scheme
            app_evidence_ids: List[str] = []
            if context:
                for match_detail in compat_res.matched_facts:
                    ev_records = context.get_evidence(match_detail.field)
                    for e in ev_records:
                        ev_id = getattr(e, "evidence_id", None) or getattr(e, "id", None)
                        if ev_id:
                            app_evidence_ids.append(str(ev_id))

            rec_evidence = RecommendationEvidence(
                source_tier=highest_tier,
                source_dataset="schemes_canonical.parquet",
                source_url=source_url,
                snippets=snippets,
                chunk_ids=chunk_ids,
                applicant_evidence_ids=list(set(app_evidence_ids)),
                provenance_metadata=dict(candidate.source_metadata),
            )

            # Conflict fields that impact this scheme
            scheme_conflicts = [f.field for f in compat_res.conflict_facts]

            # Recommendation reasons
            reasons: List[str] = []
            reasons.extend(compat_res.explanation)
            # Target-group integrity invariants:
            # 1. Target-group MISMATCH can NEVER be statutory PASS, and receives strict rank penalty
            if compat_res.target_group_match == CompatibilityState.MISMATCH:
                eligibility_status = RuleStatus.FAIL.value
                is_eligible = False
                compatibility_score = min(compatibility_score, 0.20)
            # 2. Target-group UNKNOWN can NEVER be statutory PASS (UNKNOWN != PASS)
            elif compat_res.target_group_match == CompatibilityState.UNKNOWN:
                if eligibility_status == RuleStatus.PASS.value:
                    eligibility_status = RuleStatus.UNKNOWN.value
                    is_eligible = None
                compatibility_score = min(compatibility_score, 0.65)

            if eligibility_status == RuleStatus.PASS.value:
                reasons.append("Statutory Eligibility: Confirmed PASS via deterministic policy rules.")
            elif eligibility_status == RuleStatus.FAIL.value:
                reasons.append("Statutory Eligibility: Disqualified (FAIL) on mandatory criteria.")
            elif eligibility_status == RuleStatus.REVIEW.value:
                reasons.append("Statutory Eligibility: Requires human REVIEW due to contradictory evidence.")

            # Overall Match Score Formula:
            # Deterministic composite: 0.50 * relevance_score + 0.50 * compatibility_score
            # If eligibility is evaluated:
            #   PASS: +0.05 rank bonus
            #   FAIL: -0.20 rank penalty
            composite_base = 0.50 * relevance_score + 0.50 * compatibility_score
            if eligibility_status == RuleStatus.PASS.value:
                composite_base += 0.05
            elif eligibility_status == RuleStatus.FAIL.value:
                composite_base -= 0.20

            # Target-group penalty: Mismatch is capped low, Unknown does not receive inflated scores
            if compat_res.target_group_match == CompatibilityState.MISMATCH:
                composite_base = min(composite_base * 0.35, 0.20)
            elif compat_res.target_group_match == CompatibilityState.UNKNOWN:
                composite_base = min(composite_base, 0.65)

            overall_match_score = max(0.0, min(1.0, composite_base))

            recommendation_items.append(SchemeRecommendationItem(
                scheme_id=scheme_id,
                scheme_slug=slug,
                scheme_name=scheme_name,
                relevance_score=relevance_score,
                compatibility_score=compatibility_score,
                overall_match_score=overall_match_score,
                matched_facts=[f.to_dict() for f in compat_res.matched_facts],
                unmatched_facts=[f.to_dict() for f in compat_res.unmatched_facts],
                missing_fields=missing_fields,
                missing_fields_status=missing_fields_status,
                conflict_fields=scheme_conflicts,
                eligibility_status=eligibility_status,
                is_eligible=is_eligible,
                evidence=rec_evidence,
                source_metadata=dict(candidate.source_metadata),
                recommendation_reasons=reasons,
                target_group_match=compat_res.target_group_match.value if hasattr(compat_res.target_group_match, "value") else str(compat_res.target_group_match),
                target_group_name=compat_res.target_group_name,
            ))

        # 6. Rank Recommendations
        # Primary key: overall_match_score descending
        # Secondary key: relevance_score descending
        # Tertiary key: scheme_slug ascending
        recommendation_items.sort(
            key=lambda item: (-item.overall_match_score, -item.relevance_score, item.scheme_slug)
        )
        ranked_items = recommendation_items[:clamped_top_k]

        # 7. Active Facts Summary
        active_facts_summary: Dict[str, Any] = {}
        if context:
            for field_name, fact in context.canonical_facts.items():
                if field_name not in context.conflicts and field_name not in SYSTEM_METADATA_KEYS:
                    active_facts_summary[field_name] = fact.normalized_value

        conflict_details: Dict[str, Any] = {}
        for c_field in conflicts_detected:
            c_facts = context.conflict_details.get(c_field) or [f for f in context.all_facts if f.field == c_field]
            conflict_details[c_field] = [
                {
                    "field": f.field,
                    "value": f.value,
                    "normalized_value": f.normalized_value,
                    "source_type": f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type),
                    "source_document": f.source_document,
                    "page_number": f.page_number,
                    "metadata": f.metadata or {},
                }
                for f in c_facts
            ]

        return SchemeRecommendationResult(
            applicant_id=clean_applicant_id,
            query=clean_query,
            total_candidates_retrieved=total_candidates,
            recommendations=ranked_items,
            applied_filters=filter_audit.get("applied_filters", {}),
            active_facts_summary=active_facts_summary,
            conflicts_detected=conflicts_detected,
            metadata={
                "conflict_details": conflict_details,
                "unsupported_facts_preserved": filter_audit.get("unsupported_facts_preserved", []),
                "ignored_conflicts": filter_audit.get("ignored_conflicts", []),
                "intent": qu_result.intent.value if qu_result else CanonicalIntent.SCHEME_RECOMMENDATION.value,
                "top_k_requested": clamped_top_k,
                "language": language,
            },
        )
