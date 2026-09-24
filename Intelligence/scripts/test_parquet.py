import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json

sample_data = [
    {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "slug": "108easuk",
        "scheme_name": "108, Emergency Ambulance Service - Uttarakhand",
        "short_title": "108 EASUK",
        "level": "State",
        "state": "Uttarakhand",
        "ministry": None,
        "department": "Department Of Medical Health And Family Welfare",
        "beneficiary_type": "Individual",
        "target_beneficiaries": ["Individual"],
        "benefit_type": "In Kind",
        "categories": ["Health & Wellness"],
        "sub_categories": [],
        "tags": ["Patient", "108", "Emergency", "Ambulance Service"],
        "brief_description": "A state wide emergency ambulance service...",
        "detailed_description": "Detailed description text...",
        "benefits": "Free ambulance service equipped with life support...",
        "eligibility": "1. Resident of Uttarakhand; 2. In need of emergency care.",
        "exclusions": None,
        "application_mode": ["Offline"],
        "application_process": "Call 108 in case of emergency...",
        "documents_required": "No documents required...",
        "dbt_scheme": False,
        "faq_count": 5,
        "source_url": "https://www.myscheme.gov.in/schemes/108easuk",
        "references": ["https://uk.gov.in/doc.pdf"],
        "scheme_open_date": "2013-08-27",
        "scheme_close_date": None,
        "is_supplementary": False,
        "provenance": {
            "source_file": "schemes.csv",
            "source_portal": "myScheme",
            "ingestion_status": "authoritative_primary",
            "version": "1.0"
        }
    }
]

# Write to jsonl
with open("test_sample.jsonl", "w", encoding="utf-8") as f:
    for item in sample_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

# Write to parquet
table = pa.Table.from_pandas(pd.DataFrame(sample_data))
pq.write_table(table, "test_sample.parquet")

print("Successfully written test_sample.jsonl and test_sample.parquet")
# Read back
df_read = pq.read_table("test_sample.parquet").to_pandas()
print("Read back columns:", len(df_read.columns))
print("Categories type:", type(df_read.iloc[0]['categories']))
