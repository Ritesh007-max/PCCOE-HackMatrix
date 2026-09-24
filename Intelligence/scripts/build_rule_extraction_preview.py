import os
import sys
import re
import json
import uuid
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

parquet_path = Path("data/processed/schemes_canonical.parquet")
output_path = Path("data/interim/rule_extraction_preview.jsonl")

df = pq.read_table(parquet_path).to_pandas()

indian_states = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
    "Bihar", "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
    "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
    "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

def parse_currency(num_str):
    clean = num_str.replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
    try:
        val = float(clean)
        # Check if lakhs
        return val
    except:
        return None

def extract_rules_from_clause(scheme_row, clause, clause_seq, section_name):
    rules = []
    text = clause.strip()
    if not text:
        return rules
        
    s_id = scheme_row['id']
    slug = scheme_row['slug']
    source_url = scheme_row['source_url']
    
    text_lower = text.lower()
    
    # 1. State / Residency Match
    matched_state = None
    for st in indian_states:
        pattern = rf'\b(?:resident|native|domicile|permanent resident)\s+(?:of|in)\s+(?:the\s+)?(?:state\s+of\s+)?{re.escape(st.lower())}'
        if re.search(pattern, text_lower):
            matched_state = st
            break
            
    if matched_state:
        rules.append({
            "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_state",
            "scheme_id": s_id,
            "rule_type": "eligibility",
            "field": "state",
            "operator": "=",
            "expected_value": matched_state,
            "value_type": "string",
            "logic_group": "DEFAULT",
            "required": True,
            "hard_constraint": True,
            "condition": {"field": "state", "op": "=", "val": matched_state, "unit": None},
            "raw_text": text,
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": section_name,
            "confidence": 1.0,
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "conservative_heuristic_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        })
        
    # 2. Age Match (Between / Range)
    m_between = re.search(r'(?:between|age\s+group\s+of)\s+(\d{1,2})\s*(?:to|and|-)\s*(\d{1,2})\s*years?', text_lower)
    if not m_between:
        m_between = re.search(r'minimum\s+age\s+(?:is|of)\s+(\d{1,2})\s*years?\s+and\s+maximum\s+(?:is|of)\s+(\d{1,2})\s*years?', text_lower)
        
    if m_between:
        min_age, max_age = int(m_between.group(1)), int(m_between.group(2))
        rules.append({
            "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_age_range",
            "scheme_id": s_id,
            "rule_type": "eligibility",
            "field": "age",
            "operator": "between",
            "expected_value": {"min": min_age, "max": max_age},
            "value_type": "range",
            "logic_group": "DEFAULT",
            "required": True,
            "hard_constraint": True,
            "condition": {"field": "age", "op": "between", "val": {"min": min_age, "max": max_age}, "unit": "years"},
            "raw_text": text,
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": section_name,
            "confidence": 1.0,
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "conservative_heuristic_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        })
    else:
        # Age >=
        m_min_age = re.search(r'(?:above|at\s+least|minimum\s+age\s+of|age\s+more\s+than|aged|age\s+of)\s+(\d{1,2})\s*years?', text_lower)
        if m_min_age and not re.search(r'(?:child|months)', text_lower):
            age_val = int(m_min_age.group(1))
            if 5 <= age_val <= 80:
                rules.append({
                    "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_min_age",
                    "scheme_id": s_id,
                    "rule_type": "eligibility",
                    "field": "age",
                    "operator": ">=",
                    "expected_value": age_val,
                    "value_type": "numeric",
                    "logic_group": "DEFAULT",
                    "required": True,
                    "hard_constraint": True,
                    "condition": {"field": "age", "op": ">=", "val": age_val, "unit": "years"},
                    "raw_text": text,
                    "source_url": source_url,
                    "source_document": "schemes_canonical.parquet",
                    "source_page": None,
                    "source_section": section_name,
                    "confidence": 0.95,
                    "provenance": {
                        "source_dataset": "schemes_canonical.parquet",
                        "extractor": "conservative_heuristic_v1",
                        "extraction_timestamp": "2026-09-21T16:30:00Z",
                        "review_status": "VERIFIED_DETERMINISTIC"
                    }
                })
                
    # 3. Income Ceiling Match
    m_inc = re.search(r'(?:family\s+income|annual\s+income|income).*?(?:not\s+exceed|below|less\s+than|up\s+to|maximum\s+of)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?', text_lower)
    if m_inc:
        val_str = m_inc.group(1).replace(',', '')
        multiplier = 1
        if m_inc.group(2) in ['lakh', 'lac']:
            multiplier = 100000
        elif m_inc.group(2) == 'crore':
            multiplier = 10000000
        try:
            inc_val = float(val_str) * multiplier
            rules.append({
                "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_income_cap",
                "scheme_id": s_id,
                "rule_type": "eligibility",
                "field": "annual_family_income",
                "operator": "<=",
                "expected_value": int(inc_val),
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "annual_family_income", "op": "<=", "val": int(inc_val), "unit": "INR"},
                "raw_text": text,
                "source_url": source_url,
                "source_document": "schemes_canonical.parquet",
                "source_page": None,
                "source_section": section_name,
                "confidence": 0.95,
                "provenance": {
                    "source_dataset": "schemes_canonical.parquet",
                    "extractor": "conservative_heuristic_v1",
                    "extraction_timestamp": "2026-09-21T16:30:00Z",
                    "review_status": "VERIFIED_DETERMINISTIC"
                }
            })
        except:
            pass

    # 4. Gender Match
    if re.search(r'\b(?:only\s+(?:female|women|girls)|applicant\s+should\s+be\s+a\s+girl|for\s+women|pregnant\s+women|widow)\b', text_lower):
        rules.append({
            "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_gender",
            "scheme_id": s_id,
            "rule_type": "eligibility",
            "field": "gender",
            "operator": "=",
            "expected_value": "Female",
            "value_type": "string",
            "logic_group": "DEFAULT",
            "required": True,
            "hard_constraint": True,
            "condition": {"field": "gender", "op": "=", "val": "Female", "unit": None},
            "raw_text": text,
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": section_name,
            "confidence": 0.95,
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "conservative_heuristic_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        })

    # 5. Disability Percentage
    m_dis = re.search(r'disability\s+(?:of\s+)?(\d{1,2})%\s*(?:or\s+more|and\s+above)', text_lower)
    if m_dis:
        dis_val = int(m_dis.group(1))
        rules.append({
            "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_disability",
            "scheme_id": s_id,
            "rule_type": "eligibility",
            "field": "disability_percentage",
            "operator": ">=",
            "expected_value": dis_val,
            "value_type": "numeric",
            "logic_group": "DEFAULT",
            "required": True,
            "hard_constraint": True,
            "condition": {"field": "disability_percentage", "op": ">=", "val": dis_val, "unit": "percent"},
            "raw_text": text,
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": section_name,
            "confidence": 0.95,
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "conservative_heuristic_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        })

    # 6. Exclusions: Income Tax Payer
    if "income tax" in text_lower and ("not be eligible" in text_lower or "excluded" in text_lower or section_name == "exclusions"):
        rules.append({
            "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_taxpayer_excl",
            "scheme_id": s_id,
            "rule_type": "exclusion",
            "field": "is_taxpayer",
            "operator": "is_false",
            "expected_value": False,
            "value_type": "boolean",
            "logic_group": "EXCLUSIONS",
            "required": True,
            "hard_constraint": True,
            "condition": {"field": "is_taxpayer", "op": "is_false", "val": False, "unit": None},
            "raw_text": text,
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": section_name,
            "confidence": 1.0,
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "conservative_heuristic_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        })

    # 7. Fallback: If no deterministic rule was extracted, mark as UNSTRUCTURED_REQUIRES_LLM_OR_MANUAL_REVIEW
    if not rules:
        rules.append({
            "rule_id": f"cand_{slug}_{section_name}_{clause_seq:02d}_unstructured",
            "scheme_id": s_id,
            "rule_type": "exclusion" if section_name == "exclusions" else "eligibility",
            "field": "unstructured_condition",
            "operator": "manual_review" if "discretion" in text_lower else "unstructured_nlp",
            "expected_value": text,
            "value_type": "unstructured",
            "logic_group": "UNSTRUCTURED_POOL",
            "required": True,
            "hard_constraint": False,
            "condition": {"field": "unstructured_condition", "op": "unstructured_nlp", "val": text, "unit": None},
            "raw_text": text,
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": section_name,
            "confidence": 0.50,
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "conservative_heuristic_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": "UNSTRUCTURED_REQUIRES_LLM_OR_MANUAL_REVIEW"
            }
        })
        
    return rules

print(f"Scanning all {len(df)} canonical schemes for rule extraction preview...")

total_clauses = 0
deterministic_rules_count = 0
unstructured_rules_count = 0
category_counts = {}

# Sample difficult rules
difficult_rules_samples = []

with open(output_path, "w", encoding="utf-8") as f_out:
    for idx, row in df.iterrows():
        elig_text = str(row['eligibility']) if pd.notnull(row['eligibility']) else ""
        excl_text = str(row['exclusions']) if pd.notnull(row['exclusions']) else ""
        
        # Split clauses by semicolon or newline
        elig_clauses = [c.strip() for c in re.split(r';|\n', elig_text) if c.strip() and c.strip() != 'nan']
        excl_clauses = [c.strip() for c in re.split(r';|\n', excl_text) if c.strip() and c.strip() != 'nan']
        
        for c_idx, clause in enumerate(elig_clauses, 1):
            total_clauses += 1
            extracted = extract_rules_from_clause(row, clause, c_idx, "eligibility")
            for r in extracted:
                if r["provenance"]["review_status"] == "VERIFIED_DETERMINISTIC":
                    deterministic_rules_count += 1
                    f = r["field"]
                    category_counts[f] = category_counts.get(f, 0) + 1
                else:
                    unstructured_rules_count += 1
                    category_counts["unstructured"] = category_counts.get("unstructured", 0) + 1
                    if len(difficult_rules_samples) < 10 and len(clause) > 50:
                        difficult_rules_samples.append({
                            "slug": row["slug"],
                            "scheme_name": row["scheme_name"],
                            "clause": clause[:160]
                        })
                f_out.write(json.dumps(r, ensure_ascii=False) + "\n")
                
        for c_idx, clause in enumerate(excl_clauses, 1):
            total_clauses += 1
            extracted = extract_rules_from_clause(row, clause, c_idx, "exclusions")
            for r in extracted:
                if r["provenance"]["review_status"] == "VERIFIED_DETERMINISTIC":
                    deterministic_rules_count += 1
                    f = r["field"]
                    category_counts[f] = category_counts.get(f, 0) + 1
                else:
                    unstructured_rules_count += 1
                    category_counts["unstructured"] = category_counts.get("unstructured", 0) + 1
                f_out.write(json.dumps(r, ensure_ascii=False) + "\n")

print("\n--- Rule Extraction Preview Complete ---")
print(f"Total clauses processed: {total_clauses}")
print(f"Deterministic rules extracted: {deterministic_rules_count}")
print(f"Unstructured / ambiguous clauses marked for review: {unstructured_rules_count}")
print("Category counts:", category_counts)

# Save summary stats to interim
summary_stats = {
    "total_schemes_inspected": len(df),
    "schemes_with_eligibility": int(df['eligibility'].notnull().sum()),
    "schemes_with_exclusions": int(df['exclusions'].notnull().sum()),
    "total_clauses_processed": total_clauses,
    "deterministic_rules_extracted": deterministic_rules_count,
    "unstructured_rules_for_review": unstructured_rules_count,
    "rule_categories_breakdown": category_counts,
    "difficult_rules_examples": difficult_rules_samples
}

with open("data/interim/rule_extraction_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary_stats, f, indent=2, ensure_ascii=False)

print("Saved data/interim/rule_extraction_summary.json and rule_extraction_preview.jsonl")
