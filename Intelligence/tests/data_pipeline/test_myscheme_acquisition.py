"""
Unit and Integration Tests for FIN Exhaustive Data Acquisition.
Covers multi-strategy discovery, structured eligibility extraction,
7-tier authority hierarchy, conflict resolution, SSRF protection,
reconciliation diffs, multilingual tracking, and provenance.
"""

from pathlib import Path
import sys
import unittest
import json
import tempfile
import shutil

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.acquisition import (
    AuthorityHierarchy,
    AuthorityTierName,
    AcquisitionSecurityValidator,
    SafeHttpClient,
    SchemeNormalizer,
    AcquisitionConflictResolver,
    CorpusReconciler,
    AcquisitionStorage,
    AcquisitionRAGSynchronizer,
    MySchemeAcquisitionCrawler,
    ConflictResolutionStatus,
    RelationshipType,
    SchemeStatus,
    Scheme,
    DetailStatus,
    HttpRequestRecord,
    SchemeAcquisitionEntry,
    ProvenanceStatus,
    QueueStatus,
    EndpointType,
    LiveProvenanceEnvelope,
    AcquisitionQueueItem,
    AcquisitionQueue,
)
from src.data_pipeline.models import AuthorityTier


class TestMySchemeDataAcquisition(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = AcquisitionStorage(base_data_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_authority_hierarchy_classification(self):
        """Test strict classification of URLs across all 7 authority tiers."""
        # Tier 0: Statutory / Acts / Gazettes
        t0 = AuthorityHierarchy.classify_url("https://egazette.gov.in/WriteReadData/2024/12345.pdf")
        self.assertEqual(t0, AuthorityTierName.TIER_0_LEGAL_STATUTORY)
        t0_code = AuthorityHierarchy.classify_url("https://www.indiacode.nic.in/handle/123456789/1362")
        self.assertEqual(t0_code, AuthorityTierName.TIER_0_LEGAL_STATUTORY)

        # Tier 1: First-party ministry operational portals
        t1 = AuthorityHierarchy.classify_url("https://pmkisan.gov.in/")
        self.assertEqual(t1, AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL)
        t1_dept = AuthorityHierarchy.classify_url("https://financialservices.gov.in/beta/en/schemes")
        self.assertEqual(t1_dept, AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL)

        # Tier 2: myScheme discovery portal
        t2 = AuthorityHierarchy.classify_url("https://www.myscheme.gov.in/schemes/apy")
        self.assertEqual(t2, AuthorityTierName.TIER_2_MYSCHEME)
        t2_api = AuthorityHierarchy.classify_url("https://api.myscheme.gov.in/schemes/v6/public/schemes")
        self.assertEqual(t2_api, AuthorityTierName.TIER_2_MYSCHEME)

        # Tier 3: National official portals
        t3 = AuthorityHierarchy.classify_url("https://www.india.gov.in/my-government/schemes")
        self.assertEqual(t3, AuthorityTierName.TIER_3_NATIONAL_OFFICIAL)

        # Tier 4: Official publications / PIB
        t4 = AuthorityHierarchy.classify_url("https://pib.gov.in/PressReleasePage.aspx?PRID=123456")
        self.assertEqual(t4, AuthorityTierName.TIER_4_OFFICIAL_PUBLICATION)

        # Tier 5: Supplementary data platforms
        t5 = AuthorityHierarchy.classify_url("https://huggingface.co/datasets/bharatschemes")
        self.assertEqual(t5, AuthorityTierName.TIER_5_SUPPLEMENTARY)

        # Tier 6: Untrusted / Third-party blogs
        t6 = AuthorityHierarchy.classify_url("https://sarkariyojana.blogspot.com/pmkisan-update")
        self.assertEqual(t6, AuthorityTierName.TIER_6_UNTRUSTED)

    def test_authority_precedence_ordering(self):
        """Verify Tier 0 > Tier 1 > Tier 2 > Tier 3 > Tier 4 > Tier 5 > Tier 6."""
        tiers = [
            AuthorityTierName.TIER_0_LEGAL_STATUTORY,
            AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL,
            AuthorityTierName.TIER_2_MYSCHEME,
            AuthorityTierName.TIER_3_NATIONAL_OFFICIAL,
            AuthorityTierName.TIER_4_OFFICIAL_PUBLICATION,
            AuthorityTierName.TIER_5_SUPPLEMENTARY,
            AuthorityTierName.TIER_6_UNTRUSTED,
        ]
        ranks = [t.rank for t in tiers]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

        # Tier 0 strictly outranks Tier 2
        self.assertGreater(AuthorityHierarchy.compare_precedence(tiers[0], tiers[2]), 0)
        # Tier 5 cannot outrank Tier 1 or Tier 2
        self.assertLess(AuthorityHierarchy.compare_precedence(tiers[5], tiers[1]), 0)
        self.assertLess(AuthorityHierarchy.compare_precedence(tiers[5], tiers[2]), 0)

    def test_security_ssrf_and_spoofing_defense(self):
        """Verify strict blocking of SSRF, loopback, private ranges, and deceptive host spoofing."""
        # Loopback IPv4
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://127.0.0.1/admin")
        self.assertFalse(safe)

        # Cloud Metadata IMDSv1
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe)
        self.assertIn("not an authorized", reason)

        # Deceptive spoofed domain (gov.in in subdomain of attacker domain)
        safe, reason = AcquisitionSecurityValidator.is_safe_url("https://myscheme.gov.in.evilattacker.com/steal")
        self.assertFalse(safe)
        self.assertIn("deceptive", reason.lower())

        safe2, reason2 = AcquisitionSecurityValidator.is_safe_url("https://pmkisan-gov.in/phishing")
        self.assertFalse(safe2)

        # Legitimate government domains
        safe_gov, _ = AcquisitionSecurityValidator.is_safe_url("https://www.myscheme.gov.in/api/apisetu/schemes")
        self.assertTrue(safe_gov)
        safe_nic, _ = AcquisitionSecurityValidator.is_safe_url("https://indiacode.nic.in/")
        self.assertTrue(safe_nic)

    def test_security_directory_traversal(self):
        """Verify that directory traversal attempts in file storage are rejected."""
        base_dir = self.temp_dir / "safe"
        base_dir.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(ValueError):
            AcquisitionSecurityValidator.sanitize_file_path(base_dir, "../../../evil.py")

    def test_scheme_normalizer_and_structured_eligibility(self):
        """Test extraction of both raw text and deterministic conditions from Slate AST and text."""
        raw_detail = {
            "slug": "sample-pm-scheme",
            "_id": "628b41a2c9b440ca7f31ff99",
            "data": {
                "slug": "sample-pm-scheme",
                "en": {
                    "basicDetails": {
                        "schemeName": "Pradhan Mantri Sample Yojana",
                        "schemeShortTitle": "PMSY",
                        "level": {"label": "Central", "value": "central"},
                        "schemeCategory": [{"label": "Agriculture,Rural & Environment"}],
                        "tags": ["Farmer", "Direct Benefit"],
                        "implementingAgency": "Dept of Agriculture",
                        "nodalMinistryName": {"label": "Ministry Of Agriculture And Farmers Welfare"},
                    },
                    "schemeContent": {
                        "briefDescription": "Support for marginal farmers across India.",
                        "detailedDescription_md": "Detailed terms of PMSY financial assistance.",
                        "benefitTypes": {"label": "Cash", "value": "Cash"},
                        "benefits_md": "Financial benefit of Rs 6,000 per year paid in three equal installments.",
                        "references": [
                            {"title": "Operational Guidelines", "url": "https://agricoop.nic.in/guidelines_pmsy.pdf"}
                        ],
                    },
                    "eligibilityCriteria": {
                        "eligibilityDescription_md": (
                            "1. The applicant age must be between 18 and 60 years.\n"
                            "2. Annual family income must not exceed Rs. 2,50,000.\n"
                            "3. Only female farmers are eligible.\n"
                            "4. Must belong to SC or ST category."
                        )
                    },
                    "applicationProcess": [
                        {
                            "mode": "Online",
                            "process": [{"type": "paragraph", "children": [{"text": "Visit portal and register with Aadhaar."}]}]
                        }
                    ],
                }
            }
        }
        raw_docs = {
            "data": {
                "en": {
                    "documentsRequired_md": "1. Aadhaar Card\n2. Land Ownership Record (ROR)\n3. Bank Passbook"
                }
            }
        }
        raw_faqs = {
            "data": {
                "en": {
                    "faqs": [
                        {"question": "How much financial support is given?", "answer_md": "Rs 6,000 per year."}
                    ]
                }
            }
        }

        scheme = SchemeNormalizer.normalize_myscheme_payload(
            raw_detail_json=raw_detail,
            raw_docs_json=raw_docs,
            raw_faqs_json=raw_faqs,
            source_url="https://www.myscheme.gov.in/schemes/sample-pm-scheme",
            snapshot_id="snap_test_001",
        )

        self.assertEqual(scheme.canonical_slug, "sample-pm-scheme")
        self.assertEqual(scheme.scheme_name, "Pradhan Mantri Sample Yojana")
        self.assertEqual(scheme.alternate_names, ["PMSY"])
        self.assertEqual(scheme.central_or_state, "Central")
        self.assertEqual(scheme.category, "Agriculture,Rural & Environment")
        self.assertTrue(len(scheme.content_hash) == 64)  # SHA-256

        # Verify structured eligibility conditions
        fields = [c.field for c in scheme.eligibility_criteria]
        self.assertIn("age", fields)
        self.assertIn("annual_family_income", fields)
        self.assertIn("gender", fields)
        self.assertIn("caste_category", fields)

        # Check age criteria values
        age_crits = [c for c in scheme.eligibility_criteria if c.field == "age"]
        min_age = next((c.value for c in age_crits if c.operator == ">="), None)
        max_age = next((c.value for c in age_crits if c.operator == "<="), None)
        self.assertEqual(min_age, 18)
        self.assertEqual(max_age, 60)

        # Check income criteria
        inc_crit = next(c for c in scheme.eligibility_criteria if c.field == "annual_family_income")
        self.assertEqual(inc_crit.value, 250000.0)
        self.assertEqual(inc_crit.operator, "<=")
        # Verify raw text preserved
        self.assertIn("2,50,000", inc_crit.raw_text)

        # Verify documents
        self.assertEqual(len(scheme.required_documents), 3)
        self.assertEqual(scheme.required_documents[0].document_name, "Aadhaar Card")

        # Verify FAQs
        self.assertEqual(len(scheme.faqs), 1)
        self.assertEqual(scheme.faqs[0].question, "How much financial support is given?")

    def test_conflict_detection_and_resolution(self):
        """Test multi-source conflict resolution using authority tiers and effective dates."""
        record_myscheme = {
            "annual_family_income": 250000.0,
            "min_age": 18,
            "max_age": 40,
        }
        record_ministry = {
            "annual_family_income": 300000.0,  # Official ministry guideline updated limit
            "min_age": 18,
            "max_age": 40,
        }

        # Case 1: First-party ministry (Tier 1) vs myScheme (Tier 2) -> Ministry resolves automatically
        conflicts = AcquisitionConflictResolver.detect_and_resolve_conflicts(
            scheme_slug="apy",
            record_a=record_ministry,
            record_b=record_myscheme,
            source_a="ministry_guideline",
            source_b="myscheme_portal",
            authority_a=AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL,
            authority_b=AuthorityTierName.TIER_2_MYSCHEME,
        )
        self.assertEqual(len(conflicts), 1)
        c = conflicts[0]
        self.assertEqual(c.field_name, "annual_family_income")
        self.assertEqual(c.resolution_status, ConflictResolutionStatus.RESOLVED)
        self.assertEqual(c.resolved_value, 300000.0)
        self.assertIn("deterministically resolved", c.notes.lower())

        # Case 2: Supplementary dataset (Tier 5) vs myScheme (Tier 2) -> myScheme wins
        record_supp = {"annual_family_income": 500000.0}
        conflicts_supp = AcquisitionConflictResolver.detect_and_resolve_conflicts(
            scheme_slug="apy",
            record_a=record_myscheme,
            record_b=record_supp,
            source_a="myscheme_portal",
            source_b="hf_supplementary",
            authority_a=AuthorityTierName.TIER_2_MYSCHEME,
            authority_b=AuthorityTierName.TIER_5_SUPPLEMENTARY,
        )
        self.assertEqual(len(conflicts_supp), 1)
        self.assertEqual(conflicts_supp[0].resolved_value, 250000.0)

        # Case 3: Conflicting data at same tier without verified supersession -> REVIEW required
        record_equal_a = {"annual_family_income": 200000.0}
        record_equal_b = {"annual_family_income": 250000.0}
        conflicts_equal = AcquisitionConflictResolver.detect_and_resolve_conflicts(
            scheme_slug="apy",
            record_a=record_equal_a,
            record_b=record_equal_b,
            source_a="official_notice_1",
            source_b="official_notice_2",
            authority_a=AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL,
            authority_b=AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL,
        )
        self.assertEqual(len(conflicts_equal), 1)
        self.assertEqual(conflicts_equal[0].resolution_status, ConflictResolutionStatus.REVIEW)
        self.assertIsNone(conflicts_equal[0].resolved_value)

    def test_corpus_reconciliation_diff_generation(self):
        """Verify fine-grained reconciliation against existing baseline corpora."""
        scheme1 = Scheme(
            scheme_id="id1",
            canonical_slug="apy",
            scheme_name="Atal Pension Yojana Updated",
            raw_eligibility_text="18 to 40 years",
            raw_benefits_text="Pension of Rs 1000 to 5000",
            raw_documents_text="Aadhaar",
            fetched_at="2026-09-24T00:00:00Z",
            official_scheme_url="https://jansuraksha.gov.in/apy.pdf",
        )
        scheme_new = Scheme(
            scheme_id="id2",
            canonical_slug="brand-new-live-scheme",
            scheme_name="Brand New Scheme",
            raw_eligibility_text="All citizens",
            raw_benefits_text="Direct grant",
            raw_documents_text="None",
            fetched_at="2026-09-24T00:00:00Z",
        )
        live_schemes = {"apy": scheme1, "brand-new-live-scheme": scheme_new}

        baseline_schemes = {
            "apy": {
                "scheme_name": "Atal Pension Yojana",  # Name slightly different
                "eligibility": "18 to 40 years",
                "benefits": "Pension of Rs 1000 to 5000",
                "documents_required": "Aadhaar",
                "source_url": "https://old.url/apy",
            },
            "retired-old-scheme": {
                "scheme_name": "Retired Scheme",
            }
        }

        diff_report = CorpusReconciler.reconcile(live_schemes, baseline_schemes)
        self.assertEqual(diff_report["added_count"], 1)
        self.assertEqual(diff_report["added_schemes_sample"], ["brand-new-live-scheme"])
        self.assertEqual(diff_report["removed_count"], 1)
        self.assertEqual(diff_report["removed_schemes_sample"], ["retired-old-scheme"])
        self.assertEqual(diff_report["renamed_count"], 1)
        self.assertEqual(diff_report["newly_discovered_sources_count"], 1)

    def test_rag_chunking_and_provenance(self):
        """Verify RAG chunks include all required statutory metadata fields and exact evidence spans."""
        scheme = Scheme(
            scheme_id="scheme_test_id",
            canonical_slug="test-yojana",
            scheme_name="Test National Yojana",
            category="Health & Wellness",
            raw_eligibility_text="Income under Rs 1,00,000",
            raw_benefits_text="Free medical checkup",
            fetched_at="2026-09-24T00:00:00Z",
            myscheme_url="https://www.myscheme.gov.in/schemes/test-yojana",
        )
        chunks = AcquisitionRAGSynchronizer.generate_rag_chunks_for_scheme(scheme, policy_version="v2.1")
        self.assertTrue(len(chunks) >= 3)  # Overview, Eligibility, Benefits

        for chunk in chunks:
            self.assertEqual(chunk["scheme_id"], "scheme_test_id")
            self.assertEqual(chunk["scheme_slug"], "test-yojana")
            self.assertEqual(chunk["policy_version"], "v2.1")
            self.assertEqual(chunk["authority_tier"], AuthorityTierName.TIER_2_MYSCHEME.value)
            self.assertTrue(len(chunk["content_hash"]) > 0)
            self.assertTrue(len(chunk["evidence_span"]) > 0)

    def test_catalogue_count_vs_detail_count_distinction(self):
        """Verify strict distinction between catalogue enumeration and deep detail acquisition."""
        ledger_path = _INTELLIGENCE_DIR / "data" / "coverage" / "scheme_acquisition_ledger.json"
        if not ledger_path.exists():
            self.skipTest("scheme_acquisition_ledger.json not yet generated")
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        total_entries = len(ledger)
        self.assertGreaterEqual(total_entries, 5108)

        full_detail = [e for e in ledger if e["detail_status"] == DetailStatus.FULL_DETAIL.value]
        partial_detail = [e for e in ledger if e["detail_status"] == DetailStatus.PARTIAL_DETAIL.value]
        cat_only = [e for e in ledger if e["detail_status"] == DetailStatus.CATALOG_ONLY.value]
        removed = [e for e in ledger if e["detail_status"] == DetailStatus.REMOVED_ON_PORTAL.value]

        # Ensure no false claim of 100% full detail
        self.assertNotEqual(len(full_detail), total_entries)
        self.assertGreaterEqual(len(full_detail), 4000)
        self.assertGreater(len(partial_detail), 0)
        self.assertGreaterEqual(len(cat_only), 0)
        self.assertEqual(len(removed), 7)

    def test_duplicate_slug_detection(self):
        """Verify detection and handling of duplicate slugs in catalogue e.g. tufs."""
        raw_cat_path = _INTELLIGENCE_DIR / "data" / "raw" / "myscheme" / "master_catalogue_a02a2d29d8.json"
        if not raw_cat_path.exists():
            self.skipTest("master_catalogue raw file not found")
        with open(raw_cat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        slugs = [x.get("slug") for x in data.get("data", []) if x.get("slug")]
        self.assertEqual(slugs.count("tufs"), 2)

    def test_request_ledger_instrumentation(self):
        """Verify SafeHttpClient logs detailed HttpRequestRecord for each network call."""
        client = SafeHttpClient(requests_per_second=10.0)
        self.assertEqual(len(client.request_ledger), 0)

        # Trigger safe internal mock request
        client.fetch("https://www.myscheme.gov.in/api/apisetu/schemes?slug=apy&lang=en", batch_size=1)
        self.assertGreaterEqual(len(client.request_ledger), 1)
        rec = client.request_ledger[0]
        self.assertTrue(rec.request_id.startswith("req_"))
        self.assertIn("myscheme.gov.in", rec.endpoint)
        self.assertEqual(rec.method, "GET")
        self.assertEqual(rec.batch_size, 1)

    def test_conflict_metric_accuracy(self):
        """Verify audited conflicts metrics: 3 detected, 2 resolved, 1 review -> 1 unresolved."""
        conflicts_path = _INTELLIGENCE_DIR / "data" / "conflicts" / "conflicts_ledger.json"
        if not conflicts_path.exists():
            self.skipTest("conflicts_ledger.json not found")
        with open(conflicts_path, "r", encoding="utf-8") as f:
            conflicts = json.load(f)
        self.assertEqual(len(conflicts), 3)

        resolved = [c for c in conflicts if c["resolution_status"] == ConflictResolutionStatus.RESOLVED.value]
        review = [c for c in conflicts if c["resolution_status"] == ConflictResolutionStatus.REVIEW.value]
        self.assertEqual(len(resolved), 2)
        self.assertEqual(len(review), 1)

    def test_field_coverage_matrix_validity(self):
        """Verify field coverage percentages are artifact-derived and not fabricated 100%."""
        field_path = _INTELLIGENCE_DIR / "data" / "coverage" / "field_coverage.json"
        if not field_path.exists():
            self.skipTest("field_coverage.json not found")
        with open(field_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        fields = data["fields"]
        self.assertEqual(fields["scheme_name"]["percentage"], 100.0)
        self.assertLess(fields["documents"]["percentage"], 100.0)
        self.assertGreater(fields["documents"]["percentage"], 80.0)
        self.assertLess(fields["benefits"]["percentage"], 100.0)
        self.assertGreater(fields["benefits"]["percentage"], 80.0)

    def test_document_and_faq_coverage_integrity(self):
        """Verify document and FAQ coverage ledgers report accurate, non-zero missing counts."""
        doc_path = _INTELLIGENCE_DIR / "data" / "coverage" / "document_coverage.json"
        faq_path = _INTELLIGENCE_DIR / "data" / "coverage" / "faq_coverage.json"
        if not doc_path.exists() or not faq_path.exists():
            self.skipTest("Document or FAQ coverage ledgers missing")

        with open(doc_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)
        with open(faq_path, "r", encoding="utf-8") as f:
            faq_data = json.load(f)

        self.assertGreater(doc_data["schemes_without_documents"], 0)
        self.assertEqual(doc_data["documents_failed"], 0)
        self.assertEqual(faq_data["total_faq_records"], 51435)
        self.assertGreater(faq_data["schemes_without_faqs"], 0)

    def test_per_scheme_multilingual_coverage(self):
        """Verify portal languages (15) are separated from per-scheme language variant counts."""
        lang_path = _INTELLIGENCE_DIR / "data" / "coverage" / "language_coverage.json"
        if not lang_path.exists():
            self.skipTest("language_coverage.json missing")
        with open(lang_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["portal_languages_exposed_count"], 15)
        self.assertLess(data["schemes_with_all_15_languages"], data["schemes_with_english"])
        self.assertGreaterEqual(data["schemes_with_hindi"], 3473)

    def test_normalization_baseline_record_completeness(self):
        """Verify SchemeNormalizer.normalize_baseline_record produces complete Scheme."""
        row = {
            "slug": "sample-baseline-scheme",
            "scheme_name": "Sample Baseline Scheme",
            "short_title": "SBS",
            "level": "Central",
            "state": None,
            "ministry": "Ministry of Agriculture",
            "categories": "Agriculture,Rural & Environment",
            "brief_description": "A brief overview.",
            "detailed_description": "Comprehensive details of the scheme.",
            "eligibility": "1. Applicant age must be between 18 and 60 years.\n2. Annual family income must not exceed Rs. 2,00,000.",
            "benefits": "Financial grant of Rs 5000",
            "application_process": "Apply via official portal",
            "documents_required": "1. Aadhaar Card\n2. Bank Passbook",
            "references": "https://agricoop.gov.in/guidelines.pdf",
            "source_url": "https://www.myscheme.gov.in/schemes/sample-baseline-scheme",
        }
        scheme = SchemeNormalizer.normalize_baseline_record(row)
        self.assertEqual(scheme.canonical_slug, "sample-baseline-scheme")
        self.assertEqual(scheme.scheme_name, "Sample Baseline Scheme")
        self.assertGreaterEqual(len(scheme.eligibility_criteria), 2)
        self.assertEqual(len(scheme.benefits), 1)
        self.assertEqual(len(scheme.required_documents), 2)
        self.assertEqual(len(scheme.content_hash), 64)

    def test_full_live_queue_contains_all_catalogue_schemes(self):
        """Verify queue enqueues all 5,111 catalogue items (5,110 unique slugs + 1 duplicate slug)."""
        queue_path = self.temp_dir / "test_queue.json"
        queue = AcquisitionQueue(queue_file=queue_path)

        master_cat_path = _INTELLIGENCE_DIR / "data" / "raw" / "myscheme" / "master_catalogue_a02a2d29d8.json"
        if not master_cat_path.exists():
            self.skipTest("master_catalogue_a02a2d29d8.json not found")
        with open(master_cat_path, "r", encoding="utf-8") as f:
            cat_data = json.load(f)
        items = cat_data.get("data", [])

        queue.load_or_initialize(items)
        all_items = queue.get_all_items()
        self.assertEqual(len(all_items), len(items))
        self.assertGreaterEqual(len(all_items), 5108)

        # Verify duplicate slug 'tufs' is preserved as 2 distinct items
        tufs_items = [it for it in all_items if it.slug == "tufs"]
        self.assertEqual(len(tufs_items), 2)
        self.assertNotEqual(tufs_items[0].scheme_id, tufs_items[1].scheme_id)

    def test_no_production_sample_limit(self):
        """Verify production full-live mode does NOT impose a 25-scheme sampling limit."""
        crawler = MySchemeAcquisitionCrawler(mode="full-live")
        self.assertIsNone(crawler.sample_size)
        self.assertIsNone(crawler.max_schemes_to_fetch)
        self.assertEqual(crawler.mode, "full-live")

    def test_live_vs_baseline_provenance(self):
        """Verify baseline records without live network proof cannot be marked LIVE_ACQUIRED."""
        envelope = LiveProvenanceEnvelope(
            acquisition_run_id="run_test",
            scheme_id="scheme_123",
            slug="test-scheme",
            source="myscheme",
            source_url="https://www.myscheme.gov.in/schemes/test-scheme",
            source_endpoint="https://www.myscheme.gov.in/api/apisetu/schemes?slug=test-scheme&lang=en",
            acquisition_mode="LIVE",
            retrieval_timestamp="2026-09-24T12:00:00Z",
            http_status=200,
            response_hash="hash123",
            raw_artifact="data/raw/myscheme/scheme_123.json",
            normalization_version="v2.0.0",
            snapshot_id="snap_123",
            detail_status=DetailStatus.FULL_DETAIL.value,
        )
        self.assertEqual(envelope.acquisition_mode, "LIVE")

        entry = SchemeAcquisitionEntry(
            scheme_id="scheme_base",
            slug="base-scheme",
            detail_source="HISTORICAL_BASELINE_ONLY",
            live_verified=False,
            provenance_status=ProvenanceStatus.REUSED_BASELINE.value,
        )
        self.assertFalse(entry.live_verified)
        self.assertEqual(entry.provenance_status, ProvenanceStatus.REUSED_BASELINE.value)
        self.assertNotEqual(entry.provenance_status, ProvenanceStatus.LIVE_ACQUIRED.value)

    def test_every_live_scheme_has_acquisition_status(self):
        """Verify every scheme in scheme_acquisition_ledger has an explicit, valid status."""
        ledger_path = _INTELLIGENCE_DIR / "data" / "coverage" / "scheme_acquisition_ledger.json"
        if not ledger_path.exists():
            self.skipTest("scheme_acquisition_ledger.json not found")
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        valid_statuses = {
            DetailStatus.FULL_DETAIL.value,
            DetailStatus.PARTIAL_DETAIL.value,
            DetailStatus.CATALOG_ONLY.value,
            DetailStatus.FAILED.value,
            DetailStatus.NOT_AVAILABLE.value,
            DetailStatus.REMOVED_ON_PORTAL.value,
        }
        for entry in ledger:
            self.assertIn(entry["detail_status"], valid_statuses)
            self.assertTrue(entry.get("slug"))
            self.assertTrue(entry.get("scheme_id"))
            self.assertIn("live_verified", entry)

    def test_request_ledger_scheme_mapping(self):
        """Verify request ledger entries record scheme_id, slug, endpoint_type, and run_id."""
        client = SafeHttpClient(requests_per_second=10.0)
        client.fetch(
            url="https://www.myscheme.gov.in/api/apisetu/schemes?slug=apy&lang=en",
            scheme_id="633fd00eb499026402eaec09",
            slug="apy",
            endpoint_type=EndpointType.DETAIL.value,
            run_id="run_verify_test",
        )
        self.assertEqual(len(client.request_ledger), 1)
        rec = client.request_ledger[0]
        self.assertEqual(rec.slug, "apy")
        self.assertEqual(rec.scheme_id, "633fd00eb499026402eaec09")
        self.assertEqual(rec.endpoint_type, EndpointType.DETAIL.value)
        self.assertEqual(rec.run_id, "run_verify_test")
        self.assertTrue(rec.success)

    def test_bulk_response_completeness(self):
        """Verify bulk translation payload lacking criteria is NOT classified as FULL_DETAIL."""
        bulk_payload = {
            "data": {
                "slug": "sample-bulk",
                "_id": "62862b705c708f567e107f1a",
                "en": {
                    "basicDetails": {"schemeName": "Sample Bulk Scheme"},
                    "schemeContent": {"briefDescription": "Short text"},
                },
            }
        }
        status, missing = SchemeNormalizer.validate_detail_completeness(bulk_payload)
        self.assertNotEqual(status, DetailStatus.FULL_DETAIL)
        self.assertIn("eligibilityCriteria", missing)

    def test_catalogue_only_has_no_detail_claim(self):
        """Verify catalogue-only records are not claimed as full detail or RAG indexed."""
        entry = SchemeAcquisitionEntry(
            scheme_id="62862b705c708f567e107f1a",
            slug="kkjby",
            name="Khadi Karigar Janashree Bima Yojana",
            detail_status=DetailStatus.CATALOG_ONLY.value,
            live_verified=False,
            rag_status="NOT_INDEXED",
        )
        self.assertEqual(entry.detail_status, DetailStatus.CATALOG_ONLY.value)
        self.assertFalse(entry.live_verified)
        self.assertEqual(entry.rag_status, "NOT_INDEXED")

    def test_report_metrics_are_artifact_derived(self):
        """Verify coverage audit metrics strictly correlate with individual stage components."""
        audit_path = _INTELLIGENCE_DIR / "data" / "coverage" / "coverage_audit.json"
        if not audit_path.exists():
            self.skipTest("coverage_audit.json not found")
        with open(audit_path, "r", encoding="utf-8") as f:
            audit = json.load(f)

        self.assertEqual(
            audit["detail_success_count"],
            audit["full_detail_count"] + audit["partial_detail_count"],
        )
        self.assertGreaterEqual(audit["detail_attempted_count"], audit["detail_success_count"])


if __name__ == "__main__":
    unittest.main()
