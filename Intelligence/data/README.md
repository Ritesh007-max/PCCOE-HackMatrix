# Data Directory

This directory stores all data artifacts across the lifecycle of policy ingestion, transformation, indexing, and testing.

---

## Directory Organization

- `raw/`: Unprocessed original files (PDFs of government gazettes, schemes, circulars, portal exports). Kept out of Git tracking.
- `interim/`: Intermediate artifacts undergoing transformation (extracted text, OCR dumps, partial chunk sets). Kept out of Git tracking.
- `processed/`: Final normalized datasets, clean JSON schemas, and structured scheme representations ready for vectorization and indexing. Kept out of Git tracking.
- `schemes/`: Scheme-specific assets organized by category:
  - `metadata/`: Schema definitions and high-level descriptors for schemes.
  - `rules/`: Deterministic eligibility conditions and DSL rule definitions.
  - `documents/`: Reference policy guidelines and documentation.
- `test_cases/`: Synthetic and curated citizen profiles used for deterministic and LLM verification:
  - `eligible/`: Profiles guaranteed to pass all scheme requirements.
  - `ineligible/`: Profiles that fail one or more strict criteria.
  - `borderline/`: Profiles with ambiguous, near-cutoff, or missing attributes.
- `samples/`: Small, tracked demonstration files and sample JSONs for unit testing and local development.
