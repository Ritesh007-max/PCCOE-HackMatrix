import test from 'node:test';
import assert from 'node:assert/strict';

import {
  compileDossierPdfBytes,
} from '../src/utils/dossierPdfGenerator.js';

import {
  normalizeDocRequirementId,
  buildDynamicSchemeChecklist,
  SCHEMES_CHECKLIST,
} from '../src/data/documentsData.js';

import {
  matchDocumentStatus,
} from '../src/utils/schemeDetailsHelpers.js';

import {
  clearCachedUserData,
} from '../src/services/authService.js';

test('FIN Phase D4.2: My Documents Integrity Test Suite', async (t) => {

  await t.test('1. Dossier PDF Generator: produces valid PDF-1.4 stream and rejects empty documents', () => {
    // Empty list throws clear error
    assert.throws(
      () => compileDossierPdfBytes([], { fullName: 'Test User' }),
      /No documents available in vault/
    );

    const testDocs = [
      {
        id: 'doc-1',
        name: 'Aadhaar Card',
        documentType: 'aadhaar',
        docNumber: 'XXXX-XXXX-1234',
        status: 'verified',
        issuer: 'UIDAI',
        category: 'Identity Proof',
        uploadedOn: '04 Oct 2026',
      },
      {
        id: 'doc-2',
        name: 'Income Certificate',
        documentType: 'income_cert',
        docNumber: 'INC/2026/9876',
        status: 'under_review',
        issuer: 'Revenue Department',
        category: 'Income Proof',
        uploadedOn: '04 Oct 2026',
      },
    ];

    const pdfBytes = compileDossierPdfBytes(testDocs, {
      fullName: 'Dhruv Ojha',
      id: 'usr-4412',
      state: 'Gujarat',
      district: 'Ahmedabad',
    });

    assert.ok(pdfBytes.startsWith('%PDF-1.4'), 'Must start with PDF-1.4 header');
    assert.ok(pdfBytes.endsWith('%%EOF'), 'Must end with EOF marker');
    assert.ok(pdfBytes.includes('Dhruv Ojha'), 'Must contain applicant name');
    assert.ok(pdfBytes.includes('Aadhaar Card'), 'Must include document 1 name');
    assert.ok(pdfBytes.includes('Income Certificate'), 'Must include document 2 name');
    assert.ok(pdfBytes.includes('VERIFIED'), 'Must display verified status');
    assert.ok(pdfBytes.includes('PENDING STATUTORY VERIFICATION'), 'Must display pending verification status');
    assert.ok(!pdfBytes.includes('QR Official Certification Code'), 'Must NOT make fake QR claims');
  });

  await t.test('2. Requirement Identifier Normalization: correctly normalizes aliases to canonical types', () => {
    assert.strictEqual(normalizeDocRequirementId('caste'), 'caste_cert');
    assert.strictEqual(normalizeDocRequirementId('caste_certificate'), 'caste_cert');
    assert.strictEqual(normalizeDocRequirementId('jati'), 'caste_cert');

    assert.strictEqual(normalizeDocRequirementId('address'), 'address_proof');
    assert.strictEqual(normalizeDocRequirementId('address_proof'), 'address_proof');
    assert.strictEqual(normalizeDocRequirementId('residence_proof'), 'address_proof');

    assert.strictEqual(normalizeDocRequirementId('bank'), 'bank_passbook');
    assert.strictEqual(normalizeDocRequirementId('bank_passbook'), 'bank_passbook');
    assert.strictEqual(normalizeDocRequirementId('passbook'), 'bank_passbook');

    assert.strictEqual(normalizeDocRequirementId('income'), 'income_cert');
    assert.strictEqual(normalizeDocRequirementId('income_certificate'), 'income_cert');
    assert.strictEqual(normalizeDocRequirementId('aavak_pramanpatra'), 'income_cert');

    assert.strictEqual(normalizeDocRequirementId('aadhaar'), 'aadhaar');
    assert.strictEqual(normalizeDocRequirementId('aadhar'), 'aadhaar');
    assert.strictEqual(normalizeDocRequirementId('uidai'), 'aadhaar');

    assert.strictEqual(normalizeDocRequirementId('pan'), 'pan');
    assert.strictEqual(normalizeDocRequirementId('land'), 'land');
    assert.strictEqual(normalizeDocRequirementId('domicile'), 'domicile');
  });

  await t.test('3. Dynamic Scheme Readiness Checker: parses canonical catalog schemes dynamically', () => {
    const canonicalSchemes = [
      {
        id: 'sch-pmegp',
        name: 'Prime Minister Employment Generation Programme',
        documents_required: ['Aadhaar Card', 'Caste Certificate', 'Bank Passbook', 'Project Report'],
        benefit_summary: 'Up to 35% Margin Money Subsidy',
      },
      {
        id: 'sch-pmkisan',
        name: 'PM Kisan Samman Nidhi',
        documents_required: ['Aadhaar Card', 'Bank Passbook', 'Land Record (7/12)'],
        max_benefit: 6000,
      },
    ];

    const dynamicChecklist = buildDynamicSchemeChecklist(canonicalSchemes);

    assert.strictEqual(dynamicChecklist.length, 2);
    assert.strictEqual(dynamicChecklist[0].id, 'sch-pmegp');
    assert.strictEqual(dynamicChecklist[0].name, 'Prime Minister Employment Generation Programme');
    assert.strictEqual(dynamicChecklist[0].requiredDocIds.length, 4);

    // Verify requirement normalization in dynamic list
    const pmegpDocIds = dynamicChecklist[0].requiredDocIds.map((d) => d.id);
    assert.ok(pmegpDocIds.includes('aadhaar'));
    assert.ok(pmegpDocIds.includes('caste_cert'));
    assert.ok(pmegpDocIds.includes('bank_passbook'));

    // Empty list falls back gracefully to baseline checklist
    const fallbackList = buildDynamicSchemeChecklist([]);
    assert.strictEqual(fallbackList, SCHEMES_CHECKLIST);
  });

  await t.test('4. Truthful Verification States: OCR extraction does NOT count as Verified', () => {
    const ocrExtractedUserDocs = [
      {
        documentType: 'income_cert',
        fileName: 'income_2026.pdf',
        verificationStatus: 'PENDING',
        status: 'under_review',
        extractedData: {
          annual_income: '180000',
          beneficiary_name: 'Applicant Name',
        },
      },
      {
        documentType: 'aadhaar',
        fileName: 'aadhaar.pdf',
        verificationStatus: 'VERIFIED',
        status: 'verified',
        extractedData: {
          aadhaar_last4: '9988',
        },
      },
    ];

    // Aadhaar is verified in backend -> Verified
    assert.strictEqual(matchDocumentStatus('Aadhaar Card', ocrExtractedUserDocs), 'Verified');

    // Income is extracted via OCR but pending verification -> Uploaded (NOT Verified)
    const incomeStatus = matchDocumentStatus('Income Certificate', ocrExtractedUserDocs);
    assert.strictEqual(incomeStatus, 'Uploaded');
    assert.notStrictEqual(incomeStatus, 'Verified', 'OCR extracted document must not be marked Verified prematurely');

    // Caste is missing
    assert.strictEqual(matchDocumentStatus('Caste Certificate', ocrExtractedUserDocs), 'Missing');
  });

  await t.test('5. User Isolation & Cache Cleanup: invalidates cached data on logout or session reset', () => {
    // Setup mock localStorage in Node test environment
    const mockStorage = new Map();
    globalThis.localStorage = {
      getItem: (k) => mockStorage.get(k) || null,
      setItem: (k, v) => mockStorage.set(k, String(v)),
      removeItem: (k) => mockStorage.delete(k),
      get length() { return mockStorage.size; },
      key: (i) => Array.from(mockStorage.keys())[i] || null,
      clear: () => mockStorage.clear(),
    };

    // Populate user-namespaced keys
    mockStorage.set('fin_user', JSON.stringify({ id: 'user_123' }));
    mockStorage.set('fin_documents_data_user_123', JSON.stringify([{ id: 'd1' }]));
    mockStorage.set('fin_associated_applications_data_user_123', JSON.stringify([{ id: 'app1' }]));
    mockStorage.set('fin_support_tickets_data_user_123', JSON.stringify([{ id: 'tkt1' }]));
    mockStorage.set('unrelated_key', 'keep_me');

    clearCachedUserData();

    // User-namespaced cache keys must be purged
    assert.strictEqual(mockStorage.has('fin_documents_data_user_123'), false);
    assert.strictEqual(mockStorage.has('fin_associated_applications_data_user_123'), false);
    assert.strictEqual(mockStorage.has('fin_support_tickets_data_user_123'), false);
    assert.strictEqual(mockStorage.has('unrelated_key'), true);
  });
});
