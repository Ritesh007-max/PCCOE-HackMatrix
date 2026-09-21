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

# Load CSV audit summary
with open("data/interim/csv_audit_raw.json", "r", encoding="utf-8") as f:
    csv_audit = json.load(f)

# Load ZIP audit summary
with open("scripts/zip_audit_out.json", "r", encoding="utf-8") as f:
    zip_audit = json.load(f)

print("=== Summary of datasets ===")
for k, v in csv_audit.items():
    print(f"File: {k}")
    print(f"  Rows: {v['num_rows']}, Cols: {v['num_cols']}, Schemes: {v['unique_schemes']}, Duplicates: {v['exact_duplicates']}")
    print(f"  Missing % max: {max(v['missing_percentages'].values()) if v['missing_percentages'] else 0}%")
    print(f"  Columns: {v['columns']}")

# Let's inspect `archive (1).zip` schemes
zip_path = raw_dir / "archive (1).zip"
zip_scheme_titles = []
with zipfile.ZipFile(zip_path, 'r') as z:
    for name in z.namelist():
        if name.endswith('.txt'):
            try:
                # read first 3 lines
                txt = z.read(name).decode('utf-8', errors='ignore')
                lines = [line.strip() for line in txt.split('\n') if line.strip()]
                title = lines[0] if lines else name
                zip_scheme_titles.append({
                    "path": name,
                    "folder": name.split('/')[0] if '/' in name else "root",
                    "title": title
                })
            except Exception as e:
                pass

print(f"\nZIP file text docs count: {len(zip_scheme_titles)}")
zip_df = pd.DataFrame(zip_scheme_titles)
print("ZIP sample titles:", zip_df['title'].head(5).tolist())

# Load datasets into memory for cross comparison
df_eligibility = pd.read_csv(raw_dir / "Indian_Government_Scheme_Eligibility_Dataset.csv")
df_qa = pd.read_csv(raw_dir / "indian government schemes dataset english and hindi.csv")
df_schemes = pd.read_csv(raw_dir / "schemes.csv")
df_faqs = pd.read_csv(raw_dir / "schemes_faqs.csv")
df_updated = pd.read_csv(raw_dir / "updated_data.csv")

# Extract normalized scheme names
schemes_names_main = set(df_schemes['scheme_name'].dropna().str.lower().str.strip())
schemes_slugs_main = set(df_schemes['slug'].dropna().str.lower().str.strip())

updated_names = set(df_updated['scheme_name'].dropna().str.lower().str.strip())
updated_slugs = set(df_updated['slug'].dropna().str.lower().str.strip())

qa_schemes = set(df_qa['scheme_name'].dropna().str.lower().str.strip())
elig_schemes = set(df_eligibility['Eligible_Scheme'].dropna().str.lower().str.strip())
faqs_schemes = set(df_faqs['scheme_name'].dropna().str.lower().str.strip())
faqs_slugs = set(df_faqs['scheme_slug'].dropna().str.lower().str.strip())

zip_titles_norm = set(zip_df['title'].str.lower().str.strip())

# Overlap calculation
overlap_data = {
    "schemes_vs_updated": {
        "schemes_csv_total": len(schemes_names_main),
        "updated_data_total": len(updated_names),
        "name_intersection": len(schemes_names_main.intersection(updated_names)),
        "slug_intersection": len(schemes_slugs_main.intersection(updated_slugs)),
        "schemes_csv_unique": len(schemes_names_main - updated_names),
        "updated_data_unique": len(updated_names - schemes_names_main),
    },
    "schemes_vs_faqs": {
        "schemes_csv_total": len(schemes_names_main),
        "faqs_total": len(faqs_schemes),
        "name_intersection": len(schemes_names_main.intersection(faqs_schemes)),
        "slug_intersection": len(schemes_slugs_main.intersection(faqs_slugs)),
        "faqs_unique": len(faqs_schemes - schemes_names_main)
    },
    "schemes_vs_qa": {
        "schemes_csv_total": len(schemes_names_main),
        "qa_schemes_total": len(qa_schemes),
        "name_intersection": len(schemes_names_main.intersection(qa_schemes)),
        "qa_unique": len(qa_schemes - schemes_names_main)
    },
    "schemes_vs_eligibility": {
        "schemes_csv_total": len(schemes_names_main),
        "eligibility_schemes_total": len(elig_schemes),
        "name_intersection": len(schemes_names_main.intersection(elig_schemes)),
        "eligibility_unique": len(elig_schemes - schemes_names_main),
        "eligibility_schemes_list": list(elig_schemes)
    },
    "schemes_vs_zip": {
        "schemes_csv_total": len(schemes_names_main),
        "zip_docs_total": len(zip_titles_norm),
        "title_intersection": len(schemes_names_main.intersection(zip_titles_norm)),
    }
}

print("\n=== Overlap Report ===")
print(json.dumps(overlap_data, indent=2))

with open("data/interim/dataset_overlap_raw.json", "w", encoding="utf-8") as f:
    json.dump(overlap_data, f, indent=2)

# Compare schemes.csv and updated_data.csv in detail
print("\n=== schemes.csv vs updated_data.csv ===")
print(f"schemes.csv shape: {df_schemes.shape}")
print(f"updated_data.csv shape: {df_updated.shape}")
print("updated_data.csv Unnamed: 9 null count:", df_updated['Unnamed: 9'].isnull().sum(), "out of", len(df_updated))
if df_updated['Unnamed: 9'].notnull().sum() > 0:
    print("Non-null samples in Unnamed: 9:", df_updated[df_updated['Unnamed: 9'].notnull()][['scheme_name', 'Unnamed: 9']].head(3).to_dict(orient='records'))

# Compare fields between schemes.csv and updated_data.csv
common_cols = set(df_schemes.columns).intersection(set(df_updated.columns))
print("Common columns:", common_cols)
print("Cols in schemes.csv only:", set(df_schemes.columns) - set(df_updated.columns))
print("Cols in updated_data.csv only:", set(df_updated.columns) - set(df_schemes.columns))

# Check content equality on overlapping schemes
sample_slug = list(schemes_slugs_main.intersection(updated_slugs))[0]
print(f"\nChecking sample slug: {sample_slug}")
s_row = df_schemes[df_schemes['slug'].str.lower().str.strip() == sample_slug].iloc[0]
u_row = df_updated[df_updated['slug'].str.lower().str.strip() == sample_slug].iloc[0]
print("schemes.csv eligibility length:", len(str(s_row['eligibility'])))
print("updated_data.csv eligibility length:", len(str(u_row['eligibility'])))
print("Are they identical?", str(s_row['eligibility']).strip() == str(u_row['eligibility']).strip())

# Check QA dataset
print("\n=== QA Dataset Inspection ===")
print(f"Rows: {len(df_qa)}")
print(f"Unique questions english: {df_qa['question_english'].nunique()}")
print(f"Unique questions hindi: {df_qa['question'].nunique()}")
print(f"Schemes mentioned in QA: {df_qa['scheme_name'].nunique()}")
print("Sample QA:", df_qa[['scheme_name', 'question_english', 'answer_english']].head(2).to_dict(orient='records'))

# Check Eligibility Dataset
print("\n=== Eligibility Dataset Inspection ===")
print(f"Rows: {len(df_eligibility)}")
print(df_eligibility.head(5))
print("Value counts for Eligible_Scheme:")
print(df_eligibility['Eligible_Scheme'].value_counts())
print("States in eligibility dataset:", df_eligibility['State'].unique())
print("Income range:", df_eligibility['Annual_Income_INR'].min(), "to", df_eligibility['Annual_Income_INR'].max())
print("Age range:", df_eligibility['Age'].min(), "to", df_eligibility['Age'].max())
print("Categories:", df_eligibility['Category'].unique())

# Check schemes_faqs.csv vs QA dataset
print("\n=== schemes_faqs.csv Inspection ===")
print(f"Rows: {len(df_faqs)}")
print(f"Unique schemes: {df_faqs['scheme_name'].nunique()}")
print(f"Unique slugs: {df_faqs['scheme_slug'].nunique()}")
print("Sample FAQ:", df_faqs.head(2).to_dict(orient='records'))
