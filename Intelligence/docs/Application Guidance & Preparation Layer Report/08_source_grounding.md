# Phase 11: Source Grounding & URL Verification

## 1. Domain Allowlists

To prevent malicious domain injection and spurious web links, FIN enforces strict domain allowlisting on all emitted portal URLs:
- `.gov.in` (National and State Government Portals)
- `.nic.in` (National Informatics Centre)
- `.ac.in` (Accredited Indian Academic Institutions)
- `.edu.in` (Accredited Educational Bodies)
- Trusted autonomous entities: `digitalgujarat.gov.in`, `myscheme.gov.in`, `scholarships.gov.in`, `pmkisan.gov.in`, `epfindia.gov.in`.

---

## 2. Rejection of Unverified URLs

Any URL originating from:
- Blogs (`.blogspot.com`, `.wordpress.com`)
- News sites (`timesofindia.indiatimes.com`, `hindustantimes.com`)
- Generic aggregators (`sarkariyojana.com`, `cleartax.in`)
- Search engines (`google.com`, `bing.com`)

is rejected and set to `null`, triggering a warning:
```json
{
  "code": "OFFICIAL_LINK_UNAVAILABLE",
  "severity": "MEDIUM",
  "message": "Official application portal link is not available in verified government records."
}
```
