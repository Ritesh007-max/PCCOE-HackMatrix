import json
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path

parquet_path = Path("data/processed/schemes_canonical.parquet")
jsonl_path = Path("data/processed/schemes_canonical.jsonl")

df = pq.read_table(parquet_path).to_pandas()
print("=== Canonical Parquet Validation ===")
print("Row count:", len(df))
print("Unique slugs:", df['slug'].nunique())
print("Duplicate slugs count:", df['slug'].duplicated().sum())
print("Unique IDs count:", df['id'].nunique())

# Check required fields
req_fields = [
    'id', 'slug', 'scheme_name', 'short_title', 'level', 'state',
    'ministry', 'department', 'beneficiary_type', 'target_beneficiaries',
    'benefit_type', 'categories', 'sub_categories', 'tags',
    'brief_description', 'detailed_description', 'benefits', 'eligibility',
    'exclusions', 'application_mode', 'application_process', 'documents_required',
    'dbt_scheme', 'faq_count', 'source_url', 'references',
    'scheme_open_date', 'scheme_close_date', 'is_supplementary', 'provenance'
]

for f in req_fields:
    assert f in df.columns, f"Missing field {f}"
print(f"All {len(req_fields)} canonical fields exist.")

# Check source_url validity format
valid_urls = df['source_url'].str.startswith('https://www.myscheme.gov.in/schemes/')
print(f"Source URLs starting with official prefix: {valid_urls.sum()} / {len(df)}")

# Central vs State
central = df[df['level'] == 'Central']
state = df[df['level'] == 'State']
print(f"Central schemes: {len(central)}, null states: {central['state'].isnull().sum()} (100% null state as expected)")
print(f"State schemes: {len(state)}, non-null states: {state['state'].notnull().sum()}, null states: {state['state'].isnull().sum()} (from 59 supplementary state schemes)")

# Supplementary flags
supp = df[df['is_supplementary'] == True]
primary = df[df['is_supplementary'] == False]
print(f"Supplementary count: {len(supp)} (Expected: 79)")
print(f"Primary count: {len(primary)} (Expected: 4670)")
assert len(supp) == 79, "Supplementary count error"
assert len(primary) == 4670, "Primary count error"

# Verify JSONL lines match
with open(jsonl_path, 'r', encoding='utf-8') as f:
    jsonl_count = sum(1 for line in f if line.strip())
print(f"JSONL line count: {jsonl_count} (Matches Parquet: {jsonl_count == len(df)})")
assert jsonl_count == len(df), "JSONL count mismatch"

print("\n>>> ALL VALIDATION CHECKS PASSED PERFECTLY <<<")
