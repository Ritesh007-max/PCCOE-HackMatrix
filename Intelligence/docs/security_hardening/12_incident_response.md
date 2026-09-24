# FIN Security Incident Response Playbook

## 1. Incident Response Framework

```
[ DETECT ] ──> [ CONTAIN ] ──> [ PRESERVE EVIDENCE ] ──> [ DISABLE / ROLLBACK ] ──> [ ROTATE CREDENTIALS ] ──> [ VERIFY ] ──> [ DOCUMENT ]
```

---

## 2. Threat Scenarios & Standard Operating Procedures

### 2.1 Compromised Model Provider API Key (Gemini or OpenRouter)
1. **Detect**: Alert from Google Cloud Console, OpenRouter rate anomaly, or unexpected billing spike.
2. **Contain**: Temporarily switch `LLM_PROVIDER` in environment to fallback provider (`openrouter` or `gemini`).
3. **Preserve Evidence**: Record timestamp, request IDs, and provider billing logs.
4. **Rotate Credentials**:
   - Generate new API key in provider console.
   - Update production secret store / environment variables.
   - Revoke compromised key in provider portal.
5. **Verify**: Run `POST /health/ready` to verify provider operational readiness.
6. **Document**: Post-mortem report covering exposure window and root cause.

### 2.2 Poisoned Policy Data Source Detected
1. **Detect**: Activation gate failure alert, anomalous rule additions, or citizen complaints of erroneous eligibility outcomes.
2. **Contain**: Block sync triggers immediately.
3. **Rollback**:
   - Execute authenticated `POST /v1/policy/rollback` with `Role.ADMIN`.
   - Restores the previous known good policy snapshot atomically.
4. **Preserve Evidence**: Preserve candidate snapshot artifacts and diff reports in `data/snapshots/`.
5. **Verify**: Verify active policy version via `GET /v1/policy/status`. Run automated evaluation suite.
6. **Document**: File upstream security report with portal maintainers.

### 2.3 Malicious Document Upload or Decompression Bomb Attempt
1. **Detect**: HTTP 413, HTTP 415, or `PAYLOAD_OVERSIZE` / decompression ratio alert.
2. **Contain**: Offending IP blocked by rate limiter or ingress WAF.
3. **Preserve Evidence**: Temporary file was automatically deleted by `isolated_temp_document()`. Record SHA-256 digest from validation log.
4. **Verify**: Confirm CPU/RAM usage returned to baseline.

### 2.4 Accidental Secret or PII Leakage Alert
1. **Detect**: Automated log scan or security audit flags potential key or Aadhaar pattern in logs.
2. **Contain**: Verify if `SecretRedactingLoggingFilter` caught the instance. If log file contains leak, rotate the affected credential immediately.
3. **Sanitize**: Scrub log storage volume; deploy updated regex pattern to `src/utils/secret_redactor.py`.
