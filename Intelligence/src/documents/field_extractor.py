"""
FIN Document Entity & Field Extractor.
Extracts structured administrative entities (Document Number, Beneficiary Name,
Income, Category, State, District, Issue Date, Issuing Authority) from OCR and
native PDF text streams with confidence scoring.
"""

import re
from typing import Any, Dict, Optional

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh"
]

COMMON_DISTRICTS = [
    "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Pune", "Mumbai", "Nagpur",
    "Nashik", "Thane", "Bengaluru", "Mysuru", "Jaipur", "Jodhpur", "Lucknow",
    "Kanpur", "Varanasi", "Patna", "Gaya", "Bhopal", "Indore", "Chandigarh"
]


def extract_document_fields(full_text: str, doc_type: str = "UNKNOWN_DOCUMENT", filename: str = "") -> Dict[str, Any]:
    """
    Extracts high-fidelity statutory fields from extracted document text.
    Returns normalized dictionary of key-value pairs suitable for DBT eligibility checking.
    """
    text = full_text or ""
    fields: Dict[str, Any] = {}
    doc_type_upper = str(doc_type).upper()

    # 1. Document / Certificate Number (Prioritize explicit certificate reference)
    cert_no_match = re.search(
        r"(?:Certificate\s*(?:Number|No\.?|Ref(?:erence)?)|Cert\s*No\.?)\s*[:=\-]?\s*([A-Za-z0-9\/\-_]{5,40})",
        text,
        re.IGNORECASE
    )
    if cert_no_match:
        cand = cert_no_match.group(1).strip()
        if re.search(r"[\d/\-]", cand) and cand.lower() not in ["token", "biometric", "status", "sample", "record"]:
            fields["document_number"] = cand

    if "document_number" not in fields:
        gen_cert = re.search(
            r"(?:Registration\s*No\.?|Application\s*No\.?|Doc\s*No\.?|Serial\s*No\.?|Reference\s*(?:No\.?|Code)?|Ref\s*No\.?)\s*[:=\-]?\s*([A-Za-z0-9\/\-_]{5,40})",
            text,
            re.IGNORECASE
        )
        if gen_cert:
            cand = gen_cert.group(1).strip()
            if re.search(r"[\d/\-]", cand) and cand.lower() not in ["token", "biometric", "status", "sample", "record"]:
                fields["document_number"] = cand

    if "document_number" not in fields:
        if "AADHAAR" in doc_type_upper or "aadhaar" in filename.lower():
            adh_match = re.search(r"\b(\d{4}\s*\d{4}\s*\d{4})\b", text)
            if adh_match:
                digits = adh_match.group(1).replace(" ", "")
                fields["document_number"] = f"XXXX-XXXX-{digits[-4:]}"
            else:
                adh_masked = re.search(r"\b([X\d]{4}[-\s][X\d]{4}[-\s]\d{4})\b", text, re.IGNORECASE)
                if adh_masked:
                    fields["document_number"] = adh_masked.group(1).strip()
        elif "PAN" in doc_type_upper or "pan" in filename.lower():
            pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
            if pan_match:
                fields["document_number"] = pan_match.group(1).strip()

    # Fallback document number search (standard Indian administrative slash/hyphen pattern)
    if "document_number" not in fields:
        generic_code = re.search(r"\b([A-Z]{2,4}\/[A-Z0-9]{2,6}\/\d{4}\/[A-Za-z0-9\-_]{4,15})\b", text)
        if generic_code:
            fields["document_number"] = generic_code.group(1).strip()

    # 2. Beneficiary / Applicant Name
    name_match = re.search(
        r"(?:Applicant\s*(?:Full\s*)?Name|Beneficiary\s*(?:Full\s*)?Name)\s*[:=\-]?\s*([A-Za-z\s\.]{2,40}?)(?:\n|\r|$)",
        text,
        re.IGNORECASE
    )
    if name_match:
        cand = name_match.group(1).strip()
        if len(cand) > 2 and not any(w in cand.lower() for w in ["government", "department", "certificate", "revenue", "gender", "age"]):
            fields["beneficiary_name"] = cand
    else:
        cert_name = re.search(
            r"(?:certify\s+that\s+|certifies\s+that\s+|this\s+is\s+to\s+certify\s+that\s+|name\s*(?:is|:|=)\s*)"
            r"(?:Shri|Smt|Kumari|Mr|Ms|Mrs)?\.?\s*([A-Za-z\s]{3,40}?)"
            r"(?:,|\n|resident|son\s+of|daughter\s+of|wife\s+of|w\/o|s\/o|d\/o|\s+has|\s+is)",
            text,
            re.IGNORECASE
        )
        if cert_name:
            cand = cert_name.group(1).strip()
            if len(cand) > 2 and not any(w in cand.lower() for w in ["government", "department", "certificate", "revenue", "gender"]):
                fields["beneficiary_name"] = cand
        elif "AADHAAR" in doc_type_upper:
            dob_rel = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*(?:\n|DOB|Year of Birth)", text)
            if dob_rel:
                fields["beneficiary_name"] = dob_rel.group(1).strip()

    # 3. Date of Birth & Age
    dob_match = re.search(
        r"(?:Date\s*of\s*Birth|DOB)\s*[:=\-]?\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
        text,
        re.IGNORECASE
    )
    if dob_match:
        fields["date_of_birth"] = dob_match.group(1).strip()

    age_match = re.search(
        r"(?:Completed\s*Age|\bAge\b)\s*[:=\-]?\s*([0-9]{1,3}(?:\s*Years|\s*Yrs)?)",
        text,
        re.IGNORECASE
    )
    if age_match:
        fields["age"] = age_match.group(1).strip()

    # 4. Strict Income Semantics: Separate Annual Family Income and Breakdown Components
    # 4a. Total Annual Family Income
    fam_match = (
        re.search(r"Total\s+Annual\s+Family\s+Income[\s\S]{0,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
        or re.search(r"(?:total\s+annual\s+family\s+income|annual\s+family\s+income)[\s\S]{0,120}?(?:\bis\b|\bof\b|:|-)\s*((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
        or re.search(r"(?:annual\s+family\s+income|total\s+family\s+income|family\s+income)\s*(?:is|of|[:=\-])?\s*((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
    )
    if not fam_match and ("income" in doc_type_upper or "income" in text.lower()):
        fam_match = re.search(
            r"(?:total\s+annual\s+income|annual\s+income|total\s+income)\s*[:=\-]?\s*((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
    if fam_match:
        raw_fam = fam_match.group(1).strip()
        if raw_fam:
            fmt_fam = raw_fam if (raw_fam.startswith("₹") or raw_fam.lower().startswith("rs") or raw_fam.upper().startswith("inr")) else f"₹{raw_fam}"
            fields["annual_family_income"] = fmt_fam
            fields["annual_income"] = fmt_fam

    # 4b. Father's Income Component
    father_match = (
        re.search(r"Father(?:\x27s|\'s)?\s*(?:Employment\s*)?Income[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
        or re.search(r"Annual\s+father(?:\x27s|\'s)?\s+wage[\s\S]{1,60}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
    )
    if father_match:
        raw_f = father_match.group(1).strip()
        if raw_f:
            fields["father_income"] = raw_f if (raw_f.startswith("₹") or raw_f.lower().startswith("rs") or raw_f.upper().startswith("inr")) else f"₹{raw_f}"

    # 4c. Mother's Income Component
    mother_match = (
        re.search(r"Mother(?:\x27s|\'s)?\s*(?:Self-Employment\s*)?Income[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
        or re.search(r"Annual\s+mother(?:\x27s|\'s)?\s+(?:craft\s+)?income[\s\S]{1,60}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
    )
    if mother_match:
        raw_m = mother_match.group(1).strip()
        if raw_m:
            fields["mother_income"] = raw_m if (raw_m.startswith("₹") or raw_m.lower().startswith("rs") or raw_m.upper().startswith("inr")) else f"₹{raw_m}"

    # 4d. Other Household Income Component
    other_match = re.search(r"Other\s+(?:Family\s+)?Income[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
    if other_match:
        raw_o = other_match.group(1).strip()
        if raw_o:
            fields["other_income"] = raw_o if (raw_o.startswith("₹") or raw_o.lower().startswith("rs") or raw_o.upper().startswith("inr")) else f"₹{raw_o}"

    # 4e. Explicit personal income: NEVER inferred from family income or salary cert unless explicitly stating personal/salary
    pers_match = re.search(
        r"(?:personal\s+(?:annual\s+)?income|individual\s+income|salary\s+slip|applicant\s+salary)\s*(?:is|=|:)?\s*"
        r"((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)\b",
        text,
        re.IGNORECASE
    )
    if pers_match:
        raw_p = pers_match.group(1).strip()
        if raw_p:
            fields["personal_income"] = raw_p if (raw_p.startswith("₹") or raw_p.lower().startswith("rs") or raw_p.upper().startswith("inr")) else f"₹{raw_p}"
            fields["annual_income"] = fields["personal_income"]

    # 5. Social Category / Caste
    category_match = re.search(
        r"(?:Category|Social\s*Category|Caste|Community)\s*[:=\-]?\s*([A-Za-z0-9\/\s\-]{2,30}?)(?:\n|\r|,|$)",
        text,
        re.IGNORECASE
    )
    if category_match:
        cat_val = category_match.group(1).strip()
        if cat_val and len(cat_val) < 30:
            fields["category"] = cat_val
    else:
        for c in ["OBC", "SC", "ST", "Scheduled Caste", "Scheduled Tribe", "General", "EWS", "SEBC"]:
            if re.search(rf"\b{re.escape(c)}\b", text, re.IGNORECASE):
                fields["category"] = c
                break

    # 6. Issue Date / Validity
    date_match = re.search(
        r"(?:Issue\s*Date|Date\s*of\s*Issue|Dated|Date)\s*[:=\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        text,
        re.IGNORECASE
    )
    if date_match:
        fields["issue_date"] = date_match.group(1).strip()

    # 7. Issuing Authority
    auth_match = re.search(
        r"(?:Authority|Issuing\s*Authority|Office\s*of|Issued\s*by|Signed\s*by)\s*[:=\-]?\s*([A-Za-z0-9\s,\.]{4,60}?)(?:\n|\r|$)",
        text,
        re.IGNORECASE
    )
    if auth_match:
        auth_val = auth_match.group(1).strip()
        if auth_val:
            fields["issuing_authority"] = auth_val
    elif "AADHAAR" in doc_type_upper:
        fields["issuing_authority"] = "Unique Identification Authority of India (UIDAI)"
    elif "PAN" in doc_type_upper:
        fields["issuing_authority"] = "Income Tax Department, Government of India"
    elif "revenue department" in text.lower():
        gov_match = re.search(r"government\s+of\s+([A-Za-z\s]+)", text, re.IGNORECASE)
        gov_name = gov_match.group(1).strip() if gov_match else "State Government"
        fields["issuing_authority"] = f"Revenue Department, Government of {gov_name}"

    # 8. State & District
    for st in INDIAN_STATES:
        if re.search(rf"\b{re.escape(st)}\b", text, re.IGNORECASE):
            fields["state"] = st
            break

    for dist in COMMON_DISTRICTS:
        if re.search(rf"\b{re.escape(dist)}\b", text, re.IGNORECASE):
            fields["district"] = dist
            break

    return fields
