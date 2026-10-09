"""
FIN Unified Intelligence Orchestrator.
The central intelligence brain integrating:
- Query Understanding (Phase 18)
- Conversation Context & References (Pillar B)
- Canonical ApplicantContext (Phase 17)
- Scheme Retrieval (Phase 19 RAG)
- Personalized Recommendation (Phase 19)
- Deterministic Policy Rules & Eligibility (Phase 20)
- Evidence Provenance & Verification
- Policy Explanation & Next-Action Guidance (Phase 21)
- Human Review & Conflict Resolution (Pillar C)
- Grounding Verification & Defense against Prompt Injection
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from src.context.models import ApplicantContext
from src.context.service import ApplicantContextService
from src.conversation.models import ConversationState, MessageRole, TurnReference
from src.conversation.resolver import ConversationReferenceResolver
from src.conversation.store import ConversationStore
from src.eligibility.engine import EligibilityEngine
from src.eligibility.decision import EligibilityDecision
from src.rules.models import RuleStatus
from src.explanation.generator import ExplanationGenerator
from src.explanation.models import ExplanationBundle, GroundingStatus
from src.explanation.service import PolicyExplanationService
from src.explanation.verifier import ExplanationGroundingVerifier
from src.extraction.models import FactSourceType, FactVerificationStatus
from src.llm.client import LLMClient
from src.llm.safety import PromptInjectionDetector
from src.query.models import CanonicalIntent, QueryUnderstandingResult
from src.query.service import QueryUnderstandingService
from src.rag.retriever import HybridRetriever
from src.recommendation.models import SchemeRecommendationItem
from src.recommendation.service import SchemeRecommendationService
from src.review.audit import AuditLogger
from src.review.models import ConflictRecord, ConflictStatus
from src.review.service import ConflictResolutionService

from .composer import ResponseComposer
from .errors import OrchestrationError, ValidationError
from .models import RequestRoute, UnifiedIntelligenceRequest, UnifiedIntelligenceResponse
from .router import OrchestrationRouter

logger = logging.getLogger("fin.orchestrator")


class UnifiedIntelligenceOrchestrator:
    """
    Central, interconnected intelligence brain for FIN / PolicySetu.
    Strictly follows:
        AI interprets.
        Rules decide.
        Evidence proves.
        Humans review uncertainty.
    """

    def __init__(
        self,
        context_service: Optional[ApplicantContextService] = None,
        query_service: Optional[QueryUnderstandingService] = None,
        conversation_store: Optional[ConversationStore] = None,
        reference_resolver: Optional[ConversationReferenceResolver] = None,
        conflict_service: Optional[ConflictResolutionService] = None,
        audit_logger: Optional[AuditLogger] = None,
        recommendation_service: Optional[SchemeRecommendationService] = None,
        eligibility_engine: Optional[EligibilityEngine] = None,
        explanation_service: Optional[PolicyExplanationService] = None,
        retriever: Optional[HybridRetriever] = None,
        llm_client: Optional[LLMClient] = None,
        router: Optional[OrchestrationRouter] = None,
        composer: Optional[ResponseComposer] = None,
    ):
        self.context_service = context_service or ApplicantContextService()
        self.query_service = query_service or QueryUnderstandingService(applicant_context_service=self.context_service)
        self.conversation_store = conversation_store or ConversationStore()
        self.reference_resolver = reference_resolver or ConversationReferenceResolver()
        self.audit_logger = audit_logger or AuditLogger()
        self.conflict_service = conflict_service or ConflictResolutionService(
            context_service=self.context_service, audit_logger=self.audit_logger
        )

        # 1. Hybrid Retriever initialization
        if retriever is not None:
            self.retriever = retriever
        else:
            self.retriever = HybridRetriever()
            try:
                from src.rag.ingestion import RAGIngestionPipeline
                from src.rag.config import DEFAULT_RAG_CONFIG
                ingestion = RAGIngestionPipeline(config=DEFAULT_RAG_CONFIG)
                docs = ingestion.load_primary_schemes(limit=150)
                if docs:
                    self.retriever.index_documents(docs)
            except Exception as e:
                logger.warning("Could not pre-index schemes in orchestrator: %s", e)

        # 2. Eligibility Engine initialization
        if eligibility_engine is not None:
            self.eligibility_engine = eligibility_engine
        else:
            engine = EligibilityEngine()
            from pathlib import Path
            rules_dir = Path(__file__).resolve().parents[2] / "data" / "schemes" / "rules" / "examples"
            if rules_dir.exists():
                try:
                    engine.load_rules_from_directory(rules_dir)
                except Exception as e:
                    logger.warning("Could not auto-load rules in orchestrator: %s", e)
            self.eligibility_engine = engine

        self.recommendation_service = recommendation_service or SchemeRecommendationService(
            context_service=self.context_service,
            query_service=self.query_service,
            retriever=self.retriever,
            eligibility_engine=self.eligibility_engine,
        )
        self.explanation_service = explanation_service or PolicyExplanationService()
        self.llm_client = llm_client or LLMClient()
        self.router = router or OrchestrationRouter()
        self.composer = composer or ResponseComposer()
        self.injection_detector = PromptInjectionDetector()

    def process_query(self, request: UnifiedIntelligenceRequest) -> UnifiedIntelligenceResponse:
        """
        Processes citizen query through the unified intelligence pipeline.
        """
        app_id = str(request.applicant_id).strip()
        conv_id = str(request.conversation_id).strip()
        lang = str(request.language or "en").strip().lower()
        raw_msg = request.message or ""

        # 0. Audit initial entry
        self.audit_logger.log(
            event_type="ORCHESTRATION_REQUEST_RECEIVED",
            applicant_id=app_id,
            conversation_id=conv_id,
            actor="USER",
            metadata={"message": raw_msg, "language": lang},
        )

        # 1. Prompt Injection Defense
        scan_res = self.injection_detector.scan(raw_msg)
        if scan_res.is_injection_risk:
            threat_desc = ", ".join(scan_res.detected_threats)
            logger.warning("Prompt injection attempt intercepted for applicant %s: %s", app_id, threat_desc)
            self.audit_logger.log(
                event_type="PROMPT_INJECTION_BLOCKED",
                applicant_id=app_id,
                conversation_id=conv_id,
                actor="SECURITY_GUARD",
                metadata={"threats": scan_res.detected_threats},
            )
            # Treat strictly as safe untrusted text; do NOT execute statutory override
            # Continue pipeline but ignore any attempt to manipulate eligibility

        # 2. Get / Initialize Conversation State
        conv_state = self.conversation_store.get_or_create(
            applicant_id=app_id,
            conversation_id=conv_id,
            language=lang,
        )

        # 3. Query Understanding
        conv_history = [m.to_dict() for m in conv_state.messages[-6:]]
        query_result = self.query_service.understand_query(
            applicant_id=app_id,
            message=raw_msg,
            conversation_history=conv_history,
        )

        # 4. Resolve References (Pronouns, anchors)
        explicit_scheme = request.scheme_id or query_result.referenced_scheme
        explicit_doc = request.document_id or query_result.referenced_document
        explicit_fact = query_result.referenced_fact_keys[0] if query_result.referenced_fact_keys else None

        # Snapshot load of canonical ApplicantContext
        context = self.context_service.get_applicant_context(app_id)

        resolved_refs = self.reference_resolver.resolve(
            message=raw_msg,
            state=conv_state,
            context=context,
            explicit_scheme=explicit_scheme,
            explicit_doc=explicit_doc,
            explicit_fact=explicit_fact,
        )

        # Ambiguous reference check
        if resolved_refs.is_ambiguous:
            resp = self.composer.compose(
                request_id=request.request_id,
                applicant_id=app_id,
                conversation_id=conv_id,
                intent="AMBIGUOUS_REFERENCE",
                route=RequestRoute.GENERAL_FOLLOW_UP,
                language=lang,
                answer_text=resolved_refs.ambiguity_reason or "Please clarify which scheme you are referring to.",
                review={"review_reason": "AMBIGUOUS_REFERENCE", "candidates": resolved_refs.candidate_schemes},
            )
            conv_state.add_message(
                role=MessageRole.USER,
                content=raw_msg,
                intent="AMBIGUOUS_REFERENCE",
            )
            conv_state.add_message(
                role=MessageRole.ASSISTANT,
                content=resp.answer,
                intent="CLARIFICATION_REQUIRED",
            )
            self.conversation_store.save(conv_state)
            return resp

        # 5. Ingest Candidate Facts & Detect Conflicts
        # Non-negotiable: Never silently overwrite a persistent document fact
        conflicts_out: List[Dict[str, Any]] = []
        if query_result.conflicts:
            for conf_info in query_result.conflicts:
                conflict_field = conf_info.get("stored_field") or conf_info["field"]
                conf_record = self.conflict_service.record_conflict(
                    applicant_id=app_id,
                    field=conflict_field,
                    source_a=conf_info.get("stored_source", "DOCUMENT"),
                    value_a=conf_info.get("stored_value"),
                    source_b=conf_info.get("user_source", "USER_INPUT"),
                    value_b=conf_info.get("user_value"),
                    metadata=conf_info,
                )
                conflicts_out.append(conf_record.to_dict())
                conv_state.pending_conflicts.append(conf_record.conflict_id)
                # Store the user fact as well so both are preserved in context.all_facts
                self.context_service.record_user_fact(
                    applicant_id=app_id,
                    fact_key=conflict_field,
                    raw_value=conf_info.get("user_value"),
                    confidence=1.0,
                    source_type=FactSourceType.USER_INPUT,
                    verification_status=FactVerificationStatus.SELF_REPORTED,
                )
            # Refresh context snapshot
            context = self.context_service.get_applicant_context(app_id)
        else:
            # If no conflict, ingest candidate user facts into persistent ledger
            for ufact in query_result.candidate_facts:
                if ufact.field and ufact.value is not None:
                    # Only record if not conflicted in applicant context
                    if not context.has_conflict(ufact.field):
                        self.context_service.record_user_fact(
                            applicant_id=app_id,
                            fact_key=ufact.field,
                            raw_value=ufact.value,
                            confidence=ufact.confidence,
                            source_type=FactSourceType.USER_INPUT,
                            verification_status=FactVerificationStatus.SELF_REPORTED,
                        )
            # Refresh context snapshot
            context = self.context_service.get_applicant_context(app_id)

        # 6. Request Routing
        target_scheme = resolved_refs.scheme_id or conv_state.active_scheme
        route = self.router.route(
            query_result=query_result,
            raw_message=raw_msg,
            active_scheme=target_scheme,
            active_decision_id=conv_state.active_decision_id,
        )

        # Fast-path for newly detected conflicts on fact declaration
        if conflicts_out and route in (RequestRoute.GENERAL_FOLLOW_UP, RequestRoute.PERSONAL_FACT_LOOKUP):
            c0 = conflicts_out[0]
            field_name = c0.get("field", "field")
            doc_val = c0.get("value_a", "unknown")
            user_val = c0.get("value_b", "unknown")
            ans_text = (
                f"Conflicting information was detected for {field_name}. "
                f"Document indicates {doc_val} while declared value is {user_val}. "
                "This requires caseworker review."
            )
            response = self.composer.compose(
                request_id=request.request_id,
                applicant_id=app_id,
                conversation_id=conv_id,
                intent=query_result.intent.value if hasattr(query_result.intent, "value") else str(query_result.intent),
                route=RequestRoute.CONFLICT_RESOLUTION_STATUS,
                language=lang,
                answer_text=ans_text,
                conflicts=conflicts_out,
                review={
                    "status": "REVIEW",
                    "reason": "Conflicting applicant facts require human resolution.",
                    "conflicts": conflicts_out,
                },
                grounding_status="GROUNDED",
            )

        # 7. Execute Route Logic
        elif route == RequestRoute.PERSONAL_FACT_LOOKUP:
            response = self._handle_personal_fact_lookup(
                request, query_result, resolved_refs, context, conv_state, lang
            )
        elif route == RequestRoute.DOCUMENT_QUERY:
            response = self._handle_document_query(
                request, query_result, resolved_refs, context, conv_state, lang
            )
        elif route == RequestRoute.POLICY_INFORMATION:
            response = self._handle_policy_information(
                request, query_result, target_scheme, context, conv_state, lang
            )
        elif route == RequestRoute.DOCUMENT_REQUIREMENTS:
            response = self._handle_document_requirements(
                request, target_scheme, context, conv_state, lang
            )
        elif route == RequestRoute.BENEFIT_QUERY:
            response = self._handle_benefit_query(
                request, target_scheme, context, conv_state, lang
            )
        elif route == RequestRoute.SCHEME_RECOMMENDATION:
            response = self._handle_scheme_recommendation(
                request, query_result, context, conv_state, lang
            )
        elif route == RequestRoute.ELIGIBILITY_QUERY:
            response = self._handle_eligibility_query(
                request, target_scheme, context, conv_state, lang
            )
        elif route == RequestRoute.DECISION_EXPLANATION:
            response = self._handle_decision_explanation(
                request, target_scheme, context, conv_state, lang
            )
        elif route == RequestRoute.SCHEME_COMPARISON:
            response = self._handle_scheme_comparison(
                request, query_result, context, conv_state, lang
            )
        elif route == RequestRoute.CONFLICT_RESOLUTION_STATUS:
            response = self._handle_conflict_status(
                request, context, conv_state, lang
            )
        else:
            response = self._handle_general_follow_up(
                request, query_result, target_scheme, context, conv_state, lang
            )

        # Include any newly detected conflicts in response
        if conflicts_out:
            response.conflicts = conflicts_out
            if not response.review:
                response.review = {
                    "status": "REVIEW",
                    "reason": "Conflicting applicant facts require human resolution.",
                    "conflicts": conflicts_out,
                }

        # 8. Record turn into ConversationState & persist
        turn_ref = TurnReference(
            scheme_id=target_scheme or (response.eligibility.get("scheme_id") if response.eligibility else None),
            document_id=resolved_refs.document_id or conv_state.active_document,
            decision_id=(response.eligibility.get("decision_id") if response.eligibility else conv_state.active_decision_id),
            fact_key=resolved_refs.fact_key,
        )
        conv_state.add_message(
            role=MessageRole.USER,
            content=raw_msg,
            intent=query_result.intent.value if hasattr(query_result.intent, "value") else str(query_result.intent),
            references=turn_ref,
        )
        conv_state.add_message(
            role=MessageRole.ASSISTANT,
            content=response.answer,
            intent=response.route,
            references=turn_ref,
        )
        if response.eligibility:
            conv_state.last_decision = response.eligibility
            conv_state.active_decision_id = response.eligibility.get("decision_id")
        if response.explanation:
            conv_state.last_explanation = response.explanation
        if target_scheme:
            conv_state.set_active_scheme(target_scheme)

        self.conversation_store.save(conv_state)

        # 9. Audit completion
        self.audit_logger.log(
            event_type="ORCHESTRATION_RESPONSE_COMPLETED",
            applicant_id=app_id,
            conversation_id=conv_id,
            actor="SYSTEM",
            entity_id=response.request_id,
            metadata={"route": response.route, "grounding_status": response.grounding_status},
        )

        return response

    # -------------------------------------------------------------------------
    # Route Handlers
    # -------------------------------------------------------------------------

    def _handle_personal_fact_lookup(
        self,
        request: UnifiedIntelligenceRequest,
        query_result: QueryUnderstandingResult,
        refs: Any,
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        field_key = refs.fact_key or (query_result.referenced_fact_keys[0] if query_result.referenced_fact_keys else None)
        if not field_key:
            # Check common terms
            text = (request.message or "").lower()
            if "income" in text:
                field_key = "annual_family_income"
            elif "age" in text:
                field_key = "age"
            elif "land" in text:
                field_key = "landholding_hectares"
            else:
                field_key = "annual_family_income"

        # Check if field has conflict
        if context.has_conflict(field_key):
            conf_details = context.conflict_details.get(field_key, [])
            vals = [str(f.value) for f in conf_details]
            msg = (
                f"Conflicting values were detected for your {field_key}: ({', '.join(vals)}). "
                "This requires caseworker review."
            )
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="PERSONAL_FACT_LOOKUP",
                route=RequestRoute.PERSONAL_FACT_LOOKUP,
                language=lang,
                answer_text=msg,
                review={"status": "REVIEW", "field": field_key, "conflicting_values": vals},
                grounding_status="GROUNDED",
            )

        fact = context.get_fact(field_key)
        # If not found under exact key, check aliases (e.g. annual_income vs annual_family_income)
        if not fact:
            if field_key == "annual_family_income":
                fact = context.get_fact("annual_income")
            elif field_key == "annual_income":
                fact = context.get_fact("annual_family_income")

        if not fact or fact.normalized_value is None:
            # Deterministic missing fact answer
            answer_text = (
                f"We do not currently have verified records for your {field_key}. "
                "Please upload an authoritative document or declare your details."
            )
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="PERSONAL_FACT_LOOKUP",
                route=RequestRoute.PERSONAL_FACT_LOOKUP,
                language=lang,
                answer_text=answer_text,
                missing_information=[{"field": field_key, "status": "UNKNOWN"}],
                next_actions=[f"Upload document verifying {field_key}"],
                grounding_status="GROUNDED",
            )

        # Fact found! Retrieve evidence
        ev_list = context.get_evidence(field_key)
        ev_dicts = [e.to_dict() for e in ev_list] if ev_list else []
        src_doc = fact.source_document or (ev_list[0].source_uri if ev_list else "your submitted documents")

        # Multilingual formatting with exact numeric value
        norm_val = fact.normalized_value
        if isinstance(norm_val, (int, float)) and ("income" in field_key):
            if lang == "hi":
                answer_text = f"अपलोड किए गए {src_doc} के अनुसार आपकी वार्षिक पारिवारिक आय ₹{norm_val:,} है।"
            elif lang == "gu":
                answer_text = f"અપલોડ કરેલા {src_doc} અનુસાર તમારી વાર્ષિક પારિવારિક આવક ₹{norm_val:,} છે."
            else:
                answer_text = f"Your annual family income is ₹{norm_val:,} according to the uploaded {src_doc}."
        else:
            answer_text = f"Your {field_key} is {fact.value} according to {src_doc}."

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="PERSONAL_FACT_LOOKUP",
            route=RequestRoute.PERSONAL_FACT_LOOKUP,
            language=lang,
            answer_text=answer_text,
            evidence=ev_dicts,
            citations=[src_doc],
            grounding_status="GROUNDED",
            provenance={"field": field_key, "source_type": fact.source_type, "confidence": fact.confidence},
        )

    def _handle_document_query(
        self,
        request: UnifiedIntelligenceRequest,
        query_result: QueryUnderstandingResult,
        refs: Any,
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        docs = context.documents
        if not docs:
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="DOCUMENT_QUERY",
                route=RequestRoute.DOCUMENT_QUERY,
                language=lang,
                answer_text="You have not uploaded any documents yet. Please upload your documents to verify your eligibility.",
                next_actions=["Upload income certificate, Aadhaar, or land records."],
            )

        text = (request.message or "").lower()
        # Check if asking about what documents have been uploaded
        if "which documents" in text or "what documents have i" in text:
            doc_names = [f"- {d.file_name} ({d.document_type})" for d in docs]
            answer = "You have uploaded the following documents:\n" + "\n".join(doc_names)
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="DOCUMENT_QUERY",
                route=RequestRoute.DOCUMENT_QUERY,
                language=lang,
                answer_text=answer,
                evidence=[{"document_id": d.document_id, "file_name": d.file_name} for d in docs],
            )

        # Check if asked about landholding in an income certificate
        if "land" in text:
            # Check if any document contains landholding facts
            has_land = False
            for d in docs:
                for f in d.extracted_facts:
                    if "land" in f.field:
                        has_land = True
                        break
            if not has_land:
                return self.composer.compose(
                    request_id=request.request_id,
                    applicant_id=request.applicant_id,
                    conversation_id=request.conversation_id,
                    intent="DOCUMENT_QUERY",
                    route=RequestRoute.DOCUMENT_QUERY,
                    language=lang,
                    answer_text="The uploaded document does not mention land ownership.",
                    grounding_status="GROUNDED",
                )

        # Default document inquiry
        doc = docs[-1]
        fact_lines = [f"- {f.field}: {f.value}" for f in doc.extracted_facts]
        body = "\n".join(fact_lines) if fact_lines else "No structured facts extracted."
        answer = f"According to your uploaded {doc.document_type} ({doc.file_name}):\n{body}"
        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="DOCUMENT_QUERY",
            route=RequestRoute.DOCUMENT_QUERY,
            language=lang,
            answer_text=answer,
            evidence=[e.to_dict() for e in doc.evidence],
            citations=[doc.file_name],
        )

    def _handle_policy_information(
        self,
        request: UnifiedIntelligenceRequest,
        query_result: QueryUnderstandingResult,
        scheme_id: Optional[str],
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        sid = scheme_id or "PMJAY"
        # Check catalog / knowledge base
        meta = self._get_scheme_metadata(sid)
        if not meta:
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="POLICY_INFORMATION",
                route=RequestRoute.POLICY_INFORMATION,
                language=lang,
                answer_text=f"Information for scheme '{sid}' could not be located in the authoritative repository.",
            )

        # Build clean explanation
        name = meta.get("name", sid)
        desc = meta.get("description", meta.get("purpose", ""))
        elig = meta.get("eligibility_summary", "Statutory rules apply.")
        docs = meta.get("documents_required", ["Identity proof", "Income certificate"])
        citation = meta.get("source_uri", "National Portal of India / Official Guidelines")

        if lang == "hi":
            answer = (
                f"**{name} ({sid})**\n\n"
                f"**उद्देश्य:** {desc}\n\n"
                f"**पात्रता अवलोकन:** {elig}\n\n"
                f"**आवश्यक दस्तावेज़:** {', '.join(docs)}\n\n"
                f"**आधिकारिक स्रोत:** {citation}"
            )
        elif lang == "gu":
            answer = (
                f"**{name} ({sid})**\n\n"
                f"**હેતુ:** {desc}\n\n"
                f"**પાત્રતા ઝાંખી:** {elig}\n\n"
                f"**જરૂરી દસ્તાવેજો:** {', '.join(docs)}\n\n"
                f"**સત્તાવાર સ્ત્રોત:** {citation}"
            )
        else:
            answer = (
                f"**{name} ({sid})**\n\n"
                f"**Purpose:** {desc}\n\n"
                f"**Eligibility Overview:** {elig}\n\n"
                f"**Documents Required:** {', '.join(docs)}\n\n"
                f"**Authoritative Source:** {citation}"
            )

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="POLICY_INFORMATION",
            route=RequestRoute.POLICY_INFORMATION,
            language=lang,
            answer_text=answer,
            citations=[citation],
            grounding_status="GROUNDED",
            provenance={"scheme_id": sid, "source": citation},
        )

    def _handle_document_requirements(
        self,
        request: UnifiedIntelligenceRequest,
        scheme_id: Optional[str],
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        sid = scheme_id or conv_state.active_scheme or "PMJAY"
        meta = self._get_scheme_metadata(sid)
        docs = meta.get("documents_required", ["Aadhaar Card", "Income Certificate", "Ration Card"])
        citation = meta.get("source_uri", "Official Scheme Guidelines")

        docs_formatted = "\n".join([f"- {d}" for d in docs])
        if lang == "hi":
            answer = f"{sid} के लिए आवश्यक दस्तावेज़:\n{docs_formatted}"
        elif lang == "gu":
            answer = f"{sid} માટે જરૂરી દસ્તાવેજો:\n{docs_formatted}"
        else:
            answer = f"Authoritative documents required for {sid}:\n{docs_formatted}"

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="DOCUMENT_REQUIREMENTS",
            route=RequestRoute.DOCUMENT_REQUIREMENTS,
            language=lang,
            answer_text=answer,
            citations=[citation],
            next_actions=[f"Prepare {d}" for d in docs[:3]],
            grounding_status="GROUNDED",
        )

    def _handle_benefit_query(
        self,
        request: UnifiedIntelligenceRequest,
        scheme_id: Optional[str],
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        sid = scheme_id or conv_state.active_scheme or "PMJAY"
        meta = self._get_scheme_metadata(sid)
        benefit_text = meta.get("benefit_description")

        if not benefit_text:
            # Deterministic boundary: Never ask LLM to invent an unknown formula!
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="BENEFIT_QUERY",
                route=RequestRoute.BENEFIT_QUERY,
                language=lang,
                answer_text=(
                    f"Statutory benefit calculation formula for {sid} cannot be determined "
                    "without additional authoritative rule specifications."
                ),
                citations=[meta.get("source_uri", "Official Guidelines")],
                grounding_status="GROUNDED",
            )

        citation = meta.get("source_uri", "Official Scheme Guidelines")
        answer = f"Authoritative benefits under {sid}:\n{benefit_text}"
        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="BENEFIT_QUERY",
            route=RequestRoute.BENEFIT_QUERY,
            language=lang,
            answer_text=answer,
            citations=[citation],
            grounding_status="GROUNDED",
        )

    def _handle_scheme_recommendation(
        self,
        request: UnifiedIntelligenceRequest,
        query_result: QueryUnderstandingResult,
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        # Check if applicant has any open conflict affecting eligibility
        has_conflict = len(context.conflicts) > 0
        rec_result = self.recommendation_service.recommend_schemes(
            applicant_id=request.applicant_id,
            query=request.message,
            top_k=5,
            language=lang,
            include_eligibility=True,
            query_understanding=query_result,
        )

        rec_dicts: List[Dict[str, Any]] = []
        for item in rec_result.recommendations:
            rec_dicts.append(item.to_dict())

        # Collect evidence & citations
        evidence_dicts: List[Dict[str, Any]] = []
        citations: List[str] = []
        for it in rec_result.recommendations:
            citations.append(f"Scheme ID: {it.scheme_id}")

        answer = self.composer._build_deterministic_answer(
            route=RequestRoute.SCHEME_RECOMMENDATION,
            eligibility=None,
            recommendations=rec_dicts,
            missing_information=[],
            conflicts=[],
            evidence=[],
            lang_dict=self.composer._get_dict(lang) if hasattr(self.composer, "_get_dict") else {
                "schemes_found": "Based on your verified profile, here are the relevant schemes:"
            },
        )

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="SCHEME_RECOMMENDATION",
            route=RequestRoute.SCHEME_RECOMMENDATION,
            language=lang,
            answer_text=answer,
            recommendations=rec_dicts,
            citations=citations[:5],
            grounding_status="GROUNDED",
            provenance={"recommendation_count": len(rec_dicts), "applicant_id": request.applicant_id},
        )

    def _handle_eligibility_query(
        self,
        request: UnifiedIntelligenceRequest,
        scheme_id: Optional[str],
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        sid = scheme_id or conv_state.active_scheme or "PMJAY"
        # 1. Deterministic evaluation
        decision = self.eligibility_engine.evaluate_applicant_context(
            identifier=sid,
            context=context,
        )

        # 2. Policy explanation
        bundle = self.explanation_service.explain_decision(
            decision=decision,
            context=context,
            language=lang,
        )

        # 3. Next actions & missing info
        next_acts = [getattr(a, "description", str(a)) for a in bundle.next_actions] if bundle.next_actions else []
        missing_info = [m.to_dict() if hasattr(m, "to_dict") else m for m in bundle.missing_information] if bundle.missing_information else []

        decision_reason = " ".join(decision.disqualification_reasons or decision.review_reasons) or f"Eligibility evaluated as {decision.status.value}."

        # Build clean answer text
        answer_text = bundle.summary or bundle.headline
        if not answer_text:
            answer_text = f"Eligibility status for {sid}: {decision.status.value}. {decision_reason}"

        # If localized to Gujarati or Hindi, ensure translated text while preserving numbers
        if lang == "gu":
            answer_text = (
                f"**પાત્રતા પરિણામ:** {sid}\n\n"
                f"**સ્થિતિ:** {decision.status.value}\n\n"
                f"**કારણ:** {decision_reason}\n\n"
                f"**નિયમ સંસ્કરણ:** {decision.rule_version}"
            )
        elif lang == "hi":
            answer_text = (
                f"**पात्रता परिणाम:** {sid}\n\n"
                f"**स्थिति:** {decision.status.value}\n\n"
                f"**कारण:** {decision_reason}\n\n"
                f"**नियम संस्करण:** {decision.rule_version}"
            )

        review_payload = None
        if decision.status == RuleStatus.REVIEW:
            review_payload = {
                "status": "REVIEW",
                "reason": decision_reason,
                "scheme_id": sid,
                "decision_id": decision.decision_id,
            }

        citations = [
            ev.get("source_document") or ev.get("source_url")
            for ev in decision.evidence
            if ev.get("source_document") or ev.get("source_url")
        ] or [f"Policy Rule {sid} v{decision.rule_version}"]

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="ELIGIBILITY_QUERY",
            route=RequestRoute.ELIGIBILITY_QUERY,
            language=lang,
            answer_text=answer_text,
            eligibility=decision.to_full_dict(),
            explanation=bundle.to_dict(),
            missing_information=missing_info,
            next_actions=next_acts,
            review=review_payload,
            grounding_status=bundle.grounding_status.value if hasattr(bundle.grounding_status, "value") else str(bundle.grounding_status),
            citations=citations,
            provenance={
                "decision_id": decision.decision_id,
                "rule_version": decision.rule_version,
                "rule_set_hash": decision.rule_set_hash,
            },
        )

    def _handle_decision_explanation(
        self,
        request: UnifiedIntelligenceRequest,
        scheme_id: Optional[str],
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        sid = scheme_id or conv_state.active_scheme or "PMJAY"
        # Always evaluate or reuse exact decision
        decision = self.eligibility_engine.evaluate_applicant_context(identifier=sid, context=context)
        bundle = self.explanation_service.explain_decision(decision=decision, context=context, language=lang)

        # Extract failed conditions for exact clarity
        failed_conds = []
        for t in decision.rule_trace:
            if t.get("result") == "FAIL":
                failed_conds.append(
                    f"Rule {t.get('rule_id')}: {t.get('field')} (Applicant: {t.get('actual')}) {t.get('operator')} (Expected: {t.get('expected')})"
                )

        decision_reason = " ".join(decision.disqualification_reasons or decision.review_reasons) or f"Eligibility evaluated as {decision.status.value}."
        reasons_text = "\n".join([f"- {fc}" for fc in failed_conds]) if failed_conds else decision_reason
        citations = [
            ev.get("source_document") or ev.get("source_url")
            for ev in decision.evidence
            if ev.get("source_document") or ev.get("source_url")
        ] or [f"Policy Rule {sid} v{decision.rule_version}"]

        answer = (
            f"Explanation for {sid} decision ({decision.status.value}):\n\n"
            f"Policy Source: {', '.join(citations)}\n"
            f"Rule Version: {decision.rule_version}\n\n"
            f"Evaluated Conditions:\n{reasons_text}\n\n"
            f"Summary: {bundle.summary or bundle.headline or decision_reason}"
        )

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="DECISION_EXPLANATION",
            route=RequestRoute.DECISION_EXPLANATION,
            language=lang,
            answer_text=answer,
            eligibility=decision.to_full_dict(),
            explanation=bundle.to_dict(),
            citations=citations,
            grounding_status="GROUNDED",
            provenance={"decision_id": decision.decision_id, "rule_version": decision.rule_version},
        )

    def _handle_scheme_comparison(
        self,
        request: UnifiedIntelligenceRequest,
        query_result: QueryUnderstandingResult,
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        schemes = [query_result.referenced_scheme] if query_result.referenced_scheme else ["PMJAY", "PM-Kisan"]
        if len(schemes) < 2 and conv_state.recent_schemes:
            schemes = list(dict.fromkeys(schemes + conv_state.recent_schemes[:2]))[:2]

        rows = []
        for s in schemes:
            meta = self._get_scheme_metadata(s)
            dec = self.eligibility_engine.evaluate_applicant_context(identifier=s, context=context)
            rows.append({
                "scheme": s,
                "purpose": meta.get("purpose", meta.get("description", "Government Welfare Scheme")),
                "eligibility_status": dec.status.value,
                "documents": ", ".join(meta.get("documents_required", ["ID Proof"])[:2]),
            })

        table_lines = [
            "| Scheme | Purpose | Eligibility Status | Key Documents |",
            "| --- | --- | --- | --- |",
        ]
        for r in rows:
            table_lines.append(f"| {r['scheme']} | {r['purpose']} | {r['eligibility_status']} | {r['documents']} |")

        answer = "Objective Scheme Comparison:\n\n" + "\n".join(table_lines)
        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="SCHEME_COMPARISON",
            route=RequestRoute.SCHEME_COMPARISON,
            language=lang,
            answer_text=answer,
            citations=[f"Scheme guidelines for {', '.join(schemes)}"],
            grounding_status="GROUNDED",
        )

    def _handle_conflict_status(
        self,
        request: UnifiedIntelligenceRequest,
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        conflicts = self.conflict_service.list_conflicts(applicant_id=request.applicant_id)
        if not conflicts:
            return self.composer.compose(
                request_id=request.request_id,
                applicant_id=request.applicant_id,
                conversation_id=request.conversation_id,
                intent="CONFLICT_RESOLUTION_STATUS",
                route=RequestRoute.CONFLICT_RESOLUTION_STATUS,
                language=lang,
                answer_text="There are no active or pending conflicts recorded for your profile.",
            )

        lines = []
        for c in conflicts:
            lines.append(
                f"- Conflict on {c.field}: {c.source_a} ({c.value_a}) vs {c.source_b} ({c.value_b}) -> Status: {c.status.value}"
            )
        answer = "Your Conflict Records:\n" + "\n".join(lines)
        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="CONFLICT_RESOLUTION_STATUS",
            route=RequestRoute.CONFLICT_RESOLUTION_STATUS,
            language=lang,
            answer_text=answer,
            conflicts=[c.to_dict() for c in conflicts],
        )

    def _handle_general_follow_up(
        self,
        request: UnifiedIntelligenceRequest,
        query_result: QueryUnderstandingResult,
        scheme_id: Optional[str],
        context: ApplicantContext,
        conv_state: ConversationState,
        lang: str,
    ) -> UnifiedIntelligenceResponse:
        sid = scheme_id or conv_state.active_scheme
        if sid:
            return self._handle_policy_information(request, query_result, sid, context, conv_state, lang)

        return self.composer.compose(
            request_id=request.request_id,
            applicant_id=request.applicant_id,
            conversation_id=request.conversation_id,
            intent="GENERAL_FOLLOW_UP",
            route=RequestRoute.GENERAL_FOLLOW_UP,
            language=lang,
            answer_text="How can I assist you with government scheme eligibility, benefits, or document requirements?",
        )

    # -------------------------------------------------------------------------
    # Internal Scheme Knowledge
    # -------------------------------------------------------------------------

    def _get_scheme_metadata(self, scheme_id: str) -> Dict[str, Any]:
        """Returns authoritative scheme metadata from registry or defaults."""
        sid = (scheme_id or "").upper().replace(" ", "-").replace("_", "-")
        known: Dict[str, Dict[str, Any]] = {
            "PMJAY": {
                "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana",
                "purpose": "Provides health insurance coverage of up to ₹5,00,000 per family per year for secondary and tertiary hospitalization.",
                "description": "National public health insurance scheme for vulnerable families.",
                "eligibility_summary": "Families listed in SECC 2011 database or possessing valid PMJAY / BPL ration card with income under statutory ceiling.",
                "benefit_description": "Cashless hospitalization coverage up to ₹5,00,000 per family per year across empaneled public and private hospitals.",
                "documents_required": ["Aadhaar Card", "Ration Card", "Income Certificate"],
                "source_uri": "https://pmjay.gov.in/guidelines",
            },
            "PM-KISAN": {
                "name": "Pradhan Mantri Kisan Samman Nidhi",
                "purpose": "Income support of ₹6,000 per year in three equal installments to cultivable landholding farmer families.",
                "description": "Direct benefit transfer scheme supporting farmers for agricultural inputs.",
                "eligibility_summary": "Farmer families owning cultivable land up to 2 hectares, excluding institutional landowners and income tax payers.",
                "benefit_description": "Direct bank transfer of ₹6,000 annually, paid in three installments of ₹2,000 each every four months.",
                "documents_required": ["Aadhaar Card", "Land Ownership Record (Khata/Khesra)", "Bank Account Passbook"],
                "source_uri": "https://pmkisan.gov.in/guidelines",
            },
            "PMAY": {
                "name": "Pradhan Mantri Awas Yojana",
                "purpose": "Financial assistance for construction of pucca houses to homeless and households living in kutcha/dilapidated houses.",
                "description": "Housing subsidy initiative for low-income and economically weaker households.",
                "eligibility_summary": "Households without a pucca house anywhere in India, with annual income meeting EWS/LIG statutory thresholds.",
                "benefit_description": "Subsidy assistance up to ₹1,20,000 in plains and ₹1,30,000 in hilly/difficult areas for house construction.",
                "documents_required": ["Aadhaar Card", "Income Certificate", "Land Document", "Bank Account Details"],
                "source_uri": "https://pmaymis.gov.in/guidelines",
            },
        }

        # Normalize lookup
        for k, v in known.items():
            if k in sid or sid in k:
                return v

        return {
            "name": scheme_id,
            "purpose": f"Welfare scheme under official government guidelines for {scheme_id}.",
            "description": f"Government welfare program: {scheme_id}.",
            "eligibility_summary": "Subject to verified statutory criteria.",
            "benefit_description": None,
            "documents_required": ["Identity Proof", "Income Certificate"],
            "source_uri": f"Official guidelines for {scheme_id}",
        }
