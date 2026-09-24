# Phase 11: Troubleshooting & Operational Diagnostics

## 1. Common Operational Scenarios

### 1. "Official link is null with WARNING code OFFICIAL_LINK_UNAVAILABLE"
- **Cause**: The scheme's `source_url` in `canonical/schemes.jsonl` does not belong to the approved domain allowlist (e.g., non-gov domain or blog).
- **Remedy**: Update scheme metadata in canonical registry during Phase 12 policy sync with verified government URL (`.gov.in` / `.nic.in`).

### 2. "Guidance output is marked is_deterministic_fallback: true"
- **Cause**: Remote LLM provider (Gemini / OpenRouter) was offline, rate-limited, or generated phrasing that violated statutory consistency checks.
- **Behavior**: Completely safe. The system cleanly fell back to verified deterministic templates.

### 3. "Cache returns stale guidance after profile update"
- **Cause**: Updating applicant facts directly without invoking `workflow_service.update_applicant_profile`.
- **Remedy**: Always update profiles through `ApplicationWorkflowService`, which updates `case.updated_at` and invalidates the cache key.
