"""
Application Procedure and Steps Builder.
Phase 11: Generates grounded, ordered application instructions distinguishing
POLICY_SOURCED steps from GENERAL_PREPARATION steps.
"""

from typing import Any, Dict, List, Optional
from .models import ApplicationStep, StepSourceType, ApplicationMode


class ApplicationStepBuilder:
    """
    Constructs ordered, policy-grounded application steps.
    Never presents generic advice as statutory mandate.
    """

    @classmethod
    def build_steps(
        cls,
        scheme_id: str,
        scheme_name: str,
        application_process_text: Optional[str] = None,
        application_mode: ApplicationMode = ApplicationMode.ONLINE,
        official_portal_url: Optional[str] = None,
        source_url: Optional[str] = None,
        missing_documents: Optional[List[str]] = None,
    ) -> List[ApplicationStep]:
        """
        Builds sequential application instructions.
        """
        steps: List[ApplicationStep] = []
        step_num = 1
        name = scheme_name or "the scheme"

        # 1. Step 1: Document Preparation (General Preparation)
        doc_note = ""
        if missing_documents:
            doc_note = f"Outstanding documents to obtain: {', '.join(missing_documents)}."
        else:
            doc_note = "All identified required certificates are ready."

        steps.append(
            ApplicationStep(
                step_number=step_num,
                instruction="Gather and verify all mandatory supporting documents before beginning the application.",
                source_type=StepSourceType.GENERAL_PREPARATION,
                source_reference="FIN Preparation Protocol",
                mandatory=True,
                notes=doc_note,
            )
        )
        step_num += 1

        # 2. Step 2: Portal / Office Access
        if application_mode in (ApplicationMode.ONLINE, ApplicationMode.PORTAL, ApplicationMode.BOTH):
            if official_portal_url:
                instr = f"Navigate to the official government portal: {official_portal_url}"
                src_ref = official_portal_url
            else:
                instr = f"Access the designated official online portal for {name}."
                src_ref = source_url or "Official Government Scheme Directory"

            steps.append(
                ApplicationStep(
                    step_number=step_num,
                    instruction=instr,
                    source_type=StepSourceType.POLICY_SOURCED if official_portal_url else StepSourceType.GENERAL_PREPARATION,
                    source_reference=src_ref,
                    mandatory=True,
                    notes="Ensure you are on the genuine government domain (.gov.in or .nic.in).",
                )
            )
            step_num += 1
        elif application_mode in (ApplicationMode.OFFLINE, ApplicationMode.DEPARTMENT_OFFICE, ApplicationMode.CSC):
            steps.append(
                ApplicationStep(
                    step_number=step_num,
                    instruction=f"Visit the designated district department office, Tehsildar office, or Common Service Centre (CSC) to collect physical application form for {name}.",
                    source_type=StepSourceType.POLICY_SOURCED,
                    source_reference=source_url or "Department Guidelines",
                    mandatory=True,
                    notes="Carry original identity and eligibility documents for physical verification.",
                )
            )
            step_num += 1

        # 3. Policy-Sourced Application Process (if provided in verified scheme metadata)
        if application_process_text and application_process_text.strip():
            raw_text = application_process_text.strip()
            # If the process text contains multiple enumerated items or sentences, split them sensibly
            sentences = [s.strip() for s in raw_text.split("\n") if s.strip()]
            if len(sentences) == 1 and "." in sentences[0] and len(sentences[0]) > 100:
                sentences = [s.strip() + "." for s in sentences[0].split(". ") if s.strip()]

            for s in sentences:
                clean_s = s.rstrip(".") + "."
                # Strip leading numbering like '1. ', 'Step 1: '
                clean_s = clean_s.lstrip("0123456789.-) ")
                if not clean_s:
                    continue
                steps.append(
                    ApplicationStep(
                        step_number=step_num,
                        instruction=clean_s,
                        source_type=StepSourceType.POLICY_SOURCED,
                        source_reference=source_url or scheme_id,
                        mandatory=True,
                        notes="Statutory policy instruction.",
                    )
                )
                step_num += 1
        else:
            # Fallback to standard online form completion steps if no custom process text exists
            steps.append(
                ApplicationStep(
                    step_number=step_num,
                    instruction="Register or authenticate on the portal using your Aadhaar-linked mobile number.",
                    source_type=StepSourceType.GENERAL_PREPARATION,
                    source_reference="Standard Portal Onboarding",
                    mandatory=True,
                    notes="Citizen authentication is standard across national DBT portals.",
                )
            )
            step_num += 1

            steps.append(
                ApplicationStep(
                    step_number=step_num,
                    instruction="Fill out the online application form with verified profile and demographic details.",
                    source_type=StepSourceType.GENERAL_PREPARATION,
                    source_reference="Standard Portal Onboarding",
                    mandatory=True,
                    notes="Ensure names, DOB, and category match uploaded certificates exactly.",
                )
            )
            step_num += 1

            steps.append(
                ApplicationStep(
                    step_number=step_num,
                    instruction="Upload verified digital copies of all required certificates.",
                    source_type=StepSourceType.GENERAL_PREPARATION,
                    source_reference="Standard Portal Onboarding",
                    mandatory=True,
                    notes="Typically accepted formats: PDF or JPG under 200 KB to 2 MB.",
                )
            )
            step_num += 1

        # 4. Final Submission & Reference Number (General Preparation)
        steps.append(
            ApplicationStep(
                step_number=step_num,
                instruction="Submit the completed application and immediately download/print the acknowledgement receipt containing the Application Reference Number.",
                source_type=StepSourceType.GENERAL_PREPARATION,
                source_reference="Standard Portal Onboarding",
                mandatory=True,
                notes="The reference number is strictly required for tracking application processing status and grievance redressal.",
            )
        )

        return steps
