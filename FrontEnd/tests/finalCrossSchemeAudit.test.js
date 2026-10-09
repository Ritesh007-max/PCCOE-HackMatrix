import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  adaptSchemeDetails,
  getSchemeBenefitDisplay,
  getSchemePortalDetails,
  getSchemeApplicationCycle,
  matchDocumentStatus,
  getEligibilityStateDetails
} from '../src/utils/schemeDetailsHelpers.js';
import { interpretFinancialBenefit } from '../src/utils/financialBenefitEngine.js';

describe('Final Cross-Scheme Catalog Audit Frontend Suite', () => {

  // 1. Direct Cash Assistance (e.g. PM-KISAN)
  test('1. Direct cash benefit: properly adapts scalar assistance, All India state, and validated URL', () => {
    const raw = {
      id: 'pm-kisan',
      slug: 'pm-kisan',
      scheme_name: 'Pradhan Mantri Kisan Samman Nidhi',
      state: 'All India',
      level: 'Central',
      benefit_type: 'Cash',
      max_benefit: 6000,
      brief_description: 'Income support of ₹6,000 per year in three installments.',
      source_url: 'https://pmkisan.gov.in',
      scheme_open_date: '2019-02-24',
      scheme_close_date: null
    };

    const adapted = adaptSchemeDetails(raw);
    const portal = getSchemePortalDetails(adapted);
    const benefit = getSchemeBenefitDisplay(adapted);
    const cycle = getSchemeApplicationCycle(adapted);

    assert.strictEqual(adapted.state, 'All India');
    assert.strictEqual(adapted.level, 'Central');
    assert.strictEqual(portal.officialWebsite, 'https://pmkisan.gov.in');
    assert.strictEqual(benefit.classification, 'Direct Financial Benefit');
    assert.strictEqual(benefit.hasLoanCalculator, false);
    assert.strictEqual(benefit.calculatorParameters, null);
    assert.strictEqual(cycle.status, 'ONGOING');
  });

  // 2. Scholarships and Fellowships (e.g. Ambedkar Fellowship)
  test('2. Scholarships and Fellowships: preserves recurring monthly rate without lump-sum claim', () => {
    const raw = {
      id: 'fellowship-xyz',
      scheme_name: 'National Doctoral Fellowship',
      benefit_type: 'Fellowship',
      max_benefit: 35000,
      brief_description: 'Monthly fellowship of ₹35,000 per month for doctoral scholars.'
    };

    const adapted = adaptSchemeDetails(raw);
    const benefit = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(benefit.classification, 'Fellowship / Stipend');
    assert.strictEqual(benefit.amountDisplay, '₹35,000 / month');
    assert.strictEqual(benefit.isScalarTotal, false, 'Must not claim monthly rate is total lump sum');
    assert.strictEqual(benefit.hasLoanCalculator, false);
  });

  // 3. Loans and Credit-Linked Subsidies (PMEGP vs generic credit)
  test('3. Loans and Subsidies: gates calculator strictly to schemes with verified calculator parameters', () => {
    const rawWithParams = {
      id: 'pmegp',
      scheme_name: 'Prime Minister Employment Generation Programme',
      benefit_type: 'Credit Linked Subsidy',
      calculator_parameters: {
        minProjectCost: 20000,
        maxProjectCost: 5000000,
        subsidyGrid: { manufacturing: { rural: { special: 35, general: 25 }, urban: { special: 25, general: 15 } } }
      }
    };

    const adaptedWithParams = adaptSchemeDetails(rawWithParams);
    const benefitWithParams = getSchemeBenefitDisplay(adaptedWithParams);
    assert.strictEqual(benefitWithParams.hasLoanCalculator, true);
    assert.ok(benefitWithParams.calculatorParameters);

    const rawWithoutParams = {
      id: 'unparam-loan',
      scheme_name: 'Self-Employment Loan Scheme',
      benefit_type: 'Credit Linked Subsidy'
    };

    const adaptedWithoutParams = adaptSchemeDetails(rawWithoutParams);
    const benefitWithoutParams = getSchemeBenefitDisplay(adaptedWithoutParams);
    assert.strictEqual(benefitWithoutParams.calculatorParameters, null, 'Must not fabricate parameters for unparameterized credit scheme');
  });

  // 4. Penalty Waivers (100% Penalty Mafi Yojana)
  test('4. Penalty Waiver: displays waiver without loan calculator or cash grant misclassification', () => {
    const raw = {
      id: '1pmy',
      slug: '1pmy',
      scheme_name: '100% Penalty Mafi Yojana',
      state: 'Gujarat',
      level: 'State',
      benefit_type: 'Penalty Waiver',
      benefits: '100% penalty waiver on delayed property tax payments.'
    };

    const adapted = adaptSchemeDetails(raw);
    const benefit = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(benefit.classification, 'Penalty Waiver');
    assert.strictEqual(benefit.amountDisplay, '100% Penalty Waiver');
    assert.strictEqual(benefit.hasLoanCalculator, false);
    assert.strictEqual(benefit.isScalarCashGrant, false);
  });

  // 5. Housing and Welfare (PMAY)
  test('5. Housing & Welfare: scalar capital grant does not trigger loan calculator', () => {
    const raw = {
      id: 'pmay',
      scheme_name: 'Pradhan Mantri Awas Yojana',
      benefit_type: 'Direct Financial Benefit',
      max_benefit: 120000,
      brief_description: 'Direct housing subsidy of ₹1,20,000 for pucca house construction.'
    };

    const adapted = adaptSchemeDetails(raw);
    const benefit = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(benefit.classification, 'Direct Financial Benefit');
    assert.strictEqual(benefit.isScalarCashGrant, true);
    assert.strictEqual(benefit.hasLoanCalculator, false);
  });

  // 6. State Scheme Jurisdiction & Level
  test('6. State Scheme: preserves jurisdiction without defaulting to Central', () => {
    const raw = {
      id: 'ap-welfare',
      scheme_name: 'Andhra Pradesh Weavers Assistance',
      state: 'Andhra Pradesh',
      level: 'State'
    };

    const adapted = adaptSchemeDetails(raw);
    assert.strictEqual(adapted.state, 'Andhra Pradesh');
    assert.strictEqual(adapted.level, 'State');
  });

  // 7. Schemes with Incomplete Metadata: honest unavailable state
  test('7. Incomplete metadata: produces honest null dates and NOT_SPECIFIED status', () => {
    const raw = {
      id: 'no-meta-scheme',
      scheme_name: 'Undated Welfare Initiative',
      scheme_open_date: null,
      scheme_close_date: null,
      source_url: null
    };

    const adapted = adaptSchemeDetails(raw);
    const cycle = getSchemeApplicationCycle(adapted);
    const portal = getSchemePortalDetails(adapted);

    assert.strictEqual(cycle.status, 'NOT_SPECIFIED');
    assert.strictEqual(cycle.openDate, null);
    assert.strictEqual(cycle.closeDate, null);
    assert.strictEqual(portal.officialWebsite, null);
  });

  // 8. Document Verification Integrity: uploaded != verified
  test('8. Document verification integrity: uploaded document evaluates to Uploaded, NEVER Verified', () => {
    const userDocs = [
      {
        id: 'doc-1',
        documentType: 'Aadhaar Card',
        verificationStatus: 'pending',
        ocrExtracted: true
      },
      {
        id: 'doc-2',
        documentType: 'Income Certificate',
        verificationStatus: 'verified',
        ocrExtracted: true
      }
    ];

    // Aadhaar is uploaded with pending verification
    const aadhaarStatus = matchDocumentStatus('Aadhaar Card', userDocs);
    assert.strictEqual(aadhaarStatus, 'Uploaded', 'Pending/OCR document must remain Uploaded');

    // Income certificate has explicit verified status
    const incomeStatus = matchDocumentStatus('Income Certificate', userDocs);
    assert.strictEqual(incomeStatus, 'Verified', 'Explicitly verified document must evaluate to Verified');

    // Unmatched requirement evaluates to Missing
    const panStatus = matchDocumentStatus('PAN Card', userDocs);
    assert.strictEqual(panStatus, 'Missing');
  });

  // 9. Eligibility State Integrity: unregistered scheme produces MANUAL_REVIEW with zero sentinels
  test('9. Eligibility state integrity: unregistered scheme displays honest manual review notice', () => {
    const backendResult = {
      source: 'local_fallback',
      isRegistered: false,
      evaluationCategory: 'UNREGISTERED_SCHEME',
      status: 'UNKNOWN',
      verdict: 'MANUAL_REVIEW',
      rules: [],
      missingFields: []
    };

    const state = getEligibilityStateDetails(backendResult);
    assert.strictEqual(state.status, 'UNKNOWN');
    assert.strictEqual(state.verdict, 'MANUAL_REVIEW');
    assert.strictEqual(state.badgeClass, 'amber');
    assert.strictEqual(state.isRegistered, false);
    assert.ok(state.bannerReason.includes('Automated statutory rules are not registered'));
  });

  // 10. Official Portal URL Validation: rejects untrusted commercial domains
  test('10. Official portal links: rejects untrusted aggregators and insecure protocols', () => {
    const rawAggregator = {
      id: 'scheme-agg',
      source_url: 'https://sarkariyojana.com/apply-now'
    };
    const portalAgg = getSchemePortalDetails(adaptSchemeDetails(rawAggregator));
    assert.strictEqual(portalAgg.officialWebsite, null);

    const rawInsecure = {
      id: 'scheme-js',
      source_url: 'javascript:alert(1)'
    };
    const portalInsecure = getSchemePortalDetails(adaptSchemeDetails(rawInsecure));
    assert.strictEqual(portalInsecure.officialWebsite, null);
  });
});
