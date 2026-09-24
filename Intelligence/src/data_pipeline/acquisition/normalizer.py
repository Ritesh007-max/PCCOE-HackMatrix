"""
FIN Comprehensive Scheme Normalization & Fact Extraction Engine.
Transforms raw myScheme and first-party API responses into normalized,
statutory-compliant Scheme entities with structured eligibility conditions,
immutable provenance, and graph relationship tracking.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from .models import (
    AuthorityTierName,
    Benefit,
    EligibilityCriterion,
    FAQ,
    LanguageVariant,
    RelationshipType,
    RequiredDocument,
    ApplicationStep,
    Scheme,
    SchemeAlias,
    SchemeRelationship,
    SchemeStatus,
    DetailStatus,
    LiveProvenanceEnvelope,
    ProvenanceStatus,
)
from .authority import AuthorityHierarchy
from .security import AcquisitionSecurityValidator


class SchemeNormalizer:
    """
    Normalizes multi-tier government policy data into canonical structures.
    Extracts both raw text and normalized deterministic conditions for eligibility.
    """

    @classmethod
    def parse_slate_ast(cls, node: Any) -> str:
        """
        Recursively extracts plain text from Slate.js / rich text AST nodes.
        """
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "\n".join([cls.parse_slate_ast(child) for child in node if child])
        if isinstance(node, dict):
            if "text" in node:
                return str(node["text"])
            if "children" in node:
                ntype = str(node.get("type", ""))
                sep = "\n" if ntype in ("list_item", "paragraph", "ul_list", "ol_list", "heading_four", "heading_five", "block_quote") else " "
                children_text = [cls.parse_slate_ast(child) for child in node["children"]]
                return sep.join([t for t in children_text if t])
        return ""

    @classmethod
    def extract_structured_eligibility(
        cls,
        raw_text: str,
        source_url: str,
        authority_tier: str,
        scheme_id: str,
    ) -> List[EligibilityCriterion]:
        """
        Parses raw eligibility text into deterministic structured conditions
        while strictly preserving original text evidence.
        """
        criteria: List[EligibilityCriterion] = []
        if not raw_text:
            return criteria

        clean_text = raw_text.replace("\r", "\n")
        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]

        for idx, line in enumerate(lines):
            cid = f"crit_{scheme_id[:8]}_{idx}"

            # 1. Age criteria detection
            # e.g., "The minimum age of joining is 18 years and maximum is 40 years."
            min_age_match = re.search(r"(?:minimum|min|at least|above|from)\s+(\d+)\s*(?:years|yrs)", line, re.I)
            max_age_match = re.search(r"(?:maximum|max|up to|below|under|not exceeding)\s+(\d+)\s*(?:years|yrs)", line, re.I)
            between_age_match = re.search(r"between\s+(\d+)\s*(?:and|to|-)\s*(\d+)\s*(?:years|yrs)", line, re.I)

            if between_age_match:
                min_v, max_v = int(between_age_match.group(1)), int(between_age_match.group(2))
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_min_age",
                        field="age",
                        operator=">=",
                        value=min_v,
                        unit="years",
                        raw_text=line,
                        normalized_condition={"field": "age", "operator": ">=", "value": min_v, "unit": "years"},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_max_age",
                        field="age",
                        operator="<=",
                        value=max_v,
                        unit="years",
                        raw_text=line,
                        normalized_condition={"field": "age", "operator": "<=", "value": max_v, "unit": "years"},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )
            else:
                if min_age_match:
                    min_v = int(min_age_match.group(1))
                    criteria.append(
                        EligibilityCriterion(
                            criterion_id=f"{cid}_min_age",
                            field="age",
                            operator=">=",
                            value=min_v,
                            unit="years",
                            raw_text=line,
                            normalized_condition={"field": "age", "operator": ">=", "value": min_v, "unit": "years"},
                            source_url=source_url,
                            authority_tier=authority_tier,
                        )
                    )
                if max_age_match:
                    max_v = int(max_age_match.group(1))
                    criteria.append(
                        EligibilityCriterion(
                            criterion_id=f"{cid}_max_age",
                            field="age",
                            operator="<=",
                            value=max_v,
                            unit="years",
                            raw_text=line,
                            normalized_condition={"field": "age", "operator": "<=", "value": max_v, "unit": "years"},
                            source_url=source_url,
                            authority_tier=authority_tier,
                        )
                    )

            # 2. Income criteria detection
            # e.g., "Family income must not exceed Rs. 2,50,000 per annum" or "income <= 300000"
            income_match = re.search(r"(?:income|family income|annual income)[^\d]{1,30}(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(?:per annum|annually|p\.a\.|per year)?", line, re.I)
            if income_match:
                inc_str = income_match.group(1).replace(",", "")
                try:
                    inc_val = float(inc_str)
                    criteria.append(
                        EligibilityCriterion(
                            criterion_id=f"{cid}_income",
                            field="annual_family_income",
                            operator="<=",
                            value=inc_val,
                            unit="INR/year",
                            raw_text=line,
                            normalized_condition={"field": "annual_family_income", "operator": "<=", "value": inc_val, "unit": "INR/year"},
                            source_url=source_url,
                            authority_tier=authority_tier,
                        )
                    )
                except ValueError:
                    pass

            # 3. Gender criteria
            if re.search(r"\b(women|female|girls|mothers)\b", line, re.I) and not re.search(r"\b(all|both male and female)\b", line, re.I):
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_gender",
                        field="gender",
                        operator="==",
                        value="Female",
                        raw_text=line,
                        normalized_condition={"field": "gender", "operator": "==", "value": "Female"},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )

            # 4. Social category criteria (SC / ST / OBC / Minority)
            if re.search(r"\b(SC|ST|Scheduled Caste|Scheduled Tribe)\b", line, re.I):
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_caste",
                        field="caste_category",
                        operator="in",
                        value=["SC", "ST"],
                        raw_text=line,
                        normalized_condition={"field": "caste_category", "operator": "in", "value": ["SC", "ST"]},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )
            elif re.search(r"\b(OBC|Other Backward Class)\b", line, re.I):
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_caste",
                        field="caste_category",
                        operator="in",
                        value=["OBC"],
                        raw_text=line,
                        normalized_condition={"field": "caste_category", "operator": "in", "value": ["OBC"]},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )

            # 5. Student / Education criteria
            if re.search(r"\b(student|enrolled in school|college|university|class \d+)\b", line, re.I):
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_student",
                        field="is_student",
                        operator="==",
                        value=True,
                        raw_text=line,
                        normalized_condition={"field": "is_student", "operator": "==", "value": True},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )

            # 6. BPL criteria
            if re.search(r"\b(BPL|Below Poverty Line|antodaya|AAY)\b", line, re.I):
                criteria.append(
                    EligibilityCriterion(
                        criterion_id=f"{cid}_bpl",
                        field="is_bpl",
                        operator="==",
                        value=True,
                        raw_text=line,
                        normalized_condition={"field": "is_bpl", "operator": "==", "value": True},
                        source_url=source_url,
                        authority_tier=authority_tier,
                    )
                )

        return criteria

    @classmethod
    def validate_detail_completeness(cls, raw_detail_json: Dict[str, Any]) -> Tuple[DetailStatus, List[str]]:
        """
        Validates completeness of portal scheme detail response (Section 12):
        - basicDetails
        - schemeContent
        - eligibilityCriteria
        - benefits
        - applicationProcess
        - references
        """
        data_block = raw_detail_json.get("data", {})
        if not data_block or not isinstance(data_block, dict):
            status_code = raw_detail_json.get("statusCode") or raw_detail_json.get("status")
            if status_code in (404, 410, "404", "410"):
                return DetailStatus.NOT_AVAILABLE, ["HTTP_404_NOT_FOUND"]
            return DetailStatus.FAILED, ["EMPTY_DATA_BLOCK"]

        en_block = data_block.get("en", {}) if "en" in data_block else data_block
        if not isinstance(en_block, dict) or not en_block:
            return DetailStatus.CATALOG_ONLY, ["NO_EN_BLOCK"]

        missing: List[str] = []
        basic = en_block.get("basicDetails", {})
        content = en_block.get("schemeContent", {})
        eligibility = en_block.get("eligibilityCriteria", {})
        app_proc = en_block.get("applicationProcess", [])

        # Check basic details
        if not basic or not (basic.get("schemeName") or basic.get("scheme_name")):
            missing.append("basicDetails.schemeName")

        # Check eligibility
        elig_text = eligibility.get("eligibilityDescription_md") or cls.parse_slate_ast(eligibility.get("eligibilityDescription", []))
        if not elig_text or not elig_text.strip():
            missing.append("eligibilityCriteria")

        # Check benefits
        benefits_text = content.get("benefits_md") or cls.parse_slate_ast(content.get("benefits", []))
        if not benefits_text or not benefits_text.strip():
            missing.append("benefits")

        # Check application process
        if not app_proc or not isinstance(app_proc, list) or len(app_proc) == 0:
            missing.append("applicationProcess")

        # Check references
        refs = content.get("references", [])
        if not refs or not isinstance(refs, list) or len(refs) == 0:
            missing.append("references")

        if not missing:
            return DetailStatus.FULL_DETAIL, []
        elif "eligibilityCriteria" not in missing:
            # Valid criteria present, but missing optional/secondary fields (e.g. non-monetary benefits or references)
            return DetailStatus.PARTIAL_DETAIL, missing
        elif basic and (basic.get("schemeName") or basic.get("scheme_name")):
            return DetailStatus.CATALOG_ONLY, missing
        else:
            return DetailStatus.FAILED, missing

    @classmethod
    def normalize_myscheme_payload(
        cls,
        raw_detail_json: Dict[str, Any],
        raw_docs_json: Optional[Dict[str, Any]] = None,
        raw_faqs_json: Optional[Dict[str, Any]] = None,
        raw_translations_json: Optional[Dict[str, Any]] = None,
        source_url: str = "",
        snapshot_id: str = "snap_init",
        provenance_envelope: Optional[LiveProvenanceEnvelope] = None,
        provenance_status: Optional[str] = None,
    ) -> Scheme:
        """
        Normalizes a full scheme record from API JSON responses into an authoritative Scheme entity.
        """
        data_block = raw_detail_json.get("data", {})
        if "en" in data_block:
            en_block = data_block.get("en", {})
        else:
            en_block = data_block

        slug = data_block.get("slug") or raw_detail_json.get("slug") or "unknown-slug"
        scheme_id = str(data_block.get("_id") or uuid.uuid5(uuid.NAMESPACE_URL, f"myscheme:{slug}"))

        basic = en_block.get("basicDetails", {})
        content = en_block.get("schemeContent", {})
        eligibility = en_block.get("eligibilityCriteria", {})
        app_proc = en_block.get("applicationProcess", [])

        # Identity
        scheme_name = basic.get("schemeName") or basic.get("scheme_name") or slug.replace("-", " ").title()
        short_title = basic.get("schemeShortTitle") or basic.get("shortTitle") or ""
        alternate_names: List[str] = [short_title] if short_title else []

        # Authority
        level_raw = basic.get("level")
        level_str = "Central"
        if isinstance(level_raw, dict):
            level_str = level_raw.get("label", "Central").title()
        elif isinstance(level_raw, str):
            level_str = level_raw.title()

        state_or_ut: Optional[str] = None
        if level_str == "State":
            st_raw = basic.get("state")
            if isinstance(st_raw, dict):
                state_or_ut = st_raw.get("label")
            elif isinstance(st_raw, str):
                state_or_ut = st_raw

        ministry_raw = basic.get("nodalMinistryName")
        ministry_name = ministry_raw.get("label") if isinstance(ministry_raw, dict) else str(ministry_raw or "")
        dept_raw = basic.get("nodalDepartmentName")
        dept_name = dept_raw.get("label") if isinstance(dept_raw, dict) else str(dept_raw or "")
        agency = basic.get("implementingAgency")

        # Classification
        category_raw = basic.get("schemeCategory")
        category_name = "Social welfare & Empowerment"
        if isinstance(category_raw, list) and category_raw:
            first_cat = category_raw[0]
            category_name = first_cat.get("label") if isinstance(first_cat, dict) else str(first_cat)
        elif isinstance(category_raw, dict):
            category_name = category_raw.get("label", category_name)

        tags = basic.get("tags") or []
        beneficiary_groups = basic.get("targetBeneficiaries") or []

        # Content
        brief_desc = content.get("briefDescription") or ""
        detailed_desc = content.get("detailedDescription_md") or cls.parse_slate_ast(content.get("detailedDescription", []))

        # Eligibility
        elig_md = eligibility.get("eligibilityDescription_md") or cls.parse_slate_ast(eligibility.get("eligibilityDescription", []))
        criteria = cls.extract_structured_eligibility(
            raw_text=elig_md,
            source_url=source_url,
            authority_tier=AuthorityTierName.TIER_2_MYSCHEME.value,
            scheme_id=scheme_id,
        )

        # Benefits
        benefits_md_direct = content.get("benefits_md")
        benefits_md = benefits_md_direct or cls.parse_slate_ast(content.get("benefits", []))
        benefit_type_raw = content.get("benefitTypes")
        btype = "Cash"
        if isinstance(benefit_type_raw, dict):
            btype = benefit_type_raw.get("label", "Cash")
        elif isinstance(benefit_type_raw, str):
            btype = benefit_type_raw

        benefits_list: List[Benefit] = []
        if benefits_md_direct and benefits_md_direct.strip():
            benefits_list.append(
                Benefit(
                    benefit_id=f"ben_{scheme_id[:8]}_0",
                    benefit_type=btype,
                    raw_text=benefits_md_direct,
                    source_url=source_url,
                    authority_tier=AuthorityTierName.TIER_2_MYSCHEME.value,
                )
            )

        # Application Process
        app_steps: List[ApplicationStep] = []
        app_modes: List[str] = []
        if isinstance(app_proc, list):
            for p_idx, proc_item in enumerate(app_proc):
                if isinstance(proc_item, dict):
                    mode = proc_item.get("mode", "Online")
                    if mode not in app_modes:
                        app_modes.append(mode)
                    proc_ast = proc_item.get("process", [])
                    step_text = cls.parse_slate_ast(proc_ast)
                    app_steps.append(
                        ApplicationStep(
                            step_number=p_idx + 1,
                            title=f"Application Step {p_idx + 1} ({mode})",
                            description=step_text,
                            mode=mode,
                        )
                    )

        # Official References & Documents
        official_urls: List[str] = []
        official_guideline_url: Optional[str] = None
        refs = content.get("references", [])
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, dict):
                    u = (ref.get("url") or "").strip()
                    if u and u.startswith("http"):
                        official_urls.append(u)
                        if "guideline" in ref.get("title", "").lower() or u.lower().endswith(".pdf"):
                            if not official_guideline_url:
                                official_guideline_url = u

        # Documents
        req_docs: List[RequiredDocument] = []
        docs_raw_text = ""
        if raw_docs_json and isinstance(raw_docs_json.get("data"), dict):
            doc_data = raw_docs_json.get("data", {}).get("en")
            if isinstance(doc_data, dict):
                docs_raw_text = doc_data.get("documentsRequired_md") or cls.parse_slate_ast(doc_data.get("documents_required", []))
                for d_idx, line in enumerate([ln.strip() for ln in docs_raw_text.split("\n") if ln.strip()]):
                    clean_line = re.sub(r"^[0-9*#-.\s]+", "", line).strip()
                    if clean_line and clean_line.lower() not in ("<br>", "<br/>", "<p>", "</p>", "none", "n/a", "nil"):
                        req_docs.append(
                            RequiredDocument(
                                document_id=f"doc_{scheme_id[:8]}_{d_idx}",
                                document_name=clean_line,
                                is_mandatory=True,
                                raw_text=line,
                                source_url=source_url,
                            )
                        )

        # FAQs
        faq_list: List[FAQ] = []
        if raw_faqs_json and isinstance(raw_faqs_json.get("data"), dict):
            faq_en = raw_faqs_json.get("data", {}).get("en")
            faq_entries = faq_en.get("faqs", []) if isinstance(faq_en, dict) else []
            if isinstance(faq_entries, list):
                for f_idx, f_item in enumerate(faq_entries):
                    if isinstance(f_item, dict):
                        q = f_item.get("question", "").strip()
                        ans = f_item.get("answer_md") or cls.parse_slate_ast(f_item.get("answer", []))
                        if q:
                            faq_list.append(
                                FAQ(
                                    faq_id=f"faq_{scheme_id[:8]}_{f_idx}",
                                    question=q,
                                    answer=ans.strip(),
                                    language="en",
                                    source_url=source_url,
                                )
                            )

        # Multilingual Variants
        local_names: Dict[str, str] = {}
        language_variants: List[LanguageVariant] = []
        if raw_translations_json:
            t_data = raw_translations_json.get("data", [])
            target_entry = None
            if isinstance(t_data, list):
                for item in t_data:
                    if item.get("slug") == slug:
                        target_entry = item
                        break
            if target_entry:
                for lang_code in ["hi", "gu", "as", "bn", "kn", "ks", "mai", "ml", "mr", "or", "pa", "ta", "te", "ur"]:
                    lang_obj = target_entry.get(lang_code)
                    if isinstance(lang_obj, dict):
                        b_det = lang_obj.get("basicDetails", {})
                        l_name = b_det.get("schemeName") or ""
                        if l_name:
                            local_names[lang_code] = l_name
                            language_variants.append(
                                LanguageVariant(
                                    scheme_id=scheme_id,
                                    language=lang_code,
                                    original_name=l_name,
                                    original_text=json.dumps(lang_obj, ensure_ascii=False),
                                    source_url=f"https://www.myscheme.gov.in/schemes/{slug}",
                                    fetched_at=datetime.now(timezone.utc).isoformat(),
                                )
                            )

        # Graph Relationships (e.g. umbrella / component schemes)
        relationships: List[SchemeRelationship] = []
        if "samagra" in slug or "ayushman" in slug or "pm-kisan" in slug:
            # Detect umbrella or component relationships
            if "samagra" in slug:
                relationships.append(
                    SchemeRelationship(
                        source_scheme_id=scheme_id,
                        target_scheme_id="umbrella_education_samagra",
                        relationship_type=RelationshipType.COMPONENT_OF,
                        description="Component scheme under Samagra Shiksha umbrella program",
                    )
                )

        now_iso = datetime.now(timezone.utc).isoformat()
        first_party_official_url = official_urls[0] if official_urls else None

        scheme = Scheme(
            scheme_id=scheme_id,
            canonical_slug=slug,
            scheme_name=scheme_name,
            alternate_names=alternate_names,
            local_names=local_names,
            scheme_type=basic.get("schemeType", "Central Sector"),
            scheme_status=SchemeStatus.ACTIVE,
            ministry=ministry_name if ministry_name else None,
            department=dept_name if dept_name else None,
            implementing_agency=agency,
            central_or_state=level_str,
            state_or_ut=state_or_ut,
            category=str(category_name or "Social welfare & Empowerment"),
            tags=tags,
            beneficiary_groups=beneficiary_groups,
            brief_description=AcquisitionSecurityValidator.sanitize_untrusted_text(brief_desc),
            detailed_description=AcquisitionSecurityValidator.sanitize_untrusted_text(detailed_desc),
            eligibility_criteria=criteria,
            raw_eligibility_text=elig_md,
            benefits=benefits_list,
            raw_benefits_text=benefits_md,
            application_mode=app_modes or ["Online"],
            application_steps=app_steps,
            application_portal=None,
            application_url=None,
            required_documents=req_docs,
            raw_documents_text=docs_raw_text,
            faqs=faq_list,
            myscheme_url=f"https://www.myscheme.gov.in/schemes/{slug}",
            official_scheme_url=first_party_official_url,
            official_guideline_url=official_guideline_url,
            official_pdf_urls=official_urls,
            fetched_at=now_iso,
            source_url=source_url or f"https://www.myscheme.gov.in/schemes/{slug}",
            authority_tier=AuthorityTierName.TIER_2_MYSCHEME.value,
            snapshot_id=snapshot_id,
            acquisition_run_id=provenance_envelope.acquisition_run_id if provenance_envelope else "",
            detail_status=provenance_envelope.detail_status if provenance_envelope else DetailStatus.FULL_DETAIL.value,
            provenance_status=provenance_status or (ProvenanceStatus.LIVE_ACQUIRED.value if provenance_envelope else ProvenanceStatus.NOT_LIVE_VERIFIED.value),
            provenance_envelope=provenance_envelope.to_dict() if provenance_envelope else None,
            relationships=relationships,
            language_variants=language_variants,
        )
        scheme.compute_content_hash()
        return scheme

    @classmethod
    def normalize_baseline_record(
        cls,
        row: Dict[str, Any],
        faqs: Optional[List[Dict[str, Any]]] = None,
        snapshot_id: str = "baseline_canonical",
    ) -> Scheme:
        """
        Normalizes a tabular baseline record (e.g. from schemes.csv and schemes_faqs.csv)
        into a canonical statutory Scheme entity with structured criteria.
        """
        slug = str(row.get("slug") or "").strip()
        scheme_id = str(row.get("_id") or f"scheme_{slug}")
        name = str(row.get("scheme_name") or row.get("Scheme_Name") or "").strip()
        short_title = str(row.get("short_title") or "").strip()
        alternate_names = [short_title] if short_title and short_title != name else []

        level_raw = str(row.get("level") or "Central").strip()
        level_str = "Central" if "central" in level_raw.lower() else "State"

        state_val = row.get("state")
        state_or_ut = str(state_val).strip() if state_val is not None and str(state_val).strip() and str(state_val).lower() != "nan" else None

        ministry_val = row.get("ministry")
        ministry_name = str(ministry_val).strip() if ministry_val is not None and str(ministry_val).strip() and str(ministry_val).lower() != "nan" else None

        dept_val = row.get("department")
        dept_name = str(dept_val).strip() if dept_val is not None and str(dept_val).strip() and str(dept_val).lower() != "nan" else None

        cat_val = row.get("categories") or "Social welfare & Empowerment"
        category = str(cat_val).strip()

        brief_desc = str(row.get("brief_description") or "")
        if brief_desc.lower() == "nan":
            brief_desc = ""

        detailed_desc = str(row.get("detailed_description") or "")
        if detailed_desc.lower() == "nan":
            detailed_desc = ""

        raw_elig = str(row.get("eligibility") or "")
        if raw_elig.lower() == "nan":
            raw_elig = ""

        source_url = str(row.get("source_url") or f"https://www.myscheme.gov.in/schemes/{slug}")

        # Eligibility extraction
        criteria = cls.extract_structured_eligibility(
            raw_text=raw_elig,
            source_url=source_url,
            authority_tier=AuthorityTierName.TIER_2_MYSCHEME.value,
            scheme_id=scheme_id,
        )

        # Benefits
        raw_ben = str(row.get("benefits") or "")
        if raw_ben.lower() == "nan":
            raw_ben = ""
        benefits_list: List[Benefit] = []
        if raw_ben.strip():
            b_type = str(row.get("benefit_type") or "Cash").strip()
            if b_type.lower() == "nan":
                b_type = "Cash"
            benefits_list.append(
                Benefit(
                    benefit_id=f"ben_{scheme_id[:8]}_0",
                    benefit_type=b_type,
                    raw_text=raw_ben.strip(),
                    source_url=source_url,
                    authority_tier=AuthorityTierName.TIER_2_MYSCHEME.value,
                )
            )

        # Application Process
        raw_app = str(row.get("application_process") or "")
        if raw_app.lower() == "nan":
            raw_app = ""
        app_steps: List[ApplicationStep] = []
        app_modes = [str(row.get("application_mode") or "Online").strip()]
        if raw_app.strip():
            for idx, line in enumerate([l.strip() for l in raw_app.split("\n") if l.strip()]):
                app_steps.append(
                    ApplicationStep(
                        step_number=idx + 1,
                        title=f"Step {idx + 1}",
                        description=line,
                        mode=app_modes[0] if app_modes else "Online",
                    )
                )

        # Documents Required
        raw_docs = str(row.get("documents_required") or "")
        if raw_docs.lower() == "nan":
            raw_docs = ""
        req_docs: List[RequiredDocument] = []
        if raw_docs.strip():
            for d_idx, line in enumerate([l.strip() for l in raw_docs.split("\n") if l.strip()]):
                clean_name = re.sub(r"^[0-9*#-.\s]+", "", line).strip()
                if clean_name:
                    req_docs.append(
                        RequiredDocument(
                            document_id=f"doc_{scheme_id[:8]}_{d_idx}",
                            document_name=clean_name,
                            is_mandatory=True,
                            raw_text=line,
                            source_url=source_url,
                        )
                    )

        # FAQs
        faq_list: List[FAQ] = []
        if faqs:
            for f_idx, item in enumerate(faqs):
                q = str(item.get("question") or "").strip()
                a = str(item.get("answer") or "").strip()
                if q:
                    faq_list.append(
                        FAQ(
                            faq_id=f"faq_{scheme_id[:8]}_{f_idx}",
                            question=q,
                            answer=a,
                            language="en",
                            source_url=source_url,
                        )
                    )

        # References
        official_urls: List[str] = []
        official_guideline_url: Optional[str] = None
        refs_str = str(row.get("references") or "")
        if refs_str and refs_str.lower() != "nan":
            for token in refs_str.split():
                clean_u = token.strip().strip("[],'\"")
                if clean_u.startswith("http"):
                    official_urls.append(clean_u)
                    if "guideline" in clean_u.lower() or clean_u.lower().endswith(".pdf"):
                        if not official_guideline_url:
                            official_guideline_url = clean_u

        tags_str = str(row.get("tags") or "")
        tags = [t.strip().strip("[]'\"") for t in tags_str.split(",") if t.strip()] if tags_str and tags_str.lower() != "nan" else []

        beneficiaries_str = str(row.get("target_beneficiaries") or "")
        beneficiaries = [b.strip() for b in beneficiaries_str.split(",") if b.strip()] if beneficiaries_str and beneficiaries_str.lower() != "nan" else []

        now_iso = datetime.now(timezone.utc).isoformat()
        first_party_official_url = official_urls[0] if official_urls else None

        scheme = Scheme(
            scheme_id=scheme_id,
            canonical_slug=slug,
            scheme_name=name,
            alternate_names=alternate_names,
            local_names={},
            scheme_type="Central Sector" if level_str == "Central" else "State Scheme",
            scheme_status=SchemeStatus.ACTIVE,
            ministry=ministry_name,
            department=dept_name,
            implementing_agency=None,
            central_or_state=level_str,
            state_or_ut=state_or_ut,
            category=category,
            tags=tags,
            beneficiary_groups=beneficiaries,
            brief_description=AcquisitionSecurityValidator.sanitize_untrusted_text(brief_desc),
            detailed_description=AcquisitionSecurityValidator.sanitize_untrusted_text(detailed_desc),
            eligibility_criteria=criteria,
            raw_eligibility_text=raw_elig,
            benefits=benefits_list,
            raw_benefits_text=raw_ben,
            application_mode=app_modes,
            application_steps=app_steps,
            application_portal=None,
            application_url=None,
            required_documents=req_docs,
            raw_documents_text=raw_docs,
            faqs=faq_list,
            myscheme_url=f"https://www.myscheme.gov.in/schemes/{slug}",
            official_scheme_url=first_party_official_url,
            official_guideline_url=official_guideline_url,
            official_pdf_urls=official_urls,
            fetched_at=now_iso,
            source_url=source_url,
            authority_tier=AuthorityTierName.TIER_2_MYSCHEME.value,
            snapshot_id=snapshot_id,
            relationships=[],
            language_variants=[],
        )
        scheme.compute_content_hash()
        return scheme
