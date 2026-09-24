# Phase 11: Application Steps & Process Guidance

## 1. Ordered Application Procedure

Application steps guide citizens from document preparation to final reference tracking without hallucinating procedures.

Every step specifies:
- `step_number`: Integer execution order.
- `instruction`: Clear, imperative citizen action.
- `source_type`:
  - `POLICY_SOURCED`: Extracted directly from official government scheme process guidelines (`canonical/schemes.jsonl` or chunk text).
  - `GENERAL_PREPARATION`: Standard preparation steps derived from document readiness signals.
- `source_reference`: Traceable citation (e.g., URL, section, chunk ID).
- `mandatory`: Boolean indicating if step is strictly required.
- `notes`: Specific precautions or portal instructions.

---

## 2. Standard Step Flow

1. **Step 1 (General Preparation)**: Gather and verify all mandatory certificates.
2. **Step 2 (Policy Sourced)**: Open the official verified application portal (or locate designated CSC/department office).
3. **Step 3 (Policy Sourced)**: Complete user registration and applicant information entry.
4. **Step 4 (Policy Sourced)**: Upload scanned copies of required documents.
5. **Step 5 (Policy Sourced)**: Review applicant profile for consistency with physical certificates.
6. **Step 6 (Policy Sourced)**: Submit application and obtain official acknowledgement receipt / tracking number.
