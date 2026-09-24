"""
Document Preparation Guidance Builder.
Phase 11: Actionable document requirements, issuing authorities, attestation instructions,
and status tracking without hallucination.
"""

from typing import Any, Dict, List, Optional
from src.application.case import ApplicationCase, DocumentReference
from src.application.readiness import DocumentCompletenessReport
from .models import DocumentGuidanceItem

# Standard official authorities and verification guidance for common Indian statutory certificates
STATUTORY_DOCUMENT_METADATA: Dict[str, Dict[str, str]] = {
    "income_certificate": {
        "display_name": "Income Certificate",
        "issuing_authority": "Revenue Department (Tehsildar / Sub-Divisional Magistrate / Mamlatdar)",
        "why_needed": "Required by statutory rules to verify annual family income does not exceed scheme ceiling.",
        "preparation_notes": "Must be valid for the current financial year. Typically issued within the last 1–3 years.",
    },
    "caste_certificate": {
        "display_name": "Caste / Social Category Certificate",
        "issuing_authority": "Sub-Divisional Magistrate (SDM) / District Magistrate / Revenue Authority",
        "why_needed": "Mandatory to verify constitutional reservation criteria (SC / ST / OBC).",
        "preparation_notes": "Permanent certificate; verify that applicant's name and father's name match Aadhaar exactly.",
    },
    "domicile_certificate": {
        "display_name": "Domicile / Residence Certificate",
        "issuing_authority": "Tehsildar / District Magistrate / Mamlatdar",
        "why_needed": "Required to prove continuous residency and domicile status in the state.",
        "preparation_notes": "Provide official state domicile certificate or verified ration card showing continuous residency.",
    },
    "student_id": {
        "display_name": "Student ID / Enrollment Verification",
        "issuing_authority": "Recognized Educational Institution (Principal / Registrar / Dean)",
        "why_needed": "Confirms active enrollment in eligible academic courses.",
        "preparation_notes": "Current academic session bonafide certificate or current semester fee receipt.",
    },
    "land_records": {
        "display_name": "Land Title Records (7/12 / RoR)",
        "issuing_authority": "Revenue Department / Land Records Office (Patwari / Talati)",
        "why_needed": "Verifies title to cultivable agricultural landholding.",
        "preparation_notes": "Must reflect current applicant title without unprobated joint-holding disputes.",
    },
    "bank_passbook": {
        "display_name": "Bank Passbook / Cancelled Cheque",
        "issuing_authority": "RBI-Regulated Commercial / Postal / Cooperative Bank",
        "why_needed": "Required for Direct Benefit Transfer (DBT) disbursement.",
        "preparation_notes": "Account must be active, single/primary, and linked with Aadhaar for DBT transfer.",
    },
    "disability_certificate": {
        "display_name": "Disability Certificate / UDID Card",
        "issuing_authority": "Chief Medical Officer (CMO) / District Medical Board",
        "why_needed": "Mandatory to verify benchmark disability (>= 40%).",
        "preparation_notes": "Unique Disability ID (UDID) card or government medical board certificate.",
    },
}


class DocumentGuidanceBuilder:
    """
    Assembles actionable preparation instructions for required scheme documents.
    """

    @staticmethod
    def _normalize_key(name: str) -> str:
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    @classmethod
    def build_guidance(
        cls,
        case: ApplicationCase,
        doc_report: Optional[DocumentCompletenessReport] = None,
        required_doc_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Builds a complete document guidance bundle matching the Section 24 contract.
        """
        required_types: List[str] = []
        if isinstance(required_doc_types, list):
            required_types = [str(d) for d in required_doc_types if d is not None]
        elif isinstance(required_doc_types, str) and required_doc_types.strip():
            val = required_doc_types.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    import ast
                    parsed = ast.literal_eval(val)
                    if isinstance(parsed, list):
                        required_types = [str(x) for x in parsed if x is not None]
                    else:
                        required_types = [val]
                except Exception:
                    required_types = [val]
            else:
                required_types = [val]

        if doc_report:
            for r in doc_report.required_documents.keys():
                if r not in required_types:
                    required_types.append(r)

        # Map attached documents
        attached_docs = list(case.documents.values())
        attached_norm: Dict[str, DocumentReference] = {}
        for d in attached_docs:
            norm_t = cls._normalize_key(d.document_type)
            attached_norm[norm_t] = d
            attached_norm[cls._normalize_key(d.filename)] = d

        items: List[DocumentGuidanceItem] = []
        available_list: List[str] = []
        missing_list: List[str] = []
        conflicted_list: List[str] = []

        for req in required_types:
            norm_req = cls._normalize_key(req)
            meta = STATUTORY_DOCUMENT_METADATA.get(norm_req, {})

            display_name = meta.get("display_name", req.replace("_", " ").title())
            authority = meta.get("issuing_authority", "Not specified in available policy evidence.")
            why = meta.get("why_needed", "Required for scheme eligibility verification.")
            notes = meta.get("preparation_notes", "Ensure scanned copy is legible with all official seals intact.")

            # Check status
            is_avail = False
            matching_doc = None
            for k, doc_ref in attached_norm.items():
                if norm_req in k or k in norm_req:
                    is_avail = True
                    matching_doc = doc_ref
                    break

            if is_avail:
                status_str = "AVAILABLE"
                available_list.append(display_name)
            else:
                status_str = "MISSING"
                missing_list.append(display_name)

            items.append(
                DocumentGuidanceItem(
                    document_type=req,
                    display_name=display_name,
                    status=status_str,
                    required=True,
                    why_needed=why,
                    already_provided=is_avail,
                    issuing_authority=authority,
                    preparation_notes=notes,
                    source_reference=matching_doc.document_id if matching_doc else None,
                )
            )

        # Include attached docs that were not explicitly listed in requirements
        for doc_ref in attached_docs:
            d_type = doc_ref.document_type
            norm_t = cls._normalize_key(d_type)
            if not any(cls._normalize_key(r) in norm_t for r in required_types):
                meta = STATUTORY_DOCUMENT_METADATA.get(norm_t, {})
                display_name = meta.get("display_name", doc_ref.filename)
                items.append(
                    DocumentGuidanceItem(
                        document_type=d_type,
                        display_name=display_name,
                        status="AVAILABLE",
                        required=False,
                        why_needed="Attached supplementary document.",
                        already_provided=True,
                        issuing_authority=meta.get("issuing_authority", "Not specified in available policy evidence."),
                        preparation_notes="Uploaded and processed.",
                        source_reference=doc_ref.document_id,
                    )
                )
                if display_name not in available_list:
                    available_list.append(display_name)

        return {
            "available": available_list,
            "missing": missing_list,
            "conflicted": conflicted_list,
            "items": [it.to_dict() for it in items],
        }
