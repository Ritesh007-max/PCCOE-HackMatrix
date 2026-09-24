# FIN — Data Acquisition Reproducibility Guide

## 1. Deterministic Execution

The FIN data acquisition pipeline is fully deterministic, resumable, and idempotent.

### Running Full Live Acquisition:
```bash
python -m src.data_pipeline.acquisition.runner --mode full-live --concurrency 8 --rate-limit 6.0
```

### Running Validation & Regression Tests:
```bash
python -m unittest tests/data_pipeline/test_myscheme_acquisition.py
python -m unittest discover -s tests -p "test_*.py"
```

### Running Evaluation Benchmark:
```bash
python -m src.evaluation.runner --suite all
```

### Running Static Type Verification:
```bash
npx pyright src
```

---

## 2. Artifact Lineage & Validation

- **Raw Artifacts:** Stored immutably at `Intelligence/data/raw/myscheme/`
- **Request Ledger:** Every call logged in `Intelligence/data/coverage/request_ledger.json`
- **Queue Checkpoints:** Resumable state preserved in `Intelligence/data/coverage/acquisition_queue.json`
- **Coverage Ledgers:** Stored in `Intelligence/data/coverage/`
