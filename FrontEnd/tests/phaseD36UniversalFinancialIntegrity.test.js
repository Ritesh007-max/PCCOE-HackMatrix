/**
 * FIN Phase D3.6: Universal Financial Benefit Integrity & Dynamic Calculator Refactor
 * Frontend Regression Suite
 *
 * Covers:
 * 1. Finding 1: Composite Entitlement Text Leakage
 *    - Fellowship wording appears ONLY when supported by canonical data / explicit tokens
 *    - Generic composite schemes use neutral wording (e.g. PMKVY-RPL)
 * 2. Finding 2: Cash Benefits Misclassified as In-Kind
 *    - Explicit canonical benefit types take precedence over broad keywords
 *    - Cash fellowships remain cash/fellowship (e.g. Ambedkar Fellowship)
 *    - Reimbursements remain reimbursements (e.g. AICTE Travel Grant)
 *    - Training keywords alone do not convert cash schemes into in-kind
 * 3. Finding 3: Hardcoded PMEGP Calculator Parameters
 *    - Credit-linked schemes without verified parameters have calculatorParameters === null
 *    - Genuine PMEGP parameters are preserved and usable
 *    - No fabricated subsidy percentages, EMIs, or loan estimates
 * 4. Required representative scheme categories:
 *    - YIPB fellowship
 *    - Ambedkar Fellowship Scheme
 *    - AICTE-INAE Travel Grant
 *    - PM Kaushal Vikas Yojana - Recognition of Prior Learning
 *    - PMEGP
 *    - 100% Penalty Mafi Yojana
 *    - Agriculture subsidy
 *    - Housing loan subsidy
 *    - Direct cash assistance
 *    - Healthcare/in-kind benefit
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  adaptSchemeDetails,
  getSchemeBenefitDisplay,
  interpretFinancialBenefit,
  extractCalculatorParameters,
  isLoanSchemeWithCalculator,
  BenefitCategories
} from '../src/utils/schemeDetailsHelpers.js';

describe('FIN Phase D3.6: Universal Financial Benefit Integrity & Dynamic Calculator Refactor (Frontend)', () => {

  // 1. YIPB Fellowship
  test('1. YIPB: Fellowship and research grant wording preserved with evidence', () => {
    const raw = {
      id: 'yipb_01',
      title: 'Young Investigators Programme in Biotechnology',
      benefit_type: 'Composite',
      max_benefit: 45000,
      brief_description: 'Fellowship of Rs 45,000 per month and research project grant of 25 Lakhs'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT);
    assert.strictEqual(display.classification, 'Composite');
    assert.ok(interp.entitlementText.includes('Monthly fellowship stipend + research project grant'),
      'YIPB must retain fellowship & research wording when supported');
    assert.strictEqual(interp.isScalarTotal, false, 'Must not claim monthly stipend is lump sum');
    assert.strictEqual(interp.calculatorParameters, null, 'Fellowship must not have loan calculator parameters');
  });

  // 2. Ambedkar Fellowship Scheme
  test('2. Ambedkar Fellowship Scheme: Cash fellowship remains fellowship, not in-kind', () => {
    const raw = {
      id: 'ambedkar_fellowship_02',
      title: 'Dr. Ambedkar National Fellowship for SC Students',
      benefit_type: 'Fellowship',
      max_benefit: 31000,
      brief_description: 'Monthly fellowship allowance of Rs 31,000 per month and skill training support for researchers'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.MONTHLY_FELLOWSHIP_OR_STIPEND);
    assert.strictEqual(display.classification, 'Fellowship / Stipend');
    assert.notStrictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT,
      'Skill training mention must not misclassify cash fellowship as in-kind');
    assert.strictEqual(display.amountDisplay, '₹31,000 / month');
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 3. AICTE-INAE Travel Grant
  test('3. AICTE-INAE Travel Grant: Reimbursement scheme remains reimbursement', () => {
    const raw = {
      id: 'aicte_travel_03',
      title: 'AICTE-INAE Travel Grant Scheme for Engineering Students',
      benefit_type: 'Reimbursement',
      max_benefit: 100000,
      brief_description: 'Reimbursement of airfare and conference registration fees for presenting research abroad'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.REIMBURSEMENT);
    assert.strictEqual(display.classification, 'Reimbursement');
    assert.notStrictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT);
    assert.ok(display.amountDisplay.includes('Reimbursement'));
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 4. PM Kaushal Vikas Yojana - Recognition of Prior Learning (PMKVY-RPL)
  test('4. PMKVY-RPL: Generic composite scheme uses neutral wording without fellowship leakage', () => {
    const raw = {
      id: 'pmkvy_rpl_04',
      title: 'PM Kaushal Vikas Yojana - Recognition of Prior Learning',
      benefit_type: 'Composite',
      brief_description: 'Skill certification, accidental insurance cover, and monetary reward on successful candidate assessment'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT);
    assert.strictEqual(display.classification, 'Composite');
    assert.strictEqual(display.amountDisplay, 'Multi-Component Statutory Support');
    assert.ok(interp.entitlementText.includes('Multi-component statutory support combining financial and operational assistance'),
      'Must use neutral statutory wording');
    assert.strictEqual(interp.entitlementText.includes('fellowship'), false,
      'Generic composite scheme must NEVER leak fellowship wording');
    assert.strictEqual(interp.entitlementText.includes('research project grant'), false,
      'Generic composite scheme must NEVER leak research grant wording');
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 5. PMEGP (Supported Credit-Linked Subsidy)
  test('5. PMEGP: Supported credit-linked subsidy preserves margin money calculator parameters', () => {
    const raw = {
      id: 'pmegp_05',
      title: "Prime Minister's Employment Generation Programme (PMEGP)",
      benefit_type: 'Credit Linked Subsidy',
      is_loan_scheme: true,
      brief_description: 'Margin money subsidy of 15% to 35% on micro enterprise project investments',
      details: {
        subsidy_grid: {
          special: { rural: 35, urban: 25, own: 5 },
          general: { rural: 25, urban: 15, own: 10 }
        },
        min_project_cost: 50000,
        max_project_cost: 5000000
      }
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);
    const params = extractCalculatorParameters(adapted, adapted.title.toLowerCase());

    assert.strictEqual(interp.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.strictEqual(interp.hasLoanCalculator, true);
    assert.ok(params != null, 'Calculator parameters must be present for supported PMEGP');
    assert.strictEqual(params.subsidyGrid.special.rural, 35);
    assert.strictEqual(params.subsidyGrid.general.urban, 15);
    assert.strictEqual(params.minProjectCost, 50000);
    assert.strictEqual(params.maxProjectCost, 5000000);
  });

  // 6. 100% Penalty Mafi Yojana
  test('6. 100% Penalty Mafi Yojana: Waiver behavior preserved without loan calculator', () => {
    const raw = {
      id: '1pmy_06',
      title: '100% Penalty Mafi Yojana',
      benefit_type: 'Penalty Waiver',
      brief_description: '100% waiver on accumulated late payment penalty interest on pending housing installments'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.PENALTY_OR_INTEREST_WAIVER);
    assert.strictEqual(display.classification, 'Penalty Waiver');
    assert.strictEqual(display.amountDisplay, '100% Penalty Waiver');
    assert.strictEqual(interp.hasLoanCalculator, false);
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 7. Agriculture subsidy
  test('7. Agriculture subsidy: Direct capital subsidy without loan calculator fabrication', () => {
    const raw = {
      id: 'agri_subsidy_07',
      title: 'Sub-Mission on Agricultural Mechanization (SMAM)',
      benefit_type: 'Direct Financial Benefit',
      dbt_scheme: true,
      max_benefit: 50000,
      brief_description: 'Financial assistance and capital subsidy grant for purchase of modern farm machinery'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.FIXED_ONE_TIME_GRANT);
    assert.strictEqual(display.classification, 'Direct Financial Benefit');
    assert.strictEqual(display.amountDisplay, '₹50,000');
    assert.strictEqual(interp.hasLoanCalculator, false, 'Agri capital subsidy must not show loan calculator');
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 8. Housing loan subsidy (without statutory subsidy parameters)
  test('8. Housing loan subsidy: Credit-linked without verified parameters yields null calculatorParameters', () => {
    const raw = {
      id: 'housing_credit_08',
      title: 'Affordable Housing Credit Linked Subsidy Scheme',
      benefit_type: 'Credit Linked Subsidy',
      is_loan_scheme: true,
      brief_description: 'Credit linked subsidy on home loans for eligible urban beneficiaries'
      // No details.subsidy_grid, no flat subsidy percent, no 15%/25%/35% in text
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);
    const params = extractCalculatorParameters(adapted, adapted.title.toLowerCase());

    assert.strictEqual(interp.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.strictEqual(interp.hasLoanCalculator, true, 'Belongs to credit-linked subsidy family');
    assert.strictEqual(params, null, 'Must NOT infer PMEGP 15%/25%/35% parameters without evidence');
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 9. Direct cash assistance
  test('9. Direct cash assistance: Explicit cash assistance preserves scalar grant', () => {
    const raw = {
      id: 'dbt_kisan_09',
      title: 'PM Kisan Samman Nidhi',
      benefit_type: 'Cash',
      dbt_scheme: true,
      max_benefit: 6000,
      brief_description: 'Income support of Rs 6,000 per year directly into bank accounts of farmers'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.FIXED_ONE_TIME_GRANT);
    assert.strictEqual(display.classification, 'Direct Financial Benefit');
    assert.strictEqual(display.amountDisplay, '₹6,000');
    assert.strictEqual(interp.isScalarCashGrant, true);
    assert.strictEqual(interp.hasLoanCalculator, false);
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // 10. Healthcare / In-Kind Benefit
  test('10. Healthcare / In-kind benefit: Accurately classified as in-kind without cash confusion', () => {
    const raw = {
      id: 'ayushman_pmjay_10',
      title: 'Ayushman Bharat - PM Jan Arogya Yojana',
      benefit_type: 'In Kind',
      brief_description: 'Cashless access to healthcare services for priority families up to Rs 5 lakh coverage'
    };
    const adapted = adaptSchemeDetails(raw);
    const interp = interpretFinancialBenefit(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT);
    assert.strictEqual(display.classification, 'In-Kind Assistance');
    assert.strictEqual(display.amountDisplay, 'Non-Financial / In-Kind Support');
    assert.strictEqual(interp.hasLoanCalculator, false);
    assert.strictEqual(interp.calculatorParameters, null);
  });

  // Cross-verification: Dynamic calculator input gating
  test('11. Dynamic calculator input gating: UI calculator is enabled ONLY with verified parameters', () => {
    const supportedCreditScheme = adaptSchemeDetails({
      id: 'pmegp_verified',
      title: 'PMEGP Subsidy',
      benefit_type: 'Credit Linked Subsidy',
      is_loan_scheme: true,
      details: { subsidy_percent: 25 }
    });
    const unsupportedCreditScheme = adaptSchemeDetails({
      id: 'generic_credit',
      title: 'Generic Credit Scheme',
      benefit_type: 'Credit Linked Subsidy',
      is_loan_scheme: true
    });
    const nonLoanScheme = adaptSchemeDetails({
      id: 'grant_scheme',
      title: 'Skill Grant Scheme',
      benefit_type: 'Fellowship'
    });

    const displaySupported = getSchemeBenefitDisplay(supportedCreditScheme);
    const displayUnsupported = getSchemeBenefitDisplay(unsupportedCreditScheme);
    const displayNonLoan = getSchemeBenefitDisplay(nonLoanScheme);

    // Dynamic gate condition in SchemeDetailsPage:
    // hasValidCalculator = hasLoanCalculator && Boolean(calcParams && (calcParams.subsidyGrid || calcParams.flatSubsidyPercent != null));
    const isValidSupported = displaySupported.hasLoanCalculator && Boolean(displaySupported.calculatorParameters && (displaySupported.calculatorParameters.subsidyGrid || displaySupported.calculatorParameters.flatSubsidyPercent != null));
    const isValidUnsupported = displayUnsupported.hasLoanCalculator && Boolean(displayUnsupported.calculatorParameters && (displayUnsupported.calculatorParameters.subsidyGrid || displayUnsupported.calculatorParameters.flatSubsidyPercent != null));
    const isValidNonLoan = displayNonLoan.hasLoanCalculator && Boolean(displayNonLoan.calculatorParameters && (displayNonLoan.calculatorParameters.subsidyGrid || displayNonLoan.calculatorParameters.flatSubsidyPercent != null));

    assert.strictEqual(isValidSupported, true, 'Supported scheme must validate calculator');
    assert.strictEqual(isValidUnsupported, false, 'Unsupported credit scheme must reject calculator');
    assert.strictEqual(isValidNonLoan, false, 'Non-loan scheme must reject calculator');
  });
});
