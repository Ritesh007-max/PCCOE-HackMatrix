# FIN Phase 12: Conflict Detection & Resolution

## 1. Conflict Classification

When disparate sources describe the same policy scheme, disagreements in eligibility thresholds, benefits, or document criteria can occur. FIN categorizes conflicts into two fundamental classes:

### Class A: Hierarchical Conflict (Primary vs Supplementary)
- **Occurs when**: An official primary source contradicts a supplementary source (e.g. Hugging Face dataset, NGO feed, or news report).
- **Resolution Strategy**: Automatic statutory resolution via `PRIMARY_CONFIRMED`.
- **Behavior**:
  - The statutory rule engine strictly obeys the `PRIMARY_OFFICIAL` (or `PRIMARY_CANONICALIZED`) value.
  - The supplementary value is retained in `conflicts.json` and linked to the scheme.
  - RAG responses explain the official rule while optionally noting: *"Note: Some secondary sources report an alternative threshold of ₹X, but official statutory guidelines enforce ₹Y."*

### Class B: Lateral Conflict (Equal-Tier Primary vs Primary)
- **Occurs when**: Two sources of equal statutory authority (e.g. a Central Ministry gazette vs a State Department circular) specify contradictory requirements for a state-implemented scheme.
- **Resolution Strategy**: Fail-closed suspension via `MANUAL_REVIEW`.
- **Behavior**:
  - The system **never** silently chooses or averages values.
  - The candidate change is flagged with `POLICY_SOURCE_CONFLICT`.
  - Automatic promotion of statutory rules for that scheme is halted until human caseworkers intervene.
  - In applicant eligibility checks, affected rules evaluate to `UNKNOWN` or `REVIEW`.

---

## 2. Real-World Conflict Scenario Walkthrough

### Scenario: Income Ceiling Discrepancy

```
Primary Gazette Notification:
  "Annual family income shall not exceed ₹2,50,000/-"

Hugging Face (smartduketech-2025):
  "Income: Up to ₹3,00,000 per annum"
```

1. **Detection**: `ConflictDetector.detect_conflicts()` matches schemes by slug and extracts numerical values for `income_limit`.
2. **Analysis**:
   - `primary_value` = 250000
   - `supplementary_value` = 300000
   - `primary_tier` = `PRIMARY_OFFICIAL` (Priority 5)
   - `supplementary_tier` = `SUPPLEMENTARY` (Priority 3)
3. **Resolution**: `resolution = PRIMARY_CONFIRMED`.
4. **Outcome**:
   - Applicant with income ₹2,80,000 evaluates to **FAIL** under statutory rules.
   - Audit trail records `ConflictRecord` in `conflicts.json`.
   - No silent override occurs.
