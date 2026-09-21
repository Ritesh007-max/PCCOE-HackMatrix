"""
PolicySetu Applicant Fact Extraction Pipeline.
Extracts candidate applicant facts via LLM/NLP and registers them through
Phase 4 normalization and EvidenceRegistry.
CRITICAL INVARIANTS:
1. LLM extracts raw_value only. Phase 4 exclusively owns normalization.
2. User statements map strictly to FactVerificationStatus.SELF_REPORTED.
3. Registered facts pass through Phase 4 validators and conflict detection.
"""

from typing import Any, Dict, List, Optional, Tuple
import sys
from pathlib import Path

# Ensure AI directory is on sys.path
_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import (
        ApplicantFactCandidate,
        FactExtractionResult,
        ExtractionConfidence,
    )
    from .client import LLMClient
    from .prompts import SYSTEM_PROMPT_FACT_EXTRACTION
    from .safety import PromptInjectionDetector
    from ..extraction.models import (
        ApplicantFact,
        FactVerificationStatus,
        ExtractionMethod,
        CANONICAL_PROFILE_FIELDS,
    )
    from ..documents.evidence import EvidenceRegistry
    from ..normalization.normalizer import normalize_field_value
    from ..normalization.validators import ValidationError
except (ImportError, ValueError):
    from src.llm.models import (
        ApplicantFactCandidate,
        FactExtractionResult,
        ExtractionConfidence,
    )
    from src.llm.client import LLMClient
    from src.llm.prompts import SYSTEM_PROMPT_FACT_EXTRACTION
    from src.llm.safety import PromptInjectionDetector
    from src.extraction.models import (
        ApplicantFact,
        FactVerificationStatus,
        ExtractionMethod,
        CANONICAL_PROFILE_FIELDS,
    )
    from src.documents.evidence import EvidenceRegistry
    from src.normalization.normalizer import normalize_field_value
    from src.normalization.validators import ValidationError


class ApplicantFactExtractor:
    """
    Extracts raw applicant facts from natural-language text and safely
    bridges them to Phase 4 Normalization and EvidenceRegistry.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
        self.safety_detector = PromptInjectionDetector()

    def extract_candidates(self, user_text: str) -> FactExtractionResult:
        """
        Extracts raw applicant fact candidates from text via LLMClient.
        Performs non-destructive safety scan and encases text in XML boundaries.
        """
        scan_result = self.safety_detector.scan(user_text)
        wrapped_input = self.safety_detector.wrap_untrusted_input(scan_result.raw_text)

        result: FactExtractionResult = self.llm_client.generate_structured(
            prompt=wrapped_input,
            schema_cls=FactExtractionResult,
            system_prompt=SYSTEM_PROMPT_FACT_EXTRACTION,
            operation="fact_extraction",
        )

        if scan_result.is_injection_risk:
            result.warnings.append(
                f"Prompt injection risk detected in input: {', '.join(scan_result.detected_threats)}"
            )

        return result

    def register_facts_to_phase4(
        self,
        extraction_result: FactExtractionResult,
        registry: Optional[EvidenceRegistry] = None,
        source_document: str = "user_statement"
    ) -> Tuple[EvidenceRegistry, List[ApplicantFact], List[str]]:
        """
        Transfers extracted candidates to Phase 4 EvidenceRegistry.
        ENFORCES:
        - Field exists in CANONICAL_PROFILE_FIELDS.
        - Verification status is strictly SELF_REPORTED.
        - Normalization is executed solely by Phase 4.
        Returns (registry, registered_facts, validation_warnings).
        """
        reg = registry or EvidenceRegistry(applicant_id="citizen_self_service")
        registered_facts: List[ApplicantFact] = []
        warnings: List[str] = list(extraction_result.warnings)

        for candidate in extraction_result.facts:
            field_name = candidate.field
            if field_name not in CANONICAL_PROFILE_FIELDS:
                warnings.append(f"Ignored non-canonical field extracted by LLM: '{field_name}'")
                continue

            # Invariant: User statements must be SELF_REPORTED
            verification_status = FactVerificationStatus.SELF_REPORTED

            try:
                fact = reg.record_fact(
                    field=field_name,
                    value=candidate.raw_value,  # Raw value passed to Phase 4
                    source_document=source_document,
                    text_span=candidate.evidence_text,
                    extraction_method=ExtractionMethod.NLP_MODEL.value,
                    verification_status=verification_status,
                    confidence=candidate.confidence,
                    normalize=True,   # Phase 4 normalizes
                    validate=True     # Phase 4 validates
                )
                registered_facts.append(fact)
            except ValidationError as exc:
                warnings.append(f"Phase 4 validation failed for field '{field_name}' ('{candidate.raw_value}'): {exc}")
            except Exception as exc:
                warnings.append(f"Error registering field '{field_name}': {exc}")

        return (reg, registered_facts, warnings)
