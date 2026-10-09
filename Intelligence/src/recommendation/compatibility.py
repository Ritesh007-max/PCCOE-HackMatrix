"""
FIN Applicant-Scheme Deterministic Compatibility Analyzer.
Evaluates candidate scheme alignment against canonical citizen facts.

CRITICAL INVARIANTS:
1. Compatibility is a candidate relevance/fit score, NOT statutory eligibility.
2. UNKNOWN != MATCH and UNKNOWN != MISMATCH.
3. Conflicted applicant facts produce UNKNOWN with conflict flags.
4. Scoring is 100% deterministic, explainable, and zero-LLM.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.context.models import ApplicantContext
from src.recommendation.models import (
    CompatibilityResult,
    CompatibilityState,
    FactMatchDetail,
)
from src.rag.models import SchemeRetrievalResult
from src.rag.filters import INDIAN_STATES_KEYWORDS
from src.eligibility.engine import EligibilityEngine
from src.rules.models import RuleStatus

logger = logging.getLogger("fin.recommendation.compatibility")

# In-memory cache for canonical parquet schemes (< 0.1s one-time read)
_CANONICAL_CACHE: Optional[Dict[str, Dict[str, Any]]] = None

def get_canonical_scheme_record(slug: str) -> Optional[Dict[str, Any]]:
    """Loads authoritative scheme record from canonical parquet dataset."""
    global _CANONICAL_CACHE
    if _CANONICAL_CACHE is None:
        _CANONICAL_CACHE = {}
        try:
            from pathlib import Path
            import pandas as pd
            candidates = [
                Path(__file__).resolve().parents[2] / "data" / "processed" / "schemes_canonical.parquet",
                Path("data/processed/schemes_canonical.parquet"),
            ]
            for p in candidates:
                if p.exists():
                    df = pd.read_parquet(p)
                    for _, row in df.iterrows():
                        s_slug = str(row.get("slug", "")).strip()
                        if s_slug:
                            _CANONICAL_CACHE[s_slug] = row.to_dict()
                    logger.info("Loaded %d canonical scheme records into CompatibilityAnalyzer cache", len(_CANONICAL_CACHE))
                    break
        except Exception as e:
            logger.warning("Could not load schemes_canonical.parquet into cache: %s", e)
    return _CANONICAL_CACHE.get(slug) if _CANONICAL_CACHE else None


# Transparent deterministic weights across criteria dimensions
DEFAULT_COMPATIBILITY_WEIGHTS: Dict[str, float] = {
    "state": 0.25,
    "social_category": 0.20,
    "beneficiary_type": 0.20,
    "income": 0.20,
    "age": 0.15,
}


class CompatibilityAnalyzer:
    """
    Deterministic analyzer comparing applicant facts against scheme attributes
    and registered statutory rule conditions.
    """

    def __init__(self, eligibility_engine: Optional[EligibilityEngine] = None):
        self.eligibility_engine = eligibility_engine

    def analyze(
        self,
        scheme: SchemeRetrievalResult,
        applicant_context: Optional[ApplicantContext],
    ) -> CompatibilityResult:
        """
        Computes deterministic compatibility score, matched/unmatched/unknown fact details,
        and human-readable explainability logs.
        """
        matched: List[FactMatchDetail] = []
        unmatched: List[FactMatchDetail] = []
        unknown: List[FactMatchDetail] = []
        conflicts: List[FactMatchDetail] = []
        explanation: List[str] = []

        if not applicant_context:
            return CompatibilityResult(
                overall_compatibility_score=0.5,
                explanation=["Applicant context is empty; baseline neutral compatibility assigned."],
            )

        # Hydrate with full canonical structured metadata
        source_meta = dict(scheme.source_metadata or {})
        canon = get_canonical_scheme_record(scheme.scheme_slug) or {}
        for k, v in canon.items():
            if k not in source_meta or source_meta[k] is None:
                source_meta[k] = v
        conflicted_fields = set(applicant_context.conflicts)

        # -------------------------------------------------------------------
        # 1. Dimension: State Alignment
        # -------------------------------------------------------------------
        raw_state = source_meta.get("state")
        level_str = str(source_meta.get("level") or "").strip().lower()
        title_lower = (scheme.scheme_name or "").lower()
        dept_lower = f"{source_meta.get('ministry') or ''} {source_meta.get('department') or ''}".lower()

        # Check for state mentions in scheme title, ministry, department, or description
        desc_lower = str(source_meta.get("brief_description") or source_meta.get("description") or "").lower()
        detected_title_state = None
        for kw in INDIAN_STATES_KEYWORDS:
            if f"- {kw}" in title_lower or f"({kw})" in title_lower or f"for {kw}" in title_lower or f"in {kw}" in title_lower or f"{kw} state" in title_lower:
                detected_title_state = kw.title()
                break
            elif kw in dept_lower and "government of" in dept_lower:
                detected_title_state = kw.title()
                break
            elif level_str in ("state", "state government") and (f"{kw} government" in desc_lower or f"government of {kw}" in desc_lower):
                detected_title_state = kw.title()
                break


        if detected_title_state:
            scheme_state = detected_title_state
        elif raw_state:
            s_state_clean = str(raw_state).strip().lower()
            if s_state_clean in ("all india", "all-india", "central", "all", "pan-india", "none", "nan"):
                scheme_state = None  # Universal scheme
            else:
                scheme_state = raw_state
        else:
            scheme_state = None

        if not scheme_state and level_str not in ("state", "state government"):
            # Universal scheme: open to all states
            matched.append(FactMatchDetail(
                field="state",
                applicant_value=applicant_context.get_value("state"),
                expected_value="All India / Central",
                status=CompatibilityState.NOT_APPLICABLE,
                reason="Scheme operates nationally across all States and Union Territories.",
            ))
            explanation.append("State: Open nationally (All-India scheme).")
        elif not scheme_state:
            # State-level scheme with missing state information
            unk_detail = FactMatchDetail(
                field="state",
                applicant_value=applicant_context.get_value("state"),
                expected_value="State-Level (Unspecified)",
                status=CompatibilityState.UNKNOWN,
                reason="Scheme operates at State level but specific state jurisdiction is unspecified in metadata.",
            )
            unknown.append(unk_detail)
            explanation.append("State: Unspecified state-level jurisdiction.")

        elif "state" in conflicted_fields:
            conf_detail = FactMatchDetail(
                field="state",
                applicant_value=applicant_context.get_raw_value("state"),
                expected_value=scheme_state,
                status=CompatibilityState.UNKNOWN,
                reason="State is in conflict across applicant documents; compatibility is indeterminate.",
                has_conflict=True,
            )
            conflicts.append(conf_detail)
            unknown.append(conf_detail)
            explanation.append("State: Indeterminate due to conflicting document records.")
        else:
            app_state = applicant_context.get_value("state")
            if not app_state:
                unk = FactMatchDetail(
                    field="state",
                    applicant_value=None,
                    expected_value=scheme_state,
                    status=CompatibilityState.UNKNOWN,
                    reason=f"Applicant state is unknown; scheme specifies {scheme_state}.",
                )
                unknown.append(unk)
                explanation.append(f"State: Missing in applicant profile (scheme specifies {scheme_state}).")
            else:
                s1 = str(app_state).strip().lower()
                s2 = str(scheme_state).strip().lower()
                if s1 == s2 or s1 in s2 or s2 in s1:
                    matched.append(FactMatchDetail(
                        field="state",
                        applicant_value=app_state,
                        expected_value=scheme_state,
                        status=CompatibilityState.MATCH,
                        reason=f"Applicant domicile state ({app_state}) matches scheme requirement ({scheme_state}).",
                    ))
                    explanation.append(f"State: Matches ({app_state}).")
                else:
                    unmatched.append(FactMatchDetail(
                        field="state",
                        applicant_value=app_state,
                        expected_value=scheme_state,
                        status=CompatibilityState.MISMATCH,
                        reason=f"Applicant state ({app_state}) differs from scheme jurisdiction ({scheme_state}).",
                    ))
                    explanation.append(f"State: Mismatch (Applicant: {app_state}, Scheme: {scheme_state}).")

        # -------------------------------------------------------------------
        # 2. Dimension: Social Category Alignment (Distinguished from Taxonomy)
        # -------------------------------------------------------------------
        scheme_target = source_meta.get("target_group") or source_meta.get("social_category") or source_meta.get("caste_category") or ""
        raw_scheme_cat_val = source_meta.get("category")
        if raw_scheme_cat_val is None:
            raw_scheme_cat_val = source_meta.get("categories")
        if isinstance(raw_scheme_cat_val, (list, tuple)) or (hasattr(raw_scheme_cat_val, "__iter__") and not isinstance(raw_scheme_cat_val, str)):
            raw_scheme_category = " ".join(str(c) for c in raw_scheme_cat_val)
        elif raw_scheme_cat_val is not None:
            raw_scheme_category = str(raw_scheme_cat_val)
        else:
            raw_scheme_category = ""

        # Detect if scheme has a specific caste/social category requirement
        detected_caste_target = None
        social_targets = ("scheduled caste", "sc", "scheduled tribe", "st", "other backward class", "obc", "ews", "minority")
        target_corpus = f"{scheme_target} {raw_scheme_category} {scheme.scheme_name or ''}".lower()
        
        # Check for explicit caste targets
        if any(term in target_corpus for term in ("scheduled caste", " sc ", "(sc)", "for sc")):
            detected_caste_target = "SC"
        elif any(term in target_corpus for term in ("scheduled tribe", " st ", "(st)", "for st")):
            detected_caste_target = "ST"
        elif any(term in target_corpus for term in ("other backward class", "obc", "(obc)", "for obc")):
            detected_caste_target = "OBC"
        elif any(term in target_corpus for term in ("economically weaker section", "ews", "(ews)")):
            detected_caste_target = "EWS"
        elif "minority" in target_corpus:
            detected_caste_target = "Minority"

        if not detected_caste_target:
            matched.append(FactMatchDetail(
                field="social_category",
                applicant_value=applicant_context.get_value("social_category") or applicant_context.get_value("caste_category"),
                expected_value="All Categories",
                status=CompatibilityState.NOT_APPLICABLE,
                reason="Scheme is open to all social categories without restriction.",
            ))
            explanation.append("Social Category: Open to all categories.")
        elif "social_category" in conflicted_fields or "caste_category" in conflicted_fields:
            conf_detail = FactMatchDetail(
                field="social_category",
                applicant_value=applicant_context.get_raw_value("social_category") or applicant_context.get_raw_value("caste_category"),
                expected_value=detected_caste_target,
                status=CompatibilityState.UNKNOWN,
                reason="Social category is in conflict across applicant documents.",
                has_conflict=True,
            )
            conflicts.append(conf_detail)
            unknown.append(conf_detail)
            explanation.append("Social Category: Indeterminate due to conflicting document records.")
        else:
            app_cat = applicant_context.get_value("social_category") or applicant_context.get_value("caste_category")
            if not app_cat:
                unk = FactMatchDetail(
                    field="social_category",
                    applicant_value=None,
                    expected_value=detected_caste_target,
                    status=CompatibilityState.UNKNOWN,
                    reason=f"Applicant social category is unknown; scheme targets {detected_caste_target}.",
                )
                unknown.append(unk)
                explanation.append(f"Social Category: Missing in applicant profile (scheme targets {detected_caste_target}).")
            else:
                c1 = str(app_cat).strip().lower()
                c2 = str(detected_caste_target).strip().lower()
                if c1 == c2 or c1 in c2 or c2 in c1:
                    matched.append(FactMatchDetail(
                        field="social_category",
                        applicant_value=app_cat,
                        expected_value=detected_caste_target,
                        status=CompatibilityState.MATCH,
                        reason=f"Applicant social category ({app_cat}) matches scheme criteria ({detected_caste_target}).",
                    ))
                    explanation.append(f"Social Category: Matches ({app_cat}).")
                else:
                    unmatched.append(FactMatchDetail(
                        field="social_category",
                        applicant_value=app_cat,
                        expected_value=detected_caste_target,
                        status=CompatibilityState.MISMATCH,
                        reason=f"Applicant social category ({app_cat}) does not match scheme target ({detected_caste_target}).",
                    ))
                    explanation.append(f"Social Category: Mismatch (Applicant: {app_cat}, Scheme: {detected_caste_target}).")

        # Note domain sector if present without confusing it with social category
        if raw_scheme_category and raw_scheme_category.strip().lower() not in ("none", "nan", "all", ""):
            explanation.append(f"Domain: {raw_scheme_category}")

        # -------------------------------------------------------------------
        # 3. Dimension: Explicit Target Beneficiary & Occupation Matching
        # Source Precedence:
        # Structured criteria (eligibility, rules) > Canonical tags & name > Legal tier (beneficiary_type)
        # -------------------------------------------------------------------
        name = str(source_meta.get("scheme_name") or scheme.scheme_name or "").strip()
        tags_raw = source_meta.get("tags")
        if tags_raw is None:
            tags_raw = []
        if isinstance(tags_raw, (list, tuple)):
            tag_list = [str(t).strip().lower() for t in tags_raw if t]
        elif hasattr(tags_raw, "__iter__") and not isinstance(tags_raw, str):
            tag_list = [str(t).strip().lower() for t in tags_raw if t]
        elif isinstance(tags_raw, str) and tags_raw.strip():
            tag_list = [t.strip().lower() for t in tags_raw.split(";") if t.strip()]
        else:
            tag_list = []

        elig_val = source_meta.get("eligibility")
        eligibility_text = str(elig_val).strip().lower() if elig_val is not None else ""
        desc_val = source_meta.get("brief_description")
        brief_desc = str(desc_val).strip().lower() if desc_val is not None else ""
        name_lower = name.lower()
        full_corpus = f"{name_lower} {' '.join(tag_list)} {brief_desc} {eligibility_text[:400]}".lower()

        app_student = applicant_context.get_value("is_student")
        app_occ = applicant_context.get_value("occupation")
        is_app_student = app_student is True or (app_occ and "student" in str(app_occ).lower())

        detected_evals: List[Tuple[str, CompatibilityState, str]] = []

        # 3.1 Safai Karamcharis / Manual Scavengers / Waste Pickers
        is_safai_target = (
            any("safai karamchari" in t or "manual scavenger" in t or "waste picker" in t or "scavenger" in t for t in tag_list)
            or "safai karamchari" in name_lower
            or "manual scavenger" in name_lower
            or "safai karamchari" in eligibility_text[:350]
        )
        if is_safai_target:
            app_safai = applicant_context.get_value("is_safai_karamchari") or applicant_context.get_value("safai_karamchari") or applicant_context.get_value("manual_scavenger")
            if app_safai is True:
                detected_evals.append(("Safai Karamcharis", CompatibilityState.MATCH, "Applicant has verified Safai Karamchari status."))
            elif app_safai is False:
                detected_evals.append(("Safai Karamcharis", CompatibilityState.MISMATCH, "Applicant declared non-Safai Karamchari status."))
            else:
                detected_evals.append(("Safai Karamcharis", CompatibilityState.UNKNOWN, "Scheme specifically targets Safai Karamcharis (including Waste pickers) and their dependents. Applicant profile currently does not contain verified Safai Karamchari status."))

        # 3.2 Fishermen / Fisheries / Matsya
        is_fisher_target = (
            any("fisherm" in t or "fisheries" in t or "matsya" in t or "fish farmer" in t for t in tag_list)
            or "fisherm" in name_lower
            or "matsya" in name_lower
            or "fisheries requisites" in name_lower
            or "fish farmer" in name_lower
        )
        if is_fisher_target:
            app_fish = applicant_context.get_value("is_fisherman")
            if app_fish is True or (app_occ and any(w in str(app_occ).lower() for w in ("fisherman", "fisherwoman", "fisherfolk", "fisheries"))):
                detected_evals.append(("Fishermen", CompatibilityState.MATCH, "Applicant occupation / background matches fisheries target group."))
            elif is_app_student and not app_fish:
                detected_evals.append(("Fishermen", CompatibilityState.MISMATCH, "Scheme exclusively targets Fishermen / Fisheries; applicant declared occupation is Student with no evidence of fisheries activity."))
            elif app_occ:
                detected_evals.append(("Fishermen", CompatibilityState.MISMATCH, f"Scheme exclusively targets Fishermen; applicant occupation is {app_occ}."))
            else:
                detected_evals.append(("Fishermen", CompatibilityState.UNKNOWN, "Scheme targets Fishermen; applicant occupation is unknown."))

        # 3.3 Farmers / Cultivators / Kisan / Agriculture / Allied
        is_farmer_target = (
            any("farmer" in t or "kisan" in t or "cultivator" in t or "crop" in t or "fasal" in t for t in tag_list)
            or "farmer" in name_lower
            or "kisan" in name_lower
            or "fasal bima" in name_lower
            or "cultivator" in name_lower
        )
        if is_farmer_target:
            app_farmer = applicant_context.get_value("is_farmer")
            app_land = (
                applicant_context.get_value("owns_cultivable_land")
                or applicant_context.get_value("land_holding_hectares") is not None
                or applicant_context.get_value("land_holding_acres") is not None
                or applicant_context.get_value("land_ownership") is True
            )
            if app_farmer is True or app_land or (app_occ and any(w in str(app_occ).lower() for w in ("farmer", "kisan", "cultivator", "agriculture"))):
                detected_evals.append(("Farmers", CompatibilityState.MATCH, "Applicant occupation / cultivable landholder background matches farmer target group."))
            elif is_app_student and not app_farmer and not app_land:
                detected_evals.append(("Farmers", CompatibilityState.MISMATCH, "Scheme specifically targets Farmers / Cultivators; applicant declared occupation is Student with no cultivable land."))
            elif app_occ:
                detected_evals.append(("Farmers", CompatibilityState.MISMATCH, f"Scheme targets Farmers; applicant occupation is {app_occ}."))
            else:
                detected_evals.append(("Farmers", CompatibilityState.UNKNOWN, "Scheme targets Farmers; applicant occupation and landholding are unknown."))

        # 3.4 Women Only / Female Specific
        is_women_target = (
            any(t in ("women student", "women students", "girl child", "widow", "mahila", "maternity", "women entrepreneur") for t in tag_list)
            or "women student" in name_lower
            or "women only" in name_lower
            or "girl child" in name_lower
            or "widow pension" in name_lower
        )
        if is_women_target:
            app_gender = str(applicant_context.get_value("gender") or "").strip().lower()
            if app_gender in ("male", "m"):
                detected_evals.append(("Women / Female", CompatibilityState.MISMATCH, "Scheme exclusively targets female applicants; applicant profile indicates Male."))
            elif app_gender in ("female", "f", "woman"):
                detected_evals.append(("Women / Female", CompatibilityState.MATCH, "Applicant gender matches female target group."))
            else:
                detected_evals.append(("Women / Female", CompatibilityState.UNKNOWN, "Scheme targets female applicants; applicant gender is unknown."))

        # 3.5 Senior Citizens (Age >= 60)
        is_senior_target = (
            any("senior citizen" in t or "elderly" in t or "old age" in t or "vridh" in t for t in tag_list)
            or "senior citizen" in name_lower
            or "old age pension" in name_lower
        )
        if is_senior_target:
            app_age = applicant_context.get_value("age")
            if app_age is not None:
                try:
                    age_val = int(app_age)
                    if age_val < 60:
                        detected_evals.append(("Senior Citizens (60+)", CompatibilityState.MISMATCH, f"Scheme targets Senior Citizens (Age 60+); applicant age is {age_val}."))
                    else:
                        detected_evals.append(("Senior Citizens (60+)", CompatibilityState.MATCH, f"Applicant age ({age_val}) satisfies Senior Citizen criteria (60+)."))
                except Exception:
                    detected_evals.append(("Senior Citizens (60+)", CompatibilityState.UNKNOWN, "Applicant age could not be parsed."))
            else:
                detected_evals.append(("Senior Citizens (60+)", CompatibilityState.UNKNOWN, "Scheme targets Senior Citizens (60+); applicant age is unknown."))

        # 3.6 Persons with Disabilities (PwD / Divyangjan)
        is_pwd_target = (
            any("disabilit" in t or "pwd" in t or "divyang" in t for t in tag_list)
            or "disabilit" in name_lower
            or "divyang" in name_lower
        )
        if is_pwd_target:
            app_pwd = applicant_context.get_value("disability_status")
            if app_pwd is None:
                app_pwd = applicant_context.get_value("is_disabled")
            if app_pwd is False:
                detected_evals.append(("Persons with Disabilities", CompatibilityState.MISMATCH, "Scheme targets Persons with Disabilities; applicant profile indicates no disability."))
            elif app_pwd is True:
                detected_evals.append(("Persons with Disabilities", CompatibilityState.MATCH, "Applicant profile indicates disability status satisfying PwD scheme."))
            else:
                detected_evals.append(("Persons with Disabilities", CompatibilityState.UNKNOWN, "Scheme targets Persons with Disabilities; applicant disability status is unknown."))

        # 3.7 Artisans / Weavers / Craftsmen / Vishwakarma
        is_artisan_target = (
            any("artisan" in t or "weaver" in t or "craftsman" in t or "handloom" in t for t in tag_list)
            or "artisan" in name_lower
            or "weaver" in name_lower
            or "vishwakarma" in name_lower
        )
        if is_artisan_target:
            app_artisan = applicant_context.get_value("is_artisan")
            if app_artisan is True or (app_occ and any(w in str(app_occ).lower() for w in ("artisan", "weaver", "craftsman"))):
                detected_evals.append(("Artisans / Weavers", CompatibilityState.MATCH, "Applicant occupation matches artisan/weaver target group."))
            elif is_app_student:
                detected_evals.append(("Artisans / Weavers", CompatibilityState.MISMATCH, "Scheme targets Artisans / Traditional Craftsmen; applicant declared occupation is Student."))
            else:
                detected_evals.append(("Artisans / Weavers", CompatibilityState.UNKNOWN, "Scheme targets Artisans; applicant occupation unknown."))

        # 3.8 Street Vendors / Hawkers
        is_vendor_target = (
            any("street vendor" in t or "hawker" in t or "pm-svanidhi" in t for t in tag_list)
            or "street vendor" in name_lower
            or "svanidhi" in name_lower
        )
        if is_vendor_target:
            app_vendor = applicant_context.get_value("is_street_vendor")
            if app_vendor is True or (app_occ and "vendor" in str(app_occ).lower()):
                detected_evals.append(("Street Vendors", CompatibilityState.MATCH, "Applicant occupation matches street vendor target group."))
            elif is_app_student:
                detected_evals.append(("Street Vendors", CompatibilityState.MISMATCH, "Scheme targets Street Vendors; applicant declared occupation is Student."))
            else:
                detected_evals.append(("Street Vendors", CompatibilityState.UNKNOWN, "Scheme targets Street Vendors; applicant occupation unknown."))

        # 3.9 Ex-Servicemen / Veterans
        is_veteran_target = (
            any("ex-servicemen" in t or "veteran" in t or "war widow" in t for t in tag_list)
            or "ex-servicemen" in name_lower
        )
        if is_veteran_target:
            app_vet = applicant_context.get_value("is_ex_serviceman") or applicant_context.get_value("is_veteran")
            if app_vet is False:
                detected_evals.append(("Ex-Servicemen", CompatibilityState.MISMATCH, "Scheme targets Ex-Servicemen / Veterans; applicant is a civilian."))
            elif app_vet is True:
                detected_evals.append(("Ex-Servicemen", CompatibilityState.MATCH, "Applicant has verified Ex-Servicemen / Veteran status."))
            else:
                detected_evals.append(("Ex-Servicemen", CompatibilityState.UNKNOWN, "Scheme targets Ex-Servicemen; applicant veteran status is unknown."))

        # 3.10 Students / Scholars / Education
        is_student_target = (
            any(t in ("student", "students", "scholarship", "fellowship", "education loan", "higher education") for t in tag_list)
            or "scholarship" in name_lower
            or "fellowship" in name_lower
            or "education loan" in name_lower
            or "coaching" in name_lower
            or "students" in name_lower
            or str(source_meta.get("beneficiary_type") or "").strip().lower() == "student"
        )
        if is_student_target:
            if is_app_student:
                detected_evals.append(("Students", CompatibilityState.MATCH, "Applicant student profile matches education & scholarship programme."))
            elif app_student is False:
                detected_evals.append(("Students", CompatibilityState.MISMATCH, "Scheme targets Students; applicant declared non-student status."))
            else:
                detected_evals.append(("Students", CompatibilityState.UNKNOWN, "Scheme targets Students; applicant student status unknown."))

        # -------------------------------------------------------------------
        # Compound Target-Group Resolution:
        # 1. Any MISMATCH -> Overall Target Group is MISMATCH
        # 2. Any UNKNOWN (and no MISMATCH) -> Overall Target Group is UNKNOWN
        # 3. All MATCH -> Overall Target Group is MATCH
        # 4. None detected -> NOT_APPLICABLE (Open to all citizens)
        # -------------------------------------------------------------------
        if not detected_evals:
            target_group_match = CompatibilityState.NOT_APPLICABLE
            target_group_name = "All Citizens"
            target_group_reason = "Open to all citizens without restrictive occupational or categorical criteria."
            matched.append(FactMatchDetail(
                field="target_beneficiary",
                applicant_value=None,
                expected_value="All Citizens",
                status=CompatibilityState.NOT_APPLICABLE,
                reason=target_group_reason,
            ))
            explanation.append("Beneficiary: Open to all citizens.")
        else:
            mismatches = [e for e in detected_evals if e[1] == CompatibilityState.MISMATCH]
            unknowns = [e for e in detected_evals if e[1] == CompatibilityState.UNKNOWN]
            matches = [e for e in detected_evals if e[1] == CompatibilityState.MATCH]

            if mismatches:
                target_group_match = CompatibilityState.MISMATCH
                target_group_name = mismatches[0][0]
                target_group_reason = mismatches[0][2]
                unmatched.append(FactMatchDetail(
                    field="target_beneficiary",
                    applicant_value="Unsatisfied",
                    expected_value=target_group_name,
                    status=CompatibilityState.MISMATCH,
                    reason=target_group_reason,
                ))
                explanation.append(f"Beneficiary: {target_group_reason}")
            elif unknowns:
                target_group_match = CompatibilityState.UNKNOWN
                target_group_name = unknowns[0][0]
                target_group_reason = unknowns[0][2]
                unknown.append(FactMatchDetail(
                    field="target_beneficiary",
                    applicant_value=None,
                    expected_value=target_group_name,
                    status=CompatibilityState.UNKNOWN,
                    reason=target_group_reason,
                ))
                explanation.append(f"Beneficiary: {target_group_reason}")
            else:
                target_group_match = CompatibilityState.MATCH
                target_group_name = matches[0][0]
                target_group_reason = matches[0][2]
                matched.append(FactMatchDetail(
                    field="target_beneficiary",
                    applicant_value="Satisfied",
                    expected_value=target_group_name,
                    status=CompatibilityState.MATCH,
                    reason=target_group_reason,
                ))
                explanation.append(f"Beneficiary: {target_group_reason}")

            # If student target was individually matched, record is_student fact detail for test compatibility
            if any(m[0] == "Students" for m in matches):
                matched.append(FactMatchDetail(
                    field="is_student",
                    applicant_value=True,
                    expected_value=True,
                    status=CompatibilityState.MATCH,
                    reason="Applicant is an enrolled student.",
                ))

        # -------------------------------------------------------------------
        # 3.5 Dimension: Structured Income Verification (Personal vs Family)
        # -------------------------------------------------------------------
        max_fam_inc = source_meta.get("max_family_income") or source_meta.get("family_income_limit")
        max_pers_inc = source_meta.get("max_personal_income") or source_meta.get("personal_income_limit")

        if max_fam_inc is not None:
            try:
                fam_limit = float(max_fam_inc)
                app_fam = applicant_context.get_value("family_income")
                if app_fam is None:
                    app_fam = applicant_context.get_value("annual_family_income")

                if "family_income" in conflicted_fields or "annual_family_income" in conflicted_fields:
                    conf_det = FactMatchDetail(
                        field="family_income",
                        applicant_value=app_fam,
                        expected_value=f"<= {fam_limit}",
                        status=CompatibilityState.UNKNOWN,
                        reason="Family income has conflicting records across uploaded documents.",
                        has_conflict=True,
                    )
                    conflicts.append(conf_det)
                    unknown.append(conf_det)
                    explanation.append("Income: Family income indeterminate due to conflicting document records.")
                elif app_fam is None:
                    unk_det = FactMatchDetail(
                        field="family_income",
                        applicant_value=None,
                        expected_value=f"<= {fam_limit}",
                        status=CompatibilityState.UNKNOWN,
                        reason="Scheme mandates family income ceiling; applicant has not declared family income.",
                    )
                    unknown.append(unk_det)
                    explanation.append(f"Income: Family income missing in applicant profile (ceiling <= ₹{fam_limit:,.0f}).")
                elif float(app_fam) <= fam_limit:
                    mat_det = FactMatchDetail(
                        field="family_income",
                        applicant_value=app_fam,
                        expected_value=f"<= {fam_limit}",
                        status=CompatibilityState.MATCH,
                        reason=f"Applicant family income (₹{float(app_fam):,.0f}) is within scheme limit (₹{fam_limit:,.0f}).",
                    )
                    matched.append(mat_det)
                    explanation.append(f"Income: Family income (₹{float(app_fam):,.0f}) satisfies ceiling (<= ₹{fam_limit:,.0f}).")
                else:
                    unm_det = FactMatchDetail(
                        field="family_income",
                        applicant_value=app_fam,
                        expected_value=f"<= {fam_limit}",
                        status=CompatibilityState.MISMATCH,
                        reason=f"Applicant family income (₹{float(app_fam):,.0f}) exceeds scheme ceiling (₹{fam_limit:,.0f}).",
                    )
                    unmatched.append(unm_det)
                    explanation.append(f"Income: Family income (₹{float(app_fam):,.0f}) exceeds ceiling (<= ₹{fam_limit:,.0f}).")
            except (ValueError, TypeError):
                pass

        if max_pers_inc is not None:
            try:
                pers_limit = float(max_pers_inc)
                app_pers = applicant_context.get_value("personal_income")
                if app_pers is None:
                    app_pers = applicant_context.get_value("annual_income")

                if "personal_income" in conflicted_fields or "annual_income" in conflicted_fields:
                    conf_det = FactMatchDetail(
                        field="personal_income",
                        applicant_value=app_pers,
                        expected_value=f"<= {pers_limit}",
                        status=CompatibilityState.UNKNOWN,
                        reason="Personal income has conflicting records across uploaded documents.",
                        has_conflict=True,
                    )
                    conflicts.append(conf_det)
                    unknown.append(conf_det)
                    explanation.append("Income: Personal income indeterminate due to conflicting document records.")
                elif app_pers is None:
                    unk_det = FactMatchDetail(
                        field="personal_income",
                        applicant_value=None,
                        expected_value=f"<= {pers_limit}",
                        status=CompatibilityState.UNKNOWN,
                        reason="Scheme mandates personal income ceiling; applicant has not declared personal income.",
                    )
                    unknown.append(unk_det)
                    explanation.append(f"Income: Personal income missing in applicant profile (ceiling <= ₹{pers_limit:,.0f}).")
                elif float(app_pers) <= pers_limit:
                    mat_det = FactMatchDetail(
                        field="personal_income",
                        applicant_value=app_pers,
                        expected_value=f"<= {pers_limit}",
                        status=CompatibilityState.MATCH,
                        reason=f"Applicant personal income (₹{float(app_pers):,.0f}) is within scheme limit (₹{pers_limit:,.0f}).",
                    )
                    matched.append(mat_det)
                    explanation.append(f"Income: Personal income (₹{float(app_pers):,.0f}) satisfies ceiling (<= ₹{pers_limit:,.0f}).")
                else:
                    unm_det = FactMatchDetail(
                        field="personal_income",
                        applicant_value=app_pers,
                        expected_value=f"<= {pers_limit}",
                        status=CompatibilityState.MISMATCH,
                        reason=f"Applicant personal income (₹{float(app_pers):,.0f}) exceeds scheme ceiling (₹{pers_limit:,.0f}).",
                    )
                    unmatched.append(unm_det)
                    explanation.append(f"Income: Personal income (₹{float(app_pers):,.0f}) exceeds ceiling (<= ₹{pers_limit:,.0f}).")
            except (ValueError, TypeError):
                pass

        # -------------------------------------------------------------------
        # 4. Dimension: Rule-driven Criteria (Age, Income, etc.)
        # If registered rules exist in EligibilityEngine, evaluate atomic rule compatibility
        # -------------------------------------------------------------------
        if self.eligibility_engine:
            slug = scheme.scheme_slug
            if slug in self.eligibility_engine._rulesets:
                ruleset = self.eligibility_engine.get_ruleset(slug)
                for r in ruleset.rules:
                    r_field = r.field
                    if r_field in ("state", "social_category", "is_student"):
                        continue  # Already handled in structured dimensions above

                    if r_field in conflicted_fields:
                        conf_det = FactMatchDetail(
                            field=r_field,
                            applicant_value=applicant_context.get_raw_value(r_field),
                            expected_value=r.expected_value,
                            status=CompatibilityState.UNKNOWN,
                            reason=f"Field '{r_field}' has conflicting records across documents.",
                            has_conflict=True,
                        )
                        conflicts.append(conf_det)
                        unknown.append(conf_det)
                        explanation.append(f"Rule '{r.rule_id}' ({r_field}): Indeterminate due to conflict.")
                        continue

                    val = applicant_context.get_value(r_field)
                    if val is None:
                        unk_det = FactMatchDetail(
                            field=r_field,
                            applicant_value=None,
                            expected_value=r.expected_value,
                            status=CompatibilityState.UNKNOWN,
                            reason=f"Applicant lacks fact '{r_field}' required by rule: {r.raw_text}",
                        )
                        unknown.append(unk_det)
                    else:
                        # Quick deterministic check against rule operator
                        from src.rules.operators import evaluate_operator
                        op_status, op_reason = evaluate_operator(
                            operator=r.operator,
                            applicant_val=val,
                            expected_val=r.expected_value,
                            field_name=r_field,
                        )
                        if op_status == RuleStatus.PASS:
                            matched.append(FactMatchDetail(
                                field=r_field,
                                applicant_value=val,
                                expected_value=r.expected_value,
                                status=CompatibilityState.MATCH,
                                reason=f"Statutory condition satisfied: {op_reason}",
                            ))
                            explanation.append(f"Rule '{r.rule_id}' ({r_field}): Satisfied.")
                        elif op_status == RuleStatus.FAIL:
                            unmatched.append(FactMatchDetail(
                                field=r_field,
                                applicant_value=val,
                                expected_value=r.expected_value,
                                status=CompatibilityState.MISMATCH,
                                reason=f"Statutory condition unsatisfied: {op_reason}",
                            ))
                            explanation.append(f"Rule '{r.rule_id}' ({r_field}): Unsatisfied ({op_reason}).")
                        else:
                            unknown.append(FactMatchDetail(
                                field=r_field,
                                applicant_value=val,
                                expected_value=r.expected_value,
                                status=CompatibilityState.UNKNOWN,
                                reason=op_reason,
                            ))

        # -------------------------------------------------------------------
        # 5. Transparent Deterministic Score Aggregation
        # -------------------------------------------------------------------
        # Positive score comes from MATCH and NOT_APPLICABLE
        # MISMATCH incurs penalty
        # UNKNOWN does not add score (remains neutral gap)
        # CONFLICT incurs additional uncertainty penalty
        match_count = len([m for m in matched if m.status == CompatibilityState.MATCH])
        not_applicable_count = len([m for m in matched if m.status == CompatibilityState.NOT_APPLICABLE])
        mismatch_count = len(unmatched)
        unknown_count = len(unknown)
        conflict_count = len(conflicts)

        total_evaluated = match_count + not_applicable_count + mismatch_count + unknown_count
        if total_evaluated == 0:
            overall_score = 0.5
        else:
            # Base ratio of matched vs evaluated
            positive_score = (match_count * 1.0 + not_applicable_count * 0.8) / max(1, total_evaluated)
            # Penalty for explicit mismatches
            mismatch_penalty = (mismatch_count / max(1, total_evaluated)) * 0.4
            # Penalty for conflicts
            conflict_penalty = min(0.25, conflict_count * 0.1)
            
            raw_score = positive_score - mismatch_penalty - conflict_penalty
            # If target group has explicit mismatch, apply strict score ceiling
            if target_group_match == CompatibilityState.MISMATCH:
                raw_score = min(raw_score * 0.35, 0.20)
            overall_score = max(0.0, min(1.0, raw_score))

        score_breakdown = {
            "match_count": float(match_count),
            "not_applicable_count": float(not_applicable_count),
            "mismatch_count": float(mismatch_count),
            "unknown_count": float(unknown_count),
            "conflict_count": float(conflict_count),
            "base_positive_score": round((match_count + not_applicable_count * 0.8) / max(1, total_evaluated), 4),
            "final_score": round(overall_score, 4),
            "target_group_match": target_group_match.value,
        }

        return CompatibilityResult(
            overall_compatibility_score=round(overall_score, 4),
            matched_facts=matched,
            unmatched_facts=unmatched,
            unknown_facts=unknown,
            conflict_facts=conflicts,
            score_breakdown=score_breakdown,
            explanation=explanation,
            target_group_match=target_group_match,
            target_group_name=target_group_name,
        )
