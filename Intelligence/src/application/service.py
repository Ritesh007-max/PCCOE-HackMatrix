"""
Application Workflow Service.
Phase 10: Central case workflow orchestrator around existing Phase 8 AI Pipeline,
RuleEvaluator, EligibilityEngine, and BenefitCalculator.
"""

from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

from .status import (
    ApplicationStatus,
    StatutoryDecision,
    ReadinessStatus,
    ActionType,
    ActionPriority,
    ReviewStatus,
    ReviewReason,
    EventType,
)
from .case import (
    ApplicationCase,
    DocumentReference,
    FactSnapshot,
    SchemeEvaluation,
    generate_application_id,
    current_iso_timestamp,
)
from .decision import DecisionSnapshot, generate_snapshot_id
from .lifecycle import ApplicationStateMachine
from .readiness import ApplicationReadinessEvaluator, DocumentCompletenessReport
from .actions import NextAction, NextActionEngine
from .history import HistoryEvent, ApplicationHistoryManager
from .review import ReviewCase, ReviewManager
from .repository import ApplicationRepository, InMemoryApplicationRepository
from .exceptions import (
    ApplicationNotFoundError,
    DocumentNotFoundError,
    InvalidStateTransitionError,
    ImmutableSnapshotError,
    WorkflowError,
)

# Phase 3 & 4 domain models
from src.rules.models import ApplicantProfile, RuleStatus
from src.rules.evaluator import RuleEvaluator
from src.eligibility.engine import EligibilityEngine
from src.benefits.calculator import BenefitCalculator, BenefitResult
from src.data_pipeline.snapshot import SnapshotManager
from src.documents.models import DocumentContent
from src.pipelines.application_pipeline import ApplicationPipeline, ApplicationResult

logger = logging.getLogger("fin.application.service")


class ApplicationWorkflowService:
    """
    Central orchestrator coordinating application cases, document references,
    applicant profiles, scheme evaluations, readiness signals, and immutable audit snapshots.
    Delegates heavy intelligence tasks directly to Phase 8 ApplicationPipeline.
    """

    def __init__(
        self,
        repository: Optional[ApplicationRepository] = None,
        history_manager: Optional[ApplicationHistoryManager] = None,
        review_manager: Optional[ReviewManager] = None,
        pipeline: Optional[ApplicationPipeline] = None,
        eligibility_engine: Optional[EligibilityEngine] = None,
        benefit_calculator: Optional[BenefitCalculator] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
    ):
        self.repository = repository or InMemoryApplicationRepository()
        self.history_manager = history_manager or ApplicationHistoryManager()
        self.review_manager = review_manager or ReviewManager()
        self._pipeline = pipeline
        self._eligibility_engine = eligibility_engine
        self._benefit_calculator = benefit_calculator or BenefitCalculator()
        self._snapshot_manager = snapshot_manager
        self._idempotency_cache: Dict[str, str] = {}

    @property
    def pipeline(self) -> ApplicationPipeline:
        """Lazy-loaded Phase 8 ApplicationPipeline."""
        if self._pipeline is None:
            self._pipeline = ApplicationPipeline(benefit_calculator=self._benefit_calculator)
        return self._pipeline

    @property
    def eligibility_engine(self) -> EligibilityEngine:
        """Lazy-loaded deterministic EligibilityEngine."""
        if self._eligibility_engine is None:
            rules_dir = Path(__file__).resolve().parents[2] / "data" / "schemes" / "rules" / "examples"
            if not rules_dir.exists():
                rules_dir = Path(__file__).resolve().parents[2] / "data" / "rules"
            self._eligibility_engine = EligibilityEngine(rules_dir=rules_dir if rules_dir.exists() else None)
        return self._eligibility_engine

    def get_active_policy_version(self) -> str:
        """Determine active policy snapshot version from data pipeline."""
        try:
            if self._snapshot_manager is None:
                self._snapshot_manager = SnapshotManager()
            active_id = self._snapshot_manager.get_active_snapshot_id()
            if active_id:
                return active_id
        except Exception:
            pass

        # Fallback to active_version.json if directly accessible
        active_json = Path(__file__).resolve().parents[2] / "data" / "snapshots" / "active_version.json"
        if active_json.exists():
            try:
                import json
                with open(active_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("active_snapshot", "snapshot_20260921_193823")
            except Exception:
                pass
        return "snapshot_20260921_193823"

    # -------------------------------------------------------------------------
    # 1. APPLICATION CASE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_application(
        self,
        citizen_reference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> ApplicationCase:
        """
        Initializes a new application case in DRAFT status.
        """
        app_id = generate_application_id()
        case = ApplicationCase(
            application_id=app_id,
            citizen_reference=citizen_reference,
            current_status=ApplicationStatus.DRAFT,
            metadata=dict(metadata or {}),
        )

        self.repository.save(case)

        event = self.history_manager.record_event(
            application_id=app_id,
            event_type=EventType.APPLICATION_CREATED,
            actor="CITIZEN" if citizen_reference else "SYSTEM",
            new_state=ApplicationStatus.DRAFT.value,
            request_id=request_id,
            metadata={"citizen_reference": citizen_reference},
        )
        self.repository.append_history(event)

        logger.info("Created application case '%s' in status DRAFT", app_id)
        return case

    def get_application_state(self, application_id: str) -> ApplicationCase:
        """
        Retrieve the latest state of an application case.
        """
        case = self.repository.get(application_id)
        if not case:
            raise ApplicationNotFoundError(application_id)
        return case

    # -------------------------------------------------------------------------
    # 2. DOCUMENT ATTACHMENT
    # -------------------------------------------------------------------------

    def attach_document(
        self,
        application_id: str,
        filename: str,
        document_type: str = "UNKNOWN",
        content_bytes: Optional[bytes] = None,
        file_path: Optional[Union[str, Path]] = None,
        provenance_refs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> DocumentReference:
        """
        Attaches a document reference to the application case.
        Does NOT store raw bytes inside the case aggregate.
        """
        case = self.get_application_state(application_id)

        # Compute sha256
        sha256 = ""
        if content_bytes:
            sha256 = hashlib.sha256(content_bytes).hexdigest()
        elif file_path:
            p = Path(file_path)
            if p.exists() and p.is_file():
                sha256 = hashlib.sha256(p.read_bytes()).hexdigest()

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc_ref = DocumentReference(
            document_id=doc_id,
            filename=filename,
            document_type=document_type,
            sha256_hash=sha256,
            processing_status="PENDING",
            provenance_refs=list(provenance_refs or []),
            metadata=dict(metadata or {}),
        )

        case.attach_document(doc_ref)

        # Transition DRAFT -> DOCUMENTS_PENDING if currently DRAFT
        if case.current_status == ApplicationStatus.DRAFT:
            ApplicationStateMachine.validate_transition(case.current_status, ApplicationStatus.DOCUMENTS_PENDING)
            old_st = case.current_status
            case.current_status = ApplicationStatus.DOCUMENTS_PENDING
            event = self.history_manager.record_event(
                application_id=application_id,
                event_type=EventType.DOCUMENT_ADDED,
                old_state=old_st.value,
                new_state=case.current_status.value,
                request_id=request_id,
                metadata={"document_id": doc_id, "filename": filename, "type": document_type},
            )
            self.repository.append_history(event)
        else:
            event = self.history_manager.record_event(
                application_id=application_id,
                event_type=EventType.DOCUMENT_ADDED,
                request_id=request_id,
                metadata={"document_id": doc_id, "filename": filename, "type": document_type},
            )
            self.repository.append_history(event)

        self.repository.update(case)
        return doc_ref

    # -------------------------------------------------------------------------
    # 3. DOCUMENT & PIPELINE PROCESSING (Phase 8 Integration)
    # -------------------------------------------------------------------------

    def process_documents(
        self,
        application_id: str,
        document_inputs: List[Union[str, Path, bytes, DocumentContent]],
        user_query: Optional[str] = None,
        target_scheme: Optional[str] = None,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ApplicationCase:
        """
        Executes the Phase 8 ApplicationPipeline on attached documents, extracts facts,
        evaluates candidate schemes, computes benefits, readiness, and next actions.
        """
        # Idempotency check
        if idempotency_key and idempotency_key in self._idempotency_cache:
            cached_app_id = self._idempotency_cache[idempotency_key]
            logger.info("Idempotent request with key '%s' returning existing case '%s'", idempotency_key, cached_app_id)
            return self.get_application_state(cached_app_id)

        case = self.get_application_state(application_id)

        # Validate transition to PROCESSING
        ApplicationStateMachine.validate_transition(case.current_status, ApplicationStatus.PROCESSING)
        old_state = case.current_status
        case.current_status = ApplicationStatus.PROCESSING

        evt_proc = self.history_manager.record_event(
            application_id=application_id,
            event_type=EventType.DOCUMENT_PROCESSED,
            old_state=old_state.value,
            new_state=ApplicationStatus.PROCESSING.value,
            request_id=request_id,
            metadata={"num_documents": len(document_inputs)},
        )
        self.repository.append_history(evt_proc)

        # Run Phase 8 pipeline
        pipeline_result: ApplicationResult = self.pipeline.process_application(
            documents=document_inputs,
            user_query=user_query,
            target_scheme=target_scheme,
            session_id=application_id,
        )

        # 1. Update Document References Status
        for doc_info in pipeline_result.documents_processed:
            fname = doc_info.get("filename", "")
            for d in case.documents.values():
                if d.filename == fname or (d.sha256_hash and d.sha256_hash == doc_info.get("sha256")):
                    d.processing_status = "PROCESSED"
                    d.document_type = doc_info.get("document_type", d.document_type)

        # 2. Populate Normalized Facts & Conflicts
        conflicts = list(pipeline_result.conflicts_detected)
        missing_fields = list(pipeline_result.missing_information.get("missing_fields", []))

        case.facts = FactSnapshot(
            facts=dict(pipeline_result.applicant_profile),
            conflicted_fields=conflicts,
            missing_fields=missing_fields,
            snapshot_timestamp=current_iso_timestamp(),
        )

        case.current_status = ApplicationStatus.FACTS_READY

        if conflicts:
            evt_conflict = self.history_manager.record_event(
                application_id=application_id,
                event_type=EventType.CONFLICT_DETECTED,
                request_id=request_id,
                metadata={"conflicted_fields": conflicts},
            )
            self.repository.append_history(evt_conflict)

        # 3. Populate Candidate Scheme Evaluations
        active_policy_version = self.get_active_policy_version()
        candidate_evaluations: Dict[str, SchemeEvaluation] = {}

        for rank, scheme_meta in enumerate(pipeline_result.retrieved_schemes, start=1):
            s_id = scheme_meta.get("scheme_id") or scheme_meta.get("id", f"scheme_{rank}")
            s_name = scheme_meta.get("scheme_name") or scheme_meta.get("name", "Unknown Scheme")
            relevance = float(scheme_meta.get("relevance_score") or scheme_meta.get("similarity_score", 0.0))

            # Default evaluation
            s_eval = SchemeEvaluation(
                scheme_id=s_id,
                scheme_name=s_name,
                retrieval_relevance_score=relevance,
                retrieval_rank=rank,
                decision_status=StatutoryDecision.UNKNOWN,
                policy_snapshot_version=active_policy_version,
            )
            candidate_evaluations[s_id] = s_eval

        # 4. Integrate Primary Evaluated Scheme
        primary_eval = pipeline_result.eligibility_decision
        if primary_eval and primary_eval.get("scheme_id"):
            prim_id = primary_eval["scheme_id"]
            status_str = primary_eval.get("status", "UNKNOWN")
            stat_decision = StatutoryDecision(status_str) if status_str in StatutoryDecision.__members__ else StatutoryDecision.UNKNOWN

            # Benefit calculation
            benefit_summary = None
            if pipeline_result.benefit_calculation:
                b_calc = pipeline_result.benefit_calculation
                benefit_summary = {
                    "status": b_calc.get("status"),
                    "amount": b_calc.get("amount"),
                    "type": b_calc.get("benefit_type"),
                    "formula_id": b_calc.get("formula_id"),
                }

            s_eval = SchemeEvaluation(
                scheme_id=prim_id,
                scheme_name=primary_eval.get("scheme_name", "Primary Scheme"),
                retrieval_relevance_score=1.0,
                retrieval_rank=1,
                decision_status=stat_decision,
                is_eligible=bool(primary_eval.get("eligible", False)),
                matched_rules=primary_eval.get("passed_rules", []),
                failed_rules=primary_eval.get("failed_rules", []),
                unknown_rules=primary_eval.get("unknown_rules", []),
                conflicted_fields=conflicts,
                missing_fields=missing_fields,
                benefit_summary=benefit_summary,
                policy_snapshot_version=active_policy_version,
            )
            candidate_evaluations[prim_id] = s_eval
            case.selected_scheme_id = prim_id

        case.candidate_schemes = candidate_evaluations
        case.current_status = ApplicationStatus.ELIGIBILITY_EVALUATED

        # 5. Evaluate Readiness
        selected_eval = case.get_selected_evaluation()
        req_docs: List[str] = []
        if selected_eval:
            req_docs = pipeline_result.missing_information.get("missing_documents", [])

        doc_report = ApplicationReadinessEvaluator.evaluate_document_completeness(
            required_document_types=req_docs,
            attached_documents=list(case.documents.values()),
        )
        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=selected_eval,
            required_documents=req_docs,
        )
        case.readiness = readiness

        # 6. Generate Next Actions
        actions = NextActionEngine.generate_actions(
            case=case,
            target_evaluation=selected_eval,
            doc_report=doc_report,
        )
        case.next_actions = [a.to_dict() for a in actions]

        # 7. Create Decision Snapshot
        if selected_eval:
            snapshot = self._build_decision_snapshot(
                case=case,
                evaluation=selected_eval,
                policy_version=active_policy_version,
                reason="DOCUMENT_PIPELINE_EVALUATION",
            )
            self.repository.save_decision_snapshot(snapshot)
            case.active_decision_snapshot_id = snapshot.snapshot_id

        # 8. Set Final Lifecycle State based on Readiness / Conflicts
        old_eval_state = case.current_status
        if conflicts or (selected_eval and selected_eval.decision_status == StatutoryDecision.REVIEW):
            case.current_status = ApplicationStatus.UNDER_REVIEW
            # Create manual review case
            self.review_manager.create_review(
                application_id=application_id,
                reason=ReviewReason.FACT_CONFLICT if conflicts else ReviewReason.UNSTRUCTURED_RULE,
                scheme_id=selected_eval.scheme_id if selected_eval else None,
                conflicting_fields=conflicts,
                unresolved_rules=[r.get("rule_id", str(r)) if isinstance(r, dict) else str(r) for r in selected_eval.unknown_rules] if selected_eval else [],
            )
        elif readiness == ReadinessStatus.READY_TO_APPLY:
            case.current_status = ApplicationStatus.READY_TO_APPLY
        elif readiness == ReadinessStatus.ACTION_REQUIRED:
            case.current_status = ApplicationStatus.ACTION_REQUIRED
        else:
            case.current_status = ApplicationStatus.ELIGIBILITY_EVALUATED

        evt_final = self.history_manager.record_event(
            application_id=application_id,
            event_type=EventType.ELIGIBILITY_EVALUATED,
            old_state=old_eval_state.value,
            new_state=case.current_status.value,
            request_id=request_id,
            metadata={
                "readiness": readiness.value,
                "decision": selected_eval.decision_status.value if selected_eval else "UNKNOWN",
                "snapshot_id": case.active_decision_snapshot_id,
            },
        )
        self.repository.append_history(evt_final)

        # Cache idempotency key
        if idempotency_key:
            self._idempotency_cache[idempotency_key] = application_id

        self.repository.update(case)
        return case

    # -------------------------------------------------------------------------
    # 4. PROFILE UPDATE & DIRECT EVALUATION
    # -------------------------------------------------------------------------

    def update_applicant_profile(
        self,
        application_id: str,
        facts: Dict[str, Any],
        conflicted_fields: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> ApplicationCase:
        """
        Directly update or supplement applicant profile facts.
        """
        case = self.get_application_state(application_id)

        merged_facts = dict(case.facts.facts)
        merged_facts.update(facts)

        existing_conflicts = set(case.facts.conflicted_fields)
        if conflicted_fields:
            existing_conflicts.update(conflicted_fields)

        case.facts = FactSnapshot(
            facts=merged_facts,
            verification_status=case.facts.verification_status,
            evidence_references=case.facts.evidence_references,
            conflicted_fields=list(existing_conflicts),
            missing_fields=[f for f in case.facts.missing_fields if f not in merged_facts],
            snapshot_timestamp=current_iso_timestamp(),
        )

        # Validate and transition state to FACTS_READY if in DRAFT or DOCUMENTS_PENDING
        if case.current_status in (ApplicationStatus.DRAFT, ApplicationStatus.DOCUMENTS_PENDING):
            case.current_status = ApplicationStatus.FACTS_READY

        evt = self.history_manager.record_event(
            application_id=application_id,
            event_type=EventType.FACTS_UPDATED,
            request_id=request_id,
            metadata={"updated_fields": list(facts.keys())},
        )
        case.updated_at = current_iso_timestamp()
        self.repository.append_history(evt)
        self.repository.update(case)
        return case

    def evaluate_scheme(
        self,
        application_id: str,
        scheme_id: str,
        scheme_name: str = "",
        required_documents: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> SchemeEvaluation:
        """
        Evaluates a specific scheme against the application's current facts.
        Generates an immutable DecisionSnapshot.
        """
        case = self.get_application_state(application_id)
        profile = ApplicantProfile(
            data=case.facts.facts,
            conflicts=case.facts.conflicted_fields,
        )

        active_policy_version = self.get_active_policy_version()

        # Deterministic evaluation via EligibilityEngine or RuleEvaluator
        try:
            decision = self.eligibility_engine.evaluate(scheme_id, profile)
            stat_decision = StatutoryDecision(decision.status.value)
            is_elig = bool(decision.eligible)
            matched = [r.to_dict() for r in decision.rule_results if r.status == RuleStatus.PASS]
            failed = [r.to_dict() for r in decision.rule_results if r.status == RuleStatus.FAIL]
            unknown = [r.to_dict() for r in decision.rule_results if r.status == RuleStatus.UNKNOWN]
            missing_fields = decision.missing_fields
        except Exception as e:
            logger.warning("Eligibility engine evaluation failed for '%s', marking UNKNOWN: %s", scheme_id, e)
            stat_decision = StatutoryDecision.UNKNOWN
            is_elig = False
            matched = []
            failed = []
            unknown = []
            missing_fields = []

        # Benefit calculation if eligible
        benefit_summary = None
        if stat_decision == StatutoryDecision.PASS:
            b_res: BenefitResult = self._benefit_calculator.calculate(
                scheme_id=scheme_id,
                scheme_name=scheme_name or scheme_id,
                applicant_facts=case.facts.facts,
            )
            if b_res:
                benefit_summary = b_res.to_dict()

        active_rule_version = "1.0.0"
        try:
            rs = self.eligibility_engine.get_ruleset(scheme_id)
            if rs and rs.version:
                active_rule_version = rs.version
        except Exception:
            pass

        evaluation = SchemeEvaluation(
            scheme_id=scheme_id,
            scheme_name=scheme_name or scheme_id,
            retrieval_relevance_score=1.0,
            decision_status=stat_decision,
            is_eligible=is_elig,
            matched_rules=matched,
            failed_rules=failed,
            unknown_rules=unknown,
            conflicted_fields=case.facts.conflicted_fields,
            missing_fields=missing_fields,
            benefit_summary=benefit_summary,
            policy_snapshot_version=active_policy_version,
            rule_version=active_rule_version,
        )

        case.candidate_schemes[scheme_id] = evaluation
        case.selected_scheme_id = scheme_id

        # Update readiness and actions
        req_docs = required_documents or []
        doc_report = ApplicationReadinessEvaluator.evaluate_document_completeness(
            required_document_types=req_docs,
            attached_documents=list(case.documents.values()),
        )
        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=evaluation,
            required_documents=req_docs,
        )
        case.readiness = readiness
        actions = NextActionEngine.generate_actions(
            case=case,
            target_evaluation=evaluation,
            doc_report=doc_report,
        )
        case.next_actions = [a.to_dict() for a in actions]

        # Create Decision Snapshot
        snapshot = self._build_decision_snapshot(
            case=case,
            evaluation=evaluation,
            policy_version=active_policy_version,
            reason="SCHEME_EVALUATION",
        )
        self.repository.save_decision_snapshot(snapshot)
        case.active_decision_snapshot_id = snapshot.snapshot_id

        # Update lifecycle status
        if case.facts.conflicted_fields or stat_decision == StatutoryDecision.REVIEW:
            case.current_status = ApplicationStatus.UNDER_REVIEW
        elif readiness == ReadinessStatus.READY_TO_APPLY:
            case.current_status = ApplicationStatus.READY_TO_APPLY
        elif readiness == ReadinessStatus.ACTION_REQUIRED:
            case.current_status = ApplicationStatus.ACTION_REQUIRED
        else:
            case.current_status = ApplicationStatus.ELIGIBILITY_EVALUATED

        evt = self.history_manager.record_event(
            application_id=application_id,
            event_type=EventType.ELIGIBILITY_EVALUATED,
            request_id=request_id,
            metadata={
                "scheme_id": scheme_id,
                "decision": stat_decision.value,
                "snapshot_id": snapshot.snapshot_id,
            },
        )
        self.repository.append_history(evt)
        self.repository.update(case)

        return evaluation

    # -------------------------------------------------------------------------
    # 5. RE-EVALUATION WORKFLOW (Immutability Preserved)
    # -------------------------------------------------------------------------

    def reevaluate_application(
        self,
        application_id: str,
        reason: str = "POLICY_OR_EVIDENCE_UPDATE",
        force_policy_version: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> ApplicationCase:
        """
        Re-evaluates an application upon new policy version or updated applicant facts.
        CRITICAL: Creates a NEW DecisionSnapshot (V2, V3...) and NEVER overwrites historical V1 snapshots.
        """
        case = self.get_application_state(application_id)
        selected_eval = case.get_selected_evaluation()
        if not selected_eval:
            raise WorkflowError("Cannot re-evaluate application: No candidate schemes have been evaluated.")

        scheme_id = selected_eval.scheme_id
        policy_version = force_policy_version or self.get_active_policy_version()

        # Determine next version index
        existing_snapshots = self.repository.list_decision_snapshots(application_id)
        next_version = len(existing_snapshots) + 1

        # Re-run rule evaluation
        profile = ApplicantProfile(
            data=case.facts.facts,
            conflicts=case.facts.conflicted_fields,
        )

        try:
            decision = self.eligibility_engine.evaluate(scheme_id, profile)
            stat_decision = StatutoryDecision(decision.status.value)
            is_elig = bool(decision.eligible)
            matched = [r.to_dict() for r in decision.rule_results if r.status == RuleStatus.PASS]
            failed = [r.to_dict() for r in decision.rule_results if r.status == RuleStatus.FAIL]
            unknown = [r.to_dict() for r in decision.rule_results if r.status == RuleStatus.UNKNOWN]
            missing_fields = decision.missing_fields
        except Exception:
            stat_decision = selected_eval.decision_status
            is_elig = selected_eval.is_eligible
            matched = selected_eval.matched_rules
            failed = selected_eval.failed_rules
            unknown = selected_eval.unknown_rules
            missing_fields = selected_eval.missing_fields

        benefit_summary = None
        if stat_decision == StatutoryDecision.PASS:
            b_res = self._benefit_calculator.calculate(
                scheme_id=scheme_id,
                scheme_name=selected_eval.scheme_name,
                applicant_facts=case.facts.facts,
            )
            if b_res:
                benefit_summary = b_res.to_dict()

        # Update evaluation record
        updated_eval = SchemeEvaluation(
            scheme_id=scheme_id,
            scheme_name=selected_eval.scheme_name,
            retrieval_relevance_score=selected_eval.retrieval_relevance_score,
            retrieval_rank=selected_eval.retrieval_rank,
            decision_status=stat_decision,
            is_eligible=is_elig,
            matched_rules=matched,
            failed_rules=failed,
            unknown_rules=unknown,
            conflicted_fields=case.facts.conflicted_fields,
            missing_fields=missing_fields,
            benefit_summary=benefit_summary,
            policy_snapshot_version=policy_version,
            rule_version=selected_eval.rule_version,
            evaluated_at=current_iso_timestamp(),
        )
        case.candidate_schemes[scheme_id] = updated_eval

        # Create NEW Decision Snapshot
        new_snapshot = DecisionSnapshot(
            application_id=application_id,
            scheme_id=scheme_id,
            scheme_name=selected_eval.scheme_name,
            applicant_fact_snapshot=dict(case.facts.facts),
            policy_snapshot_version=policy_version,
            rule_version=selected_eval.rule_version,
            decision_status=stat_decision,
            is_eligible=is_elig,
            matched_rules=matched,
            failed_rules=failed,
            unknown_rules=unknown,
            benefit_result=benefit_summary,
            version_index=next_version,
            reason_for_evaluation=reason,
        )

        self.repository.save_decision_snapshot(new_snapshot)
        case.active_decision_snapshot_id = new_snapshot.snapshot_id

        # Re-compute readiness and next actions
        readiness = ApplicationReadinessEvaluator.evaluate_readiness(case=case, target_evaluation=updated_eval)
        case.readiness = readiness
        actions = NextActionEngine.generate_actions(case=case, target_evaluation=updated_eval)
        case.next_actions = [a.to_dict() for a in actions]

        evt = self.history_manager.record_event(
            application_id=application_id,
            event_type=EventType.APPLICATION_REEVALUATED,
            request_id=request_id,
            metadata={
                "reason": reason,
                "version_index": next_version,
                "snapshot_id": new_snapshot.snapshot_id,
                "policy_version": policy_version,
            },
        )
        self.repository.append_history(evt)
        self.repository.update(case)

        logger.info(
            "Re-evaluated application '%s': Created snapshot %s (version %d, policy %s)",
            application_id, new_snapshot.snapshot_id, next_version, policy_version
        )
        return case

    # -------------------------------------------------------------------------
    # 6. MANUAL REVIEW
    # -------------------------------------------------------------------------

    def request_manual_review(
        self,
        application_id: str,
        reason: ReviewReason,
        scheme_id: Optional[str] = None,
        conflicting_fields: Optional[List[str]] = None,
        unresolved_rules: Optional[List[str]] = None,
        supporting_documents: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> ReviewCase:
        """
        Creates a structured manual review case for human caseworker intervention.
        """
        case = self.get_application_state(application_id)

        review = self.review_manager.create_review(
            application_id=application_id,
            reason=reason,
            scheme_id=scheme_id or case.selected_scheme_id,
            conflicting_fields=conflicting_fields or case.facts.conflicted_fields,
            unresolved_rules=unresolved_rules,
            supporting_documents=supporting_documents or list(case.documents.keys()),
        )
        self.repository.save_review_case(review)

        # Transition application to UNDER_REVIEW if permitted
        if case.current_status != ApplicationStatus.UNDER_REVIEW:
            try:
                ApplicationStateMachine.validate_transition(case.current_status, ApplicationStatus.UNDER_REVIEW)
                old_st = case.current_status
                case.current_status = ApplicationStatus.UNDER_REVIEW
                evt = self.history_manager.record_event(
                    application_id=application_id,
                    event_type=EventType.MANUAL_REVIEW_REQUESTED,
                    old_state=old_st.value,
                    new_state=ApplicationStatus.UNDER_REVIEW.value,
                    request_id=request_id,
                    metadata={"review_id": review.review_id, "reason": reason.value},
                )
                self.repository.append_history(evt)
                self.repository.update(case)
            except InvalidStateTransitionError as err:
                logger.warning("Could not transition to UNDER_REVIEW: %s", err)

        return review

    # -------------------------------------------------------------------------
    # 7. INTERNAL HELPERS
    # -------------------------------------------------------------------------

    def _build_decision_snapshot(
        self,
        case: ApplicationCase,
        evaluation: SchemeEvaluation,
        policy_version: str,
        reason: str,
    ) -> DecisionSnapshot:
        """Constructs an immutable DecisionSnapshot instance."""
        existing_snaps = self.repository.list_decision_snapshots(case.application_id)
        ver_index = len(existing_snaps) + 1

        return DecisionSnapshot(
            application_id=case.application_id,
            scheme_id=evaluation.scheme_id,
            scheme_name=evaluation.scheme_name,
            applicant_fact_snapshot=dict(case.facts.facts),
            policy_snapshot_version=policy_version,
            rule_version=evaluation.rule_version,
            decision_status=evaluation.decision_status,
            is_eligible=evaluation.is_eligible,
            matched_rules=evaluation.matched_rules,
            failed_rules=evaluation.failed_rules,
            unknown_rules=evaluation.unknown_rules,
            review_fields=evaluation.conflicted_fields,
            benefit_result=evaluation.benefit_summary,
            version_index=ver_index,
            reason_for_evaluation=reason,
        )
