# FIN — Data Acquisition Architecture

## 1. System Components

1. **SafeHttpClient (`client.py`):**
   - Thread-safe token bucket rate limiter (6.0 req/s safe window).
   - Global cooperative HTTP 429 adaptive backoff with exponential jitter.
   - Comprehensive request instrumentation into `HttpRequestRecord`.

2. **AcquisitionQueue (`queue.py`):**
   - Persistent JSON-backed state machine (`acquisition_queue.json`).
   - Duplicate slug disambiguation (`slug::scheme_id`).

3. **SchemeNormalizer (`normalizer.py`):**
   - Slate.js rich-text AST parser supporting paragraphs, lists, and headings.
   - Rule-based deterministic extraction for age, income, caste, gender, student, and BPL conditions.
   - Live provenance stamping with `LiveProvenanceEnvelope`.

4. **AcquisitionStorage (`storage.py`):**
   - Content-addressed storage for raw JSON/HTML and canonical normalized entities.

5. **AcquisitionRAGSynchronizer (`runner.py`):**
   - High-fidelity chunk generation across eligibility, benefits, application steps, and FAQs.
