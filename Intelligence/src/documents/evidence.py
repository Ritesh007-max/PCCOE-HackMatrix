"""
FIN Evidence Aggregation & Conflict Detection Layer.
Manages multi-document evidence records, detects corroboration vs contradictions,
and bridges safely to the deterministic eligibility engine.
"""

from typing import Any, Dict, List, Optional, Set
import sys
from pathlib import Path

# Ensure Intelligence directory is on sys.path
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from ..extraction.models import (
        ApplicantFact,
        FactVerificationStatus,
        ExtractionMethod,
        CANONICAL_PROFILE_FIELDS,
    )
    from ..normalization.normalizer import normalize_field_value
    from ..normalization.validators import ValidationError
    from .provenance import DocumentProvenance
    from ..rules.models import ApplicantProfile
except (ImportError, ValueError):
    from src.extraction.models import (
        ApplicantFact,
        FactVerificationStatus,
        ExtractionMethod,
        CANONICAL_PROFILE_FIELDS,
    )
    from src.normalization.normalizer import normalize_field_value
    from src.normalization.validators import ValidationError
    from src.documents.provenance import DocumentProvenance
    from src.rules.models import ApplicantProfile


# Verification tier hierarchy for corroborating evidence
VERIFICATION_HIERARCHY = {
    FactVerificationStatus.UNKNOWN: 0,
    FactVerificationStatus.SELF_REPORTED: 1,
    FactVerificationStatus.EXTRACTED: 2,
    FactVerificationStatus.USER_CONFIRMED: 3,
    FactVerificationStatus.ISSUER_VERIFIED: 4,
}


class EvidenceRegistry:
    """
    Registry for gathering facts across multiple documents.
    Enforces deterministic conflict detection and the invariant:
    'UNKNOWN or CONFLICTED facts must never be converted into PASS;
     conflicting facts must produce REVIEW.'
    """

    def __init__(self, applicant_id: str = "applicant_default"):
        self.applicant_id: str = applicant_id
        # Key: field_name -> List of all facts submitted across all documents
        self.evidence_by_field: Dict[str, List[ApplicantFact]] = {}
        # Set of fields that are in conflict across documents
        self.conflicted_fields: Set[str] = set()

    def add_fact(self, fact: ApplicantFact) -> None:
        """
        Adds an existing ApplicantFact to the registry.
        Triggers conflict detection across all documents for the fact's field.
        """
        field_name = fact.field
        if field_name not in self.evidence_by_field:
            self.evidence_by_field[field_name] = []

        self.evidence_by_field[field_name].append(fact)
        self._reconcile_field(field_name)

    def record_fact(
        self,
        field: str,
        value: Any,
        source_document: str,
        page_number: Optional[int] = None,
        text_span: Optional[str] = None,
        extraction_method: str = ExtractionMethod.EXTRACTED.value,
        verification_status: FactVerificationStatus = FactVerificationStatus.EXTRACTED,
        confidence: float = 1.0,
        provenance: Optional[DocumentProvenance] = None,
        normalize: bool = True,
        validate: bool = True
    ) -> ApplicantFact:
        """
        Constructs, normalizes, validates, and registers an applicant fact.
        Preserves original extracted value and text span verbatim.
        """
        # Determine data_type from canonical field definitions if available
        field_meta = CANONICAL_PROFILE_FIELDS.get(field, {})
        data_type = field_meta.get("data_type", "string")

        # Normalize if requested
        if normalize:
            try:
                normalized_value = normalize_field_value(field, value, validate=validate)
            except ValidationError:
                # If validation fails due to impossible value (e.g. age = -5, income = -1000),
                # we re-raise or record with validation error
                raise
        else:
            normalized_value = value

        # Metadata from provenance if provided
        metadata: Dict[str, Any] = {}
        if provenance:
            metadata["provenance"] = provenance.to_dict()

        fact = ApplicantFact(
            field=field,
            value=value,
            normalized_value=normalized_value,
            data_type=data_type,
            confidence=confidence,
            source_document=source_document,
            page_number=page_number,
            text_span=text_span,
            extraction_method=extraction_method,
            verification_status=verification_status,
            metadata=metadata,
        )

        self.add_fact(fact)
        return fact

    def _reconcile_field(self, field_name: str) -> None:
        """
        Evaluates all facts recorded for a field across documents.
        If all facts with valid normalized values agree, the evidence is corroborating.
        If facts provide discordant normalized values, marks the field as CONFLICTED.
        NEVER silently selects one value.
        """
        facts = self.evidence_by_field.get(field_name, [])
        if not facts:
            return

        # Check for explicit pre-existing CONFLICTED status
        for f in facts:
            if f.verification_status == FactVerificationStatus.CONFLICTED:
                self.conflicted_fields.add(field_name)
                return

        # Collect distinct non-None normalized values
        distinct_values: List[Any] = []
        for f in facts:
            val = f.normalized_value
            if val is not None:
                # Compare value with distinct_values
                already_present = any(self._values_match(val, existing) for existing in distinct_values)
                if not already_present:
                    distinct_values.append(val)

        if len(distinct_values) > 1:
            # CONFLICT DETECTED!
            # Example: Document A (420000) vs Document B (610000)
            self.conflicted_fields.add(field_name)
            # Mark all constituent facts as CONFLICTED
            for f in facts:
                f.verification_status = FactVerificationStatus.CONFLICTED
        elif len(distinct_values) == 1:
            # Corroborating or duplicate evidence
            if field_name in self.conflicted_fields:
                self.conflicted_fields.remove(field_name)
        else:
            # All facts have normalized_value is None (UNKNOWN)
            pass

    @staticmethod
    def _values_match(v1: Any, v2: Any) -> bool:
        """Checks if two normalized values represent the identical statutory state."""
        if v1 == v2:
            return True
        # For numeric floats, allow small floating precision tolerance
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return abs(float(v1) - float(v2)) < 1e-6
        # String case-insensitive match
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip().lower() == v2.strip().lower()
        return False

    def has_conflict(self, field_name: str) -> bool:
        """Returns True if the field has contradictory evidence across documents."""
        return field_name in self.conflicted_fields

    def get_facts_for_field(self, field_name: str) -> List[ApplicantFact]:
        """Returns all raw and normalized facts recorded for a given field."""
        return list(self.evidence_by_field.get(field_name, []))

    def get_consolidated_fact(self, field_name: str) -> Optional[ApplicantFact]:
        """
        Returns the single consolidated fact for a field.
        If conflicted, returns a fact with CONFLICTED status.
        If missing, returns None.
        """
        facts = self.evidence_by_field.get(field_name, [])
        if not facts:
            return None

        if self.has_conflict(field_name):
            first = facts[0]
            return ApplicantFact(
                field=field_name,
                value=[f.value for f in facts],
                normalized_value=None,
                data_type=first.data_type,
                confidence=min(f.confidence for f in facts),
                source_document=", ".join(sorted({f.source_document for f in facts})),
                page_number=None,
                text_span=None,
                extraction_method="MULTI_DOCUMENT_CONSOLIDATION",
                verification_status=FactVerificationStatus.CONFLICTED,
                metadata={"conflicting_values": [f.to_dict() for f in facts]},
            )

        # Non-conflicted: select the highest verification status fact
        sorted_facts = sorted(
            facts,
            key=lambda f: (
                VERIFICATION_HIERARCHY.get(f.verification_status, 0),
                f.confidence
            ),
            reverse=True
        )
        return sorted_facts[0]

    def get_conflicted_fields(self) -> List[str]:
        """Returns sorted list of all fields currently in conflict."""
        return sorted(list(self.conflicted_fields))

    def get_all_source_documents(self) -> List[str]:
        """Returns unique list of all source documents cited in evidence."""
        docs: Set[str] = set()
        for fact_list in self.evidence_by_field.values():
            for f in fact_list:
                docs.add(f.source_document)
        return sorted(list(docs))

    def to_applicant_profile(self) -> ApplicantProfile:
        """
        Compiles the evidence registry into a deterministic ApplicantProfile
        directly consumable by the RuleEvaluator and EligibilityEngine.

        CRITICAL INVARIANTS ENFORCED:
        1. Conflicted fields are populated into `_conflicts`, causing RuleEvaluator
           to evaluate matching rules as REVIEW (never PASS).
        2. Missing fields remain omitted, causing RuleEvaluator to evaluate matching
           rules as UNKNOWN (never PASS, never FAIL).
        3. Never guesses, averages, or silently resolves contradictory evidence.
        """
        profile_data: Dict[str, Any] = {}

        for field_name, facts in self.evidence_by_field.items():
            if self.has_conflict(field_name):
                # Do NOT set valid value in profile_data for conflicted fields
                continue
            consolidated = self.get_consolidated_fact(field_name)
            if consolidated and consolidated.normalized_value is not None:
                profile_data[field_name] = consolidated.normalized_value

        return ApplicantProfile(
            data=profile_data,
            conflicts=sorted(list(self.conflicted_fields))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the evidence collection according to EVIDENCE_COLLECTION_SCHEMA."""
        flat_facts: List[Dict[str, Any]] = []
        for fact_list in self.evidence_by_field.values():
            for f in fact_list:
                flat_facts.append(f.to_dict())

        return {
            "applicant_id": self.applicant_id,
            "facts": flat_facts,
            "conflicts": sorted(list(self.conflicted_fields)),
            "source_documents": self.get_all_source_documents(),
        }
