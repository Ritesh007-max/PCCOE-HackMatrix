import os
import sys
import zipfile
import json
import re
import pandas as pd
import numpy as np
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = Path("data/raw")

df_schemes = pd.read_csv(raw_dir / "schemes.csv")
df_updated = pd.read_csv(raw_dir / "updated_data.csv")
df_faqs = pd.read_csv(raw_dir / "schemes_faqs.csv")
df_qa = pd.read_csv(raw_dir / "indian government schemes dataset english and hindi.csv")
df_eligibility = pd.read_csv(raw_dir / "Indian_Government_Scheme_Eligibility_Dataset.csv")

print("=== 1. schemes.csv missing percentages per column ===")
for col in df_schemes.columns:
    null_cnt = int(df_schemes[col].isnull().sum())
    pct = round(null_cnt / len(df_schemes) * 100, 2)
    print(f"  {col}: {null_cnt} nulls ({pct}%)")

print("\n=== 2. updated_data.csv missing percentages per column ===")
for col in df_updated.columns:
    null_cnt = int(df_updated[col].isnull().sum())
    pct = round(null_cnt / len(df_updated) * 100, 2)
    print(f"  {col}: {null_cnt} nulls ({pct}%)")

print("\n=== 3. updated_data.csv duplicates ===")
dup_rows = df_updated[df_updated.duplicated(keep=False)]
print(f"Duplicate rows in updated_data.csv: {len(dup_rows)}")
print(dup_rows[['scheme_name', 'slug']].head(6))

print("\n=== 4. Why does updated_data have 106 unique names not in schemes.csv? ===")
s_slugs = set(df_schemes['slug'].dropna().str.lower().str.strip())
u_slugs = set(df_updated['slug'].dropna().str.lower().str.strip())
u_only_slugs = u_slugs - s_slugs
print(f"Slugs in updated_data but not schemes.csv: {len(u_only_slugs)}")
if u_only_slugs:
    print("Sample unique slugs in updated_data:", list(u_only_slugs)[:10])
    print(df_updated[df_updated['slug'].str.lower().str.strip().isin(list(u_only_slugs)[:5])][['scheme_name', 'slug']])

print("\n=== 5. How many slugs in schemes.csv not in updated_data? ===")
s_only_slugs = s_slugs - u_slugs
print(f"Slugs in schemes.csv but not updated_data: {len(s_only_slugs)}")

print("\n=== 6. Date / Version signals ===")
print("schemes.csv scheme_open_date non-null:", df_schemes['scheme_open_date'].notnull().sum())
print("schemes.csv sample open dates:", df_schemes['scheme_open_date'].dropna().head(5).tolist())
print("schemes.csv sample source_url:", df_schemes['source_url'].dropna().head(5).tolist())

print("\n=== 7. QA dataset date signals ===")
print("launched_year min/max:", df_qa['launched_year'].min(), "to", df_qa['launched_year'].max())
print("category distribution in QA:", df_qa['category'].value_counts().head(5).to_dict())

print("\n=== 8. Archive (1).zip origin inspection ===")
zip_path = raw_dir / "archive (1).zip"
with zipfile.ZipFile(zip_path, 'r') as z:
    for name in ["uttar-pradesh/state_uttar-pradesh_doc_1.txt", "central/central_doc_1.txt", "delhi/state_delhi_doc_1.txt"]:
        txt = z.read(name).decode('utf-8', errors='ignore')
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', txt)
        print(f"URLs found in {name}:", urls[:5])
