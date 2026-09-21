# PolicySetu AI Workspace

An isolated AI, Machine Learning, Natural Language Processing, and Retrieval-Augmented Generation (RAG) subsystem designed for the **PolicySetu** platform.

---

## 🏛 Overview & Scope

The `AI/` workspace serves as a dedicated, standalone microservice and algorithmic backbone for PolicySetu. It handles all policy intelligence, unstructured document understanding, eligibility assessment, deterministic rules execution, benefit calculation, and human-interpretable reasoning.

This workspace is decoupled from the main web application (`FrontEnd/` and `BackEnd/`) to allow independent experimentation, reproducible ML pipelines, and dedicated API serving.

### Core Capabilities

1. **Document Processing & OCR**:
   - Ingestion of government gazettes, policy PDFs, scheme guidelines, circulars, and application forms.
   - Layout-aware parsing, tabular extraction, and text digitization.

2. **NLP & Structured Extraction**:
   - Extraction of entity schemas (demographics, income ceilings, age brackets, geographic conditions, caste/category quotas).
   - Normalization and standardization of multilingual or non-standard civic terms.

3. **Knowledge Base & Cataloging**:
   - Hierarchical indexing of central, state, and municipal government schemes.
   - Scheme versioning, policy metadata registry, and dependency graphs.

4. **Embeddings & Vector Search (RAG)**:
   - Dense semantic embeddings and sparse lexical indices (BM25) for hybrid policy retrieval.
   - Multi-stage retrieval with cross-encoder re-ranking for contextual relevance.

5. **Deterministic Rule Engine & Eligibility Evaluation**:
   - Structured condition evaluation matching citizen profiles against scheme criteria.
   - Strict logic separation: LLMs assist in parsing and synthesis, while deterministic rule engines verify hard eligibility bounds to eliminate hallucinations.

6. **Benefit Calculation & Entitlement Modeling**:
   - Quantitative estimation of direct financial benefits, subsidies, scholarships, and interest waivers.
   - Non-financial benefit mapping (in-kind support, healthcare access, quotas).

7. **Explainability & Citation Auditing**:
   - Natural language explanations grounded in verified official policy excerpts.
   - Transparent audit trails detailing precisely why a citizen is eligible, ineligible, or borderline.

8. **Evaluation & Golden Benchmarks**:
   - End-to-end evaluation suites tracking retrieval accuracy (Hit Rate@K, MRR), extraction fidelity, and rule logic correctness.

9. **FastAPI Microservice (Future Serving Layer)**:
   - RESTful API interfaces serving low-latency inference endpoints for the web backend and client interfaces.

---

## 📂 Directory Layout

```
AI/
├── README.md               # Primary AI service documentation (this file)
├── .gitignore              # Ignores large weights, data, caches, and secrets
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependency manifest
├── pyproject.toml          # Project configuration, linting, and tool settings
│
├── src/                    # Core source code package
│   ├── __init__.py
│   ├── config/             # Environment configs, settings, and logging
│   ├── ingestion/          # Data loaders, PDF extractors, scrapers
│   ├── documents/          # Document data representations & chunking schemas
│   ├── extraction/         # OCR, layout analysis, structured attribute parsers
│   ├── normalization/      # Canonicalization and data cleaning routines
│   ├── knowledge_base/     # Policy registry, taxonomies, and metadata catalogs
│   ├── retrieval/          # Dense/sparse vector retrieval, hybrid search, rerankers
│   ├── rules/              # Deterministic condition parsers and rule DSLs
│   ├── eligibility/        # Citizen-to-policy criteria evaluator
│   ├── benefits/           # Subsidy, stipend, and grant calculation engines
│   ├── explainability/     # Grounded reasoning, audit generation, citation tracking
│   ├── evaluation/         # Benchmarking harnesses, golden sets, evaluation metrics
│   ├── pipelines/          # Composable ingestion and inference orchestration
│   ├── api/                # FastAPI application, routers, schemas, and dependencies
│   └── utils/              # Common utilities, text helpers, IO wrappers
│
├── data/                   # Data directory (managed & ignored by git)
│   ├── raw/                # Unprocessed original PDFs, circulars, JSON dumps
│   ├── interim/            # Cleaned, tokenized, and preprocessed artifacts
│   ├── processed/          # Final structured datasets ready for indexing
│   ├── schemes/            # Scheme specific documents, rules, and metadata
│   ├── test_cases/         # Citizen profile test suites (eligible/ineligible/borderline)
│   └── samples/            # Small reference sample files for development
│
├── models/                 # Model registry & weights storage (ignored by git)
│   ├── embeddings/         # Local embedding models
│   ├── reranker/           # Cross-encoder / reranking models
│   ├── classifiers/        # Intent and category classifiers
│   └── checkpoints/        # Checkpoints from fine-tuning or training
│
├── vectorstore/            # Vector indexes and persistent database files (ignored)
├── notebooks/              # Jupyter notebooks for prototyping and research
├── scripts/                # Utility scripts for ingestion, indexing, and eval
├── tests/                  # Pytest test suites across all domains
└── docs/                   # Extended design docs, policy models, and specifications
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (Recommended: Python 3.11)
- Virtual environment tool (`venv`, `uv`, or `conda`)

### Local Setup
```bash
# Navigate to AI workspace
cd AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies (when ready)
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
```

---

## 🔒 Safety & Isolation Policy

- The `AI/` module is strictly decoupled from `BackEnd/` and `FrontEnd/`.
- Never commit private API keys, model checkpoint binaries (`*.pt`, `*.bin`, `*.safetensors`), vector indices (`*.index`, `*.faiss`, `chroma.sqlite3`), or raw applicant documents to Git.
