"""
FIN Application Guidance & Preparation Layer.
Phase 11: Transforms statutory decisions, readiness signals, and policy metadata
into citizen-understandable, frontend-ready guidance packages.
"""

from .exceptions import (
    GuidanceError,
    GuidanceValidationError,
    ContradictoryGuidanceError,
    InvalidSourceURLError,
    MissingSourceMetadataError,
)

from .models import (
    ApplicationMode,
    GuidanceWarningCode,
    WarningSeverity,
    StepSourceType,
    DeadlineStatus,
    GuidanceWarning,
    DocumentGuidanceItem,
    ApplicationStep,
    DeadlineGuidance,
    EligibilitySummary,
    BenefitGuidance,
    SourceCitation,
    ApplicationGuidancePackage,
)

from .sources import SourceMetadataResolver
from .eligibility_summary import EligibilitySummaryBuilder
from .benefit_summary import BenefitSummaryBuilder
from .documents import DocumentGuidanceBuilder
from .steps import ApplicationStepBuilder
from .warnings import WarningGenerator
from .checklist import GuidanceChecklistAdapter
from .localization import GuidanceLocalizer
from .validator import GuidanceValidator
from .generator import ApplicationGuidanceGenerator
from .service import ApplicationGuidanceService

__all__ = [
    # Exceptions
    "GuidanceError",
    "GuidanceValidationError",
    "ContradictoryGuidanceError",
    "InvalidSourceURLError",
    "MissingSourceMetadataError",
    # Enums
    "ApplicationMode",
    "GuidanceWarningCode",
    "WarningSeverity",
    "StepSourceType",
    "DeadlineStatus",
    # Models
    "GuidanceWarning",
    "DocumentGuidanceItem",
    "ApplicationStep",
    "DeadlineGuidance",
    "EligibilitySummary",
    "BenefitGuidance",
    "SourceCitation",
    "ApplicationGuidancePackage",
    # Builders & Services
    "SourceMetadataResolver",
    "EligibilitySummaryBuilder",
    "BenefitSummaryBuilder",
    "DocumentGuidanceBuilder",
    "ApplicationStepBuilder",
    "WarningGenerator",
    "GuidanceChecklistAdapter",
    "GuidanceLocalizer",
    "GuidanceValidator",
    "ApplicationGuidanceGenerator",
    "ApplicationGuidanceService",
]
