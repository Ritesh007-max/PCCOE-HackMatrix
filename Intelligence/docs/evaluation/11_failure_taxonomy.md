# Failure Taxonomy Specification (`src/evaluation/failures.py`)

## 1. 15 Failure Categories
Every evaluation error, red-team finding, or security violation maps to a standardized, machine-readable category:

```python
class FailureType(str, Enum):
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"              # Target scheme not in top-k or ranking below threshold
    EXTRACTION_FAILURE = "EXTRACTION_FAILURE"            # Document fact extraction error or incorrect document type
    NORMALIZATION_FAILURE = "NORMALIZATION_FAILURE"      # Failure to normalize units, currencies, or dates
    RULE_FAILURE = "RULE_FAILURE"                        # Deterministic rule engine evaluation mismatch
    GROUNDING_FAILURE = "GROUNDING_FAILURE"              # Unsupported claim or missing citation link
    HALLUCINATION_FAILURE = "HALLUCINATION_FAILURE"      # System fabricated a nonexistent scheme, rule, or URL
    AUTHORITY_FAILURE = "AUTHORITY_FAILURE"              # Source hierarchy confusion (supplementary over primary)
    TEMPORAL_FAILURE = "TEMPORAL_FAILURE"                # Stale chunk used or historical immutability violated
    SECURITY_FAILURE = "SECURITY_FAILURE"                # General security or authentication boundary breach
    INJECTION_FAILURE = "INJECTION_FAILURE"              # Prompt injection executed or bypassed detection
    POLICY_POISONING_FAILURE = "POLICY_POISONING_FAILURE"# Malicious candidate dataset passed activation gates
    API_SECURITY_FAILURE = "API_SECURITY_FAILURE"        # API key leakage, stack trace leakage, or path traversal
    MULTILINGUAL_FAILURE = "MULTILINGUAL_FAILURE"        # Language misclassification or semantic divergence across languages
    GUIDANCE_FAILURE = "GUIDANCE_FAILURE"                # Incorrect preparation checklist or office routing
    VERSIONING_FAILURE = "VERSIONING_FAILURE"            # Inconsistent snapshot, rule catalog, or RAG index versions
```

## 2. Automatic Failure Classification
The failure mapper inspects evaluation errors, status codes, and exception tracebacks to automatically assign the appropriate `FailureType`. This ensures all benchmark JSON reports categorize failures systematically.
