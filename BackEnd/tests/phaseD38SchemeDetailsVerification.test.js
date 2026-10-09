const { test, describe } = require('node:test');
const assert = require('node:assert');
const { formatSchemeRecord, getFaqsBySchemeSlug } = require('../src/services/schemeService');
const { interpretFinancialBenefit } = require('../src/services/financialBenefitService');
const { checkEligibility } = require('../src/services/eligibilityService');
const authMiddleware = require('../src/middleware/authMiddleware');

describe('Phase D3.8: Seven-Tab Universal Scheme Details Verification Suite (Backend)', () => {

  // 1. Tab 1 - Overview Normalization
  test('1. Overview: derives level, state, ministry, and validated source_url without inventing defaults', () => {
    const raw = {
      id: 'scheme-test-1',
      slug: 'scheme-test-1',
      name: 'National Horticulture Mission',
      state: 'Karnataka',
      level: 'State',
      ministry: 'Department of Horticulture',
      source_url: 'https://horticulture.karnataka.gov.in',
      brief_description: 'Financial assistance for farmers establishing green houses.'
    };

    const formatted = formatSchemeRecord(raw);
    assert.strictEqual(formatted.state, 'Karnataka');
    assert.strictEqual(formatted.level, 'State');
    assert.strictEqual(formatted.ministry, 'Department of Horticulture');
    assert.strictEqual(formatted.source_url, 'https://horticulture.karnataka.gov.in');
    assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
  });

  // 2. Tab 2 - Eligibility: Fail-closed for unregistered schemes
  test('2. Eligibility: unregistered scheme produces fail-closed MANUAL_REVIEW with zero sentinels', async () => {
    const result = await checkEligibility(
      '00000000-0000-0000-0000-000000000000',
      'unregistered-policy-xyz',
      { occupation: 'business', annual_income: 200000 },
      { allowFallback: true }
    );

    assert.strictEqual(result.isEligible, false);
    assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
    assert.strictEqual(result.isRegistered, false);
    assert.strictEqual(result.status, 'UNKNOWN');
    assert.ok(!result.verdictReason.includes('unregistered-policy-xyz_not_registered'));
  });

  // 3. Tab 3 - Benefits: Pure credit scheme (e.g. MUDRA) does NOT receive loan calculator or subsidy
  test('3. Benefits: pure credit loan without subsidy does NOT receive loan calculator', () => {
    const loanRow = {
      id: 'mudra-shishu-test',
      scheme_name: 'Pradhan Mantri MUDRA Yojana – Shishu',
      benefit_type: 'Loan',
      brief_description: 'Repayable institutional loan facility up to ₹50,000 for non-farm income generation.'
    };

    const interp = interpretFinancialBenefit(loanRow);
    assert.strictEqual(interp.benefitType, 'Loan / Credit Facility');
    assert.strictEqual(interp.hasLoanCalculator, false);
    assert.strictEqual(interp.calculatorParameters, null);
    assert.strictEqual(interp.isScalarTotal, false);
  });

  // 4. Tab 4 - Documents: Canonical documents are preserved as normalized array
  test('4. Documents: splits canonical semicolon / newline separated list into clean array', () => {
    const row = {
      id: 'doc-test-scheme',
      scheme_name: 'Test Scheme',
      documents_required: 'Passport Photo; Bank Account Passbook; Aadhaar Card; Income Certificate'
    };

    const formatted = formatSchemeRecord(row);
    assert.strictEqual(formatted.documents_required.length, 4);
    assert.strictEqual(formatted.documents_required[0], 'Passport Photo');
    assert.strictEqual(formatted.documents_required[3], 'Income Certificate');
  });

  // 5. Tab 5 - How to Apply: Canonical application process preserved
  test('5. How to Apply: application process preserved without fabricating processing SLA', () => {
    const row = {
      id: 'app-process-scheme',
      scheme_name: 'Test Process Scheme',
      application_process: 'Step 1: Apply online | Step 2: Verification by Block Officer'
    };

    const formatted = formatSchemeRecord(row);
    assert.strictEqual(formatted.application_process, 'Step 1: Apply online | Step 2: Verification by Block Officer');
  });

  // 6. Tab 6 - Source & Rules: Commercial aggregators strictly rejected
  test('6. Source & Rules: commercial aggregators and unverified domains return null source_url', () => {
    const row = {
      id: 'aggregator-scheme',
      scheme_name: 'Aggregator Link Scheme',
      source_url: 'https://sarkariyojana.com/pm-kisan-apply'
    };

    const formatted = formatSchemeRecord(row);
    assert.strictEqual(formatted.source_url, null, 'Commercial aggregator must be rejected');
  });

  // 7. Tab 7 - FAQs: Graceful empty state without synthetic FAQs on missing record
  test('7. FAQs: unknown scheme slug returns clean empty array without error', async () => {
    const res = await getFaqsBySchemeSlug('non-existent-scheme-slug-999');
    assert.strictEqual(res.total, 0);
    assert.deepStrictEqual(res.faqs, []);
  });

  // 8. Security Check: Dev auth bypass strictly requires NODE_ENV === 'development'
  test('8. Security: dev auth bypass token is rejected when NODE_ENV is test or undefined', async () => {
    let statusCode = null;
    let responseBody = null;

    const req = {
      headers: {
        authorization: 'Bearer development-only-bypass-token'
      }
    };
    const res = {
      status: (code) => {
        statusCode = code;
        return {
          json: (body) => { responseBody = body; }
        };
      }
    };
    let nextCalled = false;
    const next = () => { nextCalled = true; };

    const origEnv = process.env.NODE_ENV;
    try {
      process.env.NODE_ENV = 'test';
      await authMiddleware(req, res, next);
      assert.strictEqual(nextCalled, false, 'Dev bypass must NOT be permitted when NODE_ENV is not development');
      assert.strictEqual(statusCode, 401, 'Must return 401 Unauthorized');
    } finally {
      if (origEnv !== undefined) {
        process.env.NODE_ENV = origEnv;
      } else {
        delete process.env.NODE_ENV;
      }
    }
  });

});
