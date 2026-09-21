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
interim_dir = Path("data/interim")

df_s = pd.read_csv(raw_dir / "schemes.csv")
df_u = pd.read_csv(raw_dir / "updated_data.csv")

# Clean slugs
df_s['clean_slug'] = df_s['slug'].dropna().str.lower().str.strip()
df_u['clean_slug'] = df_u['slug'].dropna().str.lower().str.strip()

# Find overlapping slugs
common_slugs = set(df_s['clean_slug']).intersection(set(df_u['clean_slug']))
print(f"Total overlapping slugs between schemes.csv and updated_data.csv: {len(common_slugs)}")

# Compare fields across overlapping schemes
diff_eligibility_count = 0
identical_eligibility_count = 0
diff_benefits_count = 0
identical_benefits_count = 0

sample_conflicts = []

for slug in list(common_slugs):
    s_row = df_s[df_s['clean_slug'] == slug].iloc[0]
    u_row = df_u[df_u['clean_slug'] == slug].iloc[0]
    
    s_elig = str(s_row['eligibility']).strip()
    u_elig = str(u_row['eligibility']).strip()
    
    s_ben = str(s_row['benefits']).strip()
    u_ben = str(u_row['benefits']).strip()
    
    if s_elig == u_elig:
        identical_eligibility_count += 1
    else:
        diff_eligibility_count += 1
        if len(sample_conflicts) < 5:
            sample_conflicts.append({
                "slug": slug,
                "scheme_name_schemes_csv": str(s_row['scheme_name']),
                "scheme_name_updated_data": str(u_row['scheme_name']),
                "schemes_csv_eligibility_len": len(s_elig),
                "updated_data_eligibility_len": len(u_elig),
                "schemes_csv_eligibility_sample": s_elig[:150],
                "updated_data_eligibility_sample": u_elig[:150],
                "schemes_csv_benefits_sample": s_ben[:150],
                "updated_data_benefits_sample": u_ben[:150]
            })
            
    if s_ben == u_ben:
        identical_benefits_count += 1
    else:
        diff_benefits_count += 1

print(f"Eligibility identical: {identical_eligibility_count}, different: {diff_eligibility_count}")
print(f"Benefits identical: {identical_benefits_count}, different: {diff_benefits_count}")

# Let's inspect the differences: is it formatting, or missing content?
if sample_conflicts:
    print("\n--- Sample Conflict 1 ---")
    c = sample_conflicts[0]
    print("Slug:", c["slug"])
    print("Name s:", c["scheme_name_schemes_csv"])
    print("Name u:", c["scheme_name_updated_data"])
    print("s elig snippet:", repr(c["schemes_csv_eligibility_sample"]))
    print("u elig snippet:", repr(c["updated_data_eligibility_sample"]))

with open("data/interim/conflict_samples.json", "w", encoding="utf-8") as f:
    json.dump(sample_conflicts, f, indent=2, ensure_ascii=False)
