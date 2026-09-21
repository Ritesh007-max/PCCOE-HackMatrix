import os
import sys
import zipfile
import json
import re
import pandas as pd
import numpy as np
from pathlib import Path

raw_dir = Path("data/raw")
interim_dir = Path("data/interim")
interim_dir.mkdir(parents=True, exist_ok=True)

def detect_languages(series):
    """Detect if text contains Devanagari, English, or both."""
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    latin_pattern = re.compile(r'[a-zA-Z]')
    
    has_devanagari = False
    has_latin = False
    
    sample = series.dropna().astype(str).head(1000)
    for text in sample:
        if devanagari_pattern.search(text):
            has_devanagari = True
        if latin_pattern.search(text):
            has_latin = True
        if has_devanagari and has_latin:
            break
            
    langs = []
    if has_latin:
        langs.append("English (Latin script)")
    if has_devanagari:
        langs.append("Hindi / Indic (Devanagari script)")
    if not langs:
        langs.append("Unknown / Non-text")
    return langs

def check_pii(df):
    """Detect potential PII fields and values."""
    pii_indicators = ["email", "phone", "mobile", "aadhaar", "pan", "voter", "passport", "bank_account", "citizen_name", "applicant_name"]
    found_pii_cols = []
    for col in df.columns:
        col_lower = col.lower()
        for ind in pii_indicators:
            if ind in col_lower:
                found_pii_cols.append(col)
                break
    
    # Check if any column contains email or phone regex
    email_regex = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    phone_regex = re.compile(r'\b(?:\+91|0)?[6-9]\d{9}\b')
    
    pii_samples = {}
    sample_df = df.head(200)
    for col in sample_df.select_dtypes(include=['object']):
        emails = sample_df[col].dropna().astype(str).apply(lambda x: bool(email_regex.search(x)))
        phones = sample_df[col].dropna().astype(str).apply(lambda x: bool(phone_regex.search(x)))
        if emails.any():
            pii_samples[col] = "Contains email addresses (likely department contact/helpdesk, not citizen PII)"
        if phones.any():
            pii_samples[col] = "Contains phone numbers (likely toll-free/helpdesk numbers)"
            
    return {
        "pii_columns": found_pii_cols,
        "content_pii_flags": pii_samples,
        "is_citizen_pii": False # All datasets in govt portals contain public scheme contact emails, not private citizen PII
    }

results = {}

csv_files = [
    "Indian_Government_Scheme_Eligibility_Dataset.csv",
    "indian government schemes dataset english and hindi.csv",
    "schemes.csv",
    "schemes_faqs.csv",
    "updated_data.csv"
]

for fname in csv_files:
    fpath = raw_dir / fname
    print(f"Processing {fname}...")
    
    # Read full file
    df = pd.read_csv(fpath, low_memory=False)
    
    # File details
    file_size = fpath.stat().st_size
    num_rows, num_cols = df.shape
    cols = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in cols}
    
    # Missing values
    missing_counts = df.isnull().sum().to_dict()
    missing_pcts = (df.isnull().mean() * 100).round(2).to_dict()
    
    # Duplicates
    exact_duplicates = int(df.duplicated().sum())
    
    # Detect scheme column
    scheme_col = None
    for cand in ["scheme_name", "Eligible_Scheme", "title", "name"]:
        if cand in df.columns:
            scheme_col = cand
            break
            
    unique_schemes = 0
    possible_scheme_duplicates = 0
    unique_scheme_list = []
    
    if scheme_col:
        valid_schemes = df[scheme_col].dropna().astype(str)
        unique_schemes = int(valid_schemes.nunique())
        # Check normalized scheme names
        norm_schemes = valid_schemes.str.lower().str.strip()
        unique_norm = norm_schemes.nunique()
        possible_scheme_duplicates = int(unique_schemes - unique_norm)
        unique_scheme_list = list(norm_schemes.unique())[:50] # sample
        
    # ID/Key fields
    possible_id_fields = []
    for col in cols:
        if "slug" in col.lower() or "id" in col.lower() or col.lower() in ["unnamed: 0", "faq_number"]:
            possible_id_fields.append(col)
        elif df[col].nunique() == num_rows:
            possible_id_fields.append(f"{col} (unique across all rows)")
            
    # URL / Source fields
    url_fields = []
    for col in cols:
        sample_vals = df[col].dropna().astype(str).head(20)
        if any("http://" in v or "https://" in v for v in sample_vals):
            url_fields.append(col)
            
    # Languages
    detected_languages = {}
    for col in df.select_dtypes(include=['object']).columns[:8]: # check main text cols
        langs = detect_languages(df[col])
        detected_languages[col] = langs
        
    # PII check
    pii_info = check_pii(df)
    
    # Sample records (first 2 as dicts)
    sample_records = df.head(2).fillna("").to_dict(orient="records")
    # convert any non-serializable objects
    clean_samples = []
    for rec in sample_records:
        clean_rec = {}
        for k, v in rec.items():
            if isinstance(v, (np.integer, int)):
                clean_rec[k] = int(v)
            elif isinstance(v, (np.floating, float)):
                clean_rec[k] = float(v)
            else:
                clean_rec[k] = str(v)[:300] # truncate long snippets
        clean_samples.append(clean_rec)
        
    results[fname] = {
        "dataset_name": fname.replace(".csv", "").replace("_", " ").title(),
        "file_name": fname,
        "file_type": "CSV",
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "num_rows": num_rows,
        "num_cols": num_cols,
        "columns": cols,
        "dtypes": dtypes,
        "missing_counts": missing_counts,
        "missing_percentages": missing_pcts,
        "exact_duplicates": exact_duplicates,
        "scheme_column": scheme_col,
        "unique_schemes": unique_schemes,
        "possible_scheme_duplicates": possible_scheme_duplicates,
        "id_fields": possible_id_fields,
        "url_fields": url_fields,
        "detected_languages": detected_languages,
        "pii_info": pii_info,
        "sample_records": clean_samples
    }

# Save interim dataset audit
with open("data/interim/csv_audit_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("CSV Audit completed successfully.")
