"""
PolicySetu Sparse Keyword Retrieval (BM25Okapi).
Provides lexical matching for exact scheme names, acronyms, document names,
caste/category classifications, and policy clauses.
"""

import math
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from .models import RAGDocument


def tokenize_text(text: str) -> List[str]:
    """
    Multilingual-friendly Unicode tokenization.
    Splits on non-alphanumeric boundaries while preserving Devanagari and Latin scripts.
    """
    if not text:
        return []
    # Matches words across Latin, Devanagari (\u0900-\u097F), and standard alphanumeric
    tokens = re.findall(r"[\w\u0900-\u097F]+", text.lower())
    return [t for t in tokens if len(t) > 1]


class BM25Retriever:
    """
    Deterministic BM25Okapi implementation for sparse lexical retrieval.
    Computes inverted document frequencies and term frequencies over corpus chunks.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_ids: List[str] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.corpus_size: int = 0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        # Inverted index: term -> {doc_idx: term_count}
        self.inverted_index: Dict[str, Dict[int, int]] = {}
        self.doc_metadata: List[Dict[str, Any]] = []

    def fit(self, documents: List[RAGDocument]) -> "BM25Retriever":
        """Builds the BM25 inverted index from a list of RAGDocuments."""
        self.doc_ids = []
        self.doc_lengths = []
        self.doc_metadata = []
        self.inverted_index = {}
        self.doc_freqs = {}
        self.corpus_size = len(documents)

        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return self

        total_length = 0

        for idx, doc in enumerate(documents):
            self.doc_ids.append(doc.id)
            self.doc_metadata.append({
                "scheme_slug": doc.scheme_slug,
                "scheme_name": doc.scheme_name,
                "content_type": doc.content_type,
                "source_tier": doc.source_tier,
                "state": doc.state,
                "category": doc.category,
                "beneficiary_type": doc.beneficiary_type,
            })

            tokens = tokenize_text(doc.content)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            term_counts: Dict[str, int] = {}
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for term, count in term_counts.items():
                if term not in self.inverted_index:
                    self.inverted_index[term] = {}
                self.inverted_index[term][idx] = count
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_doc_len = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

        # Precompute IDF for all terms in vocab
        for term, df in self.doc_freqs.items():
            # Standard Lucene/BM25Okapi IDF formula with smoothing
            self.idf[term] = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))

        return self

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_fn: Optional[Any] = None
    ) -> List[Tuple[str, float, int]]:
        """
        Executes BM25 search.
        Returns: List of tuples (chunk_id, sparse_score, rank)
        """
        if self.corpus_size == 0 or not query.strip():
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        scores: Dict[int, float] = {}

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            idf = self.idf.get(token, 0.0)
            if idf <= 0:
                continue

            term_postings = self.inverted_index[token]
            for doc_idx, tf in term_postings.items():
                doc_len = self.doc_lengths[doc_idx]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                term_score = idf * (tf * (self.k1 + 1.0)) / denom
                scores[doc_idx] = scores.get(doc_idx, 0.0) + term_score

        if not scores:
            return []

        # Filter if requested
        ranked_items = []
        for doc_idx, score in scores.items():
            if filter_fn and not filter_fn(self.doc_metadata[doc_idx]):
                continue
            ranked_items.append((doc_idx, score))

        # Sort descending by score, tie-break by stable doc_id
        ranked_items.sort(key=lambda x: (x[1], -len(self.doc_ids[x[0]]), self.doc_ids[x[0]]), reverse=True)

        results: List[Tuple[str, float, int]] = []
        for rank, (doc_idx, score) in enumerate(ranked_items[:top_k], start=1):
            results.append((self.doc_ids[doc_idx], round(float(score), 4), rank))

        return results

    def save(self, filepath: str) -> None:
        """Serializes BM25 index to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: str) -> "BM25Retriever":
        """Deserializes BM25 index from disk."""
        with open(filepath, "rb") as f:
            return pickle.load(f)
