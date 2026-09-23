# Scripts Directory

Standalone utility, maintenance, and execution scripts for batch operations.

---

## Planned Scripts

- `ingest_schemes.py`: Batch load scheme PDFs from `data/raw/` into structured JSON models.
- `build_vectorstore.py`: Process text chunks, compute embeddings, and build the persistent vector index.
- `seed_test_profiles.py`: Populate synthetic citizen profile test fixtures.
- `run_benchmarks.py`: Execute retrieval and eligibility accuracy evaluation against golden datasets.
- `download_models.py`: Fetch specified HuggingFace model weights into `models/`.
