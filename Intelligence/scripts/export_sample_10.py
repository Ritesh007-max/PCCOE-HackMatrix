import pyarrow.parquet as pq
import pandas as pd
import json
from pathlib import Path

df = pq.read_table("data/processed/schemes_canonical.parquet").to_pandas()
target_slugs = ['ab-pmjay', 'pm-svanidhi', '108easuk', 'aag', '25-ciss', 'aasgsmse', 'mj-fapm', 'pm-kisan', 'apy', 'pmmvy']

extracted_10 = []
for slug in target_slugs:
    m = df[df['slug'] == slug]
    if len(m) > 0:
        row = m.iloc[0]
        extracted_10.append({
            "id": row['id'],
            "slug": row['slug'],
            "scheme_name": row['scheme_name'],
            "level": row['level'],
            "state": row['state'] if pd.notnull(row['state']) else None,
            "eligibility": row['eligibility'],
            "exclusions": row['exclusions'],
            "source_url": row['source_url']
        })

with open("data/interim/sample_10_schemes.json", "w", encoding="utf-8") as f:
    json.dump(extracted_10, f, indent=2, ensure_ascii=False)

print(f"Exported {len(extracted_10)} schemes to data/interim/sample_10_schemes.json")
