# FIN Phase 6: LLM Evaluation & Benchmark Scoreboard

## 1. Evaluation Methodology

The Phase 6 evaluation suite measures query understanding, multi-lingual intent classification, applicant fact extraction precision, Phase 4 normalization pass rate, prompt injection defense, and decision immutability adherence.

> [!NOTE]
> All benchmarks execute **100% offline** using the deterministic `MockLLMProvider`, requiring zero internet connectivity or API credentials.
> The reported metrics represent the **offline deterministic MockLLMProvider benchmark** and are **NOT** fabricated claims of real production LLM accuracy. Production models must be benchmarked independently when API credentials and target models are deployed.

---

## 2. Executed Benchmark Results

**Execution Command:**
```bash
python src/llm/evaluation/benchmark.py
```

### Measured Benchmark Scoreboard

```
===========================================================================
  FIN Phase 6 Intelligence Layer Benchmark
  [Offline deterministic MockLLMProvider benchmark — NOT real production LLM]
===========================================================================

--- 1. Query Understanding (Retrieval Hints ONLY; No Fact Promotion) ---
Total Test Queries                 : 15
Intent Accuracy (Offline Mock)     : 100.00%
Language Accuracy (Offline Mock)   : 100.00%

--- 2. Applicant Fact Extraction & Phase 4 Normalization Integration ---
Total Fact Test Cases              : 7
True Positives (Raw Values)        : 14
Extraction Precision (Offline Mock): 100.00%
Extraction Recall (Offline Mock)   : 100.00%
F1 Score (Offline Mock)            : 100.00%
Phase 4 Normalization Pass Rate    : 100.00%

--- 3. Safety, Grounding & Decision Immutability Guardrails ---
Prompt Injection Catch Rate (Mock) : 100.00%
Raw Text Preservation Rate         : 100.00%
Decision Immutability (Phase 3 Hard): 100.00%
===========================================================================
```

---

## 3. Query Understanding Benchmark (Retrieval Hints ONLY)

Query understanding evaluates **only retrieval/query hints** (state, category, beneficiary type, intent) and **NEVER** promotes them into applicant facts (e.g. age or income).

| Language | Sample Query Tested | Intent | Retrieval Hints Extracted | Is Search Hint Only |
| :--- | :--- | :--- | :--- | :--- |
| **English** | `"What scholarship is available for SC students in Gujarat?"` | `SCHEME_DISCOVERY` | `state="Gujarat"`, `category="SC"`, `beneficiary="student"` | `True` |
| **English** | `"How to apply for PM Kisan scheme online?"` | `APPLICATION_PROCESS` | `beneficiary="farmer"`, `domain="Agriculture & Rural"` | `True` |
| **Hindi (Devanagari)** | `"गुजरात में एससी छात्रों के लिए कौन सी छात्रवृत्ति है?"` | `SCHEME_DISCOVERY` | `state="Gujarat"`, `category="SC"`, `beneficiary="student"` | `True` |
| **Hindi (Devanagari)** | `"आवेदन कैसे करें किसान सम्मान निधि में?"` | `APPLICATION_PROCESS` | `beneficiary="farmer"`, `domain="Agriculture & Rural"` | `True` |
| **Hinglish (Romanized)** | `"mujhe Gujarat me SC students ke liye scholarship chahiye"` | `SCHEME_DISCOVERY` | `state="Gujarat"`, `category="SC"`, `beneficiary="student"` | `True` |
| **Hinglish (Romanized)** | `"kya documents lagenge obc scholarship ke liye?"` | `DOCUMENT_REQUIREMENTS` | `category="OBC"`, `beneficiary="student"` | `True` |

---

## 4. Applicant Fact Extraction Benchmark (Phase 4 Integration)

Fact extraction evaluates **first-person citizen declarations**, extracting verbatim `raw_value` entries, and routing them through Phase 4 for canonical normalization and validation.

| Language | First-Person Citizen Input | Extracted Raw Values (`raw_value`) | Phase 4 Normalized Values (`normalized_value`) | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **English** | `"My family income is 4.2 lakh and I am 23 years old."` | `income="4.2 lakh"`, `age="23"` | `annual_family_income=420000.0`, `age=23` | `SELF_REPORTED` |
| **English** | `"I own about 2 acres of land and I live in Gujarat."` | `land="2 acres"`, `state="Gujarat"` | `landholding_hectares=0.809371`, `state="Gujarat"` | `SELF_REPORTED` |
| **Hindi** | `"मेरी उम्र 23 साल है और मेरी पारिवारिक आय 4.2 लाख रुपये है।"` | `age="23"`, `income="4.2 लाख"` | `age=23`, `annual_family_income=420000.0` | `SELF_REPORTED` |
| **Hindi** | `"मैं गुजरात का निवासी हूँ और मेरी उम्र 35 वर्ष है।"` | `state="Gujarat"`, `age="35"` | `state="Gujarat"`, `age=35` | `SELF_REPORTED` |
| **Hinglish** | `"meri age 23 hai aur family income 4.2 lakh hai"` | `age="23"`, `income="4.2 lakh"` | `age=23`, `annual_family_income=420000.0` | `SELF_REPORTED` |
| **Hinglish** | `"meri age 35 hai aur main Gujarat mein rehta hoon"` | `age="35"`, `state="Gujarat"` | `age=35`, `state="Gujarat"` | `SELF_REPORTED` |
| **Hinglish** | `"main kisan hoon aur mere paas 2 acres khet hai"` | `occupation="farmer"`, `land="2 acres"` | `occupation="farmer"`, `landholding_hectares=0.809371` | `SELF_REPORTED` |

---

## 5. Known Limitations & Disclaimers

1. **Benchmark Scope**: The 100% metrics reported above are from the **offline deterministic MockLLMProvider benchmark**, which executes deterministic rule-and-regex models. It is **not** a measurement of a production generative LLM API.
2. **Lexical Grounding Limitation**: Grounding verification in Phase 6 operates via structural citation validation and lexical token overlap. It does not perform deep mathematical theorem proving or logical entailment on unstructured prose.
3. **Ambiguity Requires Confirmation**: Approximate amounts (e.g. *"around 4 lakh"*) and unspecified land sizes (e.g. *"mere paas zameen hai"*) trigger `needs_confirmation=True` and must be validated through user confirmation or official documents before final certification.
4. **Dialect Coverage**: Rare, non-standard dialectal variants of regional languages outside standard Devanagari and Latin Romanization fall back to general information intent.
