"""
FIN Query Understanding Service.
Coordinates:
1. Intent classification across Phase 18 canonical taxonomy.
2. Candidate fact extraction with USER_INPUT provenance and Phase 17 normalization.
3. Conflict detection against ApplicantContext snapshot (never silently overwriting document facts).
4. Reference resolution across schemes, documents, and personal facts.
5. Structured query routing for downstream Phase 19 consumption.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.context.service import ApplicantContextService
from src.context.models import ApplicantContext
from src.extraction.models import ApplicantFact, FactSourceType
from src.query.models import (
    CanonicalIntent,
    DownstreamRoute,
    QueryUnderstandingResult,
    QueryContext,
)
from src.query.intent_classifier import IntentClassifier
from src.query.fact_extractor import UserFactExtractor
from src.query.reference_resolver import ReferenceResolver
from src.query.router import QueryRouter

logger = logging.getLogger("fin.query.service")


class QueryUnderstandingService:
    """
    Authoritative service producing canonical QueryUnderstandingResult from raw citizen input.
    Operates against a single ApplicantContext snapshot per query.
    """

    def __init__(
        self,
        applicant_context_service: Optional[ApplicantContextService] = None,
        intent_classifier: Optional[IntentClassifier] = None,
        fact_extractor: Optional[UserFactExtractor] = None,
        reference_resolver: Optional[ReferenceResolver] = None,
        router: Optional[QueryRouter] = None,
    ):
        self.context_service = applicant_context_service or ApplicantContextService()
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.fact_extractor = fact_extractor or UserFactExtractor()
        self.reference_resolver = reference_resolver or ReferenceResolver()
        self.router = router or QueryRouter()

    def understand_query(
        self,
        applicant_id: str,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> QueryUnderstandingResult:
        """
        Processes citizen utterance, aggregates context, detects conflicts,
        and constructs the canonical structured query contract.
        """
        raw_message = message or ""
        normalized_message = " ".join(raw_message.strip().split())

        # 1. Single snapshot load of canonical ApplicantContext (No scattered ad-hoc DB queries)
        context: Optional[ApplicantContext] = None
        has_context = False
        try:
            if applicant_id:
                context = self.context_service.get_applicant_context(applicant_id)
                has_context = bool(context and (context.all_facts or context.documents))
        except Exception as e:
            logger.warning("Could not load ApplicantContext for %s: %s", applicant_id, e)
            context = None
            has_context = False

        # 2. Intent Classification
        intent, confidence, intent_reason = self.intent_classifier.classify(raw_message)

        # 3. User Fact Extraction (Candidate facts marked strictly USER_INPUT)
        user_facts = self.fact_extractor.extract_user_facts(raw_message, applicant_id=applicant_id)

        # 4. Conflict Detection against stored document / verified facts
        # CRITICAL CONTRACT: Candidate user facts must NEVER silently overwrite persistent document facts.
        conflicts_detected: List[Dict[str, Any]] = []
        if context:
            # Include multi-document conflicts already detected in context
            if context.conflicts:
                for c_field in context.conflicts:
                    fl = context.conflict_details.get(c_field, [])
                    conflicts_detected.append({
                        "field": c_field,
                        "conflict_type": "MULTI_DOCUMENT_CONFLICT",
                        "sources": [f.source_document for f in fl],
                        "values": [f.value for f in fl],
                        "message": f"Conflicting values detected across documents for {c_field}: {', '.join(str(f.value) for f in fl)}"
                    })

            for ufact in user_facts:
                stored_fact = context.get_fact(ufact.field)
                if not stored_fact:
                    # Also check if user provided general income that clashes with family income
                    if ufact.field == "annual_income":
                        stored_fact = context.get_fact("annual_family_income")
                    elif ufact.field == "annual_family_income":
                        stored_fact = context.get_fact("annual_income")

                if stored_fact and stored_fact.normalized_value is not None and ufact.normalized_value is not None:
                    # Compare values
                    differs = False
                    if isinstance(stored_fact.normalized_value, (int, float)) and isinstance(ufact.normalized_value, (int, float)):
                        differs = abs(float(stored_fact.normalized_value) - float(ufact.normalized_value)) > 1e-6
                    else:
                        differs = str(stored_fact.normalized_value).strip().lower() != str(ufact.normalized_value).strip().lower()

                    if differs:
                        conflicts_detected.append({
                            "field": ufact.field,
                            "stored_field": stored_fact.field,
                            "stored_value": stored_fact.value,
                            "stored_normalized": stored_fact.normalized_value,
                            "stored_source": stored_fact.source_type.value if hasattr(stored_fact.source_type, "value") else str(stored_fact.source_type),
                            "user_value": ufact.value,
                            "user_normalized": ufact.normalized_value,
                            "user_source": FactSourceType.USER_INPUT.value,
                            "conflict_type": "DOCUMENT_VS_USER_INPUT",
                            "message": (
                                f"Declared {ufact.field} ({ufact.value}) conflicts with "
                                f"stored {stored_fact.field} ({stored_fact.value})."
                            )
                        })

        # 5. Entity & Reference Resolution
        # A. Scheme resolution
        ref_scheme, scheme_ambiguity = self.reference_resolver.resolve_scheme_reference(
            raw_message, conversation_history=conversation_history
        )

        # B. Document resolution
        ref_doc, doc_ambiguity = self.reference_resolver.resolve_document_reference(
            raw_message, applicant_context=context
        )

        # C. Personal fact resolution
        ref_fact_keys, fact_ambiguity = self.reference_resolver.resolve_personal_fact_reference(
            raw_message, applicant_context=context, conversation_history=conversation_history
        )

        # D. Missing required facts check
        missing_facts = self.reference_resolver.check_missing_required_facts(
            raw_message, referenced_scheme=ref_scheme, applicant_context=context
        )

        # Consolidate Ambiguities
        # Fact ambiguity (personal vs family income) only overrides intent if not querying a document
        if intent == CanonicalIntent.DOCUMENT_QUERY:
            consolidated_ambiguity = doc_ambiguity
        else:
            consolidated_ambiguity = scheme_ambiguity or doc_ambiguity or fact_ambiguity

        if consolidated_ambiguity and intent not in (CanonicalIntent.CLARIFICATION_REQUIRED, CanonicalIntent.UNKNOWN):
            # If high-level ambiguity exists, signal clarification
            intent = CanonicalIntent.CLARIFICATION_REQUIRED

        # Requested fact (single target if PERSONAL_FACT_LOOKUP)
        requested_fact = ref_fact_keys[0] if (intent == CanonicalIntent.PERSONAL_FACT_LOOKUP and ref_fact_keys) else None

        # 6. Query Routing
        route, route_reason = self.router.route(intent)

        # 7. Construct Result
        result = QueryUnderstandingResult(
            applicant_id=applicant_id,
            raw_message=raw_message,
            normalized_message=normalized_message,
            intent=intent,
            intent_confidence=confidence,
            route=route,
            routing_reason=route_reason,
            referenced_scheme=ref_scheme,
            referenced_document=ref_doc,
            referenced_fact_keys=ref_fact_keys,
            requested_fact=requested_fact,
            candidate_facts=user_facts,
            missing_information=missing_facts,
            conflicts=conflicts_detected,
            ambiguity=consolidated_ambiguity,
            applicant_context_available=has_context,
            metadata={
                "intent_classification_reason": intent_reason,
                "history_length": len(conversation_history) if conversation_history else 0,
            }
        )

        logger.info(
            "Query understood for %s: intent=%s, conf=%.2f, route=%s, candidate_facts=%d, conflicts=%d",
            applicant_id,
            intent.value,
            confidence,
            route.value,
            len(user_facts),
            len(conflicts_detected),
        )

        return result

    def create_query_context(
        self,
        applicant_id: str,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> QueryContext:
        """
        Creates a complete QueryContext snapshot binding applicant context and understanding.
        Directly consumable by Phase 19 Scheme Recommendation.
        """
        understanding = self.understand_query(
            applicant_id=applicant_id,
            message=message,
            conversation_history=conversation_history,
        )

        active_facts: Dict[str, Any] = {}
        unresolved_conflicts: List[str] = []
        doc_summaries: List[Dict[str, Any]] = []

        try:
            if applicant_id:
                ctx = self.context_service.get_applicant_context(applicant_id)
                if ctx:
                    for k, f in ctx.canonical_facts.items():
                        if k not in ctx.conflicts and f.normalized_value is not None:
                            active_facts[k] = f.normalized_value
                    unresolved_conflicts = list(ctx.conflicts)
                    doc_summaries = [
                        {
                            "document_id": d.document_id,
                            "document_type": d.document_type,
                            "sha256": d.document_hash,
                            "file_name": d.file_name,
                        }
                        for d in ctx.documents
                    ]
        except Exception as e:
            logger.warning("Could not assemble context details for %s: %s", applicant_id, e)

        return QueryContext(
            applicant_id=applicant_id,
            understanding=understanding,
            active_facts=active_facts,
            unresolved_conflicts=unresolved_conflicts,
            document_summaries=doc_summaries,
            conversation_history=conversation_history or [],
        )
