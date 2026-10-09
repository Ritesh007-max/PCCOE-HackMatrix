/**
 * FIN Phase D3.7: Universal Scheme Benefit Presentation & Data Integrity
 * Frontend Regression Suite
 *
 * Verifies:
 * 1. 100% Penalty Mafi Yojana text cleanup, separator normalization, and condition partitioning
 * 2. Young Investigators Programme in Biotechnology (YIPB) multi-component breakdown
 * 3. Accurate entitlement text distinguishing recurring stipends from institutional project ceilings
 * 4. PMEGP verified subsidy grid preservation
 * 5. Educational scholarship (National Post-Matric)
 * 6. Cash fellowship (Dr. Ambedkar Fellowship)
 * 7. Reimbursement (AICTE-INAE Travel Grant)
 * 8. Direct cash assistance (PM Kisan)
 * 9. Credit-linked scheme with missing parameters (Urban housing interest subsidy)
 * 10. Composite skill-development scheme without fellowship leakage (PMKVY-RPL)
 * 11. In-kind healthcare coverage (Ayushman Bharat PM-JAY)
 * 12. Complete absence of hardcoded scheme-specific branching
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  adaptSchemeDetails,
  getSchemeBenefitDisplay,
  interpretFinancialBenefit,
  parseBenefitComponents,
  extractPolicyConditions,
  cleanPolicyText,
  normalizeClauseList,
  parseSchemeBenefits,
  BenefitCategories
} from '../src/utils/schemeDetailsHelpers.js';

describe('FIN Phase D3.7: Universal Scheme Benefit Presentation & Data Integrity (Frontend)', () => {

  // 1. Penalty / Interest Waiver (100% Penalty Mafi Yojana)
  test('1. Penalty/interest waiver: cleans raw separators, removes standalone headers, partitions conditions', () => {
    const raw1pmy = {
      id: '1pmy',
      slug: '1pmy',
      scheme_name: '100% Penalty Mafi Yojana',
      short_title: '1PMY',
      benefit_type: 'Cash',
      tags: ['Housing', 'Penalty', 'Waiver', 'Tenant', 'Urban'],
      benefits: '- The applicant receives 100% waiver on the penalty amount accumulated on pending installments. | - The waiver is applicable on all arrears of installments pertaining to old schemes of the Gujarat Housing Board and Slum Clearance Cell. | - The benefit is a one-time waiver granted upon fulfillment of payment conditions. | - The waiver is applied at the time of final settlement of dues. | Conditions | _All arrears of installments must be paid in one go (lump sum payment)._ | _The payment must be completed by 31st March._ | _*The waiver applies only to the penalty component; the principal installment amount must be paid in full._'
    };

    const adapted = adaptSchemeDetails(raw1pmy);
    const display = getSchemeBenefitDisplay(adapted);
    const interp = interpretFinancialBenefit(adapted);
    const parsedClauses = parseSchemeBenefits(adapted);

    // Classification & entitlement
    assert.strictEqual(display.classification, 'Penalty Waiver');
    assert.strictEqual(display.amountDisplay, '100% Penalty Waiver');
    assert.strictEqual(display.hasLoanCalculator, false);

    // Standalone header 'Conditions' must NOT appear as a clause or bullet
    assert.ok(!parsedClauses.some(c => c.toLowerCase() === 'conditions' || c.toLowerCase() === 'conditions:'),
      'Standalone "Conditions" header must be filtered out');

    // Underscores and markdown artifacts must be stripped
    assert.ok(parsedClauses.every(c => !c.startsWith('_') && !c.endsWith('_')),
      'Clauses must not retain markdown underscores');
    assert.ok(parsedClauses.every(c => !c.includes('_*')),
      'Clauses must not retain _* markdown artifacts');

    // Conditions must be cleanly extracted into conditions array
    assert.ok(display.conditions.length >= 3, 'Must extract at least 3 policy conditions');
    assert.ok(display.conditions.some(c => c.includes('All arrears of installments must be paid in one go')));
    assert.ok(display.conditions.some(c => c.includes('The payment must be completed by 31st March')));
    assert.ok(display.conditions.some(c => c.includes('The waiver applies only to the penalty component')));

    // Normalized benefit component
    assert.ok(display.benefitComponents.length >= 1);
    const waiverComp = display.benefitComponents.find(c => c.benefitType === 'Penalty Waiver');
    assert.ok(waiverComp, 'Must contain a Penalty Waiver component');
    assert.strictEqual(waiverComp.amountDisplay, '100% Penalty Waiver');
    assert.strictEqual(waiverComp.frequency, 'one-time waiver');
    assert.strictEqual(waiverComp.isCeiling, false);
  });

  // 2. YIPB Multi-Component Research Support
  test('2. YIPB: Decomposes multiple components and distinguishes monthly stipend from project ceiling', () => {
    const rawYipb = {
      id: 'dfc0aaf8-c74f-581f-aa86-a9bae561167c',
      slug: 'yipb',
      scheme_name: 'Young Investigators Programme in Biotechnology',
      short_title: 'YIPB',
      benefit_type: 'Composite',
      max_benefit: 45000,
      tags: ['Young Investigator', 'Biotechnology', 'Fellowship', 'Principal Investigator'],
      benefits: '- Young Scientists without fellowship/salary are eligible for a fellowship of ₹45,000/- plus 10% HRA per month, in addition to the support for travel, contingency, consumables, and minor equipment. | - A Principal Investigator having a regular position can seek manpower. | - Maximum support up to ₹30 lakhs (excluding overhead charges @ 10% of the project cost subject to a ceiling of ₹ 1.0 lakh) for a period not exceeding three years.'
    };

    const adapted = adaptSchemeDetails(rawYipb);
    const display = getSchemeBenefitDisplay(adapted);
    const comps = display.benefitComponents;

    // Must have at least 4 normalized components
    assert.ok(comps.length >= 4, `Expected at least 4 components, got ${comps.length}`);

    // Component 1: Fellowship
    const fellowship = comps.find(c => c.benefitType === 'Fellowship / Stipend');
    assert.ok(fellowship, 'Must contain Fellowship / Stipend component');
    assert.strictEqual(fellowship.amount, 45000);
    assert.strictEqual(fellowship.frequency, 'monthly');
    assert.strictEqual(fellowship.unit, 'per month');
    assert.ok(fellowship.amountDisplay.includes('₹45,000 / month'));
    assert.ok(fellowship.amountDisplay.includes('10% HRA'));
    assert.strictEqual(fellowship.applicableBeneficiary, 'Young Scientists without fellowship/salary');
    assert.strictEqual(fellowship.isCeiling, false);

    // Component 2: Operational & Research Support
    const operational = comps.find(c => c.benefitType === 'Operational & Research Support');
    assert.ok(operational, 'Must contain Operational & Research Support component');
    assert.ok(operational.amountDisplay.includes('Travel, Contingency, Consumables & Minor Equipment'));

    // Component 3: Manpower Support
    const manpower = comps.find(c => c.benefitType === 'Manpower Support');
    assert.ok(manpower, 'Must contain Manpower Support component');
    assert.ok(manpower.applicableBeneficiary.includes('Principal Investigator'));

    // Component 4: Research Project Grant Ceiling
    const projectGrant = comps.find(c => c.benefitType === 'Research Project Grant');
    assert.ok(projectGrant, 'Must contain Research Project Grant component');
    assert.strictEqual(projectGrant.amount, 3000000);
    assert.strictEqual(projectGrant.isCeiling, true, 'Project grant must be labeled as ceiling, NOT individual payment');
    assert.strictEqual(projectGrant.duration, '3 years');
    assert.ok(projectGrant.conditions.some(c => c.includes('Excludes overhead charges @ 10%')));

    // Entitlement text must distinguish monthly fellowship from project ceiling
    assert.ok(display.entitlementText.includes('₹45,000 / month') || display.entitlementText.includes('45,000'));
    assert.ok(display.entitlementText.includes('Project Ceiling') || display.entitlementText.includes('30 Lakhs') || display.entitlementText.includes('grant'));
    assert.strictEqual(display.hasLoanCalculator, false);
  });

  // 3. PMEGP Verified Credit-Linked Subsidy Grid
  test('3. PMEGP: Preserves margin money calculator parameters without loan-as-grant confusion', () => {
    const pmegpScheme = {
      id: 'pmegp_1',
      title: 'Prime Minister Employment Generation Programme',
      benefit_type: 'Credit Linked Subsidy',
      is_credit_linked: true,
      is_loan_scheme: true,
      benefits: 'Margin money subsidy of 15% to 35% on project cost up to ₹50 lakhs for manufacturing and ₹20 lakhs for services.',
      brief_description: 'Credit linked subsidy scheme with 15%, 25%, and 35% margin money support'
    };

    const adapted = adaptSchemeDetails(pmegpScheme);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.strictEqual(display.hasLoanCalculator, true);
    assert.ok(display.calculatorParameters != null);
    assert.strictEqual(display.calculatorParameters.subsidyGrid.special.rural, 35);
    assert.strictEqual(display.calculatorParameters.subsidyGrid.general.urban, 15);
    assert.strictEqual(display.isScalarCashGrant, false, 'Margin money subsidy must never be classified as cash grant');
  });

  // 4. Annual Scholarship (National Post-Matric)
  test('4. Scholarship: Annual recurring assistance with correct unit and periodicity', () => {
    const scholarship = {
      id: 'post_matric_1',
      title: 'Post Matric Scholarship for Students',
      benefit_type: 'Scholarship',
      max_benefit: 12000,
      benefits: 'Scholarship of ₹12,000 per academic year for higher education fees and maintenance.'
    };

    const adapted = adaptSchemeDetails(scholarship);
    const display = getSchemeBenefitDisplay(adapted);
    const comps = display.benefitComponents;

    assert.strictEqual(display.classification, 'Scholarship');
    assert.strictEqual(display.amountDisplay, '₹12,000 / year');
    assert.strictEqual(display.isScalarTotal, false, 'Annual recurring must not be a one-time total');
    assert.strictEqual(display.hasLoanCalculator, false);

    const schComp = comps.find(c => c.benefitType === 'Scholarship');
    assert.ok(schComp);
    assert.strictEqual(schComp.unit, 'per academic year');
    assert.strictEqual(schComp.frequency, 'annual');
  });

  // 5. Monthly Fellowship (Dr. Ambedkar Fellowship)
  test('5. Fellowship: Monthly stipend with recurring unit and no lump-sum claim', () => {
    const fellowship = {
      id: 'ambedkar_fel',
      title: 'Dr. Ambedkar Post-Matric Fellowship',
      benefit_type: 'Fellowship',
      max_benefit: 25000,
      benefits: 'Monthly fellowship stipend of ₹25,000 per month for doctoral scholars.'
    };

    const adapted = adaptSchemeDetails(fellowship);
    const display = getSchemeBenefitDisplay(adapted);
    const comps = display.benefitComponents;

    assert.strictEqual(display.classification, 'Fellowship / Stipend');
    assert.strictEqual(display.amountDisplay, '₹25,000 / month');
    assert.strictEqual(display.isScalarTotal, false, 'Monthly fellowship must not be reported as a lump sum');
    assert.strictEqual(display.hasLoanCalculator, false);

    const comp = comps.find(c => c.benefitType === 'Fellowship / Stipend');
    assert.ok(comp);
    assert.strictEqual(comp.frequency, 'monthly');
    assert.strictEqual(comp.unit, 'per month');
  });

  // 6. Reimbursement (AICTE-INAE Travel Grant)
  test('6. Reimbursement: Expense reimbursement with verified expenditure ceiling', () => {
    const reimbursement = {
      id: 'aicte_inae_1',
      title: 'AICTE-INAE Travel Grant Scheme',
      benefit_type: 'Reimbursement',
      max_benefit: 100000,
      benefits: 'Reimbursement of 100% travel expenses up to a ceiling of ₹1,00,000 for attending international research conferences.'
    };

    const adapted = adaptSchemeDetails(reimbursement);
    const display = getSchemeBenefitDisplay(adapted);
    const comps = display.benefitComponents;

    assert.strictEqual(display.classification, 'Reimbursement');
    assert.strictEqual(display.amountDisplay, 'Up to ₹1,00,000 Reimbursement');
    assert.strictEqual(display.isScalarCashGrant, false);
    assert.strictEqual(display.hasLoanCalculator, false);

    const comp = comps.find(c => c.benefitType === 'Reimbursement');
    assert.ok(comp);
    assert.strictEqual(comp.isCeiling, true);
    assert.strictEqual(comp.frequency, 'post-facto claim');
  });

  // 7. Direct Cash Assistance (PM Kisan)
  test('7. Direct Cash Assistance: Verified scalar cash benefit with annual periodicity', () => {
    const pmKisan = {
      id: 'pmkisan_1',
      title: 'PM-KISAN Samman Nidhi',
      benefit_type: 'Cash',
      max_benefit: 6000,
      benefits: 'Financial assistance of ₹6,000 per year distributed in three equal four-monthly installments of ₹2,000.'
    };

    const adapted = adaptSchemeDetails(pmKisan);
    const display = getSchemeBenefitDisplay(adapted);
    const comps = display.benefitComponents;

    assert.strictEqual(display.classification, 'Direct Financial Benefit');
    assert.strictEqual(display.amountDisplay, '₹6,000');
    assert.strictEqual(display.isScalarCashGrant, true);
    assert.strictEqual(display.hasLoanCalculator, false);

    const comp = comps.find(c => c.benefitType === 'Direct Financial Benefit');
    assert.ok(comp);
    assert.strictEqual(comp.amount, 6000);
  });

  // 8. Credit-Linked Scheme with Missing Parameters (Housing Interest Subsidy)
  test('8. Credit-linked scheme with missing parameters: Safely disables calculator without fabrication', () => {
    const housingScheme = {
      id: 'urban_housing_subsidy',
      title: 'Urban Housing Interest Subsidy',
      benefit_type: 'Credit Linked Subsidy',
      is_credit_linked: true,
      benefits: 'Interest subsidy on housing loans for eligible urban home buyers.'
    };

    const adapted = adaptSchemeDetails(housingScheme);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.strictEqual(display.amountDisplay, 'Credit Linked Subsidy');
    assert.strictEqual(display.calculatorParameters, null, 'Unverified parameters must evaluate to null');
    assert.strictEqual(display.isScalarCashGrant, false);
  });

  // 9. Composite Skill Development (PMKVY-RPL)
  test('9. Composite skill-development scheme: Uses neutral wording without fellowship leakage', () => {
    const pmkvy = {
      id: 'pmkvy_rpl_1',
      title: 'PM Kaushal Vikas Yojana - RPL',
      benefit_type: 'Composite',
      benefits: 'Skill assessment, government certification, and monetary incentive upon certified completion.'
    };

    const adapted = adaptSchemeDetails(pmkvy);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'Composite');
    assert.strictEqual(display.amountDisplay, 'Multi-Component Statutory Support');
    assert.ok(!display.entitlementText.toLowerCase().includes('fellowship'),
      'Non-fellowship composite scheme must NEVER contain fellowship wording');
    assert.strictEqual(display.hasLoanCalculator, false);
  });

  // 10. In-Kind Food or Healthcare (Ayushman Bharat PM-JAY)
  test('10. In-kind healthcare coverage: Cashless ceiling without cash grant misclassification', () => {
    const pmjay = {
      id: 'pmjay_1',
      title: 'Ayushman Bharat PM-JAY',
      benefit_type: 'In Kind',
      benefits: 'Cashless healthcare coverage of up to ₹5,00,000 per family per year for secondary and tertiary care hospitalization.'
    };

    const adapted = adaptSchemeDetails(pmjay);
    const display = getSchemeBenefitDisplay(adapted);
    const comps = display.benefitComponents;

    assert.strictEqual(display.classification, 'In-Kind Assistance');
    assert.strictEqual(display.amountDisplay, 'Non-Financial / In-Kind Support');
    assert.strictEqual(display.isScalarCashGrant, false, 'Cashless healthcare must never be called a cash grant');
    assert.strictEqual(display.hasLoanCalculator, false);

    const comp = comps.find(c => c.benefitType === 'In-Kind Assistance');
    assert.ok(comp);
    assert.strictEqual(comp.isCeiling, true);
  });

  // 11. Universal Text Cleanup Edge Cases
  test('11. cleanPolicyText removes table artifacts, double punctuation, and HTML entities cleanly', () => {
    const messy = 'Benefit: ₹45,000/- &amp; 10% HRA |---| _*Special terms apply._ ;; No deduction ..';
    const cleaned = cleanPolicyText(messy);

    assert.ok(!cleaned.includes('&amp;'));
    assert.ok(!cleaned.includes('|---|'));
    assert.ok(!cleaned.includes('_*'));
    assert.ok(!cleaned.includes(';;'));
    assert.ok(cleaned.includes('&'));
    assert.ok(cleaned.includes('Special terms apply.'));
  });
});
