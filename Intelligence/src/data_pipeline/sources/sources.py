"""
FIN Pre-Configured Official and Supplementary Sources.
Enforces explicit authority hierarchy:
  PRIMARY_OFFICIAL > PRIMARY_CANONICALIZED > SUPPLEMENTARY > ARCHIVE > EVALUATION_ONLY
"""

from typing import Dict
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from ..models import SourceDefinition, SourceType, AuthorityTier
except (ImportError, ValueError):
    from src.data_pipeline.models import SourceDefinition, SourceType, AuthorityTier


APPROVED_SOURCES: Dict[str, SourceDefinition] = {
    # 1. Primary Canonical Baselines
    "myscheme_csv_baseline": SourceDefinition(
        source_id="myscheme_csv_baseline",
        source_name="myScheme Canonical Baseline CSV",
        source_type=SourceType.LOCAL_BASELINE,
        authority_tier=AuthorityTier.PRIMARY_CANONICALIZED,
        canonical=True,
        url="Intelligence/data/raw/schemes.csv",
        fetch_method="local",
        format="csv",
        update_frequency_hours=168,
        enabled=True,
        parser="myscheme_csv",
        stale_after_days=60,
        first_party_url_field="source_url",
        notes="Canonical primary scheme repository derived from schemes.csv."
    ),
    "myscheme_faqs_baseline": SourceDefinition(
        source_id="myscheme_faqs_baseline",
        source_name="myScheme Authoritative FAQs CSV",
        source_type=SourceType.LOCAL_BASELINE,
        authority_tier=AuthorityTier.PRIMARY_CANONICALIZED,
        canonical=True,
        url="Intelligence/data/raw/schemes_faqs.csv",
        fetch_method="local",
        format="csv",
        update_frequency_hours=168,
        enabled=True,
        parser="myscheme_faqs",
        stale_after_days=60,
        first_party_url_field="scheme_slug",
        notes="Authoritative 51k FAQ pairs mapped directly to primary schemes."
    ),

    # 2. Local Supplementary Datasets
    "updated_data_supplementary": SourceDefinition(
        source_id="updated_data_supplementary",
        source_name="Updated Scheme Data Supplementary CSV",
        source_type=SourceType.CSV,
        authority_tier=AuthorityTier.SUPPLEMENTARY,
        canonical=False,
        url="Intelligence/data/raw/updated_data.csv",
        fetch_method="local",
        format="csv",
        update_frequency_hours=336,
        enabled=True,
        parser="supplementary_csv",
        stale_after_days=90,
        notes="Supplementary scheme metadata and alternative field descriptions."
    ),
    "local_bilingual_dataset": SourceDefinition(
        source_id="local_bilingual_dataset",
        source_name="Local Bilingual English-Hindi Scheme Dataset",
        source_type=SourceType.LOCAL_BILINGUAL_DATASET,
        authority_tier=AuthorityTier.SUPPLEMENTARY,
        canonical=False,
        url="Intelligence/data/raw/indian government schemes dataset english and hindi.csv",
        fetch_method="local",
        format="csv",
        update_frequency_hours=336,
        enabled=True,
        parser="bharatschemes_bilingual",
        stale_after_days=90,
        notes="Local bilingual English & Hindi scheme questions/answers with non-gov CSR classification."
    ),

    # 3. Explicit Hugging Face Datasets
    "hf_bharatschemes": SourceDefinition(
        source_id="hf_bharatschemes",
        source_name="BharatSchemes v1 HuggingFace Dataset",
        source_type=SourceType.HUGGINGFACE_DATASET,
        authority_tier=AuthorityTier.SUPPLEMENTARY,
        canonical=False,
        url="satyajitdas/bharatschemes-v1",
        fetch_method="huggingface",
        format="json",
        update_frequency_hours=720,
        enabled=True,
        parser="hf_bharatschemes",
        stale_after_days=120,
        notes="HuggingFace bilingual QA corpus; contains both gov policies and CSR initiatives."
    ),
    "hf_smartduke": SourceDefinition(
        source_id="hf_smartduke",
        source_name="Indian Government Schemes 2025 HuggingFace Dataset",
        source_type=SourceType.HUGGINGFACE_DATASET,
        authority_tier=AuthorityTier.SUPPLEMENTARY,
        canonical=False,
        url="smartduketech/indian-government-schemes-2025",
        fetch_method="huggingface",
        format="json",
        update_frequency_hours=720,
        enabled=True,
        parser="hf_smartduke",
        stale_after_days=120,
        notes="HuggingFace supplementary scheme database."
    ),
    "hf_gov_myscheme": SourceDefinition(
        source_id="hf_gov_myscheme",
        source_name="Gov MyScheme HuggingFace Dataset",
        source_type=SourceType.HUGGINGFACE_DATASET,
        authority_tier=AuthorityTier.SUPPLEMENTARY,
        canonical=False,
        url="shrijayan/gov_myscheme",
        fetch_method="huggingface",
        format="json",
        update_frequency_hours=720,
        enabled=True,
        parser="hf_gov_myscheme",
        stale_after_days=120,
        notes="HuggingFace MyScheme supplementary mirror."
    ),

    # 4. Evaluation and Archive Corpora
    "eligibility_dataset_eval": SourceDefinition(
        source_id="eligibility_dataset_eval",
        source_name="Synthetic Eligibility Test Dataset",
        source_type=SourceType.CSV,
        authority_tier=AuthorityTier.EVALUATION_ONLY,
        canonical=False,
        url="Intelligence/data/raw/Indian_Government_Scheme_Eligibility_Dataset.csv",
        fetch_method="local",
        format="csv",
        update_frequency_hours=8760,
        enabled=True,
        parser="eligibility_eval",
        stale_after_days=365,
        notes="Used solely for rule evaluator regression checks and edge cases."
    ),
    "archive_txt_zip": SourceDefinition(
        source_id="archive_txt_zip",
        source_name="State Policy Document Archive Zip",
        source_type=SourceType.ZIP,
        authority_tier=AuthorityTier.ARCHIVE,
        canonical=False,
        url="Intelligence/data/raw/archive (1).zip",
        fetch_method="local",
        format="zip",
        update_frequency_hours=8760,
        enabled=True,
        parser="archive_zip",
        stale_after_days=365,
        notes="Historical raw state policy documents archive."
    ),

    # 5. Registered Official Portal Web Source
    "official_portal_web": SourceDefinition(
        source_id="official_portal_web",
        source_name="Official myScheme National Portal",
        source_type=SourceType.WEB_PAGE,
        authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
        canonical=False,
        url="https://www.myscheme.gov.in",
        fetch_method="http_get",
        format="html",
        update_frequency_hours=24,
        enabled=True,
        parser="myscheme_web",
        stale_after_days=7,
        first_party_url_field="source_url",
        notes="Discovery and live update layer; scheme first-party URLs are preserved as authoritative."
    ),
}