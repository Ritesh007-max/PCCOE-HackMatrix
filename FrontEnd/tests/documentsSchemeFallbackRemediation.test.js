import test from 'node:test';
import assert from 'node:assert/strict';

import {
  filterActiveSchemesForCatalog,
  deriveDynamicSchemeChecklist,
  validateSchemeSelection,
  resolveCanonicalSchemeDetails,
} from '../src/utils/documentSchemeValidation.js';

import {
  normalizeDocRequirementId,
  buildDynamicSchemeChecklist,
  SCHEMES_CHECKLIST,
} from '../src/data/documentsData.js';

import {
  compileDossierPdfBytes,
} from '../src/utils/dossierPdfGenerator.js';

test('FIN Remediation 2: Remove Hardcoded Scheme Fallbacks from Documents Page', async (t) => {

  await t.test('1. Canonical scheme records load and appear correctly', async () => {
    const apiResponse = {
      success: true,
      count: 3,
      schemes: [
        {
          id: 'sch-pm-kisan',
          name: 'PM Kisan Samman Nidhi',
          department: 'Ministry of Agriculture and Farmers Welfare',
          max_benefit: 6000,
          benefit_summary: '₹ 6,000 per year direct income support',
          documents_required: ['Aadhaar Card', 'Land Ownership Record (7/12)', 'Bank Passbook'],
        },
        {
          id: 'sch-pmay-g',
          name: 'Pradhan Mantri Awaas Yojana - Gramin',
          department: 'Ministry of Rural Development',
          max_benefit: 120000,
          benefit_summary: 'Financial assistance of ₹1,20,000 in plains',
          documents_required: ['Aadhaar Card', 'Bank Passbook', 'MGNREGA Job Card'],
        },
        {
          id: 'sch-yipb',
          name: 'Young Investigators Programme in Biotechnology',
          department: 'Department of Biotechnology',
          max_benefit: null,
          benefit_summary: '₹75,000 / month stipend + research grant',
          documents_required: ['PhD Degree Certificate', 'Research Proposal', 'CV'],
        },
      ]
    };

    const loadedSchemes = filterActiveSchemesForCatalog(apiResponse);
    assert.strictEqual(loadedSchemes.length, 3, 'Must retain all valid canonical schemes');
    assert.strictEqual(loadedSchemes[0].id, 'sch-pm-kisan');
    assert.strictEqual(loadedSchemes[1].id, 'sch-pmay-g');
    assert.strictEqual(loadedSchemes[2].id, 'sch-yipb');

    // Checklist derived from canonical schemes
    const dynamicChecklist = deriveDynamicSchemeChecklist(loadedSchemes);
    assert.strictEqual(dynamicChecklist.length, 3);
    assert.strictEqual(dynamicChecklist[0].name, 'PM Kisan Samman Nidhi');
    assert.strictEqual(dynamicChecklist[0].requiredDocIds.length, 3);
    assert.ok(dynamicChecklist[0].requiredDocIds.some(d => d.id === 'aadhaar'));
    assert.ok(dynamicChecklist[0].requiredDocIds.some(d => d.id === 'land'));
    assert.ok(dynamicChecklist[0].requiredDocIds.some(d => d.id === 'bank_passbook'));
  });

  await t.test('2. No hardcoded PMEGP/MUDRA fallback is used when API returns an empty list', () => {
    // When API returns empty schemes array
    const emptyApiResponse = { success: true, count: 0, schemes: [] };
    const loadedSchemes = filterActiveSchemesForCatalog(emptyApiResponse);
    assert.deepStrictEqual(loadedSchemes, [], 'Must return strictly empty array');

    // Dynamic checklist must NOT fall back to fabricated SCHEMES_CHECKLIST
    const dynamicChecklist = deriveDynamicSchemeChecklist(loadedSchemes);
    assert.deepStrictEqual(dynamicChecklist, [], 'Checklist must be empty when catalog is empty');
    assert.notStrictEqual(dynamicChecklist, SCHEMES_CHECKLIST, 'Must not return hardcoded fallback checklist');
  });

  await t.test('3. API failure does not trigger fabricated scheme options', () => {
    // Null, undefined, malformed or error responses
    assert.deepStrictEqual(filterActiveSchemesForCatalog(null), []);
    assert.deepStrictEqual(filterActiveSchemesForCatalog(undefined), []);
    assert.deepStrictEqual(filterActiveSchemesForCatalog({ error: 'Gateway Timeout' }), []);
    assert.deepStrictEqual(filterActiveSchemesForCatalog('Server Error 500'), []);

    // Empty list produces empty dynamic checklist
    const checklistAfterFailure = deriveDynamicSchemeChecklist([]);
    assert.deepStrictEqual(checklistAfterFailure, []);

    // Submission guard halts submission when catalog is empty due to API failure
    const validation = validateSchemeSelection('pmegp', []);
    assert.strictEqual(validation.valid, false);
    assert.strictEqual(validation.error, 'CATALOG_UNAVAILABLE');
    assert.ok(validation.message.includes('unavailable'), 'Should report catalog is unavailable');
  });

  await t.test('4. Submission is blocked when no scheme is selected', () => {
    const catalog = [
      { id: 'sch-pm-kisan', name: 'PM Kisan Samman Nidhi' },
      { id: 'sch-pmay', name: 'Pradhan Mantri Awaas Yojana' },
    ];

    // Empty string
    const resEmpty = validateSchemeSelection('', catalog);
    assert.strictEqual(resEmpty.valid, false);
    assert.strictEqual(resEmpty.error, 'NO_SCHEME_SELECTED');

    // Undefined / null
    const resNull = validateSchemeSelection(null, catalog);
    assert.strictEqual(resNull.valid, false);
    assert.strictEqual(resNull.error, 'NO_SCHEME_SELECTED');

    // Whitespace only
    const resWhitespace = validateSchemeSelection('   ', catalog);
    assert.strictEqual(resWhitespace.valid, false);
    assert.strictEqual(resWhitespace.error, 'NO_SCHEME_SELECTED');

    // Auto sentinel
    const resAuto = validateSchemeSelection('auto', catalog);
    assert.strictEqual(resAuto.valid, false);
    assert.strictEqual(resAuto.error, 'NO_SCHEME_SELECTED');
  });

  await t.test('5. Submission is blocked for an invalid or stale scheme ID', () => {
    const canonicalCatalog = [
      { id: 'sch-pm-kisan', scheme_id: 'sch-pm-kisan', name: 'PM Kisan Samman Nidhi' },
      { id: 'sch-ayushman', scheme_id: 'sch-ayushman', name: 'Ayushman Bharat PM-JAY' },
    ];

    // Attempting to submit fabricated PMEGP or MUDRA when not in catalog
    const resPmegp = validateSchemeSelection('pmegp', canonicalCatalog);
    assert.strictEqual(resPmegp.valid, false);
    assert.strictEqual(resPmegp.error, 'INVALID_OR_STALE_SCHEME');
    assert.ok(resPmegp.message.includes('invalid, outdated, or not found'));

    const resMudra = validateSchemeSelection('mudra-loan', canonicalCatalog);
    assert.strictEqual(resMudra.valid, false);
    assert.strictEqual(resMudra.error, 'INVALID_OR_STALE_SCHEME');

    // Random non-existent ID
    const resBogus = validateSchemeSelection('fake-scheme-999', canonicalCatalog);
    assert.strictEqual(resBogus.valid, false);
    assert.strictEqual(resBogus.error, 'INVALID_OR_STALE_SCHEME');
  });

  await t.test('6. Valid canonical scheme selection can proceed through the existing submission flow', async () => {
    const canonicalCatalog = [
      {
        id: 'sch-pm-kisan',
        name: 'PM Kisan Samman Nidhi',
        department: 'Ministry of Agriculture and Farmers Welfare',
        max_benefit: 6000,
        benefit_summary: 'Direct income support of ₹6,000 per year',
        eligibility_summary: 'All landholding farmer families in India',
      },
      {
        id: 'sch-standup-india',
        name: 'Stand-Up India Scheme',
        department: 'Department of Financial Services',
        max_benefit: 10000000,
        benefit_summary: 'Bank loans between ₹10 lakh and ₹1 crore',
      }
    ];

    // Validation passes for authentic scheme in catalog
    const validation = validateSchemeSelection('sch-pm-kisan', canonicalCatalog);
    assert.strictEqual(validation.valid, true);
    assert.ok(validation.matchingScheme);
    assert.strictEqual(validation.matchingScheme.id, 'sch-pm-kisan');

    // Scheme details resolved authentically
    const mockFetchSchemeById = async (id) => {
      assert.strictEqual(id, 'sch-pm-kisan');
      return {
        id: 'sch-pm-kisan',
        scheme_name: 'PM Kisan Samman Nidhi',
        department: 'Ministry of Agriculture and Farmers Welfare',
        max_benefit: 6000,
        benefit_summary: 'Direct income support of ₹6,000 per year',
        eligibility_summary: 'All landholding farmer families in India',
      };
    };

    const targetScheme = await resolveCanonicalSchemeDetails(validation.matchingScheme, mockFetchSchemeById);
    assert.ok(targetScheme);
    assert.strictEqual(targetScheme.id, 'sch-pm-kisan');
    assert.strictEqual(targetScheme.name, 'PM Kisan Samman Nidhi');
    assert.strictEqual(targetScheme.ministry, 'Ministry of Agriculture and Farmers Welfare');
    assert.strictEqual(targetScheme.max_benefit, 6000);
    assert.strictEqual(targetScheme.benefit, 'Direct income support of ₹6,000 per year');

    // Network lookup fallback gracefully uses catalog record without fabricating
    const targetSchemeNetworkFail = await resolveCanonicalSchemeDetails(validation.matchingScheme, async () => {
      throw new Error('Network error');
    });
    assert.ok(targetSchemeNetworkFail);
    assert.strictEqual(targetSchemeNetworkFail.id, 'sch-pm-kisan');
    assert.strictEqual(targetSchemeNetworkFail.max_benefit, 6000);
  });

  await t.test('7. Existing document functionality is not broken', () => {
    // Normalization works for statutory vault documents
    assert.strictEqual(normalizeDocRequirementId('aadhaar'), 'aadhaar');
    assert.strictEqual(normalizeDocRequirementId('caste_certificate'), 'caste_cert');
    assert.strictEqual(normalizeDocRequirementId('bank_passbook'), 'bank_passbook');
    assert.strictEqual(normalizeDocRequirementId('income_cert'), 'income_cert');
    assert.strictEqual(normalizeDocRequirementId('land_record'), 'land');

    // PDF Dossier compilation operates without failure
    const testDocs = [
      {
        id: 'doc-vault-1',
        name: 'Aadhaar Card',
        documentType: 'aadhaar',
        docNumber: 'XXXX-XXXX-9012',
        status: 'verified',
        issuer: 'UIDAI',
        category: 'Identity Proof',
        uploadedOn: '04 Oct 2026',
      }
    ];

    const pdfBytes = compileDossierPdfBytes(testDocs, {
      fullName: 'Dhruv Ojha',
      id: 'usr-cit-101',
    });

    assert.ok(pdfBytes.startsWith('%PDF-1.4'));
    assert.ok(pdfBytes.endsWith('%%EOF'));
    assert.ok(pdfBytes.includes('Dhruv Ojha'));
    assert.ok(pdfBytes.includes('Aadhaar Card'));
    assert.ok(pdfBytes.includes('VERIFIED'));
  });

});
