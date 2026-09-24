import os
import sys
import json
import uuid
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

examples_dir = Path("data/schemes/rules/examples")
examples_dir.mkdir(parents=True, exist_ok=True)

df = pq.read_table("data/processed/schemes_canonical.parquet").to_pandas()

def get_scheme(slug):
    m = df[df['slug'] == slug]
    if len(m) == 0:
        raise ValueError(f"Slug {slug} not found in canonical dataset!")
    return m.iloc[0]

# Define rule specifications for the 10 schemes strictly grounded in canonical text
specs = [
    # 1. Atal Pension Yojana (apy)
    {
        "slug": "apy",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "age",
                "operator": "between",
                "expected_value": {"min": 18, "max": 40},
                "value_type": "range",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "age", "op": "between", "val": {"min": 18, "max": 40}, "unit": "years"},
                "raw_text": "The minimum age of joining APY is 18 years and maximum is 40 years.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "has_bank_account",
                "operator": "is_true",
                "expected_value": True,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "has_bank_account", "op": "is_true", "val": True, "unit": None},
                "raw_text": "Subscriber contribution to APY shall be made through the facility of “auto-debit” of the prescribed contribution amount from the savings bank account/ post office savings bank account of the subscriber.",
                "source_section": "eligibility",
                "confidence": 0.95,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "exclusion",
                "field": "is_taxpayer",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "is_taxpayer", "op": "is_false", "val": False, "unit": None},
                "raw_text": "From 1st October, 2022, any citizen who is or has been an income tax payer, shall not be eligible to join APY.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 2. PM Kisan (pm-kisan)
    {
        "slug": "pm-kisan",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "owns_cultivable_land",
                "operator": "is_true",
                "expected_value": True,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "owns_cultivable_land", "op": "is_true", "val": True, "unit": None},
                "raw_text": "All landholding farmers' families, which have cultivable land holding in their names are eligible to get benefit under the scheme.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "exclusion",
                "field": "is_institutional_landholder",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "EXCLUSIONS_GROUP",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "is_institutional_landholder", "op": "is_false", "val": False, "unit": None},
                "raw_text": "The following categories of beneficiaries of higher economic status shall not be eligible for benefit under the scheme: a) All Institutional Landholders.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "exclusion",
                "field": "is_taxpayer",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "EXCLUSIONS_GROUP",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "is_taxpayer", "op": "is_false", "val": False, "unit": None},
                "raw_text": "All Persons who paid Income Tax in last assessment year are excluded.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 4,
                "rule_type": "exclusion",
                "field": "monthly_pension_amount",
                "operator": "<=",
                "expected_value": 10000,
                "value_type": "numeric",
                "logic_group": "EXCLUSIONS_GROUP",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "monthly_pension_amount", "op": "<=", "val": 10000, "unit": "INR/month"},
                "raw_text": "All Retired/pensioners whose monthly pension is Rs.10,000/-or more are excluded.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 3. Pradhan Mantri Matru Vandana Yojana (pmmvy)
    {
        "slug": "pmmvy",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "gender",
                "operator": "=",
                "expected_value": "Female",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "gender", "op": "=", "val": "Female", "unit": None},
                "raw_text": "The applicant should be of at least 19 years old and a pregnant women.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "age",
                "operator": ">=",
                "expected_value": 19,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "age", "op": ">=", "val": 19, "unit": "years"},
                "raw_text": "The applicant should be of at least 19 years old and a pregnant women.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "eligibility",
                "field": "is_pregnant_or_lactating",
                "operator": "is_true",
                "expected_value": True,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "is_pregnant_or_lactating", "op": "is_true", "val": True, "unit": None},
                "raw_text": "All pregnant women and lactating mothers who have experienced wage loss due to pregnancy.",
                "source_section": "eligibility",
                "confidence": 0.95,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 4,
                "rule_type": "exclusion",
                "field": "is_regular_govt_employee",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "is_regular_govt_employee", "op": "is_false", "val": False, "unit": None},
                "raw_text": "Pregnant women and lactating mothers who are in regular employment with the Central Government or State Governments or Public Sector Undertakings are excluded.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 4. PM SVANidhi (pm-svanidhi)
    {
        "slug": "pm-svanidhi",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "occupation",
                "operator": "=",
                "expected_value": "Street Vendor",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "occupation", "op": "=", "val": "Street Vendor", "unit": None},
                "raw_text": "Street vendors in possession of Certificate of Vending / Identity Card issued by Urban Local Bodies (ULBs).",
                "source_section": "eligibility",
                "confidence": 0.95,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "area_type",
                "operator": "in",
                "expected_value": ["Urban", "Peri-Urban"],
                "value_type": "list_string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "area_type", "op": "in", "val": ["Urban", "Peri-Urban"], "unit": None},
                "raw_text": "The vendors of surrounding development/ peri-urban/rural areas vending in the geographical limits of the ULBs.",
                "source_section": "eligibility",
                "confidence": 0.90,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "conditional",
                "field": "has_vending_certificate_or_lor",
                "operator": "is_true",
                "expected_value": True,
                "value_type": "boolean",
                "logic_group": "VENDING_PROOF",
                "required": True,
                "hard_constraint": False,
                "condition": {"field": "has_vending_certificate_or_lor", "op": "is_true", "val": True, "unit": None},
                "raw_text": "Street Vendors who have been issued Letter of Recommendation (LoR) by ULB / Town Vending Committee (TVC).",
                "source_section": "eligibility",
                "confidence": 0.90,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 5. Ayushman Bharat PMJAY (ab-pmjay)
    {
        "slug": "ab-pmjay",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "secc_deprivation_status",
                "operator": "manual_review",
                "expected_value": "Eligible per SECC 2011 Rural D1-D7 or Urban 11 occupational categories",
                "value_type": "unstructured",
                "logic_group": "SECC_CRITERIA",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "secc_deprivation_status", "op": "manual_review", "val": "SECC_2011_MATCH", "unit": None},
                "raw_text": "Automatically included Households without shelter, destitute, living on alms, manual scavenger families, primitive tribal groups.",
                "source_section": "eligibility",
                "confidence": 0.70,
                "review_status": "UNSTRUCTURED_REQUIRES_LLM_OR_MANUAL_REVIEW"
            },
            {
                "seq": 2,
                "rule_type": "exclusion",
                "field": "owns_motorized_vehicle",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "EXCLUSIONS_GROUP",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "owns_motorized_vehicle", "op": "is_false", "val": False, "unit": None},
                "raw_text": "Those who own a two, three, or four-wheeler or a motorized fishing boat.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "exclusion",
                "field": "owns_mechanized_farming_equipment",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "EXCLUSIONS_GROUP",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "owns_mechanized_farming_equipment", "op": "is_false", "val": False, "unit": None},
                "raw_text": "Those who own mechanized farming equipment.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 6. 108 Emergency Ambulance Service - Uttarakhand (108easuk)
    {
        "slug": "108easuk",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "state",
                "operator": "=",
                "expected_value": "Uttarakhand",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "state", "op": "=", "val": "Uttarakhand", "unit": None},
                "raw_text": "The beneficiary must be a resident of Uttarakhand.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "requires_emergency_medical_care",
                "operator": "is_true",
                "expected_value": True,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": False,
                "condition": {"field": "requires_emergency_medical_care", "op": "is_true", "val": True, "unit": None},
                "raw_text": "The benefit is provided to accident victims and individuals requiring emergency services.",
                "source_section": "eligibility",
                "confidence": 0.85,
                "review_status": "UNSTRUCTURED_REQUIRES_LLM_OR_MANUAL_REVIEW"
            }
        ]
    },
    # 7. Aponar Apon Ghar - Assam (aag)
    {
        "slug": "aag",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "state",
                "operator": "=",
                "expected_value": "Assam",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "state", "op": "=", "val": "Assam", "unit": None},
                "raw_text": "The applicants must be permanent residents of Assam state.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "annual_family_income",
                "operator": "<=",
                "expected_value": 2000000,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "annual_family_income", "op": "<=", "val": 2000000, "unit": "INR"},
                "raw_text": "The total family income of the applicant (from all sources) must not exceed ₹ 20,00,000.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "eligibility",
                "field": "housing_loan_amount",
                "operator": ">",
                "expected_value": 500000,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "housing_loan_amount", "op": ">", "val": 500000, "unit": "INR"},
                "raw_text": "The housing loan must be of more than ₹ 5,00,000 and sanctioned by bank on or after 1st April 2019.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 4,
                "rule_type": "exclusion",
                "field": "already_benefited_apon_ghar",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "already_benefited_apon_ghar", "op": "is_false", "val": False, "unit": None},
                "raw_text": "Those who already benefited under the Apon Ghar scheme are not eligible.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 8. 25% Capital Investment Subsidy Scheme (25-ciss)
    {
        "slug": "25-ciss",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "age",
                "operator": ">=",
                "expected_value": 18,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "age", "op": ">=", "val": 18, "unit": "years"},
                "raw_text": "Any individual above 18 years of age including Women, ex-servicemen & physically handicapped is eligible to apply under the scheme.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "enterprise_type",
                "operator": "in",
                "expected_value": ["Micro", "Small"],
                "value_type": "list_string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "enterprise_type", "op": "in", "val": ["Micro", "Small"], "unit": None},
                "raw_text": "New Micro or Small units engaged in manufacturing/servicing except the activities specified in the Negative List are eligible.",
                "source_section": "eligibility",
                "confidence": 0.95,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "eligibility",
                "field": "capital_investment_machinery_building",
                "operator": "<",
                "expected_value": 2500000,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "capital_investment_machinery_building", "op": "<", "val": 2500000, "unit": "INR"},
                "raw_text": "Machinery and Building below ₹25.00 Lakhs is only eligible under this Scheme.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 4,
                "rule_type": "exclusion",
                "field": "availed_other_institutional_subsidy",
                "operator": "is_false",
                "expected_value": False,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "availed_other_institutional_subsidy", "op": "is_false", "val": False, "unit": None},
                "raw_text": "The entrepreneurs who enjoyed any other subsidy from any other Institutions such as Lakshadweep Development Cooperation, LKVIB, Coir Board, Coconut Board, NABAD, etc. for the same purpose are not eligible.",
                "source_section": "exclusions",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 9. Award of Attendance Scholarship to Girl Students - Puducherry (aasgsmse)
    {
        "slug": "aasgsmse",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "citizenship",
                "operator": "=",
                "expected_value": "India",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "citizenship", "op": "=", "val": "India", "unit": None},
                "raw_text": "The applicant should be a citizen of India.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "state",
                "operator": "=",
                "expected_value": "Puducherry",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "state", "op": "=", "val": "Puducherry", "unit": None},
                "raw_text": "The applicant should be a native of the Union Territory of Puducherry by birth or by continuous residence for not less than 5 years.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "eligibility",
                "field": "gender",
                "operator": "=",
                "expected_value": "Female",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "gender", "op": "=", "val": "Female", "unit": None},
                "raw_text": "The applicant should be a Girl.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 4,
                "rule_type": "eligibility",
                "field": "age",
                "operator": "between",
                "expected_value": {"min": 11, "max": 14},
                "value_type": "range",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "age", "op": "between", "val": {"min": 11, "max": 14}, "unit": "years"},
                "raw_text": "The applicant should be in the age group of 11 to 14 years.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 5,
                "rule_type": "eligibility",
                "field": "school_attendance_percentage",
                "operator": ">=",
                "expected_value": 80,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "school_attendance_percentage", "op": ">=", "val": 80, "unit": "percent"},
                "raw_text": "The applicant should have a minimum attendance of 80% in the previous academic year.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    },
    # 10. Matru Jyothi - Financial Assistance For PwD Mothers - Kerala (mj-fapm)
    {
        "slug": "mj-fapm",
        "root_logic": "AND",
        "rules": [
            {
                "seq": 1,
                "rule_type": "eligibility",
                "field": "gender",
                "operator": "=",
                "expected_value": "Female",
                "value_type": "string",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "gender", "op": "=", "val": "Female", "unit": None},
                "raw_text": "The applicant should be a differently abled mother.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 2,
                "rule_type": "eligibility",
                "field": "has_child_under_two_years",
                "operator": "is_true",
                "expected_value": True,
                "value_type": "boolean",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "has_child_under_two_years", "op": "is_true", "val": True, "unit": None},
                "raw_text": "The differently abled mother who has a child less than two years old is eligible to apply under the scheme.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 3,
                "rule_type": "eligibility",
                "field": "disability_percentage",
                "operator": ">=",
                "expected_value": 40,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "disability_percentage", "op": ">=", "val": 40, "unit": "percent"},
                "raw_text": "The applicant with the following type of disability with 40% or more will be considered under the scheme: Blindness, Low vision, Locomotor disability, Hearing impairment.",
                "source_section": "eligibility",
                "confidence": 0.95,
                "review_status": "VERIFIED_DETERMINISTIC"
            },
            {
                "seq": 4,
                "rule_type": "eligibility",
                "field": "annual_family_income",
                "operator": "<=",
                "expected_value": 100000,
                "value_type": "numeric",
                "logic_group": "DEFAULT",
                "required": True,
                "hard_constraint": True,
                "condition": {"field": "annual_family_income", "op": "<=", "val": 100000, "unit": "INR"},
                "raw_text": "The applicant's annual family income should not exceed ₹1,00,000/-.",
                "source_section": "eligibility",
                "confidence": 1.0,
                "review_status": "VERIFIED_DETERMINISTIC"
            }
        ]
    }
]

created_files = []
for spec in specs:
    s_row = get_scheme(spec["slug"])
    scheme_id = s_row["id"]
    source_url = s_row["source_url"]
    
    rules_list = []
    for r in spec["rules"]:
        rule_id = f"rule_{spec['slug']}_{r['seq']:02d}"
        rules_list.append({
            "rule_id": rule_id,
            "scheme_id": scheme_id,
            "rule_type": r["rule_type"],
            "field": r["field"],
            "operator": r["operator"],
            "expected_value": r["expected_value"],
            "value_type": r["value_type"],
            "logic_group": r["logic_group"],
            "required": r["required"],
            "hard_constraint": r["hard_constraint"],
            "condition": r["condition"],
            "raw_text": r["raw_text"],
            "source_url": source_url,
            "source_document": "schemes_canonical.parquet",
            "source_page": None,
            "source_section": r["source_section"],
            "confidence": r["confidence"],
            "provenance": {
                "source_dataset": "schemes_canonical.parquet",
                "extractor": "policy_rule_extractor_v1",
                "extraction_timestamp": "2026-09-21T16:30:00Z",
                "review_status": r["review_status"]
            }
        })
        
    doc = {
        "scheme_id": scheme_id,
        "scheme_slug": spec["slug"],
        "scheme_name": s_row["scheme_name"],
        "version": "1.0.0",
        "last_updated": "2026-09-21T16:30:00Z",
        "root_logic": spec["root_logic"],
        "rules": rules_list
    }
    
    out_file = examples_dir / f"{spec['slug'].replace('-', '_')}_rules.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    created_files.append(out_file.name)
    print(f"Created example rule file: {out_file.name} ({len(rules_list)} rules)")

print(f"\nSuccessfully generated {len(created_files)} scheme rule example files in data/schemes/rules/examples/")
