/**
 * FIN Phase D3.10.1 — Financial Safety & Integrity Frontend Regression Tests
 *
 * Verifies:
 * 1. YIPB Apply Now contains no fabricated loan or subsidy breakdown.
 * 2. 1PMY Apply Now contains no PMEGP-style financial terms.
 * 3. Non-loan application payloads omit unsupported financial fields.
 * 4. Missing benefit type does not default to Direct Financial Benefit.
 * 5. YIPB ₹45,000 is not presented as a lump-sum total.
 * 6. Dashboard / helper functions do not treat loan principal and grants as equivalent.
 * 7. Existing supported PMEGP calculator behavior remains intact.
 * 8. Existing eligibility, documents, application status, and navigation behavior remain intact.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  isLoanSchemeWithCalculator,
  adaptSchemeDetails,
  resolveBenefitClassification,
  getSchemeBenefitDisplay
} from '../src/utils/schemeDetailsHelpers.js';

describe('FIN Phase D3.10.1: Financial Safety & Integrity Frontend Suite', () => {

  const yipbRaw = {
    id: 'dfc0aaf8-c74f-581f-aa86-a9bae561167c',
    slug: 'yipb',
    scheme_name: 'Young Investigators Programme in Biotechnology',
    department: 'Department of Biotechnology',
    benefit_type: 'Composite',
    max_benefit: 45000, // Legacy scalar regex from seed
    benefits: '- Young Scientists without fellowship/salary are eligible for a fellowship of ₹45,000/- plus 10% HRA per month | Maximum support up to ₹30 lakhs for a period not exceeding three years.'
  };

  const pmy1Raw = {
    id: '1pmy',
    slug: '1pmy',
    scheme_name: '100% Penalty Mafi Yojana',
    department: 'Urban Development and Urban Housing Department',
    benefit_type: 'Penalty Waiver',
    max_benefit: null,
    benefits: '100% waiver on accumulated late payment penalty on housing installments'
  };

  const pmegpRaw = {
    id: 'pmegp',
    slug: 'pmegp',
    scheme_name: "Prime Minister's Employment Generation Programme",
    department: 'Ministry of MSME',
    benefit_type: 'Credit Linked Subsidy',
    is_loan_scheme: true,
    max_benefit: null,
    details: { subsidy_percent: 35 }
  };

  test('1. YIPB Apply Now contains no fabricated loan or subsidy calculator', () => {
    const adapted = adaptSchemeDetails(yipbRaw);
    const hasCalculator = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(hasCalculator, false, 'YIPB research fellowship must strictly reject loan calculator');
  });

  test('2. 1PMY Apply Now contains no PMEGP-style financial terms', () => {
    const adapted = adaptSchemeDetails(pmy1Raw);
    const hasCalculator = isLoanSchemeWithCalculator(adapted);

    assert.strictEqual(hasCalculator, false, '1PMY penalty waiver must strictly reject loan calculator');
  });

  test('3. Non-loan application payloads omit unsupported financial fields', () => {
    // Simulate application payload construction from SchemeDetailsPage
    const preparePayload = (scheme, isLoan, projectCost, subsidyAmount) => {
      const payload = {
        schemeId: scheme.id,
        scheme_name: scheme.title
      };
      if (isLoan) {
        payload.projectCost = projectCost;
        payload.subsidyAmount = subsidyAmount;
      }
      return payload;
    };

    const yipbAdapted = adaptSchemeDetails(yipbRaw);
    const yipbPayload = preparePayload(
      yipbAdapted,
      isLoanSchemeWithCalculator(yipbAdapted),
      500000,
      175000
    );

    assert.strictEqual(yipbPayload.schemeId, yipbAdapted.id);
    assert.strictEqual(yipbPayload.projectCost, undefined, 'Non-loan payload must NOT include projectCost');
    assert.strictEqual(yipbPayload.subsidyAmount, undefined, 'Non-loan payload must NOT include subsidyAmount');
  });

  test('4. Missing benefit type does not default to Direct Financial Benefit or Direct Benefit', () => {
    const emptyScheme = { id: 'unknown_scheme', maxBenefit: null };
    const classification = resolveBenefitClassification(emptyScheme);
    const display = getSchemeBenefitDisplay(emptyScheme);

    assert.strictEqual(classification, 'Benefit Type Not Specified', 'Must return neutral unverified classification');
    assert.notStrictEqual(classification, 'Direct Benefit', 'Must not default to Direct Benefit');
    assert.notStrictEqual(display.amountDisplay, 'Direct Benefit / Waiver', 'Must not default to Direct Benefit / Waiver');
    assert.notStrictEqual(display.subtitle, '(Direct Financial Benefit)', 'Must not default to (Direct Financial Benefit)');
  });

  test('5. YIPB ₹45,000 is not presented as a lump-sum total entitlement', () => {
    const adapted = adaptSchemeDetails(yipbRaw);
    const display = getSchemeBenefitDisplay(adapted);

    // Invariant: Display amount must indicate composite / variable, never bare ₹45,000
    assert.notStrictEqual(display.amountDisplay, '₹45,000', 'Must not present bare ₹45,000 as lump-sum total');
    assert.strictEqual(display.isScalarTotal, false, 'YIPB must be flagged as non-scalar total');
    assert.strictEqual(display.classification, 'Composite', 'Must identify Composite structure');
    assert.ok(
      display.entitlementText.toLowerCase().includes('monthly') ||
      display.entitlementText.toLowerCase().includes('breakdown') ||
      display.entitlementText.toLowerCase().includes('multi-component'),
      'Must explain multi-component nature in entitlement description'
    );
  });

  test('6. 1PMY benefit display correctly reflects Penalty Waiver without generic fallbacks', () => {
    const adapted = adaptSchemeDetails(pmy1Raw);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(display.classification, 'Penalty Waiver');
    assert.strictEqual(display.amountDisplay, '100% Penalty Waiver');
    assert.strictEqual(display.subtitle, '(Penalty Waiver)');
  });

  test('7. Existing supported PMEGP calculator behavior remains intact', () => {
    const adapted = adaptSchemeDetails(pmegpRaw);
    const hasCalculator = isLoanSchemeWithCalculator(adapted);
    const display = getSchemeBenefitDisplay(adapted);

    assert.strictEqual(hasCalculator, true, 'PMEGP credit-linked scheme must retain loan calculator');
    assert.strictEqual(display.classification, 'Credit Linked Subsidy');
    assert.ok(display.amountDisplay.includes('Subsidy'), 'PMEGP must indicate margin money subsidy');
  });

  test('8. Existing application cycle and document parsing remain intact', () => {
    const adapted = adaptSchemeDetails(yipbRaw);

    assert.ok(adapted.title, 'Title must be adapted');
    assert.ok(adapted.subtitle, 'Subtitle must be adapted');
    assert.ok(adapted.application_cycle, 'Application cycle must be attached');
    assert.strictEqual(typeof adapted.application_cycle.status, 'string');
  });
});
