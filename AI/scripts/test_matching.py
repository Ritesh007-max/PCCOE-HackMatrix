import pandas as pd
import numpy as np
import re
import json
from difflib import SequenceMatcher

def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

df_s = pd.read_csv("data/raw/schemes.csv")
df_u = pd.read_csv("data/raw/updated_data.csv")

print(f"schemes.csv shape: {df_s.shape}")
print(f"updated_data.csv shape: {df_u.shape}")

# Drop exact duplicates in updated_data.csv
df_u_dedup = df_u.drop_duplicates().copy()
print(f"updated_data.csv after dropping exact duplicate rows: {df_u_dedup.shape}")

# Prepare match keys
df_s['norm_slug'] = df_s['slug'].astype(str).str.lower().str.strip()
df_s['norm_name'] = df_s['scheme_name'].apply(normalize_text)
df_s['norm_url'] = df_s['source_url'].astype(str).str.lower().str.strip()

df_u_dedup['norm_slug'] = df_u_dedup['slug'].astype(str).str.lower().str.strip()
df_u_dedup['norm_name'] = df_u_dedup['scheme_name'].apply(normalize_text)

# Step 1: Match by exact slug
slug_set_s = set(df_s['norm_slug'])
df_u_matched_slug = df_u_dedup[df_u_dedup['norm_slug'].isin(slug_set_s)].copy()
df_u_unmatched_slug = df_u_dedup[~df_u_dedup['norm_slug'].isin(slug_set_s)].copy()

print(f"Matched by exact slug: {len(df_u_matched_slug)}")
print(f"Unmatched after exact slug: {len(df_u_unmatched_slug)}")

# Step 2: Match unmatched by normalized name
name_set_s = set(df_s['norm_name'])
df_u_matched_name = df_u_unmatched_slug[df_u_unmatched_slug['norm_name'].isin(name_set_s)].copy()
df_u_unmatched_name = df_u_unmatched_slug[~df_u_unmatched_slug['norm_name'].isin(name_set_s)].copy()

print(f"Matched by exact normalized name among slug-unmatched: {len(df_u_matched_name)}")
print(f"Remaining unmatched: {len(df_u_unmatched_name)}")

# Step 3: Fuzzy matching review on remaining unmatched
s_names = df_s[['slug', 'scheme_name', 'norm_name']].drop_duplicates()
fuzzy_reviews = []

for idx, u_row in df_u_unmatched_name.iterrows():
    u_norm = u_row['norm_name']
    u_orig = u_row['scheme_name']
    u_slug = u_row['slug']
    
    best_ratio = 0.0
    best_match = None
    
    for _, s_row in s_names.iterrows():
        s_norm = s_row['norm_name']
        # Quick token overlap check before slow SequenceMatcher
        u_words = set(u_norm.split())
        s_words = set(s_norm.split())
        if not u_words.intersection(s_words):
            continue
        ratio = SequenceMatcher(None, u_norm, s_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = s_row
            
    if best_ratio > 0.65:
        fuzzy_reviews.append({
            "updated_slug": u_slug,
            "updated_scheme_name": u_orig,
            "best_schemes_slug": best_match['slug'],
            "best_schemes_name": best_match['scheme_name'],
            "similarity_ratio": round(best_ratio, 3),
            "recommendation": "Review required - distinct or variant"
        })

print(f"Fuzzy matches flagged for review (> 0.65 similarity): {len(fuzzy_reviews)}")
for r in fuzzy_reviews[:10]:
    print(f"  {r['updated_scheme_name']} ({r['updated_slug']}) <-> {r['best_schemes_name']} ({r['best_schemes_slug']}) [ratio: {r['similarity_ratio']}]")
