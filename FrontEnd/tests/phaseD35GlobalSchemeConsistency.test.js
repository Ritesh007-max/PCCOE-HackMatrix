/**
 * FIN Phase D3.5: Global Scheme Detail Consistency & Data Integrity Test Suite
 *
 * Requirements:
 * 1. State-level waiver scheme.
 * 2. Fellowship or scholarship scheme.
 * 3. Loan or subsidy scheme.
 * 4. Direct-benefit scheme.
 * 5. Scheme with incomplete canonical data.
 * 6. Scheme without registered statutory rules.
 * 7. Scheme with an official URL.
 * 8. Scheme without a verified official URL.
 * 9. Uploaded versus verified document status.
 * 10. Agreement between scheme details and the Apply Now modal.
 * 11. Cross-scheme state isolation (zero state leakage when switching schemes).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  isLoanSchemeWithCalculator,
  adaptSchemeDetails,
  resolveBenefitClassification,
  getSchemeBenefitDisplay,
  getSchemePortalDetails,
  parseRequiredDocuments,
  matchDocumentStatus,
  validateOfficialUrl,
  getSchemeApplicationCycle,
  getEligibilityStateDetails,
  cleanHtmlEntities,
  normalizeContentText,
  normalizeClauseList,
  parseEligibilityCriteria,
  parseSchemeBenefits,
  BenefitCategories
} from '../src/utils/schemeDetailsHelpers.js';

describe('Phase D3.5: Global Scheme Detail Consistency & Data Integrity Suite', () => {

  // 1. A state-level waiver scheme
  test('1. State-level waiver scheme: dynamic classification, no loan calculator, correct jurisdiction', () => {
    const waiverRaw = {
      id: 'state_waiver_01',
      title: 'Gujarat Housing Board Interest Waiver Scheme',
      state: 'Gujarat',
      level: 'State',
      benefit_type: 'Penalty Waiver',
      brief_description: 'Complete 100% waiver of penalty interest on housing dues arrears',
      max_benefit: null
    };
    const adapted = adaptSchemeDetails(waiverRaw);
    const portal = getSchemePortalDetails(adapted);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(adapted.state, 'Gujarat');
    assert.strictEqual(adapted.level, 'State');
    assert.strictEqual(portal.schemeType, 'Penalty Waiver');
    assert.strictEqual(portal.coverage, 'Gujarat (State)');
    assert.strictEqual(display.category, BenefitCategories.PENALTY_OR_INTEREST_WAIVER);
    assert.strictEqual(display.classification, 'Penalty Waiver');
    assert.strictEqual(hasCalc, false, 'Waiver scheme must NOT show loan calculator');
    assert.strictEqual(display.isScalarTotal, false, 'Waiver is not a cash total');
  });

  // 2. A fellowship or scholarship scheme
  test('2. Fellowship or scholarship scheme: recurring frequency, no lump-sum claim, no loan calculator', () => {
    const scholarshipRaw = {
      id: 'scholarship_02',
      title: 'Post-Matric Scholarship for Higher Education',
      state: 'All India',
      level: 'Central',
      benefit_type: 'Scholarship',
      max_benefit: 48000,
      brief_description: 'Annual scholarship assistance of Rs 48,000 per year for tuition and maintenance'
    };
    const adapted = adaptSchemeDetails(scholarshipRaw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.ANNUAL_SCHOLARSHIP);
    assert.strictEqual(display.amountDisplay, '₹48,000 / year');
    assert.strictEqual(display.isScalarTotal, false, 'Annual scholarship is periodic, not a one-time lump-sum');
    assert.strictEqual(hasCalc, false, 'Scholarship must NOT show loan calculator');
  });

  // 3. A loan or subsidy scheme
  test('3. Credit-linked capital subsidy scheme: calculator supported with margin money parameters', () => {
    const creditRaw = {
      id: 'credit_subsidy_03',
      title: 'Rural Enterprise Margin Money Subsidy Scheme',
      benefit_type: 'Credit Linked Subsidy',
      is_loan_scheme: true,
      max_benefit: 1500000,
      details: { subsidy_percent: 35 },
      brief_description: 'Credit-linked margin money subsidy up to 35% on project investments'
    };
    const adapted = adaptSchemeDetails(creditRaw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
    assert.strictEqual(hasCalc, true, 'Credit-linked subsidy must support calculator');
    assert.ok(display.amountDisplay.includes('Subsidy'));
  });

  // 4. A direct-benefit scheme
  test('4. Direct-benefit scheme: scalar cash transfer, no loan calculator, proper DBT tags', () => {
    const dbtRaw = {
      id: 'dbt_cash_04',
      title: 'Kisan Direct Income Support Scheme',
      benefit_type: 'Cash',
      dbt_scheme: true,
      max_benefit: 6000,
      brief_description: 'Direct cash transfer of Rs 6,000 transferred via DBT to Aadhaar linked bank accounts'
    };
    const adapted = adaptSchemeDetails(dbtRaw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(adapted.dbt_scheme, true);
    assert.strictEqual(display.isScalarCashGrant, true);
    assert.strictEqual(display.amountDisplay, '₹6,000');
    assert.strictEqual(hasCalc, false, 'Direct cash grant must NOT show loan calculator');
  });

  // 5. A scheme with incomplete canonical data
  test('5. Incomplete canonical data: honest unavailable states without fabricated fallbacks', () => {
    const sparseRaw = {
      id: 'sparse_scheme_05',
      title: 'Local Artisan Welfare Assistance',
      benefit_type: null,
      max_benefit: null,
      source_url: null,
      documents_required: null,
      scheme_open_date: null,
      scheme_close_date: null
    };
    const adapted = adaptSchemeDetails(sparseRaw);
    const portal = getSchemePortalDetails(adapted);
    const display = getSchemeBenefitDisplay(adapted);
    const docs = parseRequiredDocuments(adapted);
    const cycle = getSchemeApplicationCycle(adapted);

    assert.strictEqual(portal.officialWebsite, null, 'Must NOT fabricate generic portal link');
    assert.strictEqual(display.classification, 'Benefit Type Not Specified');
    assert.strictEqual(display.amountDisplay, 'Amount Specified in Guidelines');
    assert.notStrictEqual(display.amountDisplay, '₹0', 'Must not show ₹0 for missing amount');
    assert.strictEqual(docs.length, 0, 'Must not invent required documents');
    assert.strictEqual(cycle.status, 'NOT_SPECIFIED', 'Must not invent open or ongoing cycle');
  });

  // 6. A scheme without registered statutory rules
  test('6. Unregistered scheme: produces MANUAL_REVIEW with zero internal sentinels', () => {
    const unregisteredResult = {
      verdict: 'MANUAL_REVIEW',
      status: 'UNKNOWN',
      category: 'UNREGISTERED_SCHEME',
      rules_executed: 0,
      missing_profile_fields: ['scheme_xyz_not_registered', 'rule_evaluation_error'],
      verdictReason: 'Automated statutory rules are not registered for this scheme.'
    };
    const state = getEligibilityStateDetails(unregisteredResult);

    assert.strictEqual(state.verdict, 'MANUAL_REVIEW');
    assert.strictEqual(state.category, 'UNREGISTERED_SCHEME');
    assert.strictEqual(state.hasExecutedRules, false);
    assert.strictEqual(state.missingFields.length, 0, 'Internal sentinels must be stripped');
    assert.strictEqual(state.showMissingProfileBox, false);
  });

  // 7. A scheme with an official URL
  test('7. Scheme with official URL: validated government domain is preserved', () => {
    const officialGovUrl = 'https://myscheme.gov.in/schemes/pmkisan';
    const validated = validateOfficialUrl(officialGovUrl);
    assert.strictEqual(validated, officialGovUrl);

    const schemeWithUrl = { id: 's7', title: 'PM-Kisan', source_url: officialGovUrl };
    const portal = getSchemePortalDetails(schemeWithUrl);
    assert.strictEqual(portal.officialWebsite, officialGovUrl);
  });

  // 8. A scheme without a verified official URL
  test('8. Scheme without verified official URL: commercial aggregators and invalid protocols rejected', () => {
    const invalidUrls = [
      'https://www.google.com/search?q=scheme',
      'https://sarkariyojana.com/apply-now',
      'javascript:alert(1)',
      'ftp://files.gov.in/doc.pdf',
      'http://bankbazaar.com/loans'
    ];

    for (const url of invalidUrls) {
      assert.strictEqual(validateOfficialUrl(url), null, `URL should be rejected: ${url}`);
    }

    const schemeWithoutUrl = { id: 's8', title: 'Unlinked Scheme', source_url: null };
    const portal = getSchemePortalDetails(schemeWithoutUrl);
    assert.strictEqual(portal.officialWebsite, null);
  });

  // 9. Uploaded versus verified document status
  test('9. Uploaded versus verified document status: OCR extraction alone never verifies', () => {
    const userDocs = [
      { document_type: 'income', file_name: 'income_cert.pdf', status: 'uploaded', ocr_extracted: true },
      { document_type: 'aadhaar', file_name: 'aadhaar_card.pdf', status: 'verified', ocr_extracted: true },
      { document_type: 'caste', file_name: 'caste_cert.pdf', status: 'review_required' }
    ];

    // Income certificate is uploaded and OCR extracted, but NOT verified
    const incomeStatus = matchDocumentStatus('Income Certificate', userDocs);
    assert.strictEqual(incomeStatus, 'Uploaded', 'OCR-extracted file without verification must remain Uploaded');

    // Aadhaar is explicitly verified
    const aadhaarStatus = matchDocumentStatus('Aadhaar Card', userDocs);
    assert.strictEqual(aadhaarStatus, 'Verified');

    // Caste certificate is flagged for review
    const casteStatus = matchDocumentStatus('Caste Certificate', userDocs);
    assert.strictEqual(casteStatus, 'Review Required');

    // Domicile certificate was never uploaded
    const domicileStatus = matchDocumentStatus('Domicile Certificate', userDocs);
    assert.strictEqual(domicileStatus, 'Missing');
  });

  // 10. Agreement between scheme details and the Apply Now modal
  test('10. Agreement between scheme details and Apply Now modal', () => {
    const buildApplicationModel = (rawScheme, userDocs) => {
      const adapted = adaptSchemeDetails(rawScheme);
      const docs = parseRequiredDocuments(adapted);
      const hasCalc = isLoanSchemeWithCalculator(adapted);
      const docStatuses = docs.map(d => ({ name: d, status: matchDocumentStatus(d, userDocs) }));
      const verifiedDocsCount = docStatuses.filter(d => d.status === 'Verified').length;

      // Modal payload construction
      const payload = {
        scheme_id: adapted.id,
        scheme_name: adapted.title,
        required_documents_count: docs.length,
        verified_documents_count: verifiedDocsCount
      };
      if (hasCalc) {
        payload.projectCost = 1000000;
        payload.subsidyAmount = 350000;
      }
      return { adapted, docs, docStatuses, payload, hasCalc };
    };

    const waiverScheme = {
      id: 'scheme_waiver',
      title: 'Arrears Waiver Scheme',
      benefit_type: 'Penalty Waiver',
      documents_required: 'Allotment Letter; Possession Receipt; Identity Proof'
    };
    const userDocs = [
      { document_type: 'identity', file_name: 'id.pdf', status: 'verified' }
    ];

    const model = buildApplicationModel(waiverScheme, userDocs);

    // Assert counts agree
    assert.strictEqual(model.docs.length, 3);
    assert.strictEqual(model.payload.required_documents_count, 3);
    assert.strictEqual(model.payload.verified_documents_count, 1);

    // Non-loan scheme modal payload omits financial calculator fields
    assert.strictEqual(model.payload.projectCost, undefined);
    assert.strictEqual(model.payload.subsidyAmount, undefined);
  });

  // 11. Cross-scheme state isolation
  test('11. Cross-scheme state isolation: changing scheme updates all fields without leaking', () => {
    const schemeA = adaptSchemeDetails({
      id: 'scheme_aaa_111',
      title: 'Scheme Alpha',
      state: 'Kerala',
      level: 'State',
      benefit_type: 'Composite',
      max_benefit: 45000,
      documents_required: 'Research Proposal; Institutional Endorsement',
      source_url: 'https://kscste.kerala.gov.in/alpha'
    });

    const schemeB = adaptSchemeDetails({
      id: 'scheme_bbb_222',
      title: 'Scheme Beta',
      state: 'Gujarat',
      level: 'State',
      benefit_type: 'Penalty Waiver',
      max_benefit: null,
      documents_required: 'Electricity Bill; Property Tax Receipt; Aadhaar Card',
      source_url: 'https://housingboard.gujarat.gov.in/beta'
    });

    // Invariant: Scheme A and Scheme B share zero state
    assert.notStrictEqual(schemeA.id, schemeB.id);
    assert.notStrictEqual(schemeA.title, schemeB.title);
    assert.notStrictEqual(schemeA.state, schemeB.state);
    assert.notStrictEqual(schemeA.benefit_type, schemeB.benefit_type);

    const displayA = getSchemeBenefitDisplay(schemeA);
    const displayB = getSchemeBenefitDisplay(schemeB);
    assert.notStrictEqual(displayA.classification, displayB.classification);
    assert.notStrictEqual(displayA.category, displayB.category);

    const docsA = parseRequiredDocuments(schemeA);
    const docsB = parseRequiredDocuments(schemeB);
    assert.strictEqual(docsA.length, 2);
    assert.strictEqual(docsB.length, 3);
    assert.strictEqual(docsA[0], 'Research Proposal');
    assert.strictEqual(docsB[0], 'Electricity Bill');

    const portalA = getSchemePortalDetails(schemeA);
    const portalB = getSchemePortalDetails(schemeB);
    assert.strictEqual(portalA.officialWebsite, 'https://kscste.kerala.gov.in/alpha');
    assert.strictEqual(portalB.officialWebsite, 'https://housingboard.gujarat.gov.in/beta');
  });

  // 12. Content cleanup: HTML entities, markdown artifacts, bullet separators, and clause deduplication
  test('12. Content cleanup: Normalizes raw separators, markdown artifacts, underscores, duplicated clauses, and HTML entities', () => {
    const rawText = '- **First benefit clause** with &amp; entity | - First benefit clause with &amp; entity | * Second clause with _underscores_ &nbsp; and &quot;quotes&quot; | 1. Third clause /-';
    const normalized = normalizeClauseList(rawText);

    // Invariants:
    // 1. Deduplicates identical clauses
    assert.strictEqual(normalized.length, 3);
    // 2. Unescapes HTML entities
    assert.strictEqual(normalized[0], 'First benefit clause with & entity');
    // 3. Strips markdown bold, bullet prefixes, and trailing artifacts
    assert.strictEqual(normalized[1], 'Second clause with underscores   and "quotes"');
    assert.strictEqual(normalized[2], 'Third clause');
  });

  // 13. Eligibility criteria list normalization and condition preservation
  test('13. Eligibility criteria normalization: preserves policy conditions while stripping formatting noise', () => {
    const scheme = {
      criteria: 'The beneficiary must be a resident of Uttarakhand.; First two children from a family; Annual family income &lt; ₹2,50,000/-; Condition: must hold valid ration card;'
    };
    const criteriaList = parseEligibilityCriteria(scheme);

    assert.strictEqual(criteriaList.length, 4);
    assert.strictEqual(criteriaList[0], 'The beneficiary must be a resident of Uttarakhand');
    assert.strictEqual(criteriaList[1], 'First two children from a family');
    assert.strictEqual(criteriaList[2], 'Annual family income < ₹2,50,000');
    assert.strictEqual(criteriaList[3], 'Condition: must hold valid ration card');
  });

  // 14. Benefit breakdown normalization from pipes, newlines, and bullet points
  test('14. Benefit breakdown normalization: structures diverse benefit statements without data loss', () => {
    const scheme = {
      benefits: '- In any medical emergency, patients transported to hospital. | - 272 ambulances deployed statewide | - In any medical emergency, patients transported to hospital.'
    };
    const benefitsList = parseSchemeBenefits(scheme);

    // Deduplication + stripping bullets
    assert.strictEqual(benefitsList.length, 2);
    assert.strictEqual(benefitsList[0], 'In any medical emergency, patients transported to hospital');
    assert.strictEqual(benefitsList[1], '272 ambulances deployed statewide');
  });

  // 15. Absence of generic promotional slogans unless supported by actual canonical scheme record
  test('15. Promotional slogan gating: scheme without explicit slogan retains null slogan without fabricating defaults', () => {
    const schemeWithoutSlogan = adaptSchemeDetails({
      id: 'scheme_plain_01',
      title: 'National Rural Livelihood Mission',
      state: 'All India'
    });
    assert.strictEqual(schemeWithoutSlogan.slogan, null);

    const schemeWithSlogan = adaptSchemeDetails({
      id: 'scheme_slogan_02',
      title: 'Beti Bachao Beti Padhao',
      slogan: 'Educate the girl child, empower the nation'
    });
    assert.strictEqual(schemeWithSlogan.slogan, 'Educate the girl child, empower the nation');
  });
});
