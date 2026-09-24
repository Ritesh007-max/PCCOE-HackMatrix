# FIN AI Command-Line Interface (CLI) Reference

## 1. Overview & Working Directory Conventions

The FIN CLI provides unified access to the document intelligence and 21-step application evaluation pipelines.
It supports **multi-root path resolution**, resolving document paths correctly regardless of whether commands run from `Intelligence/` or the project root.

### Exact Working Directory Commands

#### From `Intelligence/` Directory (`c:\Users\ozhad\Desktop\HackMatrix\PCCOE-HackMatrix\AI`):
```bash
# Full Application Pipeline
python -m src.cli --document tests/fixtures/sample_income_cert.pdf --query "scholarship for SC students in Gujarat"

# JSON Output
python -m src.cli --document tests/fixtures/sample_income_cert.pdf --query "scholarship for SC students in Gujarat" --json

# Offline Mock Mode (No LLM credentials needed)
python -m src.cli --document tests/fixtures/sample_income_cert.pdf --query "Gujarat student scholarship" --no-llm

# OCR and Document Parsing Only
python -m src.cli --document tests/fixtures/sample_income_cert.pdf --ocr-only --json

# Multi-Document Evaluation
python -m src.cli --document tests/fixtures/sample_income_cert.pdf --document tests/fixtures/sample_caste_cert.png --scheme sc_post_matric_scholarship
```

#### From Project Root Directory (`c:\Users\ozhad\Desktop\HackMatrix\PCCOE-HackMatrix`):
```bash
# Full Application Pipeline
python -m AI.src.cli --document Intelligence/tests/fixtures/sample_income_cert.pdf --query "scholarship for SC students in Gujarat"

# JSON Output
python -m AI.src.cli --document Intelligence/tests/fixtures/sample_income_cert.pdf --no-llm --json

# OCR Only
python -m AI.src.cli --document Intelligence/tests/fixtures/sample_income_cert.pdf --ocr-only --json
```

## 2. Command-Line Arguments Matrix

| Argument | Flag | Type | Description |
|---|---|---|---|
| `--document` | `-d` | string (repeatable) | Path to citizen document (PDF, DOCX, PNG, JPG). Can be specified multiple times. |
| `--query` | `-q` | string | Citizen query or policy discovery question. |
| `--scheme` | `-s` | string | Target scheme identifier (e.g., `sc_post_matric_scholarship`, `pm_kisan`). |
| `--provider` | `-p` | choice (`auto`, `gemini`, `openrouter`, `mock`) | Routing topology mode (default: `auto`). |
| `--ocr-only` | | flag | Runs only document parsing, scan detection, and OCR extraction. |
| `--no-llm` | | flag | Executes offline using deterministic mock provider. |
| `--json` | | flag | Formats and outputs pure structured JSON. |
| `--debug` | | flag | Enables DEBUG level logging. |

## 3. Output Schema (JSON)

```json
{
  "application_id": "uuid4",
  "steps_completed": 21,
  "processing_status": "SUCCESS",
  "documents_processed": [
    {
      "file_name": "sample_income_cert.pdf",
      "document_type": "INCOME_CERTIFICATE",
      "mime_type": "application/pdf",
      "page_count": 1,
      "is_scanned": false,
      "extraction_method": "NATIVE_PDF",
      "sha256": "hash",
      "status": "VALID",
      "error": null
    }
  ],
  "applicant_profile": {},
  "conflicts_detected": [],
  "query_intent": {
    "intent": "SCHEME_DISCOVERY",
    "state": "Gujarat",
    "keywords": ["scholarship", "gujarat"]
  },
  "retrieved_schemes": [],
  "eligibility_decision": {
    "scheme_id": "sc_post_matric_scholarship",
    "status": "UNKNOWN",
    "is_eligible": false,
    "rules_breakdown": []
  },
  "benefit_calculation": {
    "amount": 7000.0,
    "benefit_type": "SCHOLARSHIP",
    "status": "CALCULATED",
    "formula_applied": "RULE_SC_PMS_2020"
  },
  "missing_information": {
    "missing_fields": ["annual_family_income", "social_category"],
    "required_documents": ["INCOME_CERTIFICATE", "CASTE_CERTIFICATE"],
    "has_missing_info": true
  },
  "explanation": {},
  "security_audit": {
    "injection_detected": false,
    "warnings": []
  },
  "telemetry": {
    "total_latency_ms": 11.5,
    "llm_provider": "auto",
    "llm_model": "gemini-2.5-flash"
  }
}
```
