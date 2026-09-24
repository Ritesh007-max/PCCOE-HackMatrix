# FIN — Data Acquisition Failure & Discrepancy Report

## 1. Network & Acquisition Failures

- **Total HTTP Requests Attempted:** 15,436
- **HTTP 200 Successes:** 15,436 (100.0%)
- **HTTP Failures / Drops:** 0 (0.0%)
- **Unreachable Endpoints:** 0
- **Dead Schemes on Portal:** 0

The rate limiter (6.0 requests/sec with cooperative exponential backoff) prevented any 429 rate limit exhaustion or dropped packets across the AWS ALB edge.

---

## 2. Partial Detail Schemes (5 Schemes)

The following 5 schemes succeeded with HTTP 200 and possess valid eligibility and benefit data, but lack optional references/links on the live portal:

1. **`cmchis`** (ID: `641bc580d88401653151a051`) — Chief Minister Comprehensive Health Insurance Scheme (Missing secondary references on portal)
2. **`mmgsy`** (ID: `641d5375ded5a517c845511d`) — Mukhya Mantri Gram Sadak Yojana (Missing secondary references on portal)
3. **`mmuy`** (ID: `6421902bb04969635da5eefd`) — Mukhyamantri Udyami Yojana (Missing secondary references on portal)
4. **`cmegp`** (ID: `65d83237938a0b13cc8eaa67`) — Chief Minister Employment Generation Programme (Missing secondary references on portal)
5. **`nari-adalat`** (ID: `67e0ee08dcf7ceef67c7909f`) — Nari Adalat (Missing secondary references on portal)

---

## 3. Historical Baseline Schemes Retired / De-Indexed on Portal (7 Schemes)

The following 7 schemes were present in historical baseline datasets (`schemes.csv`) but have been de-indexed or merged on the live portal. They are preserved with provenance `REUSED_BASELINE` and detail status `REMOVED_ON_PORTAL`:

1. `ab-pmjay`
2. `himayat`
3. `mord-ddugky-pwd`
4. `nhfdc-eduloan`
5. `pmmy-mudra-shishu`
6. `pmvdvk`
7. `rvep`

---

## 4. Unresolved Policy Conflicts (1 Flagged Review)

- **Total Detected Conflicts:** 3
- **Resolved via Hierarchy:** 2 (Central Gazette > myScheme secondary text)
- **Pending Statutory Review:** 1 (`conflict_pmkisan_land_tier2_vs_tier2` — conflicting state landholding interpretations flagged for manual review)
