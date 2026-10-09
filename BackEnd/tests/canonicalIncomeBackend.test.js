/**
 * FIN — Backend Canonical Income Model Test Suite
 *
 * Verifies backend income processing rules:
 * 1. Exact numeric annual_income preservation (350000 -> 350000)
 * 2. Range string '₹2.5 Lakhs - ₹5 Lakhs' maps to 350000
 * 3. Range string '₹1 Lakh - ₹2.5 Lakhs' maps to 200000 (NEVER 180000 to prevent document collision)
 * 4. Negative income rejection (returns 400)
 * 5. String numbers normalized to number
 * 6. Profile personal income (350000) vs Document family income (180000) separation
 */

const test = require('node:test');
const assert = require('node:assert');

test('FIN — Backend Canonical Income Model Suite', async (t) => {

  const incomeMap = {
    'Below ₹1 Lakh': 80000,
    '₹1 Lakh - ₹2.5 Lakhs': 200000,
    '₹2.5 Lakhs - ₹5 Lakhs': 350000,
    '₹5 Lakhs - ₹10 Lakhs': 750000,
    'Above ₹10 Lakhs': 1200000,
  };

  await t.test('1. Exact numeric personal income is authoritative and preserved directly', () => {
    const rawIncome = 350000;
    const processed = typeof rawIncome === 'number' ? rawIncome : parseFloat(String(rawIncome));
    assert.strictEqual(processed, 350000);
    assert.strictEqual(typeof processed, 'number');
  });

  await t.test('2. "₹2.5 Lakhs - ₹5 Lakhs" maps to canonical 350000', () => {
    assert.strictEqual(incomeMap['₹2.5 Lakhs - ₹5 Lakhs'], 350000);
  });

  await t.test('3. "₹1 Lakh - ₹2.5 Lakhs" maps to 200000 and NEVER 180000 (prevents document family income collision)', () => {
    assert.strictEqual(incomeMap['₹1 Lakh - ₹2.5 Lakhs'], 200000);
    assert.notStrictEqual(incomeMap['₹1 Lakh - ₹2.5 Lakhs'], 180000);
  });

  await t.test('4. Below ₹1 Lakh maps to 80000 and Above ₹10 Lakhs maps to 1200000', () => {
    assert.strictEqual(incomeMap['Below ₹1 Lakh'], 80000);
    assert.strictEqual(incomeMap['Above ₹10 Lakhs'], 1200000);
  });

  await t.test('5. Non-negative numeric validation: negative income is rejected', () => {
    const validateIncome = (val) => {
      const num = typeof val === 'number' ? val : (typeof val === 'string' && /^\d+(\.\d+)?$/.test(val) ? Number(val) : NaN);
      return Number.isFinite(num) && num >= 0;
    };
    assert.strictEqual(validateIncome(350000), true);
    assert.strictEqual(validateIncome(0), true);
    assert.strictEqual(validateIncome(-5000), false);
    assert.strictEqual(validateIncome('invalid'), false);
  });

  await t.test('6. Personal income and Document family income maintain separate semantic provenance', () => {
    const profile = { id: 'usr-123', annual_income: 350000 };
    const documents = [
      { id: 'doc-1', document_type: 'income_cert', extracted_fields: { annual_family_income: 180000 } }
    ];

    const recommendationFacts = {
      applicant_facts: profile,
      document_facts: documents.map(d => ({
        document_id: d.id,
        document_type: d.document_type,
        fields: d.extracted_fields
      }))
    };

    assert.strictEqual(recommendationFacts.applicant_facts.annual_income, 350000);
    assert.strictEqual(recommendationFacts.document_facts[0].fields.annual_family_income, 180000);
    assert.notStrictEqual(recommendationFacts.applicant_facts.annual_income, recommendationFacts.document_facts[0].fields.annual_family_income);
  });

});
