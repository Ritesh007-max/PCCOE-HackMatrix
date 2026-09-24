"""
FIN Administrative Document Type Detector.
Classifies document text into recognized Indian statutory document categories
(Aadhaar, Income Certificate, Domicile, Caste, Ration Card, etc.).
CRITICAL INVARIANT: Supports UNKNOWN / UNKNOWN_DOCUMENT. Unfamiliar documents
must never be forced into a false administrative category.
"""

import re
from typing import Optional, Tuple
try:
    from .provenance import DocumentType
except (ImportError, ValueError):
    from src.documents.provenance import DocumentType


class DocumentTypeDetector:
    """
    Detects official document types based on statutory textual markers and administrative headers.
    """

    PATTERNS = {
        DocumentType.AADHAAR: [
            r"\bunique\s+identification\s+authority\s+of\s+india\b",
            r"\buidai\b",
            r"\baadhaar\b",
            r"\bmera\s+aadhaar\s+meri\s+pehchan\b",
            r"\bआधार\b",
        ],
        DocumentType.PAN: [
            r"\bincometax\s+department\b",
            r"\bincome\s+tax\s+department\b",
            r"\bpermanent\s+account\s+number\b",
            r"\bpan\s+card\b",
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        ],
        DocumentType.INCOME_CERTIFICATE: [
            r"\bincome\s+certificate\b",
            r"\bannual\s+family\s+income\b",
            r"\baamdani\s+praman\s+patra\b",
            r"\bआय\s*प्रमाण\s*पत्र\b",
            r"\bcertificate\s+of\s+income\b",
            r"\btahsildar.*income\b",
        ],
        DocumentType.DOMICILE_CERTIFICATE: [
            r"\bdomicile\s+certificate\b",
            r"\bresidence\s+certificate\b",
            r"\bmool\s+niwas\s+praman\b",
            r"\bpermanent\s+resident\s+certificate\b",
            r"\bनिवास\s*प्रमाण\s*पत्र\b",
            r"\bमूल\s*निवास\b",
        ],
        DocumentType.CASTE_CERTIFICATE: [
            r"\bcaste\s+certificate\b",
            r"\bcommunity\s+certificate\b",
            r"\bscheduled\s+caste\b",
            r"\bscheduled\s+tribe\b",
            r"\bother\s+backward\s+class\b",
            r"\bजाति\s*प्रमाण\s*पत्र\b",
        ],
        DocumentType.DISABILITY_CERTIFICATE: [
            r"\bdisability\s+certificate\b",
            r"\bbenchmark\s+disability\b",
            r"\bperson\s+with\s+disability\b",
            r"\bdivyangjan\b",
            r"\bदिव्यांग\b",
            r"\budid\b",
        ],
        DocumentType.RATION_CARD: [
            r"\bration\s+card\b",
            r"\bfood\s*&\s*civil\s+supplies\b",
            r"\bnfsa\b",
            r"\bराशन\s*कार्ड\b",
            r"\bbpl\s+card\b",
        ],
        DocumentType.LAND_RECORD_ROR: [
            r"\brecord\s+of\s+rights\b",
            r"\b7/12\s+extract\b",
            r"\bkhasra\b",
            r"\bkhatauni\b",
            r"\bभूलेख\b",
            r"\bjmabandi\b",
        ],
        DocumentType.STUDENT_ID: [
            r"\bstudent\s+(?:identity|id)\s+card\b",
            r"\bbonafide\s+student\b",
            r"\benrollment\s+no\b",
            r"\bcollege\s+id\b",
            r"\bschool\s+id\b",
        ],
        DocumentType.BANK_PASSBOOK: [
            r"\bbank\s+passbook\b",
            r"\baccount\s+statement\b",
            r"\bifsc\s+code\b",
            r"\bsavings\s+bank\s+account\b",
        ],
        DocumentType.ELECTRICITY_BILL: [
            r"\belectricity\s+bill\b",
            r"\bpower\s+distribution\b",
            r"\bconsumer\s+number\b",
            r"\belectricity\s+consumer\b",
        ],
    }

    def detect(self, text: str, filename: Optional[str] = None) -> Tuple[DocumentType, float]:
        """
        Classifies document type from content and optional filename.
        Returns (DocumentType, confidence).
        Falls back strictly to DocumentType.UNKNOWN_DOCUMENT if unclassified.
        """
        if not text and not filename:
            return DocumentType.UNKNOWN_DOCUMENT, 0.0

        content = f"{filename or ''} {text or ''}".lower()

        scores = {}
        for doc_type, patterns in self.PATTERNS.items():
            matches = sum(1 for pat in patterns if re.search(pat, content, re.IGNORECASE))
            if matches > 0:
                scores[doc_type] = matches

        if not scores:
            return DocumentType.UNKNOWN_DOCUMENT, 0.0

        best_type, count = max(scores.items(), key=lambda item: item[1])
        # Need at least 1 strong match
        confidence = min(0.95, 0.50 + (0.15 * count))
        return best_type, confidence
