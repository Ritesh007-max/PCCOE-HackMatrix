"""
FIN Fact Canonicalization and OCR Provenance Mapping Engine.
Binds extracted document fields, OCR blocks, and text spans to canonical
ApplicantFact and Evidence models with strict provenance and deterministic normalization.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
    ExtractionMethod,
    CANONICAL_PROFILE_FIELDS,
)
from src.normalization.normalizer import normalize_field_value
from src.documents.models import DocumentContent, BoundingBox
from src.documents.field_extractor import extract_document_fields


CANONICAL_FIELD_SYNONYMS: Dict[str, str] = {
    # Income - Personal vs Family strictly separated
    "annual_income": "annual_income",
    "personal_income": "annual_income",
    "individual_income": "annual_income",
    "annual_personal_income": "annual_income",
    "my_salary": "annual_income",
    "salary": "annual_income",
    "annual_family_income": "annual_family_income",
    "family_income": "annual_family_income",
    "household_income": "annual_family_income",
    "parivar_aay": "annual_family_income",
    "gross_annual_family_income": "annual_family_income",
    "total_family_income": "annual_family_income",
    "father_income": "father_income",
    "father_employment_income": "father_income",
    "mother_income": "mother_income",
    "mother_employment_income": "mother_income",
    "other_income": "other_income",
    "other_family_income": "other_income",
    # Identity & Document Details
    "beneficiary_name": "beneficiary_name",
    "applicant_name": "beneficiary_name",
    "full_name": "beneficiary_name",
    "name": "beneficiary_name",
    "document_number": "document_number",
    "certificate_number": "document_number",
    "cert_number": "document_number",
    "date_of_birth": "date_of_birth",
    "dob": "date_of_birth",
    # Age & DOB
    "age": "age",
    "applicant_age": "age",
    # State & Residence
    "state": "state",
    "state_of_residence": "state",
    "domicile_state": "state",
    "permanent_state": "state",
    "district": "district",
    "city": "district",
    "is_permanent_resident": "is_permanent_resident",
    "domicile": "is_permanent_resident",
    "residency_years": "residency_years",
    # Social Category
    "category": "social_category",
    "social_category": "social_category",
    "caste_category": "social_category",
    "caste": "social_category",
    "community": "social_category",
    # Gender
    "gender": "gender",
    "sex": "gender",
    # Disability
    "disability": "disability_percentage",
    "disability_percentage": "disability_percentage",
    "disability_pct": "disability_percentage",
    "is_disabled": "is_disabled",
    "pwd": "is_disabled",
    # Occupation & Land
    "occupation": "occupation",
    "profession": "occupation",
    "livelihood": "occupation",
    "landholding_hectares": "landholding_hectares",
    "landholding": "landholding_hectares",
    "land_holding": "landholding_hectares",
    "owns_cultivable_land": "owns_cultivable_land",
    # Financial & Welfare Flags
    "bpl_card_holder": "bpl_card_holder",
    "bpl": "bpl_card_holder",
    "bpl_card": "bpl_card_holder",
    "has_bank_account": "has_bank_account",
    "bank_account": "has_bank_account",
    "is_taxpayer": "is_taxpayer",
    "taxpayer": "is_taxpayer",
    "is_govt_employee": "is_govt_employee",
    "govt_employee": "is_govt_employee",
    "government_employee": "is_govt_employee",
    "has_pucca_house": "has_pucca_house",
    "pucca_house": "has_pucca_house",
    "monthly_pension_amount": "monthly_pension_amount",
    "pension_amount": "monthly_pension_amount",
    "is_student": "is_student",
    "student": "is_student",
    "school_attendance_pct": "school_attendance_pct",
    "attendance_percentage": "school_attendance_pct",
    "is_minority": "is_minority",
}


def canonicalize_fact_key(
    key: str,
    doc_type: Optional[str] = None,
    has_family_income: bool = False,
    file_name: Optional[str] = None,
) -> str:
    """
    Deterministically maps synonyms and regional field terms to FIN canonical fields.
    Does NOT invent semantic specificity without evidence.
    Family income must never automatically become personal income.
    """
    clean = str(key).strip().lower().replace(" ", "_").replace("-", "_")
    doc_type_val = (doc_type.value if hasattr(doc_type, "value") else str(doc_type)) if doc_type else ""
    file_name_val = str(file_name or "").lower()
    is_income_cert = (
        any(t in doc_type_val.upper() for t in ("INCOME_CERT", "INCOME_CERTIFICATE"))
        or "income" in doc_type_val.lower()
        or "income" in file_name_val
    )

    if clean in ("annual_family_income", "family_income", "household_income", "parivar_aay"):
        return "annual_family_income"
    if clean in ("personal_income", "annual_personal_income", "salary", "my_salary"):
        return "annual_income"
    if clean in ("annual_income", "income"):
        if is_income_cert or has_family_income:
            return "annual_family_income"
        return "annual_income"

    return CANONICAL_FIELD_SYNONYMS.get(clean, clean)


FIELD_CONTEXT_KEYWORDS: Dict[str, List[str]] = {
    "annual_family_income": ["family income", "annual family", "household income", "total family", "parivar", "family"],
    "father_income": ["father", "employment", "wage", "father's"],
    "mother_income": ["mother", "tailoring", "craft", "mother's", "self-employment"],
    "other_income": ["other income", "other household", "other family"],
    "annual_income": ["personal income", "individual income", "salary"],
    "social_category": ["category", "caste", "community", "social category"],
    "beneficiary_name": ["certify that", "name", "applicant", "shri", "smt", "resident"],
    "document_number": ["certificate number", "cert no", "reference", "doc no", "registration no", "certificate no"],
    "date_of_birth": ["birth", "dob", "born"],
    "age": ["age", "years", "yrs"],
    "state": ["state", "domicile", "resident of"],
    "district": ["district", "dist"],
    "issuing_authority": ["authority", "office", "mamlatdar", "tehsildar", "collector", "revenue department", "issuing authority", "signatory"],
}


def _matches_needle(text: str, needle: str) -> bool:
    if not text or not needle:
        return False
    needle_str = str(needle).strip()
    needle_clean = re.sub(r"[₹,.\-\s/]", "", needle_str).lower()
    text_clean = re.sub(r"[₹,.\-\s/]", "", text).lower()
    if not needle_clean:
        return False
    if len(needle_clean) <= 3:
        return bool(re.search(rf"\b{re.escape(needle_str)}\b", text, re.IGNORECASE))
    return needle_clean in text_clean


def find_block_provenance(
    doc_content: DocumentContent,
    needle: str,
    field_key: Optional[str] = None,
) -> Tuple[int, Optional[BoundingBox], float, str, str]:
    """
    Scans document pages for native text blocks and OCR blocks matching the extracted needle.
    Preserves page number, bounding box coordinates, confidence score, and extraction method.
    Uses contextual keyword scoring to resolve ambiguous short tokens (e.g. 'SC' category vs 'schedule').
    """
    if not needle or not doc_content.pages:
        return (1, None, 1.0, doc_content.extraction_method.value if hasattr(doc_content.extraction_method, "value") else str(doc_content.extraction_method), "")

    candidates = []
    keywords = FIELD_CONTEXT_KEYWORDS.get(field_key or "", [])

    for page in doc_content.pages:
        page_text_lower = page.text.lower()

        # Check OCR blocks first if scanned (preserves paddle/heuristic OCR bbox)
        for ob in page.ocr_blocks:
            if _matches_needle(ob.text, needle):
                score = 1
                ob_lower = ob.text.lower()
                for kw in keywords:
                    if kw in ob_lower:
                        score += 3
                    elif kw in page_text_lower:
                        score += 1
                candidates.append((score, ob.page_number, ob.bounding_box, ob.confidence, ob.extraction_method.value if hasattr(ob.extraction_method, "value") else str(ob.extraction_method), ob.text))

        # Check native text blocks
        for tb in page.text_blocks:
            if _matches_needle(tb.text, needle):
                score = 1
                tb_lower = tb.text.lower()
                for kw in keywords:
                    if kw in tb_lower:
                        score += 3
                    elif kw in page_text_lower:
                        score += 1
                candidates.append((score, tb.page_number, tb.bounding_box, tb.confidence, tb.extraction_method.value if hasattr(tb.extraction_method, "value") else str(tb.extraction_method), tb.text))

    if candidates:
        candidates.sort(key=lambda c: c[0], reverse=True)
        best = candidates[0]
        return (best[1], best[2], best[3], best[4], best[5])

    # Fallback to document level
    def_method = doc_content.extraction_method.value if hasattr(doc_content.extraction_method, "value") else str(doc_content.extraction_method)
    return (1, None, 0.95, def_method, str(needle))


def extract_document_canonical_facts(
    doc_content: DocumentContent,
    applicant_id: str,
) -> Tuple[List[ApplicantFact], List[Evidence], Dict[str, Any]]:
    """
    Extracts canonical applicant facts and evidence records from an ingested DocumentContent.
    Preserves raw value, applies deterministic normalization, binds OCR block provenance,
    and returns (facts, evidence, all_extracted_raw_fields).
    """
    full_text = doc_content.get_full_text()
    doc_type_val = (
        doc_content.document_type.value
        if hasattr(doc_content.document_type, "value")
        else str(doc_content.document_type)
    )

    # 1. Run statutory field extractor
    raw_fields = extract_document_fields(
        full_text=full_text,
        doc_type=doc_type_val,
        filename=doc_content.file_name,
    )

    facts: List[ApplicantFact] = []
    evidence_list: List[Evidence] = []
    seen_canonical_keys = set()

    has_fam = "annual_family_income" in raw_fields or any("family" in k for k in raw_fields)
    for raw_key, raw_val in raw_fields.items():
        if raw_val is None or str(raw_val).strip() == "":
            continue

        canonical_key = canonicalize_fact_key(raw_key, doc_type=doc_type_val, has_family_income=has_fam)
        if canonical_key in seen_canonical_keys:
            continue
        seen_canonical_keys.add(canonical_key)

        # Determine data type from canonical registry
        field_meta = CANONICAL_PROFILE_FIELDS.get(canonical_key)
        data_type = field_meta.get("data_type", "string") if field_meta else "string"

        # Deterministic normalization (Raw value is NEVER replaced or discarded!)
        normalized_val: Any = None
        try:
            normalized_val = normalize_field_value(canonical_key, raw_val, validate=False)
        except Exception:
            normalized_val = None

        # Block-level OCR / native provenance search
        page_num, bbox, conf, ext_method, span_text = find_block_provenance(
            doc_content, str(raw_val), field_key=canonical_key
        )

        bbox_dict = bbox.to_dict() if bbox else None

        # Build canonical ApplicantFact
        fact = ApplicantFact(
            applicant_id=applicant_id,
            document_id=doc_content.document_id,
            field=canonical_key,
            value=raw_val,  # RAW VALUE PRESERVED VERBATIM
            normalized_value=normalized_val,
            data_type=data_type,
            confidence=conf,
            source_type=FactSourceType.DOCUMENT,
            source_document=doc_content.file_name,
            page_number=page_num,
            text_span=span_text or str(raw_val),
            bounding_box=bbox_dict,
            extraction_method=ext_method,
            verification_status=FactVerificationStatus.EXTRACTED,
            metadata={
                "raw_field_name": raw_key,
                "document_hash": doc_content.sha256,
                "document_type": doc_type_val,
            },
        )
        facts.append(fact)

        # Build canonical Evidence
        ev = Evidence(
            applicant_fact_id=fact.id,
            applicant_id=applicant_id,
            document_id=doc_content.document_id,
            source_type=FactSourceType.DOCUMENT,
            source_uri=doc_content.file_name,
            page_number=page_num,
            text_span=span_text or str(raw_val),
            bounding_box=bbox_dict,
            extraction_method=ext_method,
            confidence=conf,
            verification_status=FactVerificationStatus.EXTRACTED,
            document_hash=doc_content.sha256,
            metadata={
                "field": canonical_key,
                "raw_value": str(raw_val),
                "normalized_value": str(normalized_val),
                "document_type": doc_type_val,
            },
        )
        evidence_list.append(ev)

    return (facts, evidence_list, raw_fields)
