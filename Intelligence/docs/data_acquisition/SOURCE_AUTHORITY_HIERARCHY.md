# FIN — Source Authority Hierarchy & Statutory Precedence

## 1. Executive Authority Model

In FIN, statutory policy decisions cannot rely on third-party aggregators or web summaries when primary legal instruments exist. Dynamic freshness does not equal statutory authority.

The system enforces an explicit **7-tier source authority hierarchy**:

```
TIER 0 — LEGAL / STATUTORY PRIMARY AUTHORITY (Rank 10)
  ▲
TIER 1 — FIRST-PARTY GOVERNMENT OPERATIONAL SOURCE (Rank 8)
  ▲
TIER 2 — myScheme DISCOVERY & CANONICAL PLATFORM (Rank 6)
  ▲
TIER 3 — NATIONAL OFFICIAL GOVERNMENT PORTALS (Rank 5)
  ▲
TIER 4 — OFFICIAL GOVERNMENT PUBLICATIONS (Rank 4)
  ▲
TIER 5 — SUPPLEMENTARY DATASETS (Rank 2) [Discovery / Benchmark Only]
  ▲
TIER 6 — UNTRUSTED EXTERNAL SOURCES (Rank 0) [Rejected]
```

---

## 2. Detailed Tier Specifications

### TIER 0 — LEGAL / STATUTORY PRIMARY AUTHORITY
- **Definition**: The supreme legal authority governing policy existence, statutory terms, entitlements, and exclusions.
- **Approved Domains**:
  - `egazette.gov.in` (Official Gazette of India)
  - `indiacode.nic.in` (India Code Digital Repository of Acts and Rules)
  - `legislative.gov.in` (Ministry of Law and Justice)
- **Legal Instruments**: Acts of Parliament, State Legislative Acts, Statutory Rules, Regulations, Gazette Notifications, Presidential Orders.
- **Authority Scope**: Legal eligibility criteria, statutory income limits, age boundaries, penal exclusions, effective commencement dates, and legislative amendments.
- **Precedence Rule**: **Tier 0 strictly overrides all lower-level summaries and web content.**

### TIER 1 — FIRST-PARTY GOVERNMENT OPERATIONAL SOURCE
- **Definition**: The official implementing Ministry, Department, or State Government portal directly administering the scheme.
- **Approved Domains**:
  - Concerned Ministry portals (e.g. `agricoop.nic.in`, `financialservices.gov.in`, `msme.gov.in`)
  - Dedicated scheme portals (e.g. `pmkisan.gov.in`, `jansuraksha.gov.in`, `pmsvanidhi.mohua.gov.in`)
  - Official State Department platforms
- **Authority Scope**: Detailed operational guidelines, application processes, current service URLs, implementing agencies, required documentation checklists, and administrative circulars.

### TIER 2 — myScheme
- **Definition**: Mandatory central discovery, scheme enumeration, and unified citizen metadata platform.
- **Approved Domains**:
  - `www.myscheme.gov.in`
  - `search.myscheme.gov.in`
  - `rules.myscheme.gov.in`
  - `api.myscheme.gov.in`
- **Authority Scope**: Comprehensive scheme enumeration (all 5,108 schemes), categorized citizen journeys, cross-scheme eligibility summaries, multi-attribute discovery, citizen-facing FAQs, and initial canonicalization.
- **Precedence Rule**: `myScheme summary != statutory override`. When myScheme conflicts with Tier 0 or Tier 1, both versions are recorded, a conflict log is emitted, and Tier 0/1 takes precedence.

### TIER 3 — NATIONAL OFFICIAL GOVERNMENT PORTALS
- **Definition**: High-level national aggregator and service discovery portals.
- **Approved Domains**:
  - `india.gov.in` (National Portal of India)
  - `digitalindia.gov.in`
  - `data.gov.in`
  - `web.umang.gov.in` (UMANG platform)
  - `services.india.gov.in`
- **Authority Scope**: High-level ministerial directories, national service links, and broad discovery.

### TIER 4 — OFFICIAL GOVERNMENT PUBLICATIONS
- **Definition**: Official government press notices and announcements.
- **Approved Domains**:
  - `pib.gov.in` (Press Information Bureau)
  - `newsonair.gov.in` (All India Radio News)
- **Authority Scope**: Launch dates, public policy announcements, contextual announcements, and budgetary speech transcripts.
- **Precedence Rule**: Press releases do NOT override gazetted statutory guidelines unless the release constitutes the sole contemporaneous official notification.

### TIER 5 — SUPPLEMENTARY DATASETS
- **Definition**: External datasets, research corpora, benchmark fixtures, and open-source collections.
- **Examples**:
  - Hugging Face datasets (`satyajitdas/bharatschemes-v1`, `smartduketech/indian-government-schemes-2025`, `shrijayan/gov_myscheme`)
  - Kaggle datasets
  - Academic evaluation benchmarks
- **Authority Scope**: Semantic enrichment, recall benchmarking, alias expansion, query testing, and evaluation.
- **CRITICAL HARDENING RULE**: **Tier 5 content is strictly FORBIDDEN from deciding or modifying statutory eligibility rules, benefit thresholds, or official criteria.**

### TIER 6 — UNTRUSTED EXTERNAL SOURCES
- **Definition**: Unofficial blogs, commercial scheme scrapers, third-party news aggregators, and unverified websites.
- **Examples**: `sarkariyojana.com`, `cleartax.in`, Blogspot blogs.
- **Authority Scope**: Strictly rejected by the network security allowlist. Never ingested into the statutory knowledge base.

---

## 3. Field-Specific Precedence Rules

| Domain Fact / Field | Decision Authority Rule |
|---|---|
| **Eligibility Conditions** | `Tier 0 > Tier 1 > Tier 2` |
| **Statutory Exclusions** | `Tier 0 > Tier 1 > Tier 2` |
| **Benefit Calculations & Formulas** | `Tier 0 > Tier 1 > Tier 2` |
| **Operational Application Steps** | `Tier 1 > Tier 2` |
| **Official Application URL** | `Tier 1 > Tier 2` (Direct ministry portal over discovery redirect) |
| **Departmental FAQs** | Scheme-owning authority (`Tier 1`) > `Tier 2` > `Tier 5` |
| **Historical Policy Decisions** | Effective-date-aware authoritative source (`Tier 0 / 1`) |
| **General Discovery & Taxonomy** | `Tier 2` (myScheme is primary enumeration universe) |
| **Supplementary Datasets** | Discovery and evaluation only. Zero statutory authority. |
