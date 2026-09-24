"""
FIN Query Normalization & Cross-Lingual Search Expander.
Transforms raw citizen queries across English, Hindi (Devanagari), and Hinglish
into high-recall, high-precision retrieval representations.

CRITICAL INVARIANTS:
1. Always preserves verbatim user input (`original_query`).
2. Does NOT alter citizen's conversational language in UI responses.
3. Expanded search terms are strictly for internal Hybrid RAG retrieval.
4. Normalization is deterministic: zero runtime LLM formula synthesis.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata

from src.nlp.language import LanguageDetector
from .scheme_name_index import SchemeNameIndex, SchemeMatchResult
from .entity_decomposition import MultiSchemeDecomposer, DecompositionResult


@dataclass
class NormalizedQueryRecord:
    original_query: str
    normalized_query: str
    search_query: str
    detected_language: str
    confidence: float
    matched_schemes: List[SchemeMatchResult] = field(default_factory=list)
    transformations: List[str] = field(default_factory=list)
    is_multi_entity: bool = False
    decomposition: Optional[DecompositionResult] = None


# Core Devanagari concept dictionary for cross-lingual English retrieval expansion
DEVANAGARI_CONCEPT_MAP: List[Tuple[re.Pattern, str]] = [
    # Scheme concepts
    (re.compile(r"अटल\s+पेंशन|पेन्शन", re.UNICODE), "Atal Pension Yojana APY pension"),
    (re.compile(r"मातृत्व|गर्भवती\s+महिला(?:ओं)?", re.UNICODE), "Pradhan Mantri Matru Vandana Yojana PMMVY maternity pregnant women"),
    (re.compile(r"रेहड़ी\s+पटरी|पटरी\s+वाले|सड़क\s+विक्रेता", re.UNICODE), "PM SVANidhi street vendor working capital loan"),
    (re.compile(r"किसान\s+सम्मान|किसान\s+योजना", re.UNICODE), "PM Kisan Samman Nidhi farmer agricultural support"),
    (re.compile(r"आयुष्मान\s+भारत|जन\s+आरोग्य", re.UNICODE), "Ayushman Bharat PMJAY health insurance cashless"),
    (re.compile(r"एम्बुलेंस|आपातकालीन", re.UNICODE), "108 Emergency Ambulance Service medical"),

    # Policy domain keywords
    (re.compile(r"पेंशन|पेन्शन", re.UNICODE), "pension"),
    (re.compile(r"ऋण|कर्ज|लोन", re.UNICODE), "loan working capital credit"),
    (re.compile(r"दस्तावेज|दस्तावेज़|कागजात|प्रमाणपत्र", re.UNICODE), "documents required certificates proof"),
    (re.compile(r"पात्रता|पात्र", re.UNICODE), "eligibility criteria qualify"),
    (re.compile(r"सहायता|लाभ|राशि", re.UNICODE), "financial assistance benefit amount grant"),
    (re.compile(r"छात्रवृत्ति|छात्र", re.UNICODE), "scholarship student education"),
    (re.compile(r"न्यूनतम", re.UNICODE), "minimum guaranteed"),
    (re.compile(r"सरकारी", re.UNICODE), "government official central"),
]

# Common noise and injection phrases to neutralize from retrieval query strings
RETRIEVAL_NOISE_PATTERNS = [
    re.compile(r"\bignore\s+(all\s+)?(previous\s+)?rules(\s+and)?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+instructions\b", re.IGNORECASE),
    re.compile(r"\b(?:my\s+)?aadhaar(?:\s*(?:is|no|number|num)?:?\s*|\s+)[0-9]{4}[-\s][0-9]{4}[-\s][0-9]{4}\b", re.IGNORECASE),
    re.compile(r"\b[0-9]{4}[-\s][0-9]{4}[-\s][0-9]{4}\b", re.IGNORECASE),
    re.compile(r"\b(?:mobile|phone|contact)?\s*[6-9][0-9]{9}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE),
    re.compile(r"\b(?:and\s+)?income\s+(?:is\s+)?[0-9]+(?:\s*lakh|\s*rupees|\s*rs)?\b", re.IGNORECASE),
    re.compile(r"\btell\s+me\s+about\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+is\b", re.IGNORECASE),
]

# Common abbreviations mapped to full scheme search terms
ABBREVIATION_EXPANSIONS: Dict[str, str] = {
    "apy": "Atal Pension Yojana APY",
    "pmkisan": "Pradhan Mantri Kisan Samman Nidhi PM-KISAN",
    "pmmvy": "Pradhan Mantri Matru Vandana Yojana PMMVY",
    "svanidhi": "PM Street Vendor AtmaNirbhar Nidhi PM SVANidhi",
    "pmjay": "Ayushman Bharat PMJAY",
}


class QueryNormalizer:
    """
    Production-grade query normalizer for FIN Hybrid RAG.
    Performs language classification, typo/orthographic normalization,
    Devanagari cross-lingual mapping, and multi-scheme decomposition.
    """

    def __init__(
        self,
        scheme_index: Optional[SchemeNameIndex] = None,
        language_detector: Optional[LanguageDetector] = None,
    ):
        self.scheme_index = scheme_index or SchemeNameIndex()
        self.lang_detector = language_detector or LanguageDetector()
        self.decomposer = MultiSchemeDecomposer(self.scheme_index)

    def normalize(self, query_text: str) -> NormalizedQueryRecord:
        """Executes full normalization pipeline on the query text."""
        raw = query_text.strip()
        transformations: List[str] = []

        # 1. Language Detection
        lang_res = self.lang_detector.detect(raw)
        detected_lang = lang_res.language

        # 2. Unicode Normalization (NFKC) & Nukta cleanup
        clean_text = unicodedata.normalize("NFKC", raw)
        clean_text = clean_text.replace("दस्तावेज", "दस्तावेज़")
        if clean_text != raw:
            transformations.append("UNICODE_NORMALIZATION")

        # 3. Strip retrieval-polluting noise / PII from search string
        cleaned_search = clean_text
        for pat in RETRIEVAL_NOISE_PATTERNS:
            if pat.search(cleaned_search):
                cleaned_search = pat.sub(" ", cleaned_search)
                transformations.append("STRIPPED_NOISE_AND_PII")
        cleaned_search = re.sub(r"\s+", " ", cleaned_search).strip()

        # 4. Multi-Scheme Decomposition Check
        decomp = self.decomposer.decompose(clean_text)
        is_multi = decomp.is_multi_entity
        if is_multi:
            transformations.append(f"MULTI_SCHEME_DECOMPOSITION_{decomp.comparison_type}")

        # 5. Scheme Name / Alias Matching
        matched_schemes: List[SchemeMatchResult] = []
        match = self.scheme_index.match(cleaned_search)
        if match:
            matched_schemes.append(match)
            transformations.append(f"SCHEME_MATCH_{match.match_method}")

        # Also check word-level abbreviations (e.g. APY, PMMVY, PM-KISAN)
        words = re.findall(r"\b[a-zA-Z0-9-]{3,}\b", cleaned_search.lower())
        for w in words:
            w_norm = w.replace("-", "")
            if w_norm in ABBREVIATION_EXPANSIONS:
                # Add abbreviation expansion to search terms
                match_res = self.scheme_index.match(w)
                if match_res and match_res.scheme_slug not in [m.scheme_slug for m in matched_schemes]:
                    matched_schemes.append(match_res)
                    transformations.append(f"ABBREVIATION_EXPANSION_{w.upper()}")

        # 6. Devanagari Concept Expansion (Cross-Lingual Normalization)
        expanded_concepts: List[str] = []
        if detected_lang in ("hi", "mixed") or bool(re.search(r"[\u0900-\u097F]", clean_text)):
            for pat, eng_phrase in DEVANAGARI_CONCEPT_MAP:
                if pat.search(clean_text):
                    expanded_concepts.append(eng_phrase)
                    transformations.append(f"DEVANAGARI_CONCEPT_EXPANSION_{eng_phrase.split()[0]}")

        # 7. Construct Enriched Search Query for Hybrid RAG
        search_tokens = [cleaned_search]

        # Prepend matched canonical scheme names for high BM25 / dense relevance
        for m in matched_schemes:
            search_tokens.insert(0, m.canonical_name)
            search_tokens.insert(1, m.scheme_slug.upper())

        # Append cross-lingual concept expansions
        if expanded_concepts:
            search_tokens.extend(expanded_concepts)

        search_query = " ".join(dict.fromkeys(" ".join(search_tokens).split()))  # deduplicate preserving order

        # Determine confidence
        confidence = 0.95
        if matched_schemes:
            confidence = max(m.confidence for m in matched_schemes)
        elif detected_lang == "hi":
            confidence = 0.85

        return NormalizedQueryRecord(
            original_query=query_text,
            normalized_query=clean_text,
            search_query=search_query,
            detected_language=detected_lang,
            confidence=round(confidence, 3),
            matched_schemes=matched_schemes,
            transformations=transformations,
            is_multi_entity=is_multi,
            decomposition=decomp if is_multi else None,
        )
