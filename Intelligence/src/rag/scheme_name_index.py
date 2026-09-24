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
        except Exception:
            pass

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
