"""
Pipelines Module.

End-to-end orchestration workflows binding document ingestion, parsing,
fact extraction, normalization, retrieval, rule-checking, benefit calculation,
and grounded explainability into executable flows.
"""

from .application_pipeline import ApplicationPipeline, ApplicationResult

__all__ = [
    "ApplicationPipeline",
    "ApplicationResult",
]
