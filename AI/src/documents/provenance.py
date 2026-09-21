"""
PolicySetu Document Provenance Layer.
Tracks origin, issuance, and audit details for extracted facts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class DocumentType(str, Enum):
    """Recognized official document categories in the Indian administrative system."""
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    INCOME_CERTIFICATE = "INCOME_CERTIFICATE"
    DOMICILE_CERTIFICATE = "DOMICILE_CERTIFICATE"
    CASTE_CERTIFICATE = "CASTE_CERTIFICATE"
    DISABILITY_CERTIFICATE = "DISABILITY_CERTIFICATE"
    RATION_CARD = "RATION_CARD"
    LAND_RECORD_ROR = "LAND_RECORD_ROR"
    BANK_PASSBOOK = "BANK_PASSBOOK"
    STUDENT_ID = "STUDENT_ID"
    ELECTRICITY_BILL = "ELECTRICITY_BILL"
    SELF_DECLARATION = "SELF_DECLARATION"
    OTHER = "OTHER"


@dataclass
class DocumentProvenance:
    """
    Detailed provenance record detailing the exact source document, page,
    verbatim text span, and administrative issuing authority.
    """
    source_document: str
    document_type: DocumentType = DocumentType.OTHER
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    page_number: Optional[int] = None
    text_span: Optional[str] = None
    extraction_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_document": self.source_document,
            "document_type": self.document_type.value if isinstance(self.document_type, DocumentType) else str(self.document_type),
            "issuer": self.issuer,
            "issue_date": self.issue_date,
            "page_number": self.page_number,
            "text_span": self.text_span,
            "extraction_timestamp": self.extraction_timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentProvenance":
        doc_type_val = data.get("document_type", DocumentType.OTHER.value)
        try:
            doc_type = DocumentType(doc_type_val)
        except ValueError:
            doc_type = DocumentType.OTHER

        return cls(
            source_document=data["source_document"],
            document_type=doc_type,
            issuer=data.get("issuer"),
            issue_date=data.get("issue_date"),
            page_number=data.get("page_number"),
            text_span=data.get("text_span"),
            extraction_timestamp=data.get("extraction_timestamp", datetime.now(timezone.utc).isoformat()),
            metadata=data.get("metadata", {}),
        )
