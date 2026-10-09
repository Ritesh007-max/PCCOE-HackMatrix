/**
 * FIN Phase D3.10.2: Universal Financial Integrity Frontend Regression Suite
 *
 * Requirements:
 * 1. Shared logic across ALL schemes without scheme-name/slug checks.
 * 2. Covers all 10 minimum categories:
 *    - YIPB (monthly fellowship & composite research support)
 *    - 1PMY (penalty waiver)
 *    - PMEGP (credit-linked subsidy & loan calculator)
 *    - Scholarship (recurring / annual assistance)
 *    - Direct cash assistance (fixed one-time or annual grant)
 *    - Interest subsidy
 *    - Reimbursement
 *    - Non-financial / In-kind scheme
 *    - Scheme with missing benefit amount
 *    - Scheme with missing benefit classification
 * 3. Modal & calculator safety:
 *    - Financial fields strictly gated by verified financial model
 *    - Zero fabricated loan calculators
 * 4. Catalog invariants:
 *    - Zero generic Direct Financial Benefit fallbacks
 *    - Missing amounts remain unavailable / referred to guidelines, NEVER ₹0
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  isLoanSchemeWithCalculator,
  adaptSchemeDetails,
  resolveBenefitClassification,
  getSchemeBenefitDisplay,
  interpretFinancialBenefit,
  BenefitCategories
} from '../src/utils/schemeDetailsHelpers.js';

describe('FIN Phase D3.10.2: Universal Financial Integrity Frontend Suite', () => {

  // 1. YIPB: Monthly fellowship & composite research support
  test('1. YIPB: Monthly fellowship & composite research support correctly classified', () => {
    const raw = {
      id: 'yipb_arbitrary_guid_01',
      title: 'Young Investigators Programme in Biotechnology',
      benefit_type: 'Composite',
      max_benefit: 45000,
      brief_description: 'Fellowship of Rs 45,000 per month and research grant of 25 Lakhs'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT);
    assert.strictEqual(display.classification, 'Composite');
    assert.strictEqual(hasCalc, false, 'Composite fellowship must NOT show loan calculator');
    assert.strictEqual(display.isScalarTotal, false, 'Must not claim monthly stipend is total entitlement');
    assert.ok(display.amountDisplay.includes('Fellowship & Research Grant') || display.amountDisplay.includes('Composite'));
  });

  // 2. 1PMY: Penalty waiver
  test('2. 1PMY: Penalty waiver accurately identified with waiver component', () => {
    const raw = {
      id: '1pmy_random_id_02',
      title: '100% Penalty Mafi Yojana',
      benefit_type: 'Penalty Waiver',
      max_benefit: null,
      brief_description: '100% waiver on accumulated penal interest on Gujarat Housing Board dues'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.PENALTY_OR_INTEREST_WAIVER);
    assert.strictEqual(display.classification, 'Penalty Waiver');
    assert.strictEqual(hasCalc, false, 'Penalty waiver must NOT show loan calculator');
    assert.strictEqual(display.isScalarTotal, false);
    assert.ok(display.amountDisplay.includes('Waiver'));
  });

  // 3. PMEGP: Supported subsidy / loan calculator
  test('3. PMEGP: Supported credit-linked subsidy calculator preserved with verified parameters', () => {
    const raw = {
      id: 'custom_pmegp_id_03',
      title: 'Prime Minister Employment Generation Programme',
      benefit_type: 'Credit Linked Subsidy',
      is_loan_scheme: true,
      max_benefit: 1000000,
      details: { subsidy_percent: 35 }
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.strictEqual(hasCalc, true, 'Credit-linked scheme must retain loan calculator');
    assert.ok(display.amountDisplay.includes('Subsidy'));
  });

  // 4. Scholarship: Recurring annual assistance
  test('4. Scholarship: Recurring annual educational assistance', () => {
    const raw = {
      id: 'post_matric_scholarship_04',
      title: 'Post-Matric Scholarship Scheme for SC Students',
      benefit_type: 'Scholarship',
      max_benefit: 30000,
      brief_description: 'Annual scholarship assistance of Rs 30,000 per year for professional courses'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.ANNUAL_SCHOLARSHIP);
    assert.strictEqual(display.classification, 'Scholarship');
    assert.strictEqual(hasCalc, false, 'Scholarship must NOT show loan calculator');
    assert.strictEqual(display.amountDisplay, '₹30,000 / year');
  });

  // 5. Direct cash assistance
  test('5. Direct cash assistance: Fixed one-time grant', () => {
    const raw = {
      id: 'kisan_samman_cash_05',
      title: 'PM Kisan Samman Nidhi',
      benefit_type: 'Cash',
      max_benefit: 6000,
      brief_description: 'Direct cash grant of Rs 6,000 per year transferred via DBT'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(hasCalc, false, 'Direct cash assistance must NOT show loan calculator');
    assert.strictEqual(display.isScalarCashGrant, true);
    assert.strictEqual(display.amountDisplay, '₹6,000');
  });

  // 6. Interest subsidy
  test('6. Interest subsidy: Credit interest subvention', () => {
    const raw = {
      id: 'interest_subvention_scheme_06',
      title: 'Differential Rate of Interest Scheme',
      benefit_type: 'Interest Subsidy / Subvention',
      brief_description: '4% interest subsidy for economically weaker section borrowers'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.INTEREST_SUBSIDY);
    assert.strictEqual(hasCalc, false, 'Interest subvention without project cost model must not show loan calculator');
    assert.ok(display.amountDisplay.includes('Interest Subvention'));
  });

  // 7. Reimbursement
  test('7. Reimbursement: Expense reimbursement against actual receipts', () => {
    const raw = {
      id: 'tuition_fee_reimbursement_07',
      title: 'Fee Reimbursement Scheme for Professional Colleges',
      benefit_type: 'Cash',
      max_benefit: 75000,
      brief_description: 'Full tuition reimbursement up to Rs 75,000 verified against college receipts'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.REIMBURSEMENT);
    assert.strictEqual(display.classification, 'Reimbursement');
    assert.strictEqual(hasCalc, false);
    assert.strictEqual(display.isScalarCashGrant, false);
    assert.ok(display.amountDisplay.includes('Reimbursement'));
  });

  // 8. Non-financial / In-kind scheme
  test('8. Non-financial / In-kind welfare assistance', () => {
    const raw = {
      id: 'ration_card_scheme_08',
      title: 'National Food Security Act - Antyodaya Anna Yojana',
      benefit_type: 'In Kind',
      brief_description: 'Free monthly foodgrains supply to priority households'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);
    const hasCalc = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(display.category, BenefitCategories.IN_KIND_BENEFIT);
    assert.strictEqual(display.classification, 'In-Kind Assistance');
    assert.strictEqual(hasCalc, false);
    assert.strictEqual(display.amountDisplay, 'Non-Financial / In-Kind Support');
  });

  // 9. Scheme with missing benefit amount
  test('9. Scheme with missing benefit amount displays guidelines reference, never ₹0', () => {
    const raw = {
      id: 'tribal_welfare_unquantified_09',
      title: 'Integrated Tribal Development Project Aid',
      benefit_type: 'Cash',
      max_benefit: null,
      brief_description: 'Direct assistance for tribal hamlets as per district collector sanction'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.amountDisplay, 'Amount Specified in Guidelines');
    assert.notStrictEqual(display.amountDisplay, '₹0', 'Missing amount must NEVER be displayed as ₹0');
    assert.notStrictEqual(display.amountDisplay, '₹1,25,000', 'Must not display fabricated default');
  });

  // 10. Scheme with missing benefit classification
  test('10. Scheme with missing benefit classification avoids Direct Financial Benefit default', () => {
    const raw = {
      id: 'orphan_welfare_unclassified_10',
      title: 'District Child Welfare and Rehabilitation Support',
      benefit_type: null,
      max_benefit: null,
      brief_description: 'Holistic rehabilitation and care for children in need of protection'
    };
    const adapted = adaptSchemeDetails(raw);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.category, BenefitCategories.UNKNOWN_OR_NOT_SPECIFIED);
    assert.strictEqual(display.classification, 'Benefit Type Not Specified');
    assert.notStrictEqual(display.classification, 'Direct Financial Benefit');
    assert.notStrictEqual(display.classification, 'Direct Benefit / Waiver');
  });

  // 11. Modal Safety: Application payload verification
  test('11. Application modal safety: non-loan schemes omit financial fields', () => {
    const preparePayload = (scheme, isLoan, projectCost, subsidyAmount) => {
      const payload = {
        scheme_id: scheme.id,
        scheme_name: scheme.title
      };
      if (isLoan) {
        payload.projectCost = projectCost;
        payload.subsidyAmount = subsidyAmount;
      }
      return payload;
    };

    const waiverScheme = adaptSchemeDetails({ id: 'w1', title: 'Fee Waiver', benefit_type: 'Penalty Waiver' });
    const payloadWaiver = preparePayload(waiverScheme, isLoanSchemeWithCalculator(waiverScheme), 500000, 175000);
    assert.strictEqual(payloadWaiver.projectCost, undefined);
    assert.strictEqual(payloadWaiver.subsidyAmount, undefined);

    const creditScheme = adaptSchemeDetails({ id: 'c1', title: 'PMEGP Subsidy', benefit_type: 'Credit Linked Subsidy', is_loan_scheme: true });
    const payloadCredit = preparePayload(creditScheme, isLoanSchemeWithCalculator(creditScheme), 500000, 175000);
    assert.strictEqual(payloadCredit.projectCost, 500000);
    assert.strictEqual(payloadCredit.subsidyAmount, 175000);
  });
});
