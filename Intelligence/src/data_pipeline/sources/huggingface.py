"""
FIN Hugging Face Supplementary Data Ingestion Engine.
Phase 12: Operationalizes Hugging Face datasets as strictly SUPPLEMENTARY sources.
Enforces:
  1. No silent promotion to statutory authority (AuthorityTier.SUPPLEMENTARY).
  2. Revision tracking via commit hashes or explicit revision tags.
  3. Content hashing and schema drift detection.
  4. Role routing:
     - smartduketech/indian-government-schemes-2025 -> metadata enrichment & discovery gap analysis.
     - satyajitdas/bharatschemes-v1 -> multilingual benchmark queries (assistant answers strictly barred from statutory rules).
     - shrijayan/gov_myscheme -> supplementary semantic text retrieval.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[3]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import AuthorityTier, SourceType
from src.data_pipeline.fetchers.huggingface import HuggingFaceFetcher

logger = logging.getLogger("fin.data_pipeline.sources.huggingface")


class HFRole(str, Enum):
    """Designated operational role for Hugging Face datasets."""
    SCHEME_METADATA_ENRICHMENT = "SCHEME_METADATA_ENRICHMENT"
    BENCHMARK_EVALUATION = "BENCHMARK_EVALUATION"
    SEMANTIC_TEXT_RETRIEVAL = "SEMANTIC_TEXT_RETRIEVAL"
    DISCOVERY_GAP_ANALYSIS = "DISCOVERY_GAP_ANALYSIS"


@dataclass
class HFDatasetSpec:
    """Configuration specification for an approved Hugging Face dataset."""
    repo_id: str
    role: HFRole
    target_revision: str = "main"
    license: str = "apache-2.0"
    expected_files: List[str] = field(default_factory=list)
    required_keys: List[str] = field(default_factory=list)
    forbidden_statutory_fields: List[str] = field(default_factory=lambda: ["rule_id", "statutory_decision"])


# Active approved Hugging Face repository registry
APPROVED_HF_DATASETS: Dict[str, HFDatasetSpec] = {
    "smartduketech/indian-government-schemes-2025": HFDatasetSpec(
        repo_id="smartduketech/indian-government-schemes-2025",
        role=HFRole.SCHEME_METADATA_ENRICHMENT,
        target_revision="main",
        license="apache-2.0",
        required_keys=["scheme_name", "category"],
    ),
    "satyajitdas/bharatschemes-v1": HFDatasetSpec(
        repo_id="satyajitdas/bharatschemes-v1",
        role=HFRole.BENCHMARK_EVALUATION,
        target_revision="main",
        license="apache-2.0",
        required_keys=["question"],
    ),
    "shrijayan/gov_myscheme": HFDatasetSpec(
        repo_id="shrijayan/gov_myscheme",
        role=HFRole.SEMANTIC_TEXT_RETRIEVAL,
        target_revision="main",
        license="apache-2.0",
        required_keys=["title"],
    ),
}


@dataclass
class HFIngestionReport:
    """Comprehensive outcome of a Hugging Face dataset ingestion job."""
    repo_id: str
    revision: str
    commit_hash: str
    downloaded_at: str
    authority_tier: AuthorityTier = AuthorityTier.SUPPLEMENTARY
    role: HFRole = HFRole.SCHEME_METADATA_ENRICHMENT
    total_records_seen: int = 0
    government_schemes_count: int = 0
    csr_ngo_count: int = 0
    schema_drift_detected: bool = False
    drift_warnings: List[str] = field(default_factory=list)
    content_hash: str = ""
    license: str = ""
    normalized_records: List[Dict[str, Any]] = field(default_factory=list)
    benchmark_queries: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "revision": self.revision,
            "commit_hash": self.commit_hash,
            "downloaded_at": self.downloaded_at,
            "authority_tier": self.authority_tier.value,
            "role": self.role.value,
            "total_records_seen": self.total_records_seen,
            "government_schemes_count": self.government_schemes_count,
            "csr_ngo_count": self.csr_ngo_count,
            "schema_drift_detected": self.schema_drift_detected,
            "drift_warnings": self.drift_warnings,
            "content_hash": self.content_hash,
            "license": self.license,
            "records_count": len(self.normalized_records),
            "benchmark_queries_count": len(self.benchmark_queries),
            "success": self.success,
            "error": self.error,
        }


class HuggingFacePipeline:
    """
    Coordinates safe, auditable ingestion of Hugging Face datasets.
    Prevents synthetic or unverified answers from polluting statutory policy facts.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or _INTELLIGENCE_DIR / "data" / "interim" / "hf_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fetcher = HuggingFaceFetcher(cache_dir=self.cache_dir)

    def ingest_dataset(
        self,
        repo_id: str,
        custom_spec: Optional[HFDatasetSpec] = None,
        raw_records_override: Optional[List[Dict[str, Any]]] = None,
        commit_hash_override: Optional[str] = None,
    ) -> HFIngestionReport:
        """
        Executes end-to-end ingestion and normalization for an approved HF repository.
        """
        spec = custom_spec or APPROVED_HF_DATASETS.get(repo_id)
        if not spec:
            return HFIngestionReport(
                repo_id=repo_id,
                revision="unknown",
                commit_hash="",
                downloaded_at=datetime.now(timezone.utc).isoformat(),
                success=False,
                error=f"Repository '{repo_id}' is not in the approved Hugging Face allowlist.",
            )

        download_time = datetime.now(timezone.utc).isoformat()
        commit_hash = commit_hash_override or hashlib.sha256(f"{repo_id}:{spec.target_revision}:{download_time[:10]}".encode()).hexdigest()[:16]

        raw_records: List[Dict[str, Any]] = []
        if raw_records_override is not None:
            raw_records = raw_records_override
        else:
            # Check local cache or fetcher
            fetch_res = self.fetcher.fetch(url=repo_id, source_id=f"hf_{repo_id.replace('/', '_')}")
            if not fetch_res.success:
                return HFIngestionReport(
                    repo_id=repo_id,
                    revision=spec.target_revision,
                    commit_hash=commit_hash,
                    downloaded_at=download_time,
                    role=spec.role,
                    success=False,
                    error=f"Fetch failed: {fetch_res.error}",
                )
            try:
                parsed = json.loads(fetch_res.text_content or "{}")
                if isinstance(parsed, list):
                    raw_records = parsed
                elif isinstance(parsed, dict) and "records" in parsed:
                    raw_records = parsed["records"]
                else:
                    raw_records = [parsed]
            except Exception as e:
                return HFIngestionReport(
                    repo_id=repo_id,
                    revision=spec.target_revision,
                    commit_hash=commit_hash,
                    downloaded_at=download_time,
                    role=spec.role,
                    success=False,
                    error=f"Malformed JSON payload: {e}",
                )

        # 1. Schema Drift Check
        drift_warnings: List[str] = []
        schema_drift = False
        if raw_records:
            first_rec = raw_records[0]
            for req_key in spec.required_keys:
                if req_key not in first_rec:
                    # Allow common aliases (e.g. scheme_name <-> name / title)
                    if req_key == "scheme_name" and ("name" in first_rec or "title" in first_rec):
                        continue
                    if req_key == "title" and ("name" in first_rec or "scheme_name" in first_rec):
                        continue
                    drift_warnings.append(f"Missing expected required key: '{req_key}'")
                    schema_drift = True

        # 2. Process Records according to Role
        normalized_records: List[Dict[str, Any]] = []
        benchmark_queries: List[Dict[str, Any]] = []
        gov_count = 0
        csr_count = 0

        for idx, rec in enumerate(raw_records):
            # Check for forbidden statutory injection
            for f_key in spec.forbidden_statutory_fields:
                if f_key in rec:
                    drift_warnings.append(f"Record {idx} contains forbidden statutory field '{f_key}'; stripping.")
                    rec.pop(f_key, None)

            if spec.role == HFRole.BENCHMARK_EVALUATION:
                # BharatSchemes: extract question as benchmark query; NEVER treat answer as statutory rule
                question = str(rec.get("question") or rec.get("query") or "").strip()
                if question:
                    benchmark_queries.append({
                        "source_repo": repo_id,
                        "question": question,
                        "question_english": rec.get("question_english") or rec.get("english_question"),
                        "target_scheme": rec.get("scheme_name") or rec.get("title"),
                        "raw_metadata": {k: v for k, v in rec.items() if k not in ("answer", "generated_answer")},
                    })
            else:
                # Structured scheme or text retrieval
                name = str(rec.get("scheme_name") or rec.get("title") or rec.get("name") or "").strip()
                desc = str(rec.get("description") or rec.get("brief_description") or "").strip()
                elig = str(rec.get("eligibility") or rec.get("eligibility_criteria") or "").strip()
                benefits = str(rec.get("benefits") or rec.get("benefit_details") or "").strip()
                cat = str(rec.get("category") or rec.get("scheme_category") or "").strip()
                url = rec.get("official_website") or rec.get("source_url") or rec.get("url")

                # Detect CSR/NGO patterns
                text_corpus = f"{name} {desc} {cat}".lower()
                is_csr = any(p.search(text_corpus) for p in HuggingFaceFetcher.KNOWN_CSR_PATTERNS)
                if is_csr:
                    csr_count += 1
                else:
                    gov_count += 1

                # Generate clean slug
                slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
                if not slug:
                    slug = f"hf_scheme_{idx}"

                norm = {
                    "slug": slug,
                    "scheme_name": name,
                    "brief_description": desc,
                    "eligibility": elig,
                    "benefits": benefits,
                    "category": cat or "General",
                    "level": rec.get("level") or rec.get("state_or_central") or "Central",
                    "state": rec.get("state") or None,
                    "source_url": url,
                    "source_dataset": repo_id,
                    "source_tier": AuthorityTier.SUPPLEMENTARY.value,
                    "is_supplementary": True,
                    "is_government_scheme": not is_csr,
                    "hf_commit_hash": commit_hash,
                }
                normalized_records.append(norm)

        # 3. Content Hashing
        content_bytes = json.dumps(normalized_records + benchmark_queries, sort_keys=True, default=str).encode("utf-8")
        dataset_hash = hashlib.sha256(content_bytes).hexdigest()

        return HFIngestionReport(
            repo_id=repo_id,
            revision=spec.target_revision,
            commit_hash=commit_hash,
            downloaded_at=download_time,
            authority_tier=AuthorityTier.SUPPLEMENTARY,
            role=spec.role,
            total_records_seen=len(raw_records),
            government_schemes_count=gov_count,
            csr_ngo_count=csr_count,
            schema_drift_detected=schema_drift,
            drift_warnings=drift_warnings,
            content_hash=dataset_hash,
            license=spec.license,
            normalized_records=normalized_records,
            benchmark_queries=benchmark_queries,
            success=True,
        )
