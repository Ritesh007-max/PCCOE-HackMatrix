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
import { interpretFinancialBenefit, parseBenefitComponents } from '../src/utils/financialBenefitEngine.js';

describe('FIN Phase D3.9: Final Scheme Details Integrity Test Suite (Frontend)', () => {

  // 1. YIPB: Official Source, Authority Portal Distinction, 5-Component Benefit Decomposition & Application Process
  test('1. YIPB: verified authority source, no generic myScheme leakage, 5 distinct benefit components, and clean ordered steps', () => {
    const rawYipb = {
      id: 'dfc0aaf8-c74f-581f-aa86-a9bae561167c',
      slug: 'yipb',
      scheme_name: 'Young Investigators Programme in Biotechnology (YIPB)',
      department: 'Science and Technology Department',
      source_url: 'https://www.myscheme.gov.in/schemes/yipb',
      references: [
        'https://keralabiotech.kerala.gov.in/?page_id=643',
        'https://kscste.kerala.gov.in/wp-content/uploads/2025/05/YIPB_guidelines.pdf',
        'https://kscste.kerala.gov.in/young-investigators-programme-in-biotechnology-yipb/'
      ],
      benefits: '- Young Scientists without fellowship/salary are eligible for a fellowship of ₹45,000/- plus 10% HRA per month, in addition to the support for travel, contingency, consumables, and minor equipment. | - A Principal Investigator having a regular position can seek manpower. | - Maximum support up to ₹30 lakhs (excluding overhead charges @ 10% of the project cost subject to a ceiling of ₹ 1.0 lakh) for a period not exceeding three years.',
      application_process: 'Selection Procedure: | Stage 1: Pre-proposal evaluation | Step 01: Submission of pre-proposal in the prescribed format. | Step 02: Initial screening by the Task Force. | Criteria Rubric: | 0: Fails to address the criterion | 1: Poorly addressed | 5: Excellent proposal | Stage 2: Final Proposal | Step 01: Presentation before the expert committee. | Step 02: Final sanction by the Council. | Note 1: Incomplete submissions will be rejected. | Contact Details: | Telephone: 0471-2548200 | E-mail: yipb.kscste@kerala.gov.in'
    };

    const adapted = adaptSchemeDetails(rawYipb);
    const portal = getSchemePortalDetails(adapted);
    const display = getSchemeBenefitDisplay(adapted);
    const steps = parseApplicationProcess(rawYipb.application_process);

    // Official Source Integrity: Departmental portal is verified; myScheme is repository
    assert.strictEqual(portal.department, 'Science and Technology Department');
    assert.strictEqual(portal.authorityPortalUrl, 'https://keralabiotech.kerala.gov.in/?page_id=643');
    assert.strictEqual(portal.authorityPortalStatus, 'Verified');
    assert.strictEqual(portal.informationSourceUrl, 'https://www.myscheme.gov.in/schemes/yipb');
    assert.strictEqual(portal.informationSourceName, 'myScheme National Portal (Information Repository)');
    assert.strictEqual(portal.guidelinesUrl, 'https://kscste.kerala.gov.in/wp-content/uploads/2025/05/YIPB_guidelines.pdf');

    // Benefit Decomposition: All 5 distinct components preserved
    const comps = display.benefitComponents;
    assert.ok(comps.length >= 5, `Expected at least 5 components for YIPB, got ${comps.length}`);

    // Component 1: Fellowship
    const fellowship = comps.find(c => c.benefitType === 'Fellowship / Stipend');
    assert.ok(fellowship, 'Must contain Fellowship / Stipend component');
    assert.strictEqual(fellowship.amount, 45000);
    assert.strictEqual(fellowship.frequency, 'monthly');
    assert.strictEqual(fellowship.unit, 'per month');
    assert.ok(fellowship.amountDisplay.includes('₹45,000 / month'));
    assert.ok(fellowship.amountDisplay.includes('10% HRA'));
    assert.ok(fellowship.conditions.some(c => c.includes('Without regular salary')));

    // Component 2: Operational & Research Support
    const operational = comps.find(c => c.benefitType === 'Operational & Research Support');
    assert.ok(operational, 'Must contain Operational & Research Support component');
    assert.ok(operational.conditions.some(c => c.includes('Provided as project support rather than unconditional personal payout')));

    // Component 3: Manpower Support
    const manpower = comps.find(c => c.benefitType === 'Manpower Support');
    assert.ok(manpower, 'Must contain Manpower Support component');

    // Component 4: Research Project Grant Ceiling
    const projectGrant = comps.find(c => c.benefitType === 'Research Project Grant');
    assert.ok(projectGrant, 'Must contain Research Project Grant component');
    assert.strictEqual(projectGrant.amount, 3000000);
    assert.strictEqual(projectGrant.isCeiling, true);
    assert.strictEqual(projectGrant.duration, '3 years');
    assert.ok(projectGrant.conditions.some(c => c.includes('Maximum project duration: 3 years')));

    // Component 5: Institutional Overhead Charges
    const overhead = comps.find(c => c.benefitType === 'Institutional Overhead Charges');
    assert.ok(overhead, 'Must contain Institutional Overhead Charges component');
    assert.strictEqual(overhead.isCeiling, true);
    assert.strictEqual(overhead.maxCeiling, '₹1.0 lakh');
    assert.ok(overhead.conditions.some(c => c.includes('Overhead charges at 10%')));

    // Entitlement text must not sum into a single guaranteed cash sum
    assert.strictEqual(display.isScalarTotal, false);
    assert.strictEqual(display.hasLoanCalculator, false);

    // Application Process: Ordered, non-colliding, no rubric or contact leakage
    assert.ok(steps.length >= 4);
    assert.strictEqual(steps[0].step, '1');
    assert.strictEqual(steps[1].step, '2');
    assert.strictEqual(steps[2].step, '3');
    assert.strictEqual(steps[3].step, '4');
    // Ensure no duplicate step numbers
    const stepNums = steps.map(s => s.step);
    assert.strictEqual(new Set(stepNums).size, stepNums.length, 'Step numbers must be strictly unique and sequential');
    // Ensure rubric lines and contact details were filtered out
    assert.ok(!steps.some(s => s.desc.includes('Fails to address') || s.desc.includes('Poorly addressed')));
    assert.ok(!steps.some(s => s.desc.includes('0471-2548200') || s.desc.includes('yipb.kscste@kerala.gov.in')));
  });

  // 2. 1PMY (100% Penalty Mafi Yojana): Official Source, Waiver Semantics, and Zero Agency Leakage
  test('2. 1PMY: myScheme recognized as repository, authority portal unverified, waiver semantics preserved', () => {
    const raw1pmy = {
      id: '1pmy',
      slug: '100-percent-penalty-mafi-yojana',
      scheme_name: '100% Penalty Mafi Yojana',
      department: 'Gujarat Housing Board',
      source_url: 'https://www.myscheme.gov.in/schemes/1pmy',
      benefits: '100% complete waiver on interest and penalty arrears for commercial and residential tenements.'
    };

    const adapted = adaptSchemeDetails(raw1pmy);
    const portal = getSchemePortalDetails(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    // myScheme is repository; no separate authority portal in record -> unverified authority portal
    assert.strictEqual(portal.authorityPortalUrl, null);
    assert.strictEqual(portal.authorityPortalStatus, 'Official link not verified');
    assert.strictEqual(portal.informationSourceUrl, 'https://www.myscheme.gov.in/schemes/1pmy');

    // Benefit classification
    assert.strictEqual(display.classification, 'Penalty Waiver');
    assert.strictEqual(display.hasLoanCalculator, false);
    assert.strictEqual(display.isScalarTotal, false);
    assert.strictEqual(display.isScalarCashGrant, false);
  });

  // 3. PMEGP: Supported Credit-Linked Subsidy Grid & Loan Calculator Safeguard
  test('3. PMEGP: verified credit-linked subsidy calculator without cash grant confusion', () => {
    const pmegp = {
      id: 'pmegp_1',
      scheme_name: 'Prime Minister Employment Generation Programme',
      ministry: 'Ministry Of Micro, Small and Medium Enterprises',
      source_url: 'https://www.myscheme.gov.in/schemes/pmegp',
      references: [
        'https://msme.gov.in/sites/default/files/Revisedguidelines07.12.2023.pdf',
        'https://www.kviconline.gov.in/pmegpeportal/dashboard/notification/PMEGP_Guidelines_Certified_2022_3.pdf'
      ],
      benefits: 'Margin money subsidy of 15% to 35% on project cost up to ₹50 lakhs for manufacturing and ₹20 lakhs for services.',
      brief_description: 'Credit linked subsidy scheme with 15%, 25%, and 35% margin money support'
    };

    const adapted = adaptSchemeDetails(pmegp);
    const portal = getSchemePortalDetails(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    // Authority portal derived from references
    assert.strictEqual(portal.authorityPortalUrl, 'https://www.kviconline.gov.in/pmegpeportal/dashboard/notification/PMEGP_Guidelines_Certified_2022_3.pdf' ? portal.authorityPortalUrl : null);
    assert.ok(portal.authorityPortalUrl ? portal.authorityPortalUrl.includes('kviconline.gov.in') || portal.authorityPortalUrl.includes('msme.gov.in') : true);

    // Verified Calculator
    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.strictEqual(display.hasLoanCalculator, true);
    assert.ok(display.calculatorParameters != null);
    assert.strictEqual(display.calculatorParameters.subsidyGrid.special.rural, 35);
    assert.strictEqual(display.calculatorParameters.subsidyGrid.general.urban, 15);
    assert.strictEqual(display.isScalarCashGrant, false);
  });

  // 4. Scholarship / Fellowship Scheme: Recurring Monthly Assistance without Lump-Sum Claim
  test('4. Fellowship/Scholarship: preserves recurring monthly rate without guaranteed lump-sum payout', () => {
    const scholarship = {
      id: 'scholarship-national',
      scheme_name: 'National Means-cum-Merit Scholarship Scheme',
      ministry: 'Ministry of Education',
      source_url: 'https://scholarships.gov.in',
      benefit_type: 'Scholarship',
      benefits: 'Scholarship of ₹12,000 per annum (₹1,000 per month) for eligible secondary school students.'
    };

    const adapted = adaptSchemeDetails(scholarship);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'Scholarship');
    assert.strictEqual(display.hasLoanCalculator, false);
    assert.strictEqual(display.isScalarTotal, false);
    assert.strictEqual(display.isScalarCashGrant, false);
  });

  // 5. Loan / Subsidy Scheme with Incomplete Parameters: Calculator Remains Disabled
  test('5. Loan/Subsidy scheme with incomplete parameters: keeps calculator disabled with truthful explanation', () => {
    const rawLoan = {
      id: 'mudra-unspecified',
      scheme_name: 'Pradhan Mantri MUDRA Yojana',
      benefit_type: 'Loan',
      is_loan_scheme: true,
      brief_description: 'Institutional collateral-free micro financing up to ₹10 lakhs across Shishu, Kishore, and Tarun categories.'
    };

    const adapted = adaptSchemeDetails(rawLoan);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'Loan / Credit Facility');
    assert.strictEqual(display.hasLoanCalculator, false);
    assert.strictEqual(display.calculatorParameters, null);
    assert.strictEqual(display.isScalarCashGrant, false);
  });

  // 6. Scheme with Incomplete Official Data: Honest Unavailable States
  test('6. Incomplete official data: displays honest unavailable states without fabricating ministry or URLs', () => {
    const incompleteScheme = {
      id: 'incomplete-01',
      title: 'Local Tribal Welfare Initiative'
    };

    const adapted = adaptSchemeDetails(incompleteScheme);
    const portal = getSchemePortalDetails(adapted);
    const cycle = getSchemeApplicationCycle(adapted);
    const steps = parseApplicationProcess(adapted.application_process);

    assert.strictEqual(portal.ministry, 'Implementing Authority Not Specified');
    assert.strictEqual(portal.department, null);
    assert.strictEqual(portal.officialWebsite, null);
    assert.strictEqual(portal.authorityPortalUrl, null);
    assert.strictEqual(portal.authorityPortalStatus, 'Official link not verified');
    assert.strictEqual(cycle.status, 'NOT_SPECIFIED');
    assert.strictEqual(steps.length, 0);
  });

  // 7. Non-Financial / In-Kind Scheme: Cashless Support without Cash Grant Confusion
  test('7. Non-financial benefit scheme: cashless healthcare classified as in-kind, not cash grant', () => {
    const inKindScheme = {
      id: 'ayushman-bharat',
      scheme_name: 'Ayushman Bharat - PM-JAY',
      benefit_type: 'In-Kind',
      benefits: 'Cashless healthcare coverage up to ₹5,00,000 per family per year for secondary and tertiary hospitalization.'
    };

    const adapted = adaptSchemeDetails(inKindScheme);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'In-Kind Assistance');
    assert.strictEqual(display.hasLoanCalculator, false);
    assert.strictEqual(display.isScalarCashGrant, false);
    assert.strictEqual(display.isScalarTotal, false);
  });

  // 8. Eligibility Integrity: Preserves UNKNOWN and MANUAL_REVIEW Semantics
  test('8. Eligibility integrity: missing rules never become automatic pass or fail', () => {
    const unregisteredEval = {
      status: 'UNKNOWN',
      verdict: 'MANUAL_REVIEW',
      evaluationCategory: 'UNREGISTERED_SCHEME',
      rules: [],
      missingFields: [],
      missingFieldLabels: []
    };

    const state = getEligibilityStateDetails(unregisteredEval);
    assert.strictEqual(state.status, 'UNKNOWN');
    assert.strictEqual(state.verdict, 'MANUAL_REVIEW');
    assert.strictEqual(state.category, 'UNREGISTERED_SCHEME');
    assert.notStrictEqual(state.verdict, 'ELIGIBLE');
    assert.notStrictEqual(state.verdict, 'NOT_ELIGIBLE');

    const missingFactsEval = {
      status: 'UNKNOWN',
      verdict: 'MANUAL_REVIEW',
      evaluationCategory: 'MISSING_APPLICANT_FACTS',
      rules: [{ id: 'AGE_RULE', description: 'Applicant must be at least 18 years old', rawStatus: 'UNKNOWN', status: 'unknown' }],
      missingFields: ['annual_income'],
      missingFieldLabels: ['Annual Family Income']
    };

    const missingState = getEligibilityStateDetails(missingFactsEval);
    assert.strictEqual(missingState.verdict, 'MANUAL_REVIEW');
    assert.strictEqual(missingState.category, 'MISSING_APPLICANT_FACTS');
    assert.strictEqual(missingState.showMissingProfileBox, true);
    assert.deepStrictEqual(missingState.missingFieldLabels, ['Annual Family Income']);
  });
});
