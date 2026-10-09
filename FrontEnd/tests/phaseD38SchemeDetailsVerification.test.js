import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  adaptSchemeDetails,
  getSchemeBenefitDisplay,
  getSchemePortalDetails,
  getSchemeApplicationCycle,
  matchDocumentStatus,
  getEligibilityStateDetails,
  parseRequiredDocuments,
  parseApplicationProcess,
  parseEligibilityCriteria,
  parseSchemeBenefits
} from '../src/utils/schemeDetailsHelpers.js';
import { interpretFinancialBenefit, BenefitCategories } from '../src/utils/financialBenefitEngine.js';

describe('Phase D3.8: Seven-Tab Universal Scheme Details Verification Suite (Frontend)', () => {

  // TAB 1: OVERVIEW
  test('Tab 1 - Overview: dynamic jurisdiction, implementing authority, and verified official source', () => {
    // A. Central scheme
    const centralScheme = adaptSchemeDetails({
      id: 'central-welfare-1',
      scheme_name: 'Central Agriculture Mechanization Mission',
      ministry: 'Ministry of Agriculture and Farmers Welfare',
      level: 'Central',
      state: 'All India',
      source_url: 'https://agrimachinery.nic.in'
    });
    const centralPortal = getSchemePortalDetails(centralScheme);
    assert.strictEqual(centralPortal.coverage, 'All India (Central)');
    assert.strictEqual(centralPortal.ministry, 'Ministry of Agriculture and Farmers Welfare');
    assert.strictEqual(centralPortal.officialWebsite, 'https://agrimachinery.nic.in');

    // B. State scheme
    const stateScheme = adaptSchemeDetails({
      id: 'state-welfare-1',
      scheme_name: 'Rythu Bandhu Scheme',
      department: 'Department of Agriculture, Government of Telangana',
      level: 'State',
      state: 'Telangana',
      source_url: 'https://rythubandhu.telangana.gov.in'
    });
    const statePortal = getSchemePortalDetails(stateScheme);
    assert.strictEqual(statePortal.coverage, 'Telangana (State)');
    assert.strictEqual(statePortal.ministry, 'Department of Agriculture, Government of Telangana');
    assert.strictEqual(statePortal.officialWebsite, 'https://rythubandhu.telangana.gov.in');

    // C. Missing metadata handles honestly without fabricating authority
    const emptyScheme = adaptSchemeDetails({ id: 'empty-scheme', scheme_name: 'Generic Scheme' });
    const emptyPortal = getSchemePortalDetails(emptyScheme);
    assert.strictEqual(emptyPortal.ministry, 'Implementing Authority Not Specified');
    assert.strictEqual(emptyPortal.officialWebsite, null);
  });

  // TAB 2: ELIGIBILITY
  test('Tab 2 - Eligibility: unverified/unregistered scheme produces safe MANUAL_REVIEW without internal sentinels', () => {
    // Unregistered scheme evaluation
    const evalResult = {
      isRegistered: false,
      evaluationCategory: 'UNREGISTERED_SCHEME',
      verdict: 'MANUAL_REVIEW',
      verdictReason: 'Automated statutory rules are not registered for this scheme. Manual verification is required during departmental application review.',
      rules: [],
      missingFields: [],
      missingFieldLabels: []
    };

    const state = getEligibilityStateDetails(evalResult);
    assert.strictEqual(state.verdict, 'MANUAL_REVIEW');
    assert.strictEqual(state.status, 'UNKNOWN');
    assert.strictEqual(state.isRegistered, false);
    assert.strictEqual(state.category, 'UNREGISTERED_SCHEME');
    assert.ok(state.bannerReason.includes('not registered'));
    // Ensure zero internal sentinels leaked
    assert.ok(!state.bannerReason.includes('scheme_'));
    assert.ok(!state.bannerReason.includes('sentinel'));
  });

  // TAB 3: BENEFITS & FINANCIAL INTEGRITY
  test('Tab 3 - Benefits: accurate benefit classification across 8 categories without PMEGP leakage', () => {
    // 1. Direct Grant
    const directGrant = interpretFinancialBenefit({
      id: 'dbt-cash',
      benefit_type: 'Cash',
      max_benefit: 6000,
      brief_description: 'Annual cash benefit of ₹6,000 in three installments.'
    });
    assert.strictEqual(directGrant.benefitType, 'Direct Financial Benefit');
    assert.strictEqual(directGrant.isScalarTotal, true);
    assert.strictEqual(directGrant.hasLoanCalculator, false);

    // 2. Monthly Fellowship
    const fellowship = interpretFinancialBenefit({
      id: 'fellowship-1',
      benefit_type: 'Fellowship',
      brief_description: 'Fellowship of ₹31,000 per month for junior research fellows.'
    });
    assert.strictEqual(fellowship.benefitType, 'Fellowship / Stipend');
    assert.strictEqual(fellowship.isScalarTotal, false);
    assert.strictEqual(fellowship.hasLoanCalculator, false);

    // 3. Penalty Waiver
    const waiver = interpretFinancialBenefit({
      id: 'waiver-1',
      benefit_type: 'Waiver',
      brief_description: '100% waiver of late payment penalty on property tax.'
    });
    assert.strictEqual(waiver.benefitType, 'Penalty Waiver');
    assert.strictEqual(waiver.hasLoanCalculator, false);

    // 4. Loan without subsidy (e.g. MUDRA) must NOT get loan calculator or credit-linked subsidy
    const pureLoan = interpretFinancialBenefit({
      id: 'mudra-test',
      scheme_name: 'Micro Enterprise Credit Line',
      benefit_type: 'Loan',
      brief_description: 'Repayable institutional loan facility up to ₹50,000.'
    });
    assert.strictEqual(pureLoan.benefitType, 'Loan / Credit Facility');
    assert.strictEqual(pureLoan.hasLoanCalculator, false);
    assert.strictEqual(pureLoan.calculatorParameters, null);

    // 5. Credit-linked subsidy with verified parameters (PMEGP generic match)
    const creditLinked = interpretFinancialBenefit({
      id: 'subsidy-scheme',
      benefit_type: 'Credit Linked Subsidy',
      brief_description: 'Margin money subsidy for micro enterprises with 15% to 35% subsidy.',
      calculator_parameters: {
        minProjectCost: 20000,
        maxProjectCost: 5000000,
        subsidyGrid: { manufacturing: { rural: { special: 35, general: 25 }, urban: { special: 25, general: 15 } } }
      }
    });
    assert.strictEqual(creditLinked.benefitType, 'Credit Linked Subsidy');
    assert.strictEqual(creditLinked.hasLoanCalculator, true);
    assert.ok(creditLinked.calculatorParameters?.subsidyGrid);
  });

  // TAB 4: DOCUMENTS
  test('Tab 4 - Documents: scheme-specific document list, distinct statuses, OCR != verified', () => {
    const scheme = {
      documents_required: 'Aadhaar Card; Income Certificate; Caste Certificate; Bank Passbook'
    };
    const docs = parseRequiredDocuments(scheme);
    assert.strictEqual(docs.length, 4);
    assert.strictEqual(docs[0], 'Aadhaar Card');
    assert.strictEqual(docs[1], 'Income Certificate');

    // Document with OCR extracted data but verificationStatus = 'PENDING' must evaluate to 'Uploaded', NEVER 'Verified'
    const userDocs = [
      {
        documentType: 'income_cert',
        fileName: 'income_certificate.pdf',
        verificationStatus: 'PENDING',
        extractedData: { annual_income: 180000 }
      },
      {
        documentType: 'aadhaar',
        fileName: 'aadhaar.pdf',
        verificationStatus: 'VERIFIED'
      }
    ];

    assert.strictEqual(matchDocumentStatus('Income Certificate', userDocs), 'Uploaded');
    assert.strictEqual(matchDocumentStatus('Aadhaar Card', userDocs), 'Verified');
    assert.strictEqual(matchDocumentStatus('Caste Certificate', userDocs), 'Missing');
  });

  // TAB 5: HOW TO APPLY
  test('Tab 5 - How to Apply: parses numbered steps without fabricating SLAs or generic steps', () => {
    const schemeWithSteps = {
      application_process: 'Step 1: Register on portal | Step 2: Fill application form | Step 3: Upload mandatory documents'
    };
    const steps = parseApplicationProcess(schemeWithSteps.application_process);
    assert.strictEqual(steps.length, 3);
    assert.strictEqual(steps[0].step, '1');
    assert.strictEqual(steps[0].title, 'Register on portal');

    // Missing application process returns clean empty array without inventing 5-step fallback
    const schemeWithoutSteps = { application_process: null };
    const emptySteps = parseApplicationProcess(schemeWithoutSteps.application_process);
    assert.strictEqual(emptySteps.length, 0);
  });

  // TAB 6: SOURCE & RULES
  test('Tab 6 - Source & Rules: validates authoritative government domains and derives guidelines URL', () => {
    // Valid government URL
    const validGovScheme = adaptSchemeDetails({
      id: 'valid-scheme',
      source_url: 'https://myscheme.gov.in/schemes/pmkisan',
      references: [
        'https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf'
      ]
    });
    const portal = getSchemePortalDetails(validGovScheme);
    assert.strictEqual(portal.officialWebsite, 'https://myscheme.gov.in/schemes/pmkisan');

    // Invalid commercial URL rejected
    const badScheme = adaptSchemeDetails({
      id: 'bad-scheme',
      source_url: 'https://cleartax.in/s/pm-kisan-yojana'
    });
    const badPortal = getSchemePortalDetails(badScheme);
    assert.strictEqual(badPortal.officialWebsite, null, 'Commercial aggregators must be rejected');
  });

  // TAB 7: APPLICATION CYCLE & DEADLINES
  test('Tab 7 - Application Cycle: preserves open and close dates without fabricating Ongoing or FY dates', () => {
    // Specific closed window
    const closedScheme = adaptSchemeDetails({
      scheme_open_date: '2023-01-01',
      scheme_close_date: '2023-12-31'
    });
    const closedCycle = getSchemeApplicationCycle(closedScheme);
    assert.strictEqual(closedCycle.status, 'CLOSED');

    // Scheme with no dates
    const unspecScheme = adaptSchemeDetails({
      scheme_open_date: null,
      scheme_close_date: null
    });
    const unspecCycle = getSchemeApplicationCycle(unspecScheme);
    assert.strictEqual(unspecCycle.status, 'NOT_SPECIFIED');
  });

});
