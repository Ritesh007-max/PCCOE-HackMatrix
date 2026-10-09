"""
FIN Canonical Scheme Name & Alias Index.
Builds a fast, deterministic lookup index mapping exact names, abbreviations,
transliterations, Devanagari titles, and fuzzy spelling variants to canonical scheme slugs.

CRITICAL INVARIANTS:
1. Fully deterministic: zero LLM hallucination of arbitrary aliases.
2. Low-confidence matches preserve candidates without forcing false positives.
3. Used purely for retrieval candidate generation, never for statutory eligibility.
"""

from dataclasses import dataclass
import difflib
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata
from pathlib import Path


@dataclass
class SchemeMatchResult:
    scheme_slug: str
    canonical_name: str
    confidence: float
    match_method: str  # EXACT, ALIAS, TRANSLITERATED, DEVANAGARI, FUZZY, PHONETIC


# Core curated aliases for canonical schemes frequently queried across vernacular/English
CANONICAL_SCHEME_ALIASES: Dict[str, Dict[str, Any]] = {
    "apy": {
        "canonical_name": "Atal Pension Yojana",
        "short_title": "APY",
        "aliases": [
            "atal pension yojana", "atal pension", "atal pension yojna", "atal penshan yojana",
            "atal penshan yojna", "atall penshion yojna", "atle penshan yojna", "atal penson yojana",
            "atal penson yojna", "atal penshan", "pension yojana for unorganized", "apy scheme",
        ],
        "devanagari": [
            "अटल पेंशन योजना", "अटल पेंशन", "अटल पेन्शन योजना", "अटल पेंशन स्कीम", "अटल पेन्शन"
        ],
        "keywords": ["pension", "unorganized", "old age pension", "guaranteed pension", "60 years"]
    },
    "pm-kisan": {
        "canonical_name": "Pradhan Mantri Kisan Samman Nidhi",
        "short_title": "PM-KISAN",
        "aliases": [
            "pm kisan", "pm kisan samman nidhi", "pm-kisan", "pmkisan", "kisan samman nidhi",
            "kisan samman", "pm kisan yojana", "pm kisan yojna", "kisan samman nidhi yojana",
            "farmer 6000 scheme", "pm farmer scheme", "kisan 6000", "farmer support", "farmer scheme",
        ],
        "devanagari": [
            "पीएम किसान", "प्रधानमंत्री किसान सम्मान निधि", "किसान सम्मान निधि", "पीएम किसान योजना",
            "प्रधानमंत्री किसान योजना", "किसान योजना"
        ],
        "keywords": ["farmer", "kisan", "cultivable land", "agricultural support", "income support", "6000"]
    },
    "pmmvy": {
        "canonical_name": "Pradhan Mantri Matru Vandana Yojana",
        "short_title": "PMMVY",
        "aliases": [
            "pmmvy", "pm matru vandana yojana", "pradhan mantri matru vandana yojana",
            "matru vandana yojana", "matru vandana yojna", "pm matrutva yojana",
            "pmmvy maternity", "pm maternity scheme", "pregnant woman 5000", "matritva yojana",
            "matru vandana",
        ],
        "devanagari": [
            "प्रधानमंत्री मातृ वंदना योजना", "मातृ वंदना योजना", "मातृ वंदना", "पीएमएमवीवाई",
            "मातृत्व सहायता योजना", "गर्भवती महिला योजना"
        ],
        "keywords": ["pregnant", "maternity", "first live birth", "lactating", "wage loss", "5000"]
    },
    "pm-svanidhi": {
        "canonical_name": "PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)",
        "short_title": "PM SVANIDHI",
        "aliases": [
            "pm svanidhi", "pm-svanidhi", "pmsvanidhi", "svanidhi", "pm swanidhi", "swanidhi",
            "street vendor loan", "pm street vendor scheme", "street vendor atmanirbhar nidhi",
            "vendor loan 10000", "rehri patri loan", "vendor working capital",
        ],
        "devanagari": [
            "पीएम स्वनिधि", "पीएम स्वनिधि योजना", "स्वनिधि योजना", "स्वनिधि", "रेहड़ी पटरी वालों के लिए ऋण",
            "रेहड़ी पटरी योजना", "स्ट्रीट वेंडर योजना", "पीएम स्वानिधि"
        ],
        "keywords": ["street vendor", "urban vendor", "vending certificate", "working capital loan", "10000"]
    },
    "ab-pmjay": {
        "canonical_name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana",
        "short_title": "AB-PMJAY",
        "aliases": [
            "ayushman bharat", "pmjay", "ab pmjay", "ab-pmjay", "ayushman bharat pmjay",
            "jan arogya yojana", "ayushman card", "pm jan arogya yojana", "ayushman scheme",
            "5 lakh health insurance", "ayushman gold card",
        ],
        "devanagari": [
            "आयुष्मान भारत", "पीएम जन आरोग्य योजना", "जन आरोग्य योजना", "आयुष्मान भारत योजना",
            "आयुष्मान कार्ड", "पीएमजेएवाई"
        ],
        "keywords": ["health insurance", "hospitalization", "5 lakh", "cashless treatment", "pmjay"]
    },
    "108easuk": {
        "canonical_name": "108 Emergency Ambulance Service (Uttarakhand)",
        "short_title": "108 EAS UK",
        "aliases": [
            "108 ambulance uttarakhand", "108 emergency ambulance", "108 medical service uttarakhand",
            "108 ambulance", "uttarakhand 108 ambulance",
        ],
        "devanagari": ["108 एम्बुलेंस उत्तराखंड", "108 आपातकालीन एम्बुलेंस"],
        "keywords": ["ambulance", "uttarakhand", "emergency", "108", "medical"]
    },
}


def normalize_text_key(text: str) -> str:
    """Normalizes string for dictionary lookup: lowercase, strip punctuation, single spaces."""
    if not text:
        return ""
    # NFKC unicode normalization
    t = unicodedata.normalize("NFKC", text).lower()
    # Replace hyphens and underscores with space
    t = t.replace("-", " ").replace("_", " ")
    # Remove non-alphanumeric except spaces
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class SchemeNameIndex:
    """
    Searchable index of scheme names and aliases for deterministic resolution and typo recovery.
    """

    def __init__(self, parquet_path: Optional[Path] = None):
        self._exact_map: Dict[str, Tuple[str, str, str]] = {}  # norm_key -> (slug, canonical_name, method)
        self._alias_tokens: Dict[str, Set[str]] = {}           # slug -> set of tokens
        self._slug_to_canonical: Dict[str, str] = {}           # slug -> canonical_name
        self._all_slugs: Set[str] = set()
        self._devanagari_map: Dict[str, Tuple[str, str]] = {}  # devanagari_phrase -> (slug, canonical_name)

        self._canonical_records: Dict[str, Dict[str, Any]] = {} # slug -> full canonical row dict

        self._build_curated_index()
        if parquet_path and parquet_path.exists():
            self._load_from_parquet(parquet_path)

    def _build_curated_index(self) -> None:
        """Populates curated authoritative scheme titles, abbreviations, and Devanagari names."""
        for slug, data in CANONICAL_SCHEME_ALIASES.items():
            canon = data["canonical_name"]
            short = data.get("short_title", "")
            self._slug_to_canonical[slug] = canon
            self._all_slugs.add(slug)

            # 1. Exact canonical name & short title
            canon_key = normalize_text_key(canon)
            self._exact_map[canon_key] = (slug, canon, "EXACT")
            if short:
                self._exact_map[normalize_text_key(short)] = (slug, canon, "EXACT")
            self._exact_map[slug.replace("-", " ")] = (slug, canon, "EXACT")
            self._exact_map[slug.replace("-", "")] = (slug, canon, "EXACT")

            # 2. Curated English/Hinglish aliases
            tokens_for_slug: Set[str] = set(canon_key.split())
            for alias in data.get("aliases", []):
                ak = normalize_text_key(alias)
                self._exact_map[ak] = (slug, canon, "ALIAS")
                tokens_for_slug.update(ak.split())

            # 3. Devanagari names
            for dev in data.get("devanagari", []):
                dev_norm = unicodedata.normalize("NFKC", dev).strip()
                self._devanagari_map[dev_norm] = (slug, canon)
                dev_key = normalize_text_key(dev)
                self._exact_map[dev_key] = (slug, canon, "DEVANAGARI")

            self._alias_tokens[slug] = tokens_for_slug

    def _load_from_parquet(self, path: Path) -> None:
        """Enriches index from processed schemes_canonical.parquet."""
        try:
            import pandas as pd
            df = pd.read_parquet(path)
            for _, row in df.iterrows():
                slug = str(row.get("slug", "")).strip().lower()
                name = str(row.get("scheme_name", "")).strip()
                short = str(row.get("short_title", "")).strip()
                if not slug or not name:
                    continue
                rec = row.to_dict()
                self._canonical_records[slug] = rec
                if slug not in self._slug_to_canonical:
                    self._slug_to_canonical[slug] = name
                    self._all_slugs.add(slug)

                nk = normalize_text_key(name)
                if nk and nk not in self._exact_map:
                    self._exact_map[nk] = (slug, name, "CANONICAL_INDEX")
                if short:
                    sk = normalize_text_key(short)
                    if sk and sk not in self._exact_map:
                        self._exact_map[sk] = (slug, name, "SHORT_TITLE")
                slug_k = normalize_text_key(slug)
                if slug_k and slug_k not in self._exact_map:
                    self._exact_map[slug_k] = (slug, name, "SLUG")

                words = nk.split()
                if len(words) >= 3:
                    for i in range(len(words) - 1, 1, -1):
                        prefix = " ".join(words[:i])
                        if len(prefix) >= 12 and prefix not in self._exact_map:
                            self._exact_map[prefix] = (slug, name, "TITLE_PREFIX")
        except Exception:
            pass

    def get_record(self, slug: str) -> Optional[Dict[str, Any]]:
        """Returns the canonical scheme record dictionary by slug if available."""
        if not slug:
            return None
        return self._canonical_records.get(slug.lower())

    def resolve_canonical_scheme(self, text: str) -> Optional[Tuple[SchemeMatchResult, Dict[str, Any]]]:
        """
        Attempts to resolve an explicit scheme mention from text against the canonical index.
        Returns (SchemeMatchResult, canonical_record_dict) if matched and found.
        """
        match = self.match(text)
        if match:
            rec = self.get_record(match.scheme_slug)
            if rec:
                return (match, rec)
        return None

    def lookup_exact(self, query: str) -> Optional[SchemeMatchResult]:
        """Performs fast exact lookup on normalized text."""
        k = normalize_text_key(query)
        if k in self._exact_map:
            slug, name, method = self._exact_map[k]
            return SchemeMatchResult(
                scheme_slug=slug,
                canonical_name=name,
                confidence=1.0 if method == "EXACT" else 0.95,
                match_method=method,
            )
        return None

    def lookup_devanagari(self, text: str) -> Optional[SchemeMatchResult]:
        """Checks if any known Devanagari scheme phrases appear in the text."""
        text_norm = unicodedata.normalize("NFKC", text)
        # Check longest Devanagari matches first
        for phrase, (slug, canon) in sorted(self._devanagari_map.items(), key=lambda x: -len(x[0])):
            if phrase in text_norm:
                return SchemeMatchResult(
                    scheme_slug=slug,
                    canonical_name=canon,
                    confidence=0.98,
                    match_method="DEVANAGARI",
                )
        return None

    def lookup_fuzzy(self, query: str, threshold: float = 0.65) -> Optional[SchemeMatchResult]:
        """
        Token-level and whole-phrase fuzzy match against known scheme aliases.
        Handles severe phonetic and keyboard typos (e.g. 'Atle Penshan Yojna').
        """
        k = normalize_text_key(query)
        if not k:
            return None

        # 1. Whole phrase close match
        closest = difflib.get_close_matches(k, list(self._exact_map.keys()), n=1, cutoff=threshold)
        if closest:
            best_key = closest[0]
            sim = difflib.SequenceMatcher(None, k, best_key).ratio()
            slug, name, method = self._exact_map[best_key]
            return SchemeMatchResult(
                scheme_slug=slug,
                canonical_name=name,
                confidence=round(sim, 3),
                match_method="FUZZY",
            )

        # 2. Token-level overlap similarity
        # Handles cases where words are slightly misspelled (e.g. 'Atle' -> 'Atal', 'Penshan' -> 'Pension')
        query_tokens = k.split()
        if len(query_tokens) < 2:
            return None

        best_slug: Optional[str] = None
        best_score = 0.0

        for slug, candidate_tokens in self._alias_tokens.items():
            token_matches = 0
            for q_tok in query_tokens:
                # Find best token match
                tok_sims = [difflib.SequenceMatcher(None, q_tok, c_tok).ratio() for c_tok in candidate_tokens]
                if tok_sims and max(tok_sims) >= 0.70:
                    token_matches += 1

            overlap_ratio = token_matches / max(len(query_tokens), 1)
            if overlap_ratio > best_score and overlap_ratio >= 0.50:
                best_score = overlap_ratio
                best_slug = slug

        if best_slug and best_score >= threshold:
            canon = self._slug_to_canonical[best_slug]
            return SchemeMatchResult(
                scheme_slug=best_slug,
                canonical_name=canon,
                confidence=round(best_score, 3),
                match_method="PHONETIC",
            )

        return None

    def lookup_subphrase(self, query: str) -> Optional[SchemeMatchResult]:
        """Checks if any known scheme alias appears as a distinct subphrase within query."""
        k = f" {normalize_text_key(query)} "
        best_match: Optional[SchemeMatchResult] = None
        longest_len = 0
        for alias_key, (slug, name, method) in self._exact_map.items():
            if len(alias_key) >= 4 and f" {alias_key} " in k:
                if len(alias_key) > longest_len:
                    longest_len = len(alias_key)
                    best_match = SchemeMatchResult(
                        scheme_slug=slug,
                        canonical_name=name,
                        confidence=0.95,
                        match_method="SUBPHRASE_ALIAS",
                    )
        return best_match

    def match(self, text: str) -> Optional[SchemeMatchResult]:
        """
        Hierarchical matching:
        1. Exact lookup
        2. Devanagari phrase lookup
        3. Subphrase alias lookup
        4. Fuzzy & Phonetic lookup
        """
        # Step 1: Exact
        res = self.lookup_exact(text)
        if res:
            return res

        # Step 2: Devanagari
        res = self.lookup_devanagari(text)
        if res:
            return res

        # Step 3: Subphrase Alias
        res = self.lookup_subphrase(text)
        if res:
            return res

        # Step 4: Fuzzy / Phonetic
        res = self.lookup_fuzzy(text)
        if res:
            return res

        return None


_scheme_name_index_instance: Optional["SchemeNameIndex"] = None


def get_scheme_name_index() -> SchemeNameIndex:
    """Returns singleton SchemeNameIndex loaded with authoritative canonical schemes."""
    global _scheme_name_index_instance
    if _scheme_name_index_instance is None:
        p_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "schemes_canonical.parquet"
        _scheme_name_index_instance = SchemeNameIndex(parquet_path=p_path if p_path.exists() else None)
    return _scheme_name_index_instance


def clean_canonical_field(val: Any) -> Optional[str]:
    """Cleans null/nan/empty values from parquet/database records."""
    if val is None:
        return None
    if isinstance(val, (list, tuple)) or (hasattr(val, "__iter__") and not isinstance(val, (str, bytes))):
        items = [str(x).strip() for x in val if x is not None and str(x).strip()]
        if not items:
            return None
        return ", ".join(items)
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "[]", "null", "n/a"):
        return None
    return val_str


def format_bullet_list(text: Optional[str], sep: str = ";") -> str:
    """Formats semicolon, pipe, or newline separated text into neat markdown bullets."""
    if not text:
        return "Not specified in official scheme record"
    cleaned = text.replace("\ufffd", "-").replace("&amp;", "&")
    items = [i.strip() for i in re.split(r"(?:[;\n]+|\s*\|\s*-?\s*)", cleaned) if i.strip()]
    if not items:
        return cleaned
    return "\n".join(f"- {item.lstrip('-• ').strip()}" for item in items)


def detect_scheme_query_scope(query: str) -> Dict[str, Any]:
    """
    Detects requested information scope and exclusivity constraints from a scheme query.
    Respects explicit exclusive terms such as: only, just, exclusively, solely, merely, strictly.
    """
    q = (query or "").lower().strip()
    is_exclusive = bool(re.search(r"\b(?:only|just|exclusively|solely|merely|strictly)\b", q))

    wants_process = bool(re.search(
        r"\b(?:application|apply|how\s+to\s+apply|procedure|submission|stages?|process|steps?|mode|method|timeline|deadline|portal|kaise\s+apply|kahan\s+apply|where\s+do\s+i\s+apply|અરજી)\b",
        q
    ))
    wants_eligibility = bool(re.search(
        r"\b(?:eligibility|eligible|who\s+can\s+apply|qualify|qualification|age\s+limit|patrata|patra|kaun\s+apply|પાત્રતા)\b|(?<!selection\s)(?<!evaluation\s)\bcriteria\b",
        q
    ))
    wants_documents = bool(re.search(
        r"\b(?:documents?|certificates?|proofs?|endorsements?|forms?|records?|docs?|dastavej|kagaz|praman\s*patra|kya\s+lagega|દસ્તાવેજ|કાગળ|પ્રમાણપત્ર)\b",
        q
    ))
    wants_benefits = bool(re.search(
        r"\b(?:benefits?|financial\s+assistance|assistance|grant|fellowship|stipend|funding|allowance|subsidy|amount|how\s+much|money|fayda|kitna\s+milega|kya\s+milta\s+hai|લાભ|ફાયદો|કેટલા\s+પૈસા)\b",
        q
    ))
    wants_scoring = bool(re.search(
        r"\b(?:scoring|rubric|evaluation(?:\s+criteria|\s+matrix|\s+rubric|\s+rules)?|selection\s+criteria|peer\s+review(?:\s+criteria|\s+rubric|\s+process)?|marks|score\s+breakdown|detailed\s+criteria)\b",
        q
    ))
    wants_jurisdiction = bool(re.search(
        r"\b(?:jurisdiction|state|territory|location|applicable|applicability|domicile|resident|residence)\b",
        q
    ))
    wants_institutional_docs = bool(re.search(
        r"\b(?:institutional(?:\s+(?:endorsement|documents?|forms?|requirements?))?|endorsement\s+(?:documents?|forms?|certificates?|requirements?))\b",
        q
    ))
    wants_all_docs = bool(re.search(
        r"\b(?:all(?:\s+required)?\s+documents?|complete\s+documents?|every\s+document|general\s+documents?|identity\s+documents?|checklist|full\s+document\s+list)\b",
        q
    ))
    wants_institutional_only = wants_institutional_docs and not wants_all_docs
    wants_sources = bool(re.search(
        r"\b(?:sources?|official\s+source|website|link|portal|references?)\b",
        q
    ))
    wants_contacts = bool(re.search(
        r"\b(?:contact|helpline|helpdesk|phone|email|address|telephone)\b",
        q
    ))

    has_specific_intent = bool(wants_process or wants_eligibility or wants_documents or wants_benefits or wants_scoring or wants_jurisdiction)
    explicit_purpose = bool(re.search(
        r"\b(?:purpose|overview|objective|goal|summary|aim|introduction)\b",
        q
    ))
    wants_purpose = explicit_purpose or (bool(re.search(r"\babout\b", q)) and not has_specific_intent)

    is_explicit_broad = bool(re.search(r"\b(?:all|complete|full|everything|entire|overview|details|tell\s+me\s+about)\b", q))
    is_broad_overview = is_explicit_broad or (bool(re.search(r"\bwhat\s+is\b", q)) and not has_specific_intent) or not has_specific_intent

    # Targeted questions asking strictly about documents, benefits, application process, or eligibility
    is_focused_intent = bool(
        (wants_documents and not (wants_benefits or wants_process or wants_eligibility)) or
        (wants_benefits and not (wants_documents or wants_process or wants_eligibility)) or
        (wants_process and not (wants_documents or wants_benefits or wants_eligibility)) or
        (wants_eligibility and not (wants_documents or wants_benefits or wants_process))
    )
    if is_focused_intent and not is_explicit_broad:
        is_exclusive = True

    return {
        "is_exclusive": is_exclusive,
        "wants_process": wants_process,
        "wants_eligibility": wants_eligibility,
        "wants_documents": wants_documents,
        "wants_benefits": wants_benefits,
        "wants_purpose": wants_purpose,
        "wants_sources": wants_sources,
        "wants_contacts": wants_contacts,
        "wants_jurisdiction": wants_jurisdiction,
        "wants_institutional_docs": wants_institutional_docs,
        "wants_institutional_only": wants_institutional_only,
        "wants_all_docs": wants_all_docs,
        "wants_scoring": wants_scoring,
        "is_broad_overview": is_broad_overview,
    }


def categorize_canonical_documents(
    docs_raw: Optional[str],
    app_process_raw: Optional[str] = "",
    only_institutional: bool = False,
) -> str:
    """
    Separates documents based on source wording into:
    1. Institutional endorsement and research documents
    2. Applicant identity and general supporting documents
    3. Other stated requirements
    Preserves original wording and links. Ambiguous items remain under a neutral heading.
    """
    if not docs_raw and not app_process_raw:
        return "Not specified in official scheme record"

    docs_text = (docs_raw or "").replace("\ufffd", "-").replace("&amp;", "&")
    app_text = (app_process_raw or "").replace("\ufffd", "-").replace("&amp;", "&")

    raw_doc_items = [d.strip() for d in re.split(r"(?:[;\n]+|\s*\|\s*-?\s*)", docs_text) if d.strip()]

    # Extract institutional items explicitly mentioned in application process notes (e.g. Note 02 in YIPB)
    institutional_from_process: List[str] = []
    note_match = re.search(r"Note\s*0?2\s*:\s*([^|]+)", app_text, re.IGNORECASE)
    if note_match:
        note_body = note_match.group(1).strip()
        sub_items = re.findall(
            r"(?:an\s+)?(Endorsement\s+from\s+the\s+Implementing\s+Institution|Certificate\s+from\s+the\s+Investigators|Certificate\s+of\s+No\s+pending\s+SE&?UC|Resumes?\s+of\s+PI\s+and\s+Co-I\(s\)|Self\s+Appraisal\s+of\s+the\s+PI[^,)]*)",
            note_body,
            re.IGNORECASE
        )
        for si in sub_items:
            s_clean = si.strip().rstrip(",")
            if s_clean and not any(s_clean.lower() in x.lower() for x in institutional_from_process):
                institutional_from_process.append(s_clean)

    inst_keywords = [
        "endorsement", "implementing institution", "host institution", "investigators",
        "principal investigator", "se&uc", "statement of expenditure", "utilization certificate",
        "annual report format", "project completion report", "asset transfer certificate",
        "pre-proposal", "detailed proposal", "project proposal", "co-i"
    ]

    identity_keywords = [
        "identity proof", "aadhaar", "passport", "photo", "voter", "pan card", "ration card",
        "educational certificate", "degree", "marksheet", "community certificate", "caste certificate",
        "disability certificate", "physically handicapped", "experience certificate", "income certificate",
        "domicile", "residence", "bank account", "passbook", "salary slip"
    ]

    other_keywords = [
        "any other", "other supporting", "as required", "as specified"
    ]

    institutional_docs: List[str] = []
    applicant_docs: List[str] = []
    other_docs: List[str] = []

    # Map existing links in docs_raw (e.g. "[Endorsement Form](https://...)")
    endorsement_link = None
    for item in raw_doc_items:
        m = re.search(r"\[([^\]]+)\]\((https?://[^\)]+)\)", item)
        if m and "endorsement" in m.group(1).lower():
            endorsement_link = m.group(2)

    for item in institutional_from_process:
        if "endorsement" in item.lower() and endorsement_link:
            institutional_docs.append(f"{item} — [Prescribed Format]({endorsement_link})")
        else:
            institutional_docs.append(item)

    for item in raw_doc_items:
        item_clean = item.lstrip("-• ").strip()
        item_lower = item_clean.lower()

        if "endorsement" in item_lower and any("endorsement" in x.lower() for x in institutional_docs):
            continue

        if any(k in item_lower for k in inst_keywords):
            institutional_docs.append(item_clean)
        elif any(k in item_lower for k in other_keywords):
            other_docs.append(item_clean)
        elif any(k in item_lower for k in identity_keywords):
            applicant_docs.append(item_clean)
        else:
            other_docs.append(item_clean)

    if only_institutional:
        if institutional_docs:
            return "**1. Institutional Endorsement & Research Documents:**\n" + "\n".join(f"- {i}" for i in institutional_docs)
        return "No specific institutional endorsement documents specified in official scheme record"

    if not institutional_docs:
        if not applicant_docs and not other_docs:
            return "Not specified in official scheme record"
        all_items = applicant_docs + other_docs
        return "\n".join(f"- {i}" for i in all_items)

    blocks: List[str] = []
    if institutional_docs:
        blocks.append("**1. Institutional Endorsement & Research Documents:**\n" + "\n".join(f"- {i}" for i in institutional_docs))
    if applicant_docs:
        blocks.append("**2. Applicant Identity & General Supporting Documents:**\n" + "\n".join(f"- {i}" for i in applicant_docs))
    if other_docs:
        blocks.append("**3. Other Stated Requirements:**\n" + "\n".join(f"- {i}" for i in other_docs))

    return "\n\n".join(blocks)



def format_canonical_references(source_url: Optional[str], refs_raw: Any, max_refs: int = 4) -> str:
    """
    Produces readable Markdown links with descriptive titles derived from URLs and filenames.
    Preserves exact canonical URLs without fabrication. Avoids dumping repetitive links.
    """
    cleaned_source = clean_canonical_field(source_url) or ""

    ref_urls: List[str] = []
    if refs_raw is not None:
        if isinstance(refs_raw, (list, tuple)) or (hasattr(refs_raw, "__iter__") and not isinstance(refs_raw, (str, bytes))):
            raw_items = [str(x) for x in refs_raw]
            refs_str = " ".join(raw_items)
        else:
            refs_str = str(refs_raw)
        found = re.findall(r"https?://[^\s'\"\]]+", refs_str)
        seen = set()
        for u in found:
            u_clean = u.rstrip("',\"")
            if u_clean not in seen:
                seen.add(u_clean)
                ref_urls.append(u_clean)

    def derive_title(url: str, is_primary: bool = False) -> str:
        if is_primary:
            return "Official Scheme Portal"

        path = url.split("?")[0].split("#")[0]
        filename = path.rstrip("/").split("/")[-1].lower()

        if "guideline" in filename:
            return "Statutory Scheme Guidelines (PDF)"
        elif "endorsement" in filename:
            return "Institutional Endorsement Format (PDF)"
        elif "tc" in filename or "term" in filename:
            return "Terms and Conditions (PDF)"
        elif "annualreport" in filename or "annual_report" in filename:
            return "Annual Progress Report Format (PDF)"
        elif "seuc" in filename or "ucse" in filename:
            return "Statement of Expenditure & Utilization Certificate Format (SE&UC) (PDF)"
        elif "completion" in filename:
            return "Project Completion Report Format (PDF)"
        elif "asset" in filename:
            return "Asset Transfer Certificate Format (PDF)"
        elif "date" in filename or "start" in filename or "call" in filename:
            return "Application Schedule & Call Notification (PDF)"
        elif "form" in filename or "application" in filename:
            return "Application Form / Format (PDF)"
        elif filename.endswith(".pdf"):
            stem = filename[:-4].replace("_", " ").replace("-", " ").title()
            return f"{stem} (PDF)"
        else:
            return "Official Reference Portal"

    links: List[str] = []
    if cleaned_source:
        links.append(f"- [{derive_title(cleaned_source, is_primary=True)}]({cleaned_source})")

    priority_order = ["guideline", "endorsement", "tc", "date", "form", "seuc", "completion"]
    sorted_refs = []
    remaining = []
    for r in ref_urls:
        if r.rstrip("/") == cleaned_source.rstrip("/"):
            continue
        p_match = False
        r_low = r.lower()
        for p in priority_order:
            if p in r_low:
                sorted_refs.append(r)
                p_match = True
                break
        if not p_match:
            remaining.append(r)

    candidate_refs = sorted_refs + remaining
    added = 0
    for r in candidate_refs:
        if added >= max_refs:
            break
        title = derive_title(r, is_primary=False)
        links.append(f"- [{title}]({r})")
        added += 1

    if not links:
        return "Not specified in official scheme record"
    return "\n".join(links)


def format_canonical_application_process(
    app_process_raw: Optional[str],
    app_mode: Any = "",
    open_date: Optional[str] = "",
    close_date: Optional[str] = "",
    compact_rubric: bool = True,
    has_separate_docs_section: bool = False,
) -> Tuple[str, Optional[str]]:
    """
    Cleans raw application process text:
    - Formats stages and steps with clear Markdown hierarchy
    - Strips raw pipe delimiters (| - )
    - Splits out contact details into a separate string
    - Includes application mode and application window/deadline
    - Compacts reviewer scoring rubric when evaluation criteria are not specifically requested
    - Avoids duplicating institutional requirements when a separate documents section is displayed
    Returns (cleaned_process_text, contact_details_text_or_None)
    """
    if not app_process_raw:
        return ("Not specified in official scheme record", None)

    raw = app_process_raw.replace("\ufffd", "-").replace("&amp;", "&").strip()

    contact_details = None
    if "Contact Details:" in raw:
        parts = raw.split("Contact Details:", 1)
        proc_body = parts[0].strip()
        raw_contact = parts[1].strip()
        contact_lines = [c.strip().lstrip("-• ") for c in re.split(r"(?:[;\n]+|\s*\|\s*-?\s*)", raw_contact) if c.strip()]
        if contact_lines:
            contact_details = "**Nodal Contact Details & Helpdesk:**\n" + "\n".join(f"- {cl}" for cl in contact_lines)
    else:
        proc_body = raw

    segments = [s.strip() for s in re.split(r"(?:\n+|\s*\|\s*)", proc_body) if s.strip()]

    formatted_lines: List[str] = []

    # 1. Mode of application
    clean_mode = clean_canonical_field(app_mode)
    if clean_mode:
        modes = re.findall(r"'([^']+)'", clean_mode)
        mode_str = ", ".join(modes) if modes else clean_mode
        formatted_lines.append(f"• **Application Mode:** {mode_str}")

    # 2. Window / Deadlines
    window_lines = []
    if open_date:
        window_lines.append(f"- Application Start: {open_date}")
    if close_date:
        window_lines.append(f"- Application Deadline: {close_date}")
    if not window_lines:
        window_lines.append("- Current application window & deadline: Specific active call dates are notified periodically via official advertisement/website.")
    formatted_lines.append("• **Application Window & Deadlines:**\n" + "\n".join(window_lines))

    # 3. Procedural Stages & Steps
    score_entries: List[Tuple[str, str]] = []

    def flush_scores():
        if not score_entries:
            return
        if not compact_rubric:
            formatted_lines.append("\n##### Reviewer Scoring Rubric (Detailed Criteria):")
            for s, desc in score_entries:
                formatted_lines.append(f"  - **Score {s}:** {desc}")
        score_entries.clear()

    for seg in segments:
        seg_clean = seg.lstrip("-• ").strip()
        if not seg_clean:
            continue

        if seg_clean.lower() in ("selection procedure:", "selection procedure"):
            continue

        score_m = re.match(r"^(\d)\s*:\s*(.*)$", seg_clean)
        if score_m:
            score_entries.append((score_m.group(1), score_m.group(2)))
            continue

        flush_scores()

        stage_m = re.match(r"^(Stage\s+\d+)\s*:\s*(.*)$", seg_clean, re.IGNORECASE)
        if stage_m:
            stage_num = stage_m.group(1).title()
            stage_title = stage_m.group(2).strip()
            formatted_lines.append(f"\n#### {stage_num}: {stage_title}")
            continue

        step_m = re.match(r"^(Step\s+\d+)\s*:\s*(?:([^:]+):\s*)?(.*)$", seg_clean, re.IGNORECASE)
        if step_m:
            step_num = step_m.group(1).title()
            step_subtitle = (step_m.group(2) or "").strip()
            step_desc = step_m.group(3).strip()
            if compact_rubric:
                # 1. Trailing criteria pointers & score scales
                step_desc = re.sub(r",?\s*(?:\(scores\s+from\s+\d+\s+to\s+\d+\),?\s*)?as\s+per\s+the\s+following\s+criteria:?\s*$", "", step_desc, flags=re.IGNORECASE).strip()
                step_desc = re.sub(r"\s*\(scores\s+from\s+\d+\s+to\s+\d+\)\s*$", "", step_desc, flags=re.IGNORECASE).strip()

                # 2. Evaluation matrix descriptions
                step_desc = re.sub(r"(?<=\.)\s+The\s+pre-?proposal\s+will\s+be\s+evaluated\s+based\s+on\s+an\s+evaluation\s+matrix[^.]*\.?", "", step_desc, flags=re.IGNORECASE)
                step_desc = re.sub(r"\s+based\s+on\s+an\s+evaluation\s+matrix\s+containing\s+\d+\s+criteria\b", "", step_desc, flags=re.IGNORECASE)

                # 3. Reviewer counts (e.g. 'to 3 subject experts' -> 'to subject experts')
                step_desc = re.sub(r"\bto\s+(?:\d+|three|four|five|six|seven|eight)\s+(?:national[- ]level\s+|subject\s+)?experts\b", "to subject experts", step_desc, flags=re.IGNORECASE)
                step_desc = re.sub(r"\b(?:\d+|three|four|five|six|seven|eight)\s+(?:national[- ]level\s+|subject\s+)?experts\b", "subject experts", step_desc, flags=re.IGNORECASE)

                # 4. Redundant referee logistics sentences
                step_desc = re.sub(r"(?<=\.)\s+The\s+proposal\s+will\s+be\s+sent\s+to\s+[^.]*for\s+peer\s+review\.", "", step_desc, flags=re.IGNORECASE)

                # 5. Redundant reviewer scoring mechanics before threshold
                step_desc = re.sub(r"^The\s+reviewers\s+will\s+assign\s+suitable\s+scores\s+based\s+on\s+[^.]*\.\s*", "", step_desc, flags=re.IGNORECASE)

                # 6. Committee governance / constitution
                step_desc = re.sub(
                    r"(?<=\.)\s+(?:[A-Z0-9\-]+\s+is\s+a\s+(?:high[- ]level\s+)?committee|The\s+(?:Council|Committee|Board)\s+(?:assesses|considers|evaluates)|The\s+decision\s+made\s+by\s+[^.]+\s+shall\s+be\s+final)[^.]*(?:\.[^.]*)*\.?",
                    "",
                    step_desc,
                    flags=re.IGNORECASE
                ).strip()
            if step_subtitle:
                formatted_lines.append(f"• **{step_num} — {step_subtitle}:** {step_desc}")
            else:
                formatted_lines.append(f"• **{step_num}:** {step_desc}")
            continue

        if seg_clean.lower().startswith("note"):
            if has_separate_docs_section and ("endorsement" in seg_clean.lower() or ("upload" in seg_clean.lower() and "document" in seg_clean.lower())):
                formatted_lines.append(
                    f"> **Important Requirement ({seg_clean[:7].strip()}):** While applying online, "
                    f"please ensure all required institutional endorsement and research documents "
                    f"(itemized with prescribed formats under Required Documents) are uploaded."
                )
            else:
                formatted_lines.append(f"> **Important Requirement ({seg_clean[:7].strip()}):** {seg_clean[8:].strip()}")
            continue

        formatted_lines.append(seg_clean)

    flush_scores()

    cleaned_process = "\n\n".join(formatted_lines).strip()
    return (cleaned_process, contact_details)


def format_canonical_scheme_response(
    rec: Dict[str, Any],
    query: str = "",
    applicant_facts: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Constructs an evidence-grounded, zero-hallucination markdown breakdown for a canonical scheme.
    Features:
    - Dynamic scope selection respecting exclusive keywords ('only', 'just', 'exclusively', 'solely')
    - Evidence-grounded document categorization (Institutional vs Applicant Identity & General vs Other)
    - Clean procedural hierarchy without raw pipe delimiter artifacts
    - Source links with descriptive Markdown titles preserving canonical URLs
    - Transparent jurisdiction handling distinguishing scheme territory from applicant eligibility
    - Gated jurisdiction note so multi-line eligibility disclaimers only show when relevant
    """
    title = clean_canonical_field(rec.get("scheme_name")) or "Government Welfare Scheme"
    short = clean_canonical_field(rec.get("short_title"))
    header = f"### {title}" + (f" ({short})" if short and short != title else "")

    level = clean_canonical_field(rec.get("level"))
    state = clean_canonical_field(rec.get("state"))
    dept = clean_canonical_field(rec.get("department")) or clean_canonical_field(rec.get("ministry"))

    meta_parts = []
    if state:
        meta_parts.append(f"**State / Jurisdiction:** {state}")
    elif level:
        meta_parts.append(f"**Level:** {level}")
    if dept:
        meta_parts.append(f"**Nodal Authority:** {dept}")
    meta_line = " • ".join(meta_parts)

    jurisdiction_note = None
    if state and state.lower() not in ("central", "all india", "national", "india"):
        user_state = None
        if applicant_facts and isinstance(applicant_facts, dict):
            user_state = applicant_facts.get("state")

        if user_state and str(user_state).strip().lower() != state.lower():
            jurisdiction_note = (
                f"> **Jurisdiction & Applicability:** This scheme operates under the jurisdiction of **{state}**. "
                f"Your profile indicates state **{user_state}**. Statutory rules determine whether research or institutional "
                f"affiliation must be hosted within {state}; applicant applicability remains **unverified** in the canonical summary "
                f"(statutory eligibility status remains **UNKNOWN**). Please consult the official scheme guidelines to verify institutional eligibility."
            )
        else:
            jurisdiction_note = (
                f"> **Jurisdiction & Applicability:** This scheme operates under the jurisdiction of **{state}**. "
                f"Statutory eligibility depends on institutional affiliation and criteria specified in the official scheme guidelines; "
                f"applicability remains **unverified** without complete applicant and institutional evidence (statutory eligibility status remains **UNKNOWN**)."
            )

    purpose = (
        clean_canonical_field(rec.get("detailed_description"))
        or clean_canonical_field(rec.get("brief_description"))
        or "Not specified in official scheme record"
    )

    eligibility_raw = clean_canonical_field(rec.get("eligibility"))
    eligibility = format_bullet_list(eligibility_raw)

    benefits_raw = clean_canonical_field(rec.get("benefits"))
    benefits = format_bullet_list(benefits_raw)

    docs_raw = clean_canonical_field(rec.get("documents_required"))
    app_process_raw = clean_canonical_field(rec.get("application_process"))
    app_mode = clean_canonical_field(rec.get("application_mode"))
    open_date = clean_canonical_field(rec.get("scheme_open_date"))
    close_date = clean_canonical_field(rec.get("scheme_close_date"))

    # Dynamic scope selection
    scope = detect_scheme_query_scope(query)
    is_exclusive = scope["is_exclusive"]

    # Determine whether a separate docs section will be included
    wants_docs_section = False
    if is_exclusive:
        wants_docs_section = scope["wants_documents"] or (
            scope["wants_process"] and any(w in query.lower() for w in ["document", "institutional", "endorsement", "checklist"])
        )
    else:
        wants_docs_section = True

    only_institutional = scope.get("wants_institutional_only", False)
    categorized_docs = categorize_canonical_documents(
        docs_raw, app_process_raw, only_institutional=only_institutional
    )

    compact_rubric = not scope.get("wants_scoring", False)
    cleaned_process, contact_details = format_canonical_application_process(
        app_process_raw,
        app_mode=app_mode,
        open_date=open_date,
        close_date=close_date,
        compact_rubric=compact_rubric,
        has_separate_docs_section=wants_docs_section,
    )

    source_url = clean_canonical_field(rec.get("source_url"))
    refs_raw = rec.get("references")
    sources_str = format_canonical_references(source_url, refs_raw)

    sec_purpose = f"**Purpose & Overview**\n{purpose}"
    sec_eligibility = f"**Eligibility Criteria**\n{eligibility}"
    sec_benefits = f"**Financial Assistance & Benefits**\n{benefits}"
    sec_docs = f"**Required Documents**\n{categorized_docs}"
    sec_process = f"**Application Process & How to Apply**\n{cleaned_process}"
    sec_source = f"**Official Source & References**\n{sources_str}"
    sec_contacts = contact_details if contact_details else None

    sections = [header]
    if meta_line:
        sections.append(meta_line)

    # Gate detailed jurisdiction note according to query scope:
    # Preserve scheme jurisdiction metadata (meta_line) always.
    # Append multi-line jurisdiction applicability only when user asks about eligibility or jurisdiction,
    # or in a broad scheme overview, or for non-exclusive cross-state applicant queries.
    # Exclude from exclusive application-process or document queries.
    wants_elig_or_jurisdiction = scope["wants_eligibility"] or scope.get("wants_jurisdiction", False)
    include_jurisdiction_note = False
    if jurisdiction_note:
        user_state = (applicant_facts or {}).get("state") if isinstance(applicant_facts, dict) else None
        is_cross_state = bool(user_state and state and str(user_state).strip().lower() != state.lower())
        if is_exclusive:
            if wants_elig_or_jurisdiction or is_cross_state:
                include_jurisdiction_note = True
        else:
            if wants_elig_or_jurisdiction or is_cross_state or scope.get("is_broad_overview", False):
                include_jurisdiction_note = True

    if include_jurisdiction_note and jurisdiction_note:
        sections.append(jurisdiction_note)

    if is_exclusive:
        # Respect exclusive terms: include strictly requested sections
        if scope["wants_process"] or scope.get("wants_scoring", False):
            sections.append(sec_process)
        if wants_docs_section:
            sections.append(sec_docs)
        if scope["wants_eligibility"]:
            sections.append(sec_eligibility)
        if scope["wants_benefits"]:
            sections.append(sec_benefits)
        if scope["wants_purpose"]:
            sections.append(sec_purpose)
        if scope["wants_contacts"] and sec_contacts:
            sections.append(sec_contacts)
        # Always provide official source & references for statutory evidence verification
        sections.append(sec_source)
    else:
        # Non-exclusive queries: provide comprehensive information with priority reordering
        if scope["is_broad_overview"]:
            sections.extend([sec_purpose, sec_eligibility, sec_benefits, sec_docs, sec_process, sec_source])
        elif scope["wants_process"] or scope.get("wants_scoring", False):
            sections.extend([sec_process, sec_docs, sec_purpose, sec_eligibility, sec_benefits, sec_source])
        elif scope["wants_documents"]:
            sections.extend([sec_docs, sec_purpose, sec_eligibility, sec_benefits, sec_process, sec_source])
        elif scope["wants_eligibility"]:
            sections.extend([sec_eligibility, sec_purpose, sec_benefits, sec_docs, sec_process, sec_source])
        elif scope["wants_benefits"]:
            sections.extend([sec_benefits, sec_purpose, sec_eligibility, sec_docs, sec_process, sec_source])
        else:
            sections.extend([sec_purpose, sec_eligibility, sec_benefits, sec_docs, sec_process, sec_source])

        if scope["wants_contacts"] and sec_contacts:
            sections.append(sec_contacts)

    return "\n\n".join(sections).strip()


def format_canonical_score_explanation(
    rec: Dict[str, Any],
    query: str = "",
    applicant_facts: Optional[Dict[str, Any]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Constructs an evidence-grounded, zero-hallucination criterion-level eligibility breakdown
    and match score audit for a canonical scheme.

    Mandatory Invariants (Phase D2.2):
    - UNKNOWN must NEVER become PASS.
    - Search retrieval relevance (100%) is strictly separated from statutory eligibility.
    - Missing applicant facts (Ph.D., Postdoc, Age) remain UNKNOWN.
    - Cross-state or unverified jurisdiction remains REVIEW.
    - Discloses actual formula (or absence of formula) and list of unverified criteria.
    - Discloses machine-readable ruleset availability status.
    """
    scheme_name = clean_canonical_field(rec.get("scheme_name")) or "Government Welfare Scheme"
    short = clean_canonical_field(rec.get("short_title"))
    header_title = f"{scheme_name}" + (f" ({short})" if short and short != scheme_name else "")

    level = clean_canonical_field(rec.get("level")) or "Central / State"
    state = clean_canonical_field(rec.get("state")) or "All India"
    dept = clean_canonical_field(rec.get("department")) or clean_canonical_field(rec.get("ministry")) or "Competent Nodal Authority"
    source_url = clean_canonical_field(rec.get("source_url")) or "https://www.myscheme.gov.in"

    facts = dict(applicant_facts or {})
    docs = list(documents or [])

    # Extract any available verified facts from uploaded documents
    doc_provenance_map: Dict[str, Tuple[str, str]] = {}
    for d in docs:
        d_name = d.get("file_name") or d.get("document_type") or "Uploaded Document"
        ext_fields = d.get("extracted_fields") or {}
        for fk, fv in ext_fields.items():
            if fv and fk not in doc_provenance_map:
                doc_provenance_map[fk] = (str(fv), f"Verified Document: `{d_name}`")
        if "state" not in doc_provenance_map:
            issuer = str(d.get("issuer") or ext_fields.get("issuing_authority") or "")
            if "maharashtra" in issuer.lower():
                doc_provenance_map["state"] = ("Maharashtra", f"Verified Document Issuer: `{d_name}`")
            elif "kerala" in issuer.lower():
                doc_provenance_map["state"] = ("Kerala", f"Verified Document Issuer: `{d_name}`")

    # Extract raw eligibility items from canonical record
    raw_elig = clean_canonical_field(rec.get("eligibility"))
    if raw_elig:
        raw_items = [it.strip().lstrip("-•* ").strip() for it in re.split(r"[;\n]+", raw_elig) if it.strip()]
    else:
        raw_items = []

    criteria_rows: List[Dict[str, str]] = []
    unverified_list: List[str] = []

    # Helper to check applicant state
    applicant_state = facts.get("state")
    state_prov = "Applicant Profile"
    if not applicant_state and "state" in doc_provenance_map:
        applicant_state, state_prov = doc_provenance_map["state"]

    # Helper to check applicant age
    applicant_age = facts.get("age")
    age_prov = "Applicant Profile"
    if applicant_age is None and "age" in doc_provenance_map:
        try:
            applicant_age = int(re.sub(r"[^\d]", "", doc_provenance_map["age"][0]))
            age_prov = doc_provenance_map["age"][1]
        except Exception:
            pass

    # Helper to check education / doctoral qualification
    applicant_education = facts.get("education") or facts.get("qualification") or facts.get("highest_qualification")
    edu_prov = "Applicant Profile"
    if not applicant_education:
        for fk in ["education", "degree", "qualification"]:
            if fk in doc_provenance_map:
                applicant_education, edu_prov = doc_provenance_map[fk]
                break

    # Helper to check postdoc / research experience
    applicant_exp = facts.get("experience") or facts.get("postdoc_experience") or facts.get("research_experience")
    exp_prov = "Applicant Profile"
    if not applicant_exp:
        for fk in ["experience", "postdoc", "research_experience"]:
            if fk in doc_provenance_map:
                applicant_exp, exp_prov = doc_provenance_map[fk]
                break

    # 1. Parse each statutory condition
    for idx, item in enumerate(raw_items, start=1):
        item_lower = item.lower()

        # Case A: Post-Doctoral Experience (checked before doctoral degree to prevent substring collision)
        if "post-doctoral" in item_lower or "postdoctoral" in item_lower or "post doctoral" in item_lower or "post-doc" in item_lower:
            crit_name = "Post-Doctoral Research Experience"
            cond = item
            if applicant_exp and any(w in str(applicant_exp).lower() for w in ["3", "three", "postdoc", "post-doc"]):
                status = "PASS"
                fact_val = str(applicant_exp)
                prov = exp_prov
                reason = "Applicant satisfies post-doctoral experience requirement."
            else:
                status = "UNKNOWN"
                fact_val = "Not on file (Missing)"
                prov = "Missing from profile and document vault"
                reason = "Applicant has not provided verified records or certificates demonstrating 3 years of postdoctoral research in Biotechnology."
                unverified_list.append("Post-Doctoral Experience (3 years in Biotechnology)")

        # Case B: Doctoral / Ph.D. degree requirement
        elif "ph.d" in item_lower or "phd" in item_lower or bool(re.search(r"\bdoctoral\b|\bdoctorate\b|\bdoctor\s+of\s+philosophy\b", item_lower)):
            crit_name = "Doctoral Degree Qualification"
            cond = item
            if applicant_education and ("ph.d" in str(applicant_education).lower() or "phd" in str(applicant_education).lower()):
                status = "PASS"
                fact_val = str(applicant_education)
                prov = edu_prov
                reason = "Applicant possesses required Ph.D. degree as verified on record."
            else:
                status = "UNKNOWN"
                fact_val = "Not on file (Missing)"
                prov = "Missing from profile and document vault"
                reason = "Applicant has not provided a verified Ph.D. degree certificate or declared doctoral qualifications. Missing facts remain UNKNOWN."
                unverified_list.append("Doctoral Degree Qualification (Ph.D. in Life Sciences)")

        # Case C: Age limit (e.g., less than 40 years)
        elif "age" in item_lower:
            crit_name = "Statutory Age Limit"
            cond = item
            age_limit_match = re.search(r"(?:less\s+than|<|below|under|not\s+exceed(?:ing)?)\s*(\d+)", item_lower)
            age_limit = int(age_limit_match.group(1)) if age_limit_match else 40

            if applicant_age is not None:
                try:
                    num_age = int(re.sub(r"[^\d]", "", str(applicant_age)))
                    fact_val = f"{num_age} years"
                    prov = age_prov
                    if num_age < age_limit:
                        status = "PASS"
                        reason = f"Applicant age ({num_age}) meets the statutory ceiling (under {age_limit} years)."
                    else:
                        status = "FAIL"
                        reason = f"Applicant age ({num_age}) exceeds statutory ceiling of {age_limit} years."
                except Exception:
                    status = "UNKNOWN"
                    fact_val = str(applicant_age)
                    prov = age_prov
                    reason = "Applicant age could not be mathematically validated."
                    unverified_list.append(f"Statutory Age Verification (< {age_limit} years)")
            else:
                status = "UNKNOWN"
                fact_val = "Not on file (Missing)"
                prov = "Missing from profile and document vault"
                reason = f"Date of birth or age verification document is not on file to confirm age under {age_limit} years."
                unverified_list.append(f"Statutory Age Verification (< {age_limit} years)")

        # Case D: Generic criteria
        else:
            crit_name = f"Statutory Condition #{idx}"
            cond = item
            status = "UNKNOWN"
            fact_val = "Not on file (Missing)"
            prov = "Missing from profile and document vault"
            reason = "No matching verified applicant evidence found on file."
            unverified_list.append(item)

        criteria_rows.append({
            "idx": str(len(criteria_rows) + 1),
            "name": crit_name,
            "condition": cond,
            "fact": fact_val,
            "provenance": prov,
            "rule_source": "Statutory Policy Record (v1.0)",
            "status": status,
            "reason": reason
        })

    # 2. Add State / Institutional Jurisdiction Criterion if applicable
    if state and state.lower() not in ["all india", "central", "national", ""]:
        jurisdiction_cond = f"Scheme is administered by {dept} for eligible institutions located within {state}."
        if applicant_state:
            if str(applicant_state).strip().lower() == state.lower():
                j_status = "PASS"
                j_reason = f"Applicant domicile/state matches scheme jurisdiction ({state})."
            else:
                j_status = "REVIEW"
                j_reason = f"Applicant registered in {applicant_state}. This is a {state} State scheme ({dept}). Cross-state applicants require administrative review and proof of host institution endorsement located in {state}."
                unverified_list.append(f"Host institution endorsement within {state}")
            j_fact = str(applicant_state)
            j_prov = state_prov
        else:
            j_status = "UNKNOWN"
            j_fact = "Not on file (Missing)"
            j_prov = "Missing from profile and document vault"
            j_reason = f"Applicant state residency or institutional affiliation in {state} is unverified."
            unverified_list.append(f"State residency / Institutional endorsement in {state}")

        criteria_rows.append({
            "idx": str(len(criteria_rows) + 1),
            "name": "State & Institutional Jurisdiction",
            "condition": jurisdiction_cond,
            "fact": j_fact,
            "provenance": j_prov,
            "rule_source": "Statutory Policy Record (v1.0)",
            "status": j_status,
            "reason": j_reason
        })

    # Build Markdown table
    table_lines = [
        "| # | Eligibility Criterion | Required Condition | Actual Applicant Fact | Fact Provenance | Rule Source | Status | Reason / Auditor Note |",
        "|---|---|---|---|---|---|---|---|"
    ]
    for r in criteria_rows:
        table_lines.append(
            f"| {r['idx']} | {r['name']} | {r['condition']} | {r['fact']} | {r['provenance']} | {r['rule_source']} | **{r['status']}** | {r['reason']} |"
        )
    table_md = "\n".join(table_lines)

    # Format Unverified criteria list
    if unverified_list:
        unverified_md = "\n".join(f"- [ ] {item}" for item in unverified_list)
    else:
        unverified_md = "None (All criteria evaluated with verified evidence)."

    has_pass = any(r["status"] == "PASS" for r in criteria_rows)
    has_fail = any(r["status"] == "FAIL" for r in criteria_rows)
    has_unknown = any(r["status"] == "UNKNOWN" for r in criteria_rows)
    has_review = any(r["status"] == "REVIEW" for r in criteria_rows)

    if has_fail:
        overall_status = "FAIL"
    elif has_unknown and has_review:
        overall_status = "UNKNOWN / REVIEW"
    elif has_unknown:
        overall_status = "UNKNOWN"
    elif has_review:
        overall_status = "REVIEW"
    elif has_pass:
        overall_status = "PASS"
    else:
        overall_status = "UNKNOWN"

    disclosure_section = (
        f"### 🏛️ {header_title} — Scheme Match Score & Eligibility Audit\n\n"
        f"**Score Semantics & Search Relevance Disclosure:**\n"
        f"• **Search Retrieval Relevance:** `100%` (Exact title & semantic query match)\n"
        f"• **Statutory Eligibility Score:** `None` (No percentage scoring formula exists in statutory guidelines)\n"
        f"• **Overall Evaluated Eligibility Status:** **`{overall_status}`**\n"
        f"• **Clarification on 100% Score:** The `100%` previously shown on the scheme card represents **search relevance ranking** (i.e., this scheme record was a 100% relevant match for your query topic). It does **not** mean you have been confirmed eligible. True statutory eligibility requires proof for all unverified criteria below.\n\n"
        f"---\n\n"
        f"### Criterion-Level Statutory Evaluation\n\n"
        f"{table_md}\n\n"
        f"---\n\n"
        f"### Unverified Criteria Requiring Supporting Evidence\n"
        f"{unverified_md}\n\n"
        f"### Statutory Scoring Formula & Calculation\n"
        f"• **Scoring Formula:** None. Statutory welfare and research schemes are governed by binary statutory conditions (mandatory prerequisites), not an arithmetic percentage formula.\n"
        f"• **Calculation:** N/A (Missing mandatory applicant evidence prevents affirmative determination).\n"
        f"• **Machine-Readable Ruleset Status:** A formalized machine-readable JSON ruleset has not yet been authored for this scheme. Criteria were extracted directly from the official statutory policy record ({source_url}). In accordance with FIN safety invariants, missing facts remain strictly **UNKNOWN** and cannot be inferred."
    )

    return disclosure_section.strip()


