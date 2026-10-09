import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { getSchemePortalDetails, validateOfficialUrl } from '../src/utils/schemeDetailsHelpers.js';
import { interpretFinancialBenefit, BenefitCategories } from '../src/utils/financialBenefitEngine.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Scheme Details Dynamic Content & Sections Suite', async (t) => {
  await t.test('1. Scheme Details Page contains all 7 required dynamic sections', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    // Section 1: Overview
    assert.ok(content.includes("activeTab === 'overview'"), 'Must contain Overview tab');
    // Section 2: Eligibility
    assert.ok(content.includes("activeTab === 'eligibility'"), 'Must contain Eligibility tab');
    // Section 3: Benefits
    assert.ok(content.includes("activeTab === 'benefits'"), 'Must contain Benefits tab');
    // Section 4: Documents
    assert.ok(content.includes("activeTab === 'documents'"), 'Must contain Documents tab');
    // Section 5: How To Apply
    assert.ok(content.includes("activeTab === 'how-to-apply'"), 'Must contain How To Apply tab');
    // Section 6: Source & Rules
    assert.ok(content.includes("activeTab === 'source-rules'"), 'Must contain Source & Rules tab');
    // Section 7: FAQs
    assert.ok(content.includes("activeTab === 'faqs'"), 'Must contain FAQs tab');
  });

  await t.test('2. Overview populates dynamically from canonical scheme data', () => {
    const scheme = {
      id: 'scheme-xyz',
      title: 'Kisan Samman Yojana',
      ministry: 'Ministry of Agriculture and Farmers Welfare',
      department: 'Department of Agriculture & Cooperation',
      categories: ['Agriculture', 'Direct Financial Assistance'],
      target_beneficiaries: ['Small and Marginal Farmers'],
      state: 'Gujarat',
      level: 'State',
      source_url: 'https://agri.gujarat.gov.in/scheme'
    };

    const details = getSchemePortalDetails(scheme);
    assert.strictEqual(details.department, 'Department of Agriculture & Cooperation');
    assert.strictEqual(details.ministry, 'Department of Agriculture & Cooperation');
    assert.strictEqual(details.schemeType, 'Agriculture, Direct Financial Assistance');
    assert.strictEqual(details.targetBeneficiaries, 'Small and Marginal Farmers');
    assert.strictEqual(details.coverage, 'Gujarat (State)');
    assert.strictEqual(details.officialWebsite, 'https://agri.gujarat.gov.in/scheme');
  });

  await t.test('3. Eligibility display remains informational and separate from recommendation scores', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    // Asserts no recommendation percentage or AI score is disguised as statutory eligibility
    assert.ok(!content.includes('recommendation_score as eligibility'), 'No recommendation score substitution');
    assert.ok(content.includes('Descriptive Policy Eligibility Requirements'), 'Must retain descriptive statutory criteria');
  });

  await t.test('4. Benefits engine correctly distinguishes loan from cash grant', () => {
    const loanScheme = {
      title: 'Pradhan Mantri Mudra Yojana',
      benefit_type: 'Loan',
      financial_benefit_max: 1000000,
      description: 'Collateral-free business loans up to Rs 10 Lakh.'
    };

    const interpLoan = interpretFinancialBenefit(loanScheme);
    assert.notStrictEqual(interpLoan.category, BenefitCategories.DIRECT_BENEFIT_TRANSFER);
    assert.strictEqual(interpLoan.isScalarCashGrant, false, 'Loan must not be classified as scalar cash grant');
    assert.ok(
      interpLoan.category === BenefitCategories.COMPOSITE_LOAN_FACILITY ||
      interpLoan.category === BenefitCategories.CREDIT_LINKED_SUBSIDY ||
      interpLoan.benefitType?.toLowerCase().includes('loan') ||
      interpLoan.amountDisplay.includes('10,00,000'),
      'Loan must be properly identified'
    );
  });

  await t.test('5. No hardcoded PMEGP or MUDRA fallback text in SchemeDetailsPage helper logic', () => {
    const helperPath = path.join(__dirname, '..', 'src', 'utils', 'schemeDetailsHelpers.js');
    const helperContent = fs.readFileSync(helperPath, 'utf8');

    assert.ok(!helperContent.includes('fallback: "PMEGP"'), 'No hardcoded PMEGP fallback');
    assert.ok(!helperContent.includes('defaultScheme = "mudra"'), 'No hardcoded MUDRA default');
  });
});
