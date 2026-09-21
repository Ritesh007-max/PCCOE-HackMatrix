# PolicySetu Phase 6: LLM & NLP Intelligence Layer Architecture

## 1. Architectural Overview

The Phase 6 Intelligence Layer bridges unstructured, conversational citizen inquiries (in English, Hindi Devanagari, and Hinglish Romanized Hindi) with the deterministic, rule-based statutory subsystems built in Phase 3, Phase 4, and Phase 5.

```
+-----------------------------------------------------------------------------------+
| CITIZEN NATURAL LANGUAGE INPUT (English / Hindi / Hinglish)                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 1. LANGUAGE & QUERY UNDERSTANDING (AI/src/nlp/)                                   |
|    - LanguageDetector: classifies into 'en', 'hi', 'hinglish'                     |
|    - QueryParser: extracts retrieval hints (State, Category, Beneficiary, Domain) |
|    - AmbiguityDetector: flags approximate values, missing units, entity confusion |
|    - PromptInjectionDetector: non-destructive threat scanning (preserves raw text)|
+-----------------------------------------------------------------------------------+
                                         |
                    +--------------------+--------------------+
                    |                                         |
                    v                                         v
+------------------------------------+   +------------------------------------+
| 2. RETRIEVAL BRANCH                |   | 3. APPLICANT FACT EXTRACTION       |
|    QueryIntent (Search Hints ONLY):|   |    ApplicantFactCandidate:         |
|    - intent: SCHEME_DISCOVERY      |   |    - field: "annual_family_income" |
|    - state: "Gujarat"              |   |    - raw_value: "4.2 lakh" (raw!)  |
|    - category: "SC"                |   |    - provenance: SELF_REPORTED     |
+------------------------------------+   +------------------------------------+
                    |                                         |
                    v                                         v
+------------------------------------+   +------------------------------------+
| Phase 5 HybridRetriever            |   | Phase 4 Normalization & Registry   |
| (Dense BGE-M3 + Sparse BM25)       |   | - normalize_field_value(field,raw) |
|    -> RetrievedChunk[]             |   |   -> 420000.0 (Phase 4 ONLY!)      |
+------------------------------------+   | - EvidenceRegistry.record_fact()   |
                    |                    |   -> Canonical ApplicantProfile    |
                    |                    +------------------------------------+
                    |                                         |
                    +--------------------+--------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. DETERMINISTIC EVALUATION & AST MISSING FIELDS (Phase 3 Engine)                 |
|    - RuleASTMissingFieldAnalyzer: traverses ruleset logic tree (AND/OR/NOT)       |
|    - Computes minimal missing fields needed to resolve decision to PASS           |
|    - RuleEvaluator.evaluate_ruleset(ruleset, profile)                             |
|    -> Authoritative Status: PASS / FAIL / UNKNOWN / REVIEW                        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 5. GROUNDED EXPLANATION GENERATION & SAFETY AUDIT                                 |
|    - Structural Immutability: explanation wraps authoritative RuleStatus          |
|    - DecisionImmutabilityGuard: checks prose; REJECTS contradiction -> template  |
|    - Two-Tier GroundingVerifier: citation existence + lexical claim support       |
|    - Output: Verified GroundedExplanation                                         |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Invariants & Structural Guarantees

### Invariant 1: The LLM Never Makes Eligibility Decisions
- Statutory eligibility remains under the exclusive jurisdiction of the **Phase 3 Deterministic Rule Engine** (`RuleEvaluator`).
- The LLM explanation model wraps the authoritative `RuleStatus` (`PASS`, `FAIL`, `UNKNOWN`, `REVIEW`).
- If an LLM-generated explanation contradicts the authoritative status (e.g. asserts the applicant is eligible when the status is `FAIL` or `REVIEW`), the explanation is **rejected** and an auditable deterministic template is produced instead.

### Invariant 2: Phase 4 Exclusively Owns Normalization
- The LLM extracts `raw_value` strings only (e.g. `"4.2 lakh"`, `"2 acres"`).
- `ApplicantFactCandidate` deliberately contains no `normalized_value`.
- Normalization is executed solely by Phase 4's `normalize_field_value` (`normalize_inr`, `normalize_area_hectares`). LLM-generated normalized numbers are never trusted or accepted.

### Invariant 3: Query Entities Are Retrieval Hints Only
- Entities extracted from search queries (e.g. `state="Gujarat"`, `social_category="SC"` from *"scholarships for SC students in Gujarat"*) populate `QueryIntent.is_search_hint_only = True`.
- They are **never** automatically converted into `ApplicantFact` entries unless the user explicitly makes a first-person statement about themselves.

### Invariant 4: AST-Aware Missing Information
- Missing fields are not computed as naive set subtraction (`required - known`).
- `RuleASTMissingFieldAnalyzer` evaluates the AST condition tree (`AND`, `OR`, `NOT` logic groups) to determine whether alternative branches are already satisfied or irrevocably disqualified.

### Invariant 5: Accurate Fact Provenance
- User natural-language statements map strictly to `FactVerificationStatus.SELF_REPORTED`.
- User input is never silently elevated to `EXTRACTED` or `ISSUER_VERIFIED`.

### Invariant 6: Non-Destructive Prompt Injection Defense
- Source text is never mutated, truncated, or stripped before storage or audit.
- Injection markers are recorded in safety metadata, and text is isolated within `<UNTRUSTED_USER_INPUT>` XML boundaries for the model.

---

## 3. Directory Layout

```
AI/src/llm/
    __init__.py
    models.py             # Typed schemas: QueryIntent, ApplicantFactCandidate, GroundedExplanation
    config.py             # Centralized configuration with offline defaults and env overrides
    errors.py             # Strict exception hierarchy
    providers.py          # LLMProvider base, MockLLMProvider (offline), OpenAICompatibleProvider
    client.py             # Coordinator with telemetry, latency timing, and failure isolation
    prompts.py            # Prompt contracts with XML data boundaries
    structured_output.py  # Robust JSON cleaner, fence stripper, and schema validator
    safety.py             # Non-destructive injection detector & DecisionImmutabilityGuard
    grounding.py          # Two-tier citation validation & lexical claim support verifier
    extraction.py         # Candidate fact extraction & Phase 4 EvidenceRegistry bridge
    explanation.py        # Grounded explanation generator with contradiction rejection
    ast_analyzer.py       # Phase 3 AST logic group missing-field analyzer

AI/src/nlp/
    __init__.py
    language.py           # Multi-lingual classifier (en, hi, hinglish)
    query_parser.py       # Indian governance entity parser for retrieval hints
    intent.py             # Deterministic + LLM-assisted multi-lingual intent classifier
    ambiguity.py          # Ambiguity detector (approximate values, missing units, entity confusion)

AI/src/llm/evaluation/
    __init__.py
    metrics.py            # Precision, recall, F1, intent accuracy, immutability adherence
    test_cases.py         # Curated multi-lingual, adversarial, and edge-case datasets
    benchmark.py          # Offline benchmark runner producing exact scoreboard
```
