"""
FIN Multi-Scheme Query Decomposition.
Identifies comparison, multi-scheme, and multi-entity queries,
decomposes them into atomic sub-queries, and merges results fairly so that
no candidate scheme is suppressed by global score concentration.

CRITICAL INVARIANT:
Candidate candidates remain candidates for retrieval;
decomposition never forces or alters statutory eligibility logic.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class DecomposedEntity:
    entity_text: str
    scheme_slug: Optional[str] = None
    sub_query: str = ""


@dataclass
class DecompositionResult:
    is_multi_entity: bool
    original_query: str
    entities: List[DecomposedEntity] = field(default_factory=list)
    comparison_type: Optional[str] = None  # VS, COMPARE, MULTI_TARGET


# Regex patterns indicating comparison or multi-scheme intent
COMPARISON_SPLIT_PATTERNS = [
    re.compile(r"\b(?:vs\.?|versus)\b", re.IGNORECASE),
    re.compile(r"\bcompare\s+(.+?)\s+(?:and|with|to)\s+(.+)", re.IGNORECASE),
    re.compile(r"\bdifference\s+between\s+(.+?)\s+and\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(.+?)\s+(?:aur|and)\s+(.+?)\s+(?:me\s+kya\s+difference|ka\s+difference|difference|comparison)\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+is\s+better\s*:\s*(.+?)\s+(?:or|vs)\s+(.+)", re.IGNORECASE),
]


class MultiSchemeDecomposer:
    """
    Detects and decomposes multi-scheme queries into parallel single-scheme sub-queries.
    """

    def __init__(self, scheme_index: Any = None):
        if scheme_index is None:
            from .scheme_name_index import SchemeNameIndex
            scheme_index = SchemeNameIndex()
        self.scheme_index = scheme_index

    def decompose(self, query_text: str) -> DecompositionResult:
        """Analyzes query text and decomposes into entities if multiple schemes are targeted."""
        text = query_text.strip()

        # Check explicit comparison patterns
        # 1. "X vs Y"
        if re.search(r"\b(?:vs\.?|versus)\b", text, re.IGNORECASE):
            parts = re.split(r"\b(?:vs\.?|versus)\b", text, flags=re.IGNORECASE)
            if len(parts) >= 2:
                entities = self._build_entities_from_parts(parts, text)
                if len(entities) >= 2:
                    return DecompositionResult(
                        is_multi_entity=True,
                        original_query=text,
                        entities=entities,
                        comparison_type="VS",
                    )

        # 2. "Compare X and Y"
        m = re.search(r"\bcompare\s+(.+?)\s+(?:and|with|to)\s+(.+)", text, re.IGNORECASE)
        if m:
            parts = [m.group(1), m.group(2)]
            entities = self._build_entities_from_parts(parts, text)
            if len(entities) >= 2:
                return DecompositionResult(
                    is_multi_entity=True,
                    original_query=text,
                    entities=entities,
                    comparison_type="COMPARE",
                )

        # 3. "Difference between X and Y"
        m = re.search(r"\bdifference\s+between\s+(.+?)\s+and\s+(.+)", text, re.IGNORECASE)
        if m:
            parts = [m.group(1), m.group(2)]
            entities = self._build_entities_from_parts(parts, text)
            if len(entities) >= 2:
                return DecompositionResult(
                    is_multi_entity=True,
                    original_query=text,
                    entities=entities,
                    comparison_type="DIFFERENCE",
                )

        # 4. "X aur Y me kya difference / ka difference / comparison"
        m = re.search(r"(.+?)\s+(?:aur|and)\s+(.+?)\s+(?:me\s+kya\s+difference|ka\s+difference|difference|comparison)\b", text, re.IGNORECASE)
        if m:
            parts = [m.group(1), m.group(2)]
            entities = self._build_entities_from_parts(parts, text)
            if len(entities) >= 2:
                return DecompositionResult(
                    is_multi_entity=True,
                    original_query=text,
                    entities=entities,
                    comparison_type="DIFFERENCE",
                )

        # 5. "Which is better: X or Y"
        m = re.search(r"which\s+is\s+better(?:\s*:\s*|\s+for\s+.+?:\s*|\s+for\s+.+?\s+between\s+|\s+)?(.+?)\s+(?:or|vs\.?)\s+(.+)", text, re.IGNORECASE)
        if m:
            parts = [m.group(1), m.group(2)]
            entities = self._build_entities_from_parts(parts, text)
            if len(entities) >= 2:
                return DecompositionResult(
                    is_multi_entity=True,
                    original_query=text,
                    entities=entities,
                    comparison_type="WHICH_IS_BETTER",
                )

        # 6. Multi-scheme detection via scheme name index scanning
        # Check if multiple distinct known scheme entities are mentioned
        matched_slugs: Dict[str, str] = {}
        for part in re.split(r"[,;]|\band\b|\baur\b|\bor\b|\bvs\.?\b", text, flags=re.IGNORECASE):
            p_strip = part.strip()
            if not p_strip:
                continue
            m = self.scheme_index.match(p_strip)
            if m and m.scheme_slug not in matched_slugs:
                matched_slugs[m.scheme_slug] = p_strip

        if len(matched_slugs) >= 2:
            entities = [
                DecomposedEntity(
                    entity_text=raw_part,
                    scheme_slug=slug,
                    sub_query=f"{raw_part} {self.scheme_index._slug_to_canonical.get(slug, '')}".strip(),
                )
                for slug, raw_part in matched_slugs.items()
            ]
            return DecompositionResult(
                is_multi_entity=True,
                original_query=text,
                entities=entities,
                comparison_type="MULTI_TARGET",
            )

        return DecompositionResult(
            is_multi_entity=False,
            original_query=text,
            entities=[],
        )

    def _build_entities_from_parts(self, parts: List[str], full_query: str) -> List[DecomposedEntity]:
        entities = []
        for p in parts:
            clean = p.strip().rstrip("?.,")
            clean = re.sub(r"^(?:which\s+is\s+better(?:\s+for)?|compare|difference\s+between)\s+", "", clean, flags=re.IGNORECASE).strip()
            if not clean:
                continue
            m = self.scheme_index.match(clean)
            slug = m.scheme_slug if m else None
            # If matched, include canonical name in sub_query for optimal retrieval
            canonical = self.scheme_index._slug_to_canonical.get(slug, "") if slug else ""
            sub_query = f"{clean} {canonical}".strip() if canonical else clean
            entities.append(DecomposedEntity(
                entity_text=clean,
                scheme_slug=slug,
                sub_query=sub_query,
            ))
        return entities

    @staticmethod
    def interleave_results(
        entity_results: Optional[List[List[Any]]] = None,
        total_limit: int = 5,
        per_entity_results: Optional[List[List[Any]]] = None,
        total_top_k: Optional[int] = None
    ) -> List[Any]:
        """
        Fair round-robin interleaving of candidate lists from decomposed sub-queries.
        Ensures all mentioned schemes are represented in the top-k results.
        """
        res_list = per_entity_results if per_entity_results is not None else (entity_results or [])
        limit = total_top_k if total_top_k is not None else total_limit

        merged = []
        seen_slugs: Set[str] = set()
        max_len = max((len(r) for r in res_list), default=0)

        for i in range(max_len):
            for r_list in res_list:
                if i < len(r_list):
                    item = r_list[i]
                    raw_slug = getattr(item, "scheme_slug", None) or getattr(item, "id", None)
                    norm_slug = str(raw_slug).replace("_", "-").strip().lower() if raw_slug else None
                    if norm_slug and norm_slug not in seen_slugs:
                        seen_slugs.add(norm_slug)
                        merged.append(item)
                    elif not norm_slug:
                        merged.append(item)
                    if len(merged) >= limit:
                        return merged

        return merged[:limit]
