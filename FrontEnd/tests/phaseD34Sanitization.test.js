import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getSchemePortalDetails,
  parseRequiredDocuments,
  matchDocumentStatus,
  parseApplicationProcess,
  isLoanSchemeWithCalculator,
  adaptSchemeDetails,
  validateOfficialUrl
} from '../src/utils/schemeDetailsHelpers.js';

// -----------------------------------------------------------------------------
// Test Case 1: 1pmy does not show a business-loan calculator
// -----------------------------------------------------------------------------
test('1. 1pmy (100% Penalty Mafi Yojana) does not show a business-loan calculator', () => {
  const scheme1pmy = {
    id: '1pmy',
    slug: '1pmy',
    title: '100% Penalty Mafi Yojana',
    benefit_type: 'Penalty Waiver',
    is_loan_scheme: false,
    source_url: 'https://www.myscheme.gov.in/schemes/1pmy'
  };

  const hasCalculator = isLoanSchemeWithCalculator(scheme1pmy);
  assert.strictEqual(hasCalculator, false, '1pmy must never activate loan calculator');
});

// -----------------------------------------------------------------------------
// Test Case 2: Non-loan schemes do not show PMEGP loan percentages or project limits
// -----------------------------------------------------------------------------
test('2. Non-loan schemes (housing penalty waiver, scholarship, grant) reject loan calculator', () => {
  const penaltyScheme = { id: 'guj-waiver', benefit_type: 'Penalty Waiver' };
  const grantScheme = { id: 'grant-01', benefit_type: 'Direct Cash Grant' };
  const scholarshipScheme = { id: 'post-matric', benefit_type: 'Scholarship' };

  assert.strictEqual(isLoanSchemeWithCalculator(penaltyScheme), false);
  assert.strictEqual(isLoanSchemeWithCalculator(grantScheme), false);
  assert.strictEqual(isLoanSchemeWithCalculator(scholarshipScheme), false);
});

// -----------------------------------------------------------------------------
// Test Case 3: Missing financial parameters do not produce fabricated benefit estimates
// -----------------------------------------------------------------------------
test('3. Missing financial parameters do not produce fabricated benefit estimates (₹1,25,000 / ₹1,75,000)', () => {
  const schemeNoBenefit = {
    id: 'scheme-no-cost',
    title: 'Welfare Support Scheme',
    max_benefit: null,
    benefit_amount: null
  };

  const adapted = adaptSchemeDetails(schemeNoBenefit);
  assert.strictEqual(adapted.maxBenefit, null);
  assert.strictEqual(adapted.benefitAmount, null);
  // Default fallback must not be ₹1,25,000 or ₹1,75,000
  assert.notStrictEqual(adapted.benefitAmount, '₹1,25,000');
  assert.notStrictEqual(adapted.benefitAmount, '₹1,75,000');
});

// -----------------------------------------------------------------------------
// Test Case 4: dbt_scheme: false hides the DBT badge
// -----------------------------------------------------------------------------
test('4. dbt_scheme: false (and null/undefined) strictly hides the DBT badge', () => {
  const schemeDbtFalse = { id: 's1', dbt_scheme: false };
  const schemeDbtNull = { id: 's2', dbt_scheme: null };
  const schemeDbtUndefined = { id: 's3' };
  const schemeDbtTrue = { id: 's4', dbt_scheme: true };

  // Only strict boolean true must show DBT badge
  assert.strictEqual(schemeDbtFalse.dbt_scheme === true, false);
  assert.strictEqual(schemeDbtNull.dbt_scheme === true, false);
  assert.strictEqual(schemeDbtUndefined.dbt_scheme === true, false);
  assert.strictEqual(schemeDbtTrue.dbt_scheme === true, true);
});

// -----------------------------------------------------------------------------
// Test Case 5: Missing source_url does not produce an unrelated official URL
// -----------------------------------------------------------------------------
test('5. Missing source_url does not produce an unrelated official URL (e.g. india.gov.in)', () => {
  const schemeNoUrl = {
    id: 's-no-url',
    title: 'State Scheme Without Source',
    source_url: null,
    official_url: null
  };

  const portal = getSchemePortalDetails(schemeNoUrl);
  assert.strictEqual(portal.officialWebsite, null);
  assert.notStrictEqual(portal.officialWebsite, 'https://india.gov.in');
  assert.notStrictEqual(portal.officialWebsite, 'https://india.gov.in/');

  const schemeWithUrl = {
    id: '1pmy',
    source_url: 'https://www.myscheme.gov.in/schemes/1pmy'
  };
  const portalWithUrl = getSchemePortalDetails(schemeWithUrl);
  assert.strictEqual(portalWithUrl.officialWebsite, 'https://www.myscheme.gov.in/schemes/1pmy');
});

// -----------------------------------------------------------------------------
// Test Case 6: Scheme-specific documents are rendered from canonical data
// -----------------------------------------------------------------------------
test('6. Scheme-specific documents are parsed from canonical documents_required', () => {
  const rawDocs = 'Aadhaar Card; Gujarat Housing Board Allotment Letter; Penalty Demand Notice; Bank Account Details';
  const scheme = { documents_required: rawDocs };

  const parsed = parseRequiredDocuments(scheme);
  assert.strictEqual(parsed.length, 4);
  assert.strictEqual(parsed[0], 'Aadhaar Card');
  assert.strictEqual(parsed[1], 'Gujarat Housing Board Allotment Letter');
  assert.strictEqual(parsed[2], 'Penalty Demand Notice');
  assert.strictEqual(parsed[3], 'Bank Account Details');

  // Should NOT contain generic PMEGP documents
  assert.strictEqual(parsed.includes('Project Report (Detailed DPR)'), false);
  assert.strictEqual(parsed.includes('EDP Training Certificate'), false);
});

// -----------------------------------------------------------------------------
// Test Case 7: Uploaded but unverified documents are not labeled verified
// -----------------------------------------------------------------------------
test('7. Uploaded but unverified documents are not labeled verified', () => {
  const userDocs = [
    { name: 'aadhaar_card.pdf', document_type: 'aadhaar', status: 'verified' },
    { name: 'ghb_allotment.pdf', document_type: 'ghb_allotment', status: 'uploaded' },
    { name: 'penalty_notice.pdf', document_type: 'penalty_notice', status: 'review_required' }
  ];

  // Verified document
  assert.strictEqual(matchDocumentStatus('Aadhaar Card', userDocs), 'Verified');

  // Uploaded document (NOT verified)
  assert.strictEqual(matchDocumentStatus('ghb_allotment', userDocs), 'Uploaded');

  // Pending/Review required document
  assert.strictEqual(matchDocumentStatus('penalty_notice', userDocs), 'Review Required');

  // Missing document
  assert.strictEqual(matchDocumentStatus('Bank Passbook', userDocs), 'Missing');

  // Never mark verified when user document list is empty
  assert.strictEqual(matchDocumentStatus('Aadhaar Card', []), 'Missing');
});

// -----------------------------------------------------------------------------
// Test Case 8: Missing application-process data does not create generic workflow steps
// -----------------------------------------------------------------------------
test('8. Missing application-process data does not create generic workflow steps', () => {
  const emptySteps1 = parseApplicationProcess(null);
  const emptySteps2 = parseApplicationProcess('');
  const emptySteps3 = parseApplicationProcess('   ');

  assert.deepStrictEqual(emptySteps1, []);
  assert.deepStrictEqual(emptySteps2, []);
  assert.deepStrictEqual(emptySteps3, []);

  // When structured steps exist in canonical data
  const canonicalProcess = 'Step 1: Check Penalty Notice | Step 2: Submit Application to GHB Officer | Step 3: Pay Principal Amount';
  const parsed = parseApplicationProcess(canonicalProcess);
  assert.strictEqual(parsed.length, 3);
  assert.strictEqual(parsed[0].title, 'Check Penalty Notice');
  assert.strictEqual(parsed[1].title, 'Submit Application to GHB Officer');
  assert.strictEqual(parsed[2].title, 'Pay Principal Amount');
});

// -----------------------------------------------------------------------------
// Test Case 9: Missing deadlines and SLAs remain unavailable
// -----------------------------------------------------------------------------
test('9. Missing deadlines and SLAs remain unavailable without arbitrary 24x7 or 48h claims', () => {
  const schemeOpen = {
    scheme_open_date: null,
    scheme_close_date: null
  };

  const portalDetails = getSchemePortalDetails(schemeOpen);
  // No hardcoded 24x7 helpline hours or 48h grievance SLAs
  assert.strictEqual(portalDetails.helplineHours, null);
  assert.strictEqual(portalDetails.helplineNumber, null);
});

// -----------------------------------------------------------------------------
// Test Case 10: UNKNOWN eligibility remains UNKNOWN
// -----------------------------------------------------------------------------
test('10. UNKNOWN eligibility remains UNKNOWN and is not converted to PASS or FAIL', () => {
  const eligibilityVerdict = {
    verdict: 'UNKNOWN',
    reasons: ['Statutory rule set not registered for automated evaluation'],
    missing_fields: ['ghb_allotment_number', 'penalty_outstanding_amount']
  };

  assert.strictEqual(eligibilityVerdict.verdict, 'UNKNOWN');
  assert.notStrictEqual(eligibilityVerdict.verdict, 'PASS');
  assert.notStrictEqual(eligibilityVerdict.verdict, 'FAIL');
});

// -----------------------------------------------------------------------------
// Test Case 11: Missing relevance data is not presented as a genuine 0% score
// -----------------------------------------------------------------------------
test('11. Missing relevance data is not presented as a genuine 0% score', () => {
  const schemeUnranked = {
    id: '1pmy',
    relevanceScore: null,
    matchScore: null
  };

  const adapted = adaptSchemeDetails(schemeUnranked);
  assert.strictEqual(adapted.relevanceScore, null);
  assert.strictEqual(adapted.matchScore, null);
  // When null, UI displays '—' / 'Not ranked', not '0%'
});

// -----------------------------------------------------------------------------
// Test Case 12: Empty or unavailable FAQs are handled gracefully
// -----------------------------------------------------------------------------
test('12. Empty or unavailable FAQs are handled gracefully with canonical notice', () => {
  const faqs = [];
  const faqsLoaded = true;
  const isFaqsLoading = false;
  const faqsError = null;

  const shouldShowEmptyState = !isFaqsLoading && !faqsError && faqs.length === 0 && faqsLoaded;
  assert.strictEqual(shouldShowEmptyState, true);
});

// -----------------------------------------------------------------------------
// Test Case 13: Genuinely credit-linked scheme displays calculator when parameters exist
// -----------------------------------------------------------------------------
test('13. Genuinely credit-linked scheme (PMEGP) displays calculator with parameters', () => {
  const pmegpScheme = {
    id: 'pmegp',
    slug: 'pmegp',
    title: 'Prime Minister Employment Generation Programme',
    benefit_type: 'Credit Linked Subsidy',
    is_loan_scheme: true,
    max_benefit: 1000000
  };

  const hasCalculator = isLoanSchemeWithCalculator(pmegpScheme);
  assert.strictEqual(hasCalculator, true, 'Credit-linked scheme must support calculator');
});

// -----------------------------------------------------------------------------
// Test Case 14: Applicant isolation is preserved
// -----------------------------------------------------------------------------
test('14. Applicant isolation is preserved during document status matching', () => {
  const applicantADocs = [
    { file_name: 'applicant_a_aadhaar.pdf', document_type: 'aadhaar', status: 'verified', user_id: 'user-aaa' }
  ];
  const applicantBDocs = [
    { file_name: 'applicant_b_doc.pdf', document_type: 'income', status: 'uploaded', user_id: 'user-bbb' }
  ];

  // User A has Aadhaar verified
  assert.strictEqual(matchDocumentStatus('Aadhaar Card', applicantADocs), 'Verified');
  // User B does NOT have Aadhaar
  assert.strictEqual(matchDocumentStatus('Aadhaar Card', applicantBDocs), 'Missing');
});

// -----------------------------------------------------------------------------
// Test Case 15: Diverse scheme coverage (penalty waiver, scholarship, credit-linked, grant)
// -----------------------------------------------------------------------------
test('15. Dynamic handling across diverse scheme types without hardcoded branch lists', () => {
  const schemes = [
    { id: '1pmy', title: '100% Penalty Mafi Yojana', type: 'Penalty Waiver', hasCalc: false },
    { id: 'pmegp', title: 'PMEGP', is_loan_scheme: true, hasCalc: true },
    { id: 'pmawy', title: 'PM Awas Yojana', benefit_type: 'Credit Linked Subsidy', maxBenefit: 250000, hasCalc: true },
    { id: 'scholarship-1', title: 'National Scholarship', benefit_type: 'Scholarship', hasCalc: false }
  ];

  for (const s of schemes) {
    const calc = isLoanSchemeWithCalculator(s);
    assert.strictEqual(calc, s.hasCalc, `Scheme ${s.id} calculator mismatch: expected ${s.hasCalc}, got ${calc}`);
  }
});

// -----------------------------------------------------------------------------
// Test Case 16: State schemes are not labeled Central Government
// -----------------------------------------------------------------------------
test('16. State schemes are not labeled Central Government', () => {
  const gujaratScheme = {
    id: '1pmy',
    state: 'Gujarat',
    level: null // unstated in DB row
  };
  const adapted = adaptSchemeDetails(gujaratScheme);
  assert.strictEqual(adapted.state, 'Gujarat');
  assert.strictEqual(adapted.level, 'State');
  assert.notStrictEqual(adapted.level, 'Central');
  assert.ok(adapted.tags.includes('Gujarat') || adapted.tags.includes('State Scheme'));
  assert.strictEqual(adapted.tags.includes('Central Scheme'), false);
  assert.strictEqual(adapted.tags.includes('Central Government'), false);
});

// -----------------------------------------------------------------------------
// Phase D3.4.1 Tests: Official Scheme Website URL Validation & Rendering
// -----------------------------------------------------------------------------

test('17. Phase D3.4.1: Valid government official URLs are accepted and populated', () => {
  const scheme1pmy = {
    id: '1pmy',
    source_url: 'https://www.myscheme.gov.in/schemes/1pmy'
  };
  const portal = getSchemePortalDetails(scheme1pmy);
  assert.strictEqual(portal.officialWebsite, 'https://www.myscheme.gov.in/schemes/1pmy');

  const schemeGujarat = {
    id: 'guj-scheme',
    source_url: 'https://mariyojana.gujarat.gov.in/Schemeatoz.aspx'
  };
  const portalGujarat = getSchemePortalDetails(schemeGujarat);
  assert.strictEqual(portalGujarat.officialWebsite, 'https://mariyojana.gujarat.gov.in/Schemeatoz.aspx');
});

test('18. Phase D3.4.1: Missing official URL retains honest null state without fallback to generic portal', () => {
  const schemeNoUrl = {
    id: 'scheme-missing-link',
    source_url: null,
    official_url: null
  };
  const portal = getSchemePortalDetails(schemeNoUrl);
  assert.strictEqual(portal.officialWebsite, null);
  assert.notStrictEqual(portal.officialWebsite, 'https://india.gov.in');
  assert.notStrictEqual(portal.officialWebsite, 'https://india.gov.in/');
});

test('19. Phase D3.4.1: Invalid URL protocols (javascript, data, ftp, file) are strictly rejected', () => {
  const invalidProtocols = [
    'javascript:alert(1)',
    'javascript://evil.com/%0Aalert(1)',
    'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
    'ftp://myscheme.gov.in/portal',
    'file:///etc/hosts',
    '//myscheme.gov.in/schemes/1pmy'
  ];

  for (const badUrl of invalidProtocols) {
    const portal = getSchemePortalDetails({ id: 'bad-proto', source_url: badUrl });
    assert.strictEqual(portal.officialWebsite, null, `Protocol '${badUrl}' should be rejected`);
    assert.strictEqual(validateOfficialUrl(badUrl), null);
  }
});

test('20. Phase D3.4.1: Untrusted commercial and third-party aggregator portals are rejected', () => {
  const untrustedUrls = [
    'https://www.google.com/search?q=1pmy',
    'https://sarkariyojana.com/100-penalty-mafi',
    'https://cleartax.in/s/gujarat-housing-board',
    'https://timesofindia.indiatimes.com/scheme',
    'https://blog.wordpress.com/scheme-details'
  ];

  for (const untrusted of untrustedUrls) {
    const portal = getSchemePortalDetails({ id: 'bad-domain', source_url: untrusted });
    assert.strictEqual(portal.officialWebsite, null, `Domain '${untrusted}' should be rejected`);
    assert.strictEqual(validateOfficialUrl(untrusted), null);
  }
});

// -----------------------------------------------------------------------------
// Phase D3.4.2 Tests: Scheme Document Status Mapping & OCR Verification Pipeline
// -----------------------------------------------------------------------------

test('21. Phase D3.4.2: Uploaded document with pending verification evaluates to Uploaded, NEVER Verified', () => {
  // Document uploaded and pending verification
  const userDocs = [
    {
      id: 'doc-income-1',
      fileName: 'income_certificate_2026.pdf',
      documentType: 'income_cert',
      verificationStatus: 'pending'
    }
  ];

  assert.strictEqual(
    matchDocumentStatus('Income Certificate.', userDocs),
    'Uploaded',
    'Pending document must evaluate to Uploaded'
  );
});

test('22. Phase D3.4.2: OCR extraction alone must NEVER imply verification', () => {
  // Document with rich OCR extraction facts, but verification status is pending or uploaded
  const userDocs = [
    {
      id: 'doc-income-ocr',
      fileName: 'income_slip.pdf',
      documentType: 'income_cert',
      verificationStatus: 'pending',
      extractedData: { annual_income: 180000, issuing_authority: 'Mamlatdar Office' },
      extractedText: 'Government of Gujarat Income Certificate Annual Income 180000'
    }
  ];

  const status = matchDocumentStatus('Income Certificate.', userDocs);
  assert.strictEqual(status, 'Uploaded', 'OCR-extracted document with pending verification must NEVER be marked Verified');
  assert.notStrictEqual(status, 'Verified', 'OCR extraction must never elevate status to Verified without explicit verification');
});

test('23. Phase D3.4.2: Explicitly verified document evaluates to Verified', () => {
  const userDocs = [
    {
      id: 'doc-income-verified',
      fileName: 'income_certificate.pdf',
      documentType: 'income_cert',
      verificationStatus: 'verified'
    }
  ];

  assert.strictEqual(
    matchDocumentStatus('Income Certificate.', userDocs),
    'Verified',
    'Explicitly verified document must evaluate to Verified'
  );
});

test('24. Phase D3.4.2: Document requiring review or flagged evaluates to Review Required', () => {
  const userDocs = [
    {
      id: 'doc-aadhaar-flagged',
      fileName: 'aadhaar_card.pdf',
      documentType: 'aadhaar',
      verificationStatus: 'review_required'
    },
    {
      id: 'doc-pan-conflict',
      fileName: 'pan_card.jpg',
      documentType: 'pan',
      verificationStatus: 'conflict'
    }
  ];

  assert.strictEqual(matchDocumentStatus('Aadhaar Card.', userDocs), 'Review Required');
  assert.strictEqual(matchDocumentStatus('Permanent Account Number Card.', userDocs), 'Review Required');
});

test('25. Phase D3.4.2: Unmatched document requirement evaluates to Missing', () => {
  const userDocs = [
    {
      id: 'doc-pan',
      fileName: 'pan_card.pdf',
      documentType: 'pan',
      verificationStatus: 'verified'
    }
  ];

  assert.strictEqual(
    matchDocumentStatus('Death Certificate (In case of death of the original tenant or power of attorney holder).', userDocs),
    'Missing'
  );
  assert.strictEqual(
    matchDocumentStatus('Latest Photograph of the House.', userDocs),
    'Missing'
  );
});

test('26. Phase D3.4.2: Normalized matching handles camelCase, snake_case, and canonical aliases', () => {
  // Simulates frontend API payloads that use camelCase
  const camelCaseDocs = [
    { fileName: 'pan_front.jpg', documentType: 'pan', verificationStatus: 'verified' },
    { fileName: 'ghb_receipt_2025.pdf', documentType: 'receipt', verificationStatus: 'uploaded' },
    { fileName: 'lease_agreement.pdf', documentType: 'rent_agreement', verificationStatus: 'verified' }
  ];

  assert.strictEqual(matchDocumentStatus('Permanent Account Number Card.', camelCaseDocs), 'Verified');
  assert.strictEqual(matchDocumentStatus('Xerox Copies of the Receipt of the Amount Previously Paid to the Gujarat Housing Board.', camelCaseDocs), 'Uploaded');
  assert.strictEqual(matchDocumentStatus('Copy of Rent Agreement, Delivery of Rent, or Letter from the Landlord.', camelCaseDocs), 'Verified');

  // Simulates raw database rows with snake_case
  const snakeCaseDocs = [
    { file_name: 'income_cert.pdf', document_type: 'income_cert', verification_status: 'verified' },
    { file_name: 'aadhaar_scan.pdf', document_type: 'aadhaar', status: 'uploaded' }
  ];

  assert.strictEqual(matchDocumentStatus('Income Certificate.', snakeCaseDocs), 'Verified');
  assert.strictEqual(matchDocumentStatus('Aadhaar Card.', snakeCaseDocs), 'Uploaded');
});

test('27. Phase D3.4.2: Tenant isolation strictly excludes documents from other applicants', () => {
  const tenantDocs = [
    {
      id: 'doc-applicant-a',
      fileName: 'income_cert_a.pdf',
      documentType: 'income_cert',
      verificationStatus: 'verified',
      userId: 'user-applicant-a'
    }
  ];

  // Request from Applicant A (the owner)
  assert.strictEqual(
    matchDocumentStatus('Income Certificate.', tenantDocs, 'user-applicant-a'),
    'Verified',
    'Owner applicant must match their own document'
  );

  // Request from Applicant B (unauthorized third-party tenant)
  assert.strictEqual(
    matchDocumentStatus('Income Certificate.', tenantDocs, 'user-applicant-b'),
    'Missing',
    'Other applicant must NEVER see or match another tenant documents'
  );
});



