import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  isValidSchemeIdentifier,
  extractCanonicalSchemeId,
  getSchemeDocumentsUrl,
  navigateToSchemeDocuments,
} from '../src/utils/schemeNavigation.js';

import {
  evaluateRequirementStatus,
  evaluateSchemeReadiness,
  deriveDynamicSchemeChecklist,
  filterApplicantRelevantSchemes,
  isCentralScheme,
} from '../src/utils/documentSchemeValidation.js';

import {
  buildDynamicSchemeChecklist,
  normalizeDocRequirementId,
} from '../src/data/documentsData.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Scheme to Document Readiness Direct Navigation Suite', async (t) => {
  // -------------------------------------------------------------------------
  // 1 & 2: REUSABLE NAVIGATION HELPER & URL STRUCTURE
  // -------------------------------------------------------------------------
  await t.test('1. Navigation helper validates canonical scheme identifiers', () => {
    assert.strictEqual(isValidSchemeIdentifier('1pmy'), true);
    assert.strictEqual(isValidSchemeIdentifier('c17d0324-7f1f-5cf3-9b0e-3219cb9222fc'), true);
    assert.strictEqual(isValidSchemeIdentifier('pm-kisan'), true);
    assert.strictEqual(isValidSchemeIdentifier(''), false);
    assert.strictEqual(isValidSchemeIdentifier(null), false);
    assert.strictEqual(isValidSchemeIdentifier(undefined), false);
    assert.strictEqual(isValidSchemeIdentifier('   '), false);
    assert.strictEqual(isValidSchemeIdentifier('auto'), false);
  });

  await t.test('2. extractCanonicalSchemeId extracts slug or ID dynamically from object or string', () => {
    assert.strictEqual(extractCanonicalSchemeId('1pmy'), '1pmy');
    assert.strictEqual(extractCanonicalSchemeId({ slug: '1pmy', id: 'uuid-123' }), '1pmy');
    assert.strictEqual(extractCanonicalSchemeId({ id: 'uuid-123' }), 'uuid-123');
    assert.strictEqual(extractCanonicalSchemeId({ scheme_slug: 'pm-kisan' }), 'pm-kisan');
    assert.strictEqual(extractCanonicalSchemeId({ scheme_id: 'uuid-456' }), 'uuid-456');
    assert.strictEqual(extractCanonicalSchemeId(null), '');
  });

  await t.test('3. getSchemeDocumentsUrl creates stable deep-link URL with canonical schemeId', () => {
    assert.strictEqual(getSchemeDocumentsUrl('1pmy'), '/documents?schemeId=1pmy');
    assert.strictEqual(getSchemeDocumentsUrl('pm-kisan'), '/documents?schemeId=pm-kisan');
    assert.strictEqual(
      getSchemeDocumentsUrl({ id: 'uuid-test-99' }),
      '/documents?schemeId=uuid-test-99'
    );
    assert.strictEqual(getSchemeDocumentsUrl(''), '/documents');
    assert.strictEqual(getSchemeDocumentsUrl(null), '/documents');
  });

  await t.test('4. navigateToSchemeDocuments invokes router navigate with URL and options', () => {
    let capturedUrl = null;
    let capturedOpts = null;
    const mockNavigate = (url, opts) => {
      capturedUrl = url;
      capturedOpts = opts;
    };

    navigateToSchemeDocuments(mockNavigate, '1pmy');
    assert.strictEqual(capturedUrl, '/documents?schemeId=1pmy');

    navigateToSchemeDocuments(mockNavigate, { slug: 'csmsu' }, { replace: true });
    assert.strictEqual(capturedUrl, '/documents?schemeId=csmsu');
    assert.deepStrictEqual(capturedOpts, { replace: true });
  });

  // -------------------------------------------------------------------------
  // 5 & 6: SCHEME DETAILS ACTION INTEGRATION
  // -------------------------------------------------------------------------
  await t.test('5. SchemeDetailsPage contains Check Required Documents action button', () => {
    const detailsPath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(detailsPath, 'utf8');

    assert.ok(
      content.includes('handleCheckDocumentsClick'),
      'SchemeDetailsPage must declare handleCheckDocumentsClick handler'
    );
    assert.ok(
      content.includes('btn-check-docs-main'),
      'SchemeDetailsPage must render .btn-check-docs-main button'
    );
    assert.ok(
      content.includes('Check Required Documents'),
      'Button text must include Check Required Documents'
    );
    assert.ok(
      content.includes('navigateToSchemeDocuments'),
      'SchemeDetailsPage must call navigateToSchemeDocuments'
    );
  });

  await t.test('6. SchemeDetailsPage Documents tab panel contains direct readiness link', () => {
    const detailsPath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(detailsPath, 'utf8');

    assert.ok(
      content.includes('btn-check-docs-secondary'),
      'Documents tab must render secondary check readiness action'
    );
    assert.ok(
      content.includes('Check Readiness in My Documents'),
      'Must contain explicit label Check Readiness in My Documents'
    );
  });

  // -------------------------------------------------------------------------
  // 7, 8, 9, 10: DOCUMENTS PAGE DEEP LINK & READINESS CALCULATION
  // -------------------------------------------------------------------------
  await t.test('7. DocumentsPage reads schemeId from URL search params on mount', () => {
    const docsPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const content = fs.readFileSync(docsPath, 'utf8');

    assert.ok(content.includes('useSearchParams'), 'DocumentsPage must use useSearchParams');
    assert.ok(content.includes("searchParams.get('schemeId')"), 'DocumentsPage must read schemeId query param');
    assert.ok(content.includes('ref={checkerCardRef}'), 'DocumentsPage must bind checkerCardRef');
    assert.ok(content.includes('id="scheme-readiness-checker"'), 'Must have accessible id="scheme-readiness-checker"');
  });

  await t.test('8. Automatic scheme selection loads real canonical document requirements', () => {
    const canonicalSchemes = [
      {
        id: '1pmy',
        slug: '1pmy',
        name: '100% Penalty Mafi Yojana',
        state: 'Gujarat',
        documents_required: ['Electricity Bill', 'Aadhaar Card', 'Property Document'],
      },
      {
        id: 'pm-kisan',
        slug: 'pm-kisan',
        name: 'Pradhan Mantri Kisan Samman Nidhi',
        state: 'All India',
        documents_required: ['Land Ownership Document', 'Aadhaar Card', 'Bank Passbook'],
      }
    ];

    const checklist = deriveDynamicSchemeChecklist(canonicalSchemes);
    assert.strictEqual(checklist.length, 2);

    const selected = checklist.find((s) => s.id === '1pmy' || s.slug === '1pmy');
    assert.ok(selected, '100% Penalty Mafi Yojana must be resolved from checklist');
    assert.strictEqual(selected.name, '100% Penalty Mafi Yojana');
    assert.strictEqual(selected.requiredDocIds.length, 3);
    assert.deepStrictEqual(
      selected.requiredDocIds.map((r) => r.label),
      ['Electricity Bill', 'Aadhaar Card', 'Property Document']
    );
  });

  await t.test('9. Readiness calculation evaluates against real user documents with OCR != Verified', () => {
    const scheme = {
      id: '1pmy',
      name: '100% Penalty Mafi Yojana',
      state: 'Gujarat',
      documents_required: ['Income Certificate', 'Aadhaar Card', 'Electricity Bill'],
    };

    const userDocs = [
      // 1. Verified Aadhaar
      {
        id: 'doc_1',
        documentType: 'aadhaar',
        verificationStatus: 'VERIFIED',
        extractedData: { id_number: 'XXXX-XXXX-1234' },
      },
      // 2. Uploaded Income Certificate (OCR extracted but NOT verified)
      {
        id: 'doc_2',
        documentType: 'income_cert',
        verificationStatus: 'UNDER_REVIEW',
        extractedData: { annual_income: 180000 }, // Fact extracted via OCR
      },
      // 3. Electricity Bill is missing from vault
    ];

    const evaluation = evaluateSchemeReadiness(scheme, userDocs);
    assert.strictEqual(evaluation.schemeId, '1pmy');
    assert.strictEqual(evaluation.totalCount, 3);
    assert.strictEqual(evaluation.verifiedCount, 1, 'Only Aadhaar should be verified');
    assert.strictEqual(evaluation.pendingCount, 1, 'Income certificate should be pending');
    assert.strictEqual(evaluation.missingCount, 1, 'Electricity bill should be missing');
    assert.strictEqual(evaluation.isFullyReady, false);

    // Verify individual requirement status objects
    const aadhaarReq = evaluation.requirements.find((r) => r.id === 'aadhaar');
    assert.strictEqual(aadhaarReq.status, 'Verified');
    assert.strictEqual(aadhaarReq.isVerified, true);

    const incomeReq = evaluation.requirements.find((r) => r.id === 'income_cert');
    assert.strictEqual(incomeReq.status, 'Pending Verification');
    assert.strictEqual(incomeReq.isVerified, false, 'OCR extracted fact must NOT be marked Verified');
    assert.strictEqual(incomeReq.isPending, true);

    const billReq = evaluation.requirements.find((r) => r.id === 'electricity_bill');
    assert.strictEqual(billReq.status, 'Missing');
    assert.strictEqual(billReq.isMissing, true);
  });

  // -------------------------------------------------------------------------
  // 10 & 11: USER/TENANT ISOLATION
  // -------------------------------------------------------------------------
  await t.test('10. Tenant isolation: cannot access another user documents via schemeId URL', () => {
    const reqItem = { id: 'caste_cert', label: 'Caste Certificate' };
    const otherUserDocs = [
      {
        id: 'doc_other_1',
        documentType: 'caste_cert',
        verificationStatus: 'VERIFIED',
        userId: 'attacker_user_999',
      }
    ];

    // Current logged-in user is 'genuine_user_123'
    const statusResult = evaluateRequirementStatus(reqItem, otherUserDocs, 'genuine_user_123');
    assert.strictEqual(
      statusResult.status,
      'Missing',
      'Documents belonging to another tenant/user must be strictly ignored'
    );
    assert.strictEqual(statusResult.isVerified, false);
    assert.strictEqual(statusResult.matchedDoc, null);
  });

  // -------------------------------------------------------------------------
  // 12 & 13: INVALID SCHEME ID & INAPPLICABLE SCHEME
  // -------------------------------------------------------------------------
  await t.test('11. Missing schemeId yields clean neutral unselected state', () => {
    const readiness = evaluateSchemeReadiness(null, []);
    assert.strictEqual(readiness.schemeId, null);
    assert.strictEqual(readiness.status, 'NO_SCHEME_SELECTED');
    assert.strictEqual(readiness.canApply, false);
    assert.strictEqual(readiness.neutralMessage, 'Select a scheme to check document readiness.');
  });

  await t.test('12. DocumentsPage renders honest not-found state when schemeId is invalid', () => {
    const docsPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const content = fs.readFileSync(docsPath, 'utf8');

    assert.ok(
      content.includes('checker-not-found-state'),
      'Must contain checker-not-found-state styling for invalid scheme IDs'
    );
    assert.ok(
      content.includes('Scheme could not be found.'),
      'Must render honest "Scheme could not be found." notice'
    );
  });

  await t.test('13. Inapplicable scheme (e.g. other-state) is displayed honestly without silent substitution', () => {
    const haryanaScheme = {
      id: 'haryana-welfare',
      name: 'Haryana State Welfare Scheme',
      state: 'Haryana',
      documents_required: ['Residence Certificate', 'Income Certificate'],
    };

    // Evaluate for Gujarat applicant
    const isCentral = isCentralScheme(haryanaScheme);
    assert.strictEqual(isCentral, false, 'Haryana scheme is not central');

    const checklist = deriveDynamicSchemeChecklist([haryanaScheme]);
    assert.strictEqual(checklist.length, 1);
    assert.strictEqual(checklist[0].name, 'Haryana State Welfare Scheme');
    assert.strictEqual(checklist[0].state, 'Haryana');

    // Requirements are evaluated faithfully for this scheme without replacing with a Gujarat scheme
    const evaluation = evaluateSchemeReadiness(checklist[0], []);
    assert.strictEqual(evaluation.schemeId, 'haryana-welfare');
    assert.strictEqual(evaluation.totalCount, 2);
  });

  // -------------------------------------------------------------------------
  // 14 & 15: MANUAL SCHEME CHANGE & HISTORY PRESERVATION
  // -------------------------------------------------------------------------
  await t.test('14. DocumentsPage updates URL search params using replace: true on scheme change', () => {
    const docsPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const content = fs.readFileSync(docsPath, 'utf8');

    assert.ok(
      content.includes('setSearchParams({ schemeId: cleanId }, { replace: true })'),
      'Must update search params with replace: true to preserve browser history'
    );
    assert.ok(
      content.includes('setSearchParams({}, { replace: true })'),
      'Must clear search params with replace: true on clear'
    );
  });

  // -------------------------------------------------------------------------
  // 16 & 17: ZERO PRODUCTION HARDCODING IN NAVIGATION
  // -------------------------------------------------------------------------
  await t.test('15. Zero production hardcoding in schemeNavigation.js helper', () => {
    const navPath = path.join(__dirname, '..', 'src', 'utils', 'schemeNavigation.js');
    const content = fs.readFileSync(navPath, 'utf8');

    assert.ok(!content.includes('100% Penalty Mafi Yojana'), 'Must not hardcode scheme names');
    assert.ok(!content.includes('1pmy'), 'Must not hardcode scheme IDs');
    assert.ok(!content.includes('pm-kisan'), 'Must not hardcode scheme IDs');
    assert.ok(!content.includes('Aadhaar Card'), 'Must not hardcode document names');
  });

  await t.test('16. SuggestedSchemesPage integrates navigateToSchemeDocuments in modal', () => {
    const suggestedPath = path.join(__dirname, '..', 'src', 'pages', 'SuggestedSchemesPage.jsx');
    const content = fs.readFileSync(suggestedPath, 'utf8');

    assert.ok(
      content.includes('navigateToSchemeDocuments(navigate, targetId)'),
      'SuggestedSchemesPage modal must use navigateToSchemeDocuments'
    );
    assert.ok(
      content.includes('Check Documents & Apply'),
      'Modal button should clarify document checking'
    );
  });
});
