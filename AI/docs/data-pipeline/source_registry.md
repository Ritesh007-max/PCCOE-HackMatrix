# PolicySetu Source Registry and Authority Hierarchy

## 1. Source Classification and Identification

The PolicySetu Phase 7 Source Registry (`SourceRegistry`) enforces a strict, cryptographically verified inventory of all data sources used across the AI subsystem.

### Source Taxonomy & Explicit Identification

| Source ID | Source Type | Authority Tier | Repository / File Identifier | Trust Level | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `official_portal_web` | `OFFICIAL_PORTAL` | `PRIMARY_OFFICIAL` | `https://www.myscheme.gov.in` | Discovery Mirror | Central government discovery portal with scheme-level canonical schemas. |
| `ministry_first_party` | `MINISTRY_PORTAL` | `PRIMARY_OFFICIAL` | `https://*.gov.in` / `https://*.nic.in` | Statutory Authority | First-party ministry and departmental gazette portals. Overrides aggregate portal text on conflict. |
| `primary_schemes_canonical` | `LOCAL_CSV` | `PRIMARY_CANONICALIZED` | `schemes.csv` | High (Curated Baseline) | Pre-canonicalized scheme dataset containing 4,749 schemes with eligibility, benefits, and tags. |
| `primary_faqs_canonical` | `LOCAL_CSV` | `PRIMARY_CANONICALIZED` | `schemes_faqs.csv` | High (Curated Baseline) | 51,435 official FAQ pairs mapped to scheme slugs. |
| `supplementary_schemes_updated` | `LOCAL_CSV` | `SUPPLEMENTARY` | `updated_data.csv` | Medium (Enrichment) | 3,400 supplementary records (79 distinct supplementary schemes) providing application steps and additional guidelines. |
| `LOCAL_BILINGUAL_DATASET` | `LOCAL_CSV` | `SUPPLEMENTARY` | `indian government schemes dataset english and hindi.csv` | Medium (Bilingual Enrichment) | 3,473 bilingual English-Hindi paired records for multilingual query routing and retrieval. |
| `HF_BHARATSCHEMES` | `HUGGINGFACE_DATASET` | `SUPPLEMENTARY` | `satyajitdas/bharatschemes-v1` | Medium (External Mirror) | Verified HuggingFace mirror of Indian government schemes. |
| `HF_SMARTDUKE` | `HUGGINGFACE_DATASET` | `SUPPLEMENTARY` | `smartduketech/indian-government-schemes-2025` | Medium (External Mirror) | 2025 government schemes compilation from SmartDuke. |
| `HF_SHRIJAYAN` | `HUGGINGFACE_DATASET` | `SUPPLEMENTARY` | `shrijayan/gov_myscheme` | Medium (External Mirror) | myScheme crawl snapshot hosted on HuggingFace. |
| `archive_zip_historical` | `ARCHIVE_ZIP` | `ARCHIVE` | `archive (1).zip` | Low (Historical Baseline) | 1,524 historical scheme guideline documents in zip format. |

> [!IMPORTANT]
> The source registry strictly separates the local bilingual CSV file (`LOCAL_BILINGUAL_DATASET`) from the remote HuggingFace repository `satyajitdas/bharatschemes-v1` (`HF_BHARATSCHEMES`). Furthermore, all HuggingFace sources must carry explicit HF repo IDs.

---

## 2. Authority Hierarchy

When identical fields (e.g., eligibility criteria, income thresholds, required documents) conflict across multiple sources for the same scheme slug, the system resolves discrepancies using the following precedence hierarchy:

```
PRIMARY_OFFICIAL (First-party Ministry / Gazette)
      > PRIMARY_OFFICIAL (myScheme Discovery Portal)
            > PRIMARY_CANONICALIZED (schemes.csv / schemes_faqs.csv)
                  > SUPPLEMENTARY (updated_data.csv / LOCAL_BILINGUAL_DATASET / HF Repos)
                        > ARCHIVE (archive (1).zip)
                              > EVALUATION_ONLY (Synthetic Test Datasets)
```

### Precedence Rules

1. **First-Party Supremacy**:
   A verified ministry gazette notice or department order hosted on an official `.gov.in` domain takes absolute precedence over third-party scrapers and secondary aggregation portals.
2. **Freshness $\neq$ Authority**:
   A newer supplementary crawl cannot silently overwrite an authoritative statutory rule established by a `PRIMARY_OFFICIAL` or `PRIMARY_CANONICALIZED` source.
3. **Additive Ingestion for Supplementary Sources**:
   Supplementary datasets can contribute:
   - Missing application steps or offline submission office details.
   - Multilingual translations (Hindi Devanagari text).
   - Additional non-conflicting FAQs.
   They *cannot* mutate existing statutory age or income limits without generating a conflict record and triggering manual audit review.

---

## 3. Domain Allowlist and Network Security Hardening

To prevent unauthorized web scraping, SSRF attacks, or ingestion of unvetted third-party web content, `SourceRegistry.is_url_allowed()` enforces strict security hardening. Broad suffix matching (such as wildcard `huggingface.co` or `raw.githubusercontent.com`) is forbidden in production because multi-tenant platforms host arbitrary unvetted repositories.

Instead, the pipeline requires **exact registered hosts** and **exact approved repository paths**:

### 1. Exact Registered Discovery Portals
```python
APPROVED_EXACT_HOSTS = {
    "www.myscheme.gov.in",
    "myscheme.gov.in",
    "india.gov.in",
    "www.india.gov.in",
}
```

### 2. Official Statutory Government Domains
Official Indian government portals are restricted to statutory `.gov.in` and `.nic.in` domains with strict boundary checking:
```python
if host == "gov.in" or host.endswith(".gov.in") or host == "nic.in" or host.endswith(".nic.in"):
    return True
```

### 3. Exact Third-Party Repository Path Validation
For external hosting platforms like HuggingFace, blanket domain matching is disabled. The URL path must explicitly match one of the curated, registered repository identifiers:
```python
APPROVED_HF_REPOS = {
    "satyajitdas/bharatschemes-v1",
    "smartduketech/indian-government-schemes-2025",
    "shrijayan/gov_myscheme",
}
```
Any arbitrary repository (e.g. `attacker/fake-schemes` or `raw.githubusercontent.com/evil/data.csv`) is rejected before any network socket is opened.

---

## 4. Update Schedules and TTL Policies

| Authority Tier | Default TTL | Refresh Strategy | Failure Handling |
| :--- | :--- | :--- | :--- |
| `PRIMARY_OFFICIAL` | 7 Days | HTTP Conditional GET (`If-None-Match`, `If-Modified-Since`) | Retain active cached revision; flag warning if stale > 30 days. |
| `PRIMARY_CANONICALIZED` | 30 Days | Hash comparison on disk | Immutable unless explicit data pipeline migration is run. |
| `SUPPLEMENTARY` | 30 Days | Checksum verification on update | Ingest additive metadata; quarantine conflicting criteria. |
| `ARCHIVE` | 365 Days | Read-only historical snapshot | Static fallback reference. |
