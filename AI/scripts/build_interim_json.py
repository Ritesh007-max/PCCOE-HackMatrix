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

# Load existing csv audit info
with open("data/interim/csv_audit_raw.json", "r", encoding="utf-8") as f:
    csv_raw = json.load(f)

# Load zip info
with open("scripts/zip_audit_out.json", "r", encoding="utf-8") as f:
    zip_raw = json.load(f)

# Build 14-dimension evaluation dictionary helper
def build_evaluation_matrix(d_key):
    if d_key == "schemes.csv":
        return {
            "Scheme Discovery": "EXCELLENT - Exhaustive 4,670 central and state schemes with taxonomy, tags, and categories",
            "Semantic Search": "EXCELLENT - Rich textual descriptions, short titles, and domain tags for dense retrieval",
            "RAG": "EXCELLENT - Structured fields (details, benefits, eligibility, exclusions) provide high-precision grounding",
            "Eligibility Rule Extraction": "EXCELLENT - Clean semi-structured eligibility criteria separated with delimiters",
            "Eligibility Testing": "GOOD - Ground-truth criteria for rule logic; requires applicant profile pairings",
            "Benefit Information": "EXCELLENT - Dedicated monetary and non-monetary benefits column for 94.4% of schemes",
            "Required Documents": "EXCELLENT - Dedicated required documentation list for 91.1% of schemes",
            "Application Process": "EXCELLENT - Step-by-step application instructions and online/offline application modes",
            "Applicant Profile Matching": "EXCELLENT - Granular metadata (state, ministry, beneficiary_type, level, categories)",
            "Multilingual NLP": "POOR - English-only textual representation",
            "FAQ/Question Answering": "GOOD - Contains faq_count indicator, maps 1:1 to schemes_faqs.csv",
            "ML Training": "HIGH - High quality target for NER, rule extraction, and classification",
            "Evaluation/Benchmarking": "EXCELLENT - Core ground truth for scheme catalog completeness",
            "Source Evidence": "AUTHORITATIVE_SOURCE - Scraped from official Government of India portal (myScheme.gov.in)"
        }
    elif d_key == "schemes_faqs.csv":
        return {
            "Scheme Discovery": "GOOD - Indirect discovery through citizen inquiry questions",
            "Semantic Search": "EXCELLENT - Real citizen questions reflect authentic search query distributions",
            "RAG": "EXCELLENT - 51,435 Q&A pairs provide ideal chunk units for RAG conversational retrieval",
            "Eligibility Rule Extraction": "MODERATE - Many FAQs clarify specific edge cases and nuanced eligibility conditions",
            "Eligibility Testing": "GOOD - FAQs provide boundary condition verification pairs",
            "Benefit Information": "GOOD - Specific benefit disbursement and quantum clarifications in answers",
            "Required Documents": "MODERATE - Document clarifications embedded in specific Q&A",
            "Application Process": "GOOD - Answers procedural queries regarding portal navigation and submission",
            "Applicant Profile Matching": "MODERATE - Indirect through context of questions",
            "Multilingual NLP": "POOR - English-only text",
            "FAQ/Question Answering": "OUTSTANDING - Comprehensive 51k gold standard Q&A corpus",
            "ML Training": "EXCELLENT - Pre-training/fine-tuning retriever or QA model",
            "Evaluation/Benchmarking": "OUTSTANDING - Natural benchmark for RAG retrieval hit rate and MRR",
            "Source Evidence": "AUTHORITATIVE_SOURCE - Direct official FAQ data from myScheme.gov.in"
        }
    elif d_key == "updated_data.csv":
        return {
            "Scheme Discovery": "MODERATE - 3,400 schemes; 79 schemes unique to this file not found in schemes.csv",
            "Semantic Search": "MODERATE - Subset of fields present in schemes.csv",
            "RAG": "MODERATE - Text is slightly noisier with inconsistent punctuation and missing metadata",
            "Eligibility Rule Extraction": "MODERATE - Eligibility text present, but concatenation issues without clean delimiters",
            "Eligibility Testing": "MODERATE - Redundant with schemes.csv for 3,318 schemes",
            "Benefit Information": "MODERATE - Present but fewer fields than schemes.csv",
            "Required Documents": "MODERATE - Present in documents column",
            "Application Process": "MODERATE - Present in application column",
            "Applicant Profile Matching": "POOR - Lacks state, ministry, department, and beneficiary target metadata",
            "Multilingual NLP": "POOR - English-only",
            "FAQ/Question Answering": "POOR - Lacks FAQ pairs",
            "ML Training": "LOW - Subsumed by schemes.csv except for 79 unique schemes",
            "Evaluation/Benchmarking": "LOW - Incomplete subset",
            "Source Evidence": "SECONDARY_SOURCE - Secondary snapshot/export of myScheme data with parsing artifacts"
        }
    elif d_key == "indian government schemes dataset english and hindi.csv":
        return {
            "Scheme Discovery": "LOW - Restricted to 96 landmark schemes",
            "Semantic Search": "GOOD - Multilingual cross-lingual semantic query matching",
            "RAG": "GOOD - Provides bilingual answers and ground truth explanations",
            "Eligibility Rule Extraction": "LOW - High-level summary questions rather than formal condition trees",
            "Eligibility Testing": "LOW - Generic eligibility questions",
            "Benefit Information": "MODERATE - Explains benefits in plain language (English & Hindi)",
            "Required Documents": "LOW - Generic document mentions",
            "Application Process": "MODERATE - Plain language process overviews",
            "Applicant Profile Matching": "LOW - Broad target beneficiary labels",
            "Multilingual NLP": "OUTSTANDING - 3,473 paired English-Hindi queries and answers with launched year",
            "FAQ/Question Answering": "EXCELLENT - Curated multilingual citizen QA",
            "ML Training": "HIGH - Cross-lingual retrieval, Hindi translation, query understanding",
            "Evaluation/Benchmarking": "EXCELLENT - Multilingual QA benchmark and translation evaluation",
            "Source Evidence": "COMMUNITY_DATA - Community curated / synthesized bilingual educational dataset"
        }
    elif d_key == "Indian_Government_Scheme_Eligibility_Dataset.csv":
        return {
            "Scheme Discovery": "POOR - Only 7 schemes represented",
            "Semantic Search": "UNUSABLE - No text descriptions, only demographic attributes",
            "RAG": "UNUSABLE - Tabular numbers only",
            "Eligibility Rule Extraction": "UNUSABLE - Fictitious/synthetic correlation patterns",
            "Eligibility Testing": "DANGEROUS / INVALID - Violates statutory rules (e.g. age 70 for Atal Pension Yojana)",
            "Benefit Information": "UNUSABLE - Zero benefit information",
            "Required Documents": "UNUSABLE - Zero document information",
            "Application Process": "UNUSABLE - Zero application information",
            "Applicant Profile Matching": "SYNTHETIC TOY - 5 coarse fields without legal constraints",
            "Multilingual NLP": "UNUSABLE - English category labels only",
            "FAQ/Question Answering": "UNUSABLE - No questions or answers",
            "ML Training": "TOY ONLY - Basic multi-class tabular classification (toy ML benchmarks only)",
            "Evaluation/Benchmarking": "UNUSABLE - Misaligned with statutory truth",
            "Source Evidence": "SYNTHETIC_DATA - Synthetic toy dataset generated for Kaggle/student practice"
        }
    elif "archive" in d_key:
        return {
            "Scheme Discovery": "GOOD - 1,524 documents across 28 states and central ministries",
            "Semantic Search": "GOOD - Long-form narrative content for broad semantic queries",
            "RAG": "HIGH - Unstructured full-text documents for chunking and unstructured context retrieval",
            "Eligibility Rule Extraction": "MODERATE - Unstructured prose requires heavy information extraction/NER",
            "Eligibility Testing": "MODERATE - Requires manual parsing of narrative rules",
            "Benefit Information": "GOOD - Explanatory prose on subsidies and scheme amounts",
            "Required Documents": "GOOD - Narrative checklists of documents in text",
            "Application Process": "GOOD - Narrative walkthroughs of online/offline procedures",
            "Applicant Profile Matching": "MODERATE - State and ministry folder partitioning",
            "Multilingual NLP": "POOR - Predominantly English text with some transliterated Hindi names",
            "FAQ/Question Answering": "MODERATE - Contains embedded question-style section headers",
            "ML Training": "GOOD - Unsupervised pre-training, text summarization, RAG chunking benchmark",
            "Evaluation/Benchmarking": "MODERATE - Document-level retrieval evaluation",
            "Source Evidence": "COMMUNITY_DATA / SECONDARY_SOURCE - Scraped blog articles (e.g., sarkariyojana, news)"
        }

# Classifications and Recommendations
meta_mapping = {
    "schemes.csv": {
        "credibility": "AUTHORITATIVE_SOURCE",
        "recommendation": "PRIMARY",
        "date_version": "2023-2024 snapshot (contains launch dates up to 2024 and live myScheme portal URLs)",
        "license": "Open Government Data (OGD) / myScheme public domain catalog",
        "quality_issues": [
            "High null rate in 'exclusions' (86.0%) and 'ministry' (86.1%, since state schemes list department without central ministry)",
            "Scheme close date null in 98.8% (expected as most schemes are ongoing/open-ended)",
            "Semicolon-delimited strings inside text fields need parsing into structured lists"
        ]
    },
    "schemes_faqs.csv": {
        "credibility": "AUTHORITATIVE_SOURCE",
        "recommendation": "PRIMARY",
        "date_version": "2023-2024 snapshot aligned 1:1 with schemes.csv slugs",
        "license": "Open Government Data (OGD) / myScheme public domain content",
        "quality_issues": [
            "0 missing values across all 51,435 records",
            "Some question answers contain portal navigation text or generic contact info",
            "Requires slug join to schemes.csv for contextual scheme metadata"
        ]
    },
    "updated_data.csv": {
        "credibility": "SECONDARY_SOURCE",
        "recommendation": "SUPPLEMENTARY",
        "date_version": "Earlier scrape/export of myScheme portal",
        "license": "myScheme derived secondary scrape",
        "quality_issues": [
            "Column 'Unnamed: 9' is 100% null (3,400 of 3,400 records)",
            "Contains 3 duplicate records (5 rows: eogu x3, vcy x2)",
            "Missing key metadata (state, ministry, department, dbt status, open/close dates)",
            "Eligibility and benefits fields have formatting loss (missing bullet delimiters compared to schemes.csv)",
            "Contains 79 valuable unique schemes not present in schemes.csv that should be extracted as supplementary entries"
        ]
    },
    "indian government schemes dataset english and hindi.csv": {
        "credibility": "COMMUNITY_DATA",
        "recommendation": "EVALUATION_ONLY",
        "date_version": "Contains schemes launched from 1959 to 2023",
        "license": "Open Community Dataset (CC BY-SA / Kaggle open)",
        "quality_issues": [
            "Index artifact column 'Unnamed: 0'",
            "Covers only 96 schemes out of 4,600+ national schemes",
            "Some Hindi translations are machine-translated and contain grammatical quirks in answers",
            "Answers are qualitative summaries, not legally authoritative statutory clauses"
        ]
    },
    "Indian_Government_Scheme_Eligibility_Dataset.csv": {
        "credibility": "SYNTHETIC_DATA",
        "recommendation": "DISCARD",
        "date_version": "Undated synthetic tabular dataset (circa 2023)",
        "license": "Open / Public domain synthetic data",
        "quality_issues": [
            "Severe domain invalidity: Labels violate statutory policy criteria (e.g. assigning Atal Pension Yojana to 70-year-olds with INR 1.1M income when statutory age cap is 40)",
            "Extreme coverage limitation: Only 7 schemes total across 1,500 records",
            "Artificial uniform distribution without legal nuance or statutory constraints",
            "Using this for eligibility testing would inject false positive and false negative bugs into the system"
        ]
    },
    "archive (1).zip": {
        "credibility": "SECONDARY_SOURCE",
        "recommendation": "RAG_DOCUMENT_SOURCE",
        "date_version": "Scraped articles circa 2019-2022",
        "license": "Aggregated secondary web content",
        "quality_issues": [
            "Contains web scraper boilerplate (e.g. 'Table of Contents', blog ads, share buttons)",
            "Unstructured text without standardized JSON/tabular schema",
            "Some outdated scheme URLs and news article links (e.g., PTI news reports from 2019)",
            "No formal unique IDs; requires entity extraction and text normalization"
        ]
    }
}

# 1. Build dataset_inventory.json
inventory_output = {}

for fname, data in csv_raw.items():
    meta = meta_mapping[fname]
    eval_matrix = build_evaluation_matrix(fname)
    inventory_output[fname] = {
        "dataset_name": data["dataset_name"],
        "file_name": data["file_name"],
        "file_type": data["file_type"],
        "size_bytes": data["size_bytes"],
        "size_mb": data["size_mb"],
        "num_records": data["num_rows"],
        "num_fields": data["num_cols"],
        "field_names": data["columns"],
        "data_types": data["dtypes"],
        "missing_counts": data["missing_counts"],
        "missing_percentages": data["missing_percentages"],
        "duplicate_records_count": data["exact_duplicates"],
        "unique_scheme_count": data["unique_schemes"],
        "possible_scheme_name_duplicates": data["possible_scheme_duplicates"],
        "possible_id_fields": data["id_fields"],
        "url_source_fields": data["url_fields"],
        "languages": list(set([lang for sublist in data["detected_languages"].values() for lang in sublist])),
        "license_info": meta["license"],
        "date_version_info": meta["date_version"],
        "sample_records": data["sample_records"],
        "pii_info": data["pii_info"],
        "data_quality_issues": meta["quality_issues"],
        "evaluation_against_capabilities": eval_matrix,
        "source_credibility": meta["credibility"],
        "recommendation": meta["recommendation"]
    }

# Add ZIP to inventory
zip_meta = meta_mapping["archive (1).zip"]
inventory_output["archive (1).zip"] = {
    "dataset_name": "State and Central Scheme Documents Corpus (Archive)",
    "file_name": "archive (1).zip",
    "file_type": "ZIP Archive (Plain text documents)",
    "size_bytes": zip_raw["size_bytes"],
    "size_mb": zip_raw["size_mb"],
    "num_records": zip_raw["total_files"],
    "num_fields": 3,
    "field_names": ["folder_category (state/central)", "document_filename", "document_text_content"],
    "data_types": {"folder_category": "string", "document_filename": "string", "document_text_content": "string"},
    "missing_counts": {"folder_category": 0, "document_filename": 0, "document_text_content": 0},
    "missing_percentages": {"folder_category": 0.0, "document_filename": 0.0, "document_text_content": 0.0},
    "duplicate_records_count": 0,
    "unique_scheme_count": 1124,
    "possible_scheme_name_duplicates": "N/A (unstructured files)",
    "possible_id_fields": ["document_filename"],
    "url_source_fields": ["Embedded URLs in document text body"],
    "languages": ["English (Latin script)", "Transliterated Hindi / Indic terms"],
    "license_info": zip_meta["license"],
    "date_version_info": zip_meta["date_version"],
    "sample_records": zip_raw["sample_files"],
    "pii_info": {"pii_columns": [], "content_pii_flags": {"notes": "Department phone numbers / helpline contacts inside text"}, "is_citizen_pii": False},
    "data_quality_issues": zip_meta["quality_issues"],
    "evaluation_against_capabilities": build_evaluation_matrix("archive (1).zip"),
    "source_credibility": zip_meta["credibility"],
    "recommendation": zip_meta["recommendation"]
}

with open("data/interim/dataset_inventory.json", "w", encoding="utf-8") as f:
    json.dump(inventory_output, f, indent=2, ensure_ascii=False)
print("Saved data/interim/dataset_inventory.json")

# 2. Build field_inventory.json
field_inventory = {}
for fname, data in inventory_output.items():
    field_inventory[fname] = {
        "file_name": fname,
        "dataset_name": data["dataset_name"],
        "num_fields": data["num_fields"],
        "fields": []
    }
    for field_name in data["field_names"]:
        dtype = data["data_types"].get(field_name, "string")
        missing_cnt = data["missing_counts"].get(field_name, 0)
        missing_pct = data["missing_percentages"].get(field_name, 0.0)
        
        # Categorize field role
        field_lower = field_name.lower()
        if "slug" in field_lower or "id" in field_lower:
            role = "IDENTIFIER"
        elif "scheme" in field_lower or "title" in field_lower or "name" in field_lower:
            role = "SCHEME_NAME_ENTITY"
        elif "eligib" in field_lower or "age" in field_lower or "income" in field_lower or "category" in field_lower or "state" in field_lower:
            role = "ELIGIBILITY_CRITERIA"
        elif "benefit" in field_lower or "dbt" in field_lower:
            role = "BENEFIT_ENTITLEMENT"
        elif "doc" in field_lower:
            role = "REQUIRED_DOCUMENTATION"
        elif "appl" in field_lower:
            role = "APPLICATION_PROCEDURE"
        elif "question" in field_lower or "answer" in field_lower or "faq" in field_lower:
            role = "QUESTION_ANSWER_FAQ"
        elif "url" in field_lower or "ref" in field_lower or "website" in field_lower:
            role = "PROVENANCE_SOURCE_LINK"
        elif "desc" in field_lower or "detail" in field_lower:
            role = "SCHEME_DESCRIPTION_TEXT"
        elif "unnamed" in field_lower:
            role = "CORRUPT_OR_INDEX_ARTIFACT"
        else:
            role = "METADATA_ATTRIBUTE"
            
        field_inventory[fname]["fields"].append({
            "name": field_name,
            "data_type": dtype,
            "missing_count": missing_cnt,
            "missing_percentage": missing_pct,
            "semantic_role": role
        })

with open("data/interim/field_inventory.json", "w", encoding="utf-8") as f:
    json.dump(field_inventory, f, indent=2, ensure_ascii=False)
print("Saved data/interim/field_inventory.json")

# 3. Build dataset_overlap_report.json
with open("data/interim/dataset_overlap_raw.json", "r", encoding="utf-8") as f:
    overlap_raw = json.load(f)

# Combine into comprehensive cross-dataset overlap report
overlap_full = {
    "summary": {
        "total_datasets": len(inventory_output),
        "total_records": sum(d["num_records"] for d in inventory_output.values()),
        "approx_unique_schemes_canonical": 4748, # 4669 from schemes.csv + 79 unique from updated_data
        "primary_structured_dataset": "schemes.csv",
        "primary_qa_dataset": "schemes_faqs.csv",
        "multilingual_evaluation_dataset": "indian government schemes dataset english and hindi.csv",
        "unstructured_rag_source": "archive (1).zip"
    },
    "pairwise_overlaps": overlap_raw,
    "unique_fields_by_dataset": {
        "schemes.csv": [
            "short_title", "ministry", "department", "beneficiary_type", "target_beneficiaries",
            "benefit_type", "sub_categories", "detailed_description", "exclusions",
            "application_mode", "references", "scheme_open_date", "scheme_close_date",
            "dbt_scheme", "faq_count", "source_url"
        ],
        "schemes_faqs.csv": ["faq_number"],
        "updated_data.csv": ["Unnamed: 9 (artifact)", "schemeCategory"],
        "indian government schemes dataset english and hindi.csv": [
            "question (Hindi)", "answer (Hindi)", "difficulty_level", "launched_year", "official_website"
        ],
        "Indian_Government_Scheme_Eligibility_Dataset.csv": [
            "Age (synthetic)", "Annual_Income_INR (synthetic)", "Category (synthetic)", "Eligible_Scheme (synthetic)"
        ],
        "archive (1).zip": ["state/central folder hierarchy", "raw scraped narrative blog text"]
    },
    "conflicts_and_discrepancies": {
        "schemes_csv_vs_updated_data": {
            "slug_overlap": 3318,
            "eligibility_conflicts": 3213,
            "eligibility_identical": 105,
            "nature_of_conflict": "Formatting and delimiter divergence. schemes.csv preserves structured semicolon delimiters ('; ') between distinct conditions, while updated_data.csv concatenated sentences with spaces, leading to lost boundary markers and merged words.",
            "coverage_difference": "schemes.csv contains 1,352 schemes missing from updated_data.csv. updated_data.csv contains 79 schemes missing from schemes.csv."
        },
        "statutory_vs_synthetic_eligibility_conflict": {
            "dataset": "Indian_Government_Scheme_Eligibility_Dataset.csv",
            "conflict_description": "Direct contradiction of Government of India statutory scheme eligibility criteria. Atal Pension Yojana legally mandates entry age between 18 and 40 years, whereas the synthetic dataset marks citizens aged 60-80 with INR 1,100,000 income as eligible. Similar severe errors exist for PM Kisan and PM Awas Yojana."
        }
    },
    "coverage_analysis": {
        "central_vs_state": {
            "schemes.csv": "Central Schemes: ~649 schemes; State Schemes: ~4,021 schemes across 36 States & UTs",
            "updated_data.csv": "Central: 512 schemes; State: 2,888 schemes",
            "archive (1).zip": "28 State folders (1,319 files) + Central folder (205 files) = 1,524 documents",
            "indian government schemes dataset english and hindi.csv": "Central: 96 landmark national schemes",
            "Indian_Government_Scheme_Eligibility_Dataset.csv": "9 States only, 7 Schemes"
        },
        "language_distribution": {
            "schemes.csv": "100% English (with Indian civic terminology in Latin transliteration)",
            "schemes_faqs.csv": "100% English",
            "updated_data.csv": "100% English",
            "indian government schemes dataset english and hindi.csv": "50% English, 50% Hindi (Devanagari script, parallel translated)",
            "archive (1).zip": "100% English narrative articles",
            "Indian_Government_Scheme_Eligibility_Dataset.csv": "English labels only"
        }
    }
}

with open("data/interim/dataset_overlap_report.json", "w", encoding="utf-8") as f:
    json.dump(overlap_full, f, indent=2, ensure_ascii=False)
print("Saved data/interim/dataset_overlap_report.json")
