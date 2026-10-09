"""
FIN Applicant Context & Fact Query Service.
Coordinates canonical fact extraction, multi-document evidence reconciliation,
structured persistence, and deterministic context assembly for downstream Intelligence layers.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
    CANONICAL_PROFILE_FIELDS,
)
from src.normalization.normalizer import normalize_field_value
from src.documents.models import DocumentContent
from src.context.models import DocumentContext, ApplicantContext
from src.context.fact_mapper import canonicalize_fact_key, extract_document_canonical_facts
from src.persistence.repository import FactPersistenceRepository, PersistenceError

logger = logging.getLogger("fin.context.service")


class ApplicantContextService:
    """
    Authoritative service managing citizen facts, multi-document evidence,
    and unified ApplicantContext assembly.
    """

    def __init__(self, repository: Optional[FactPersistenceRepository] = None):
        self.repository = repository or FactPersistenceRepository()

    def process_and_store_document(
        self,
        doc_content: DocumentContent,
        applicant_id: str = "default_applicant",
    ) -> Tuple[DocumentContext, List[ApplicantFact], List[Evidence]]:
        """
        Coordinates statutory extraction, block-level provenance mapping,
        idempotency checking, and transactional persistence.
        """
        if not applicant_id:
            applicant_id = "default_applicant"

        # 1. Idempotency check: see if file with identical SHA-256 is already stored for this applicant
        existing_doc = self.repository.get_document_by_hash(applicant_id, doc_content.sha256)
        if existing_doc:
            logger.info(
                "Document %s (hash %s) already processed for applicant %s. Reusing canonical facts.",
                doc_content.file_name,
                doc_content.sha256[:12],
                applicant_id,
            )
            return (existing_doc, existing_doc.extracted_facts, existing_doc.evidence)

        # 2. Extract statutory facts and bind block-level OCR / native provenance
        facts, evidence_list, raw_fields = extract_document_canonical_facts(doc_content, applicant_id)

        # 3. Create structured DocumentContext
        doc_context = DocumentContext.from_document_content(
            doc_content=doc_content,
            applicant_id=applicant_id,
            facts=facts,
            evidence=evidence_list,
        )
        doc_context.metadata["raw_extracted_fields"] = raw_fields

        # 4. Transactionally persist document, facts, and evidence
        self.repository.save_document_facts_and_evidence(doc_context, facts, evidence_list)

        logger.info(
            "Persisted document %s (%d facts, %d evidence records) for applicant %s.",
            doc_content.file_name,
            len(facts),
            len(evidence_list),
            applicant_id,
        )

        return (doc_context, facts, evidence_list)

    def record_user_fact(
        self,
        applicant_id: str,
        fact_key: str,
        raw_value: Any,
        confidence: float = 1.0,
        source_type: FactSourceType = FactSourceType.USER_INPUT,
        verification_status: FactVerificationStatus = FactVerificationStatus.SELF_REPORTED,
        doc_type: Optional[str] = None,
        source_document: str = "user_declaration",
        page_number: Optional[int] = None,
        has_family_income: bool = False,
        file_name: Optional[str] = None,
    ) -> ApplicantFact:
        """
        Records an atomic citizen-provided fact (e.g. from chat conversation or profile declaration).
        Applies deterministic normalization and stores in persistence ledger.
        """
        if not applicant_id:
            raise ValueError("Applicant ID is required to record user facts.")

        canonical_key = canonicalize_fact_key(
            fact_key,
            doc_type=doc_type,
            has_family_income=has_family_income,
            file_name=file_name or source_document,
        )
        field_meta = CANONICAL_PROFILE_FIELDS.get(canonical_key)
        data_type = field_meta.get("data_type", "string") if field_meta else "string"

        normalized_val: Any = None
        try:
            normalized_val = normalize_field_value(canonical_key, raw_value, validate=False)
        except Exception:
            normalized_val = None

        fact = ApplicantFact(
            applicant_id=applicant_id,
            field=canonical_key,
            value=raw_value,
            normalized_value=normalized_val,
            data_type=data_type,
            confidence=confidence,
            source_type=source_type,
            source_document=source_document,
            page_number=page_number,
            extraction_method="MANUAL_ENTRY" if source_type == FactSourceType.USER_INPUT else "SYSTEM_INFERRED",
            verification_status=verification_status,
            metadata={"input_key": fact_key, "doc_type": doc_type} if doc_type else {"input_key": fact_key},
        )

        ev = Evidence(
            applicant_fact_id=fact.id,
            applicant_id=applicant_id,
            source_type=source_type,
            source_uri=source_document,
            page_number=page_number,
            confidence=confidence,
            verification_status=verification_status,
            metadata={"field": canonical_key, "raw_value": str(raw_value), "doc_type": str(doc_type)},
        )

        self.repository.save_fact(fact, ev)
        return fact

    def _sync_from_supabase(self, applicant_id: str) -> None:
        """Pulls authoritative profile and document facts directly from Supabase REST API (zero local database)."""
        import os
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_ROLE_KEY")
        if not supabase_url or not supabase_key or not applicant_id:
            return

        try:
            import httpx
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
            }
            with httpx.Client(timeout=4.0) as client:
                # 1. Fetch applicant profile from Supabase
                p_res = client.get(f"{supabase_url}/rest/v1/applicant_profiles?id=eq.{applicant_id}", headers=headers)
                if p_res.status_code == 200:
                    profiles = p_res.json()
                    if profiles:
                        prof = profiles[0]
                        for k, v in prof.items():
                            if v is not None and k not in ("id", "created_at", "updated_at"):
                                try:
                                    self.record_user_fact(
                                        applicant_id=applicant_id,
                                        fact_key=k,
                                        raw_value=v,
                                        confidence=1.0,
                                        source_type=FactSourceType.PROFILE,
                                        verification_status=FactVerificationStatus.SELF_REPORTED,
                                        source_document="applicant_profile",
                                    )
                                except Exception:
                                    pass

                # 2. Fetch applications & verified documents from Supabase
                apps_res = client.get(f"{supabase_url}/rest/v1/applications?applicant_id=eq.{applicant_id}&select=id", headers=headers)
                if apps_res.status_code == 200:
                    app_ids = [a["id"] for a in apps_res.json() if "id" in a]
                    query_part = f"application_id=in.({','.join(app_ids)})" if app_ids else "application_id=is.null"
                    docs_res = client.get(f"{supabase_url}/rest/v1/documents?{query_part}", headers=headers)
                    if docs_res.status_code == 200:
                        for d in docs_res.json():
                            remarks = d.get("reviewer_remarks")
                            doc_type = d.get("document_type")
                            file_name = d.get("file_name", "document.pdf")
                            if remarks:
                                import json
                                parsed = json.loads(remarks) if isinstance(remarks, str) else remarks
                                extracted = parsed.get("extractedFields") or parsed.get("fields") or {}
                                has_fam = (
                                    any(k in extracted for k in ("annual_family_income", "family_income", "father_income", "mother_income", "household_income", "parivar_aay"))
                                    or "income" in (doc_type or "").lower()
                                    or "income" in file_name.lower()
                                )
                                for fk, fv in extracted.items():
                                    if fv is not None:
                                        try:
                                            self.record_user_fact(
                                                applicant_id=applicant_id,
                                                fact_key=fk,
                                                raw_value=fv,
                                                confidence=0.95,
                                                source_type=FactSourceType.DOCUMENT,
                                                verification_status=FactVerificationStatus.EXTRACTED,
                                                doc_type=doc_type,
                                                source_document=file_name,
                                                has_family_income=has_fam,
                                                file_name=file_name,
                                            )
                                        except Exception:
                                            pass
        except Exception as e:
            logger.debug("Supabase sync notice for %s: %s", applicant_id, e)

    def get_applicant_context(self, applicant_id: str) -> ApplicantContext:
        """
        Assembles canonical ApplicantContext aggregating documents, facts,
        and evidence with deterministic multi-document conflict detection.
        Pulls dynamically from authoritative Supabase if not yet cached in-memory.
        """
        facts = self.repository.get_facts_for_applicant(applicant_id)
        if not facts and applicant_id and applicant_id != "default_applicant":
            self._sync_from_supabase(applicant_id)
            facts = self.repository.get_facts_for_applicant(applicant_id)

        docs = self.repository.get_applicant_documents(applicant_id)
        evidence = self.repository.get_evidence_for_applicant(applicant_id)

        context = ApplicantContext(
            applicant_id=applicant_id,
            all_facts=facts,
            evidence=evidence,
            documents=docs,
        )
        return context

    def get_fact(self, applicant_id: str, fact_key: str) -> Optional[ApplicantFact]:
        """
        Returns the single consolidated canonical fact for an applicant.
        Returns None if missing or conflicted.
        """
        ctx = self.get_applicant_context(applicant_id)
        canonical_key = canonicalize_fact_key(fact_key)
        return ctx.get_fact(canonical_key)

    def get_all_facts(self, applicant_id: str) -> List[ApplicantFact]:
        """Returns all atomic applicant facts recorded for this applicant."""
        return self.repository.get_facts_for_applicant(applicant_id)

    def get_fact_history(self, applicant_id: str, fact_key: str) -> List[ApplicantFact]:
        """Returns historical values and candidates across documents for a fact key."""
        canonical_key = canonicalize_fact_key(fact_key)
        return self.repository.get_fact_history(applicant_id, canonical_key)

    def get_conflicts(self, applicant_id: str) -> List[str]:
        """Returns list of all field keys currently in conflict."""
        ctx = self.get_applicant_context(applicant_id)
        return ctx.conflicts

    def get_evidence_for_applicant(self, applicant_id: str) -> List[Evidence]:
        """Returns all evidence records supporting applicant facts."""
        return self.repository.get_evidence_for_applicant(applicant_id)

    def delete_document(self, applicant_id: str, document_id: str) -> bool:
        """Deletes a document from the applicant repository."""
        return self.repository.delete_document(applicant_id, document_id)
