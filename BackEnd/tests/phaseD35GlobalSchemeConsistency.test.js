const test = require('node:test');
const assert = require('node:assert/strict');

const schemeService = require('../src/services/schemeService');
const {
    interpretFinancialBenefit,
    BenefitCategories
} = require('../src/services/financialBenefitService');
const eligibilityService = require('../src/services/eligibilityService');

test('FIN Phase D3.5: Global Scheme Detail Consistency & Data Integrity (Backend)', async (t) => {

    await t.test('1. State-level waiver scheme: dynamic jurisdiction and null max_benefit', () => {
        const rawWaiver = {
            id: 'state_waiver_01',
            slug: 'state_waiver_01',
            name: 'Gujarat Housing Board Interest Waiver Scheme',
            state: 'Gujarat',
            level: 'State',
            benefit_type: 'Penalty Waiver',
            max_benefit: 50000, // unanchored penalty amount from seed
            brief_description: 'Complete 100% waiver of penalty interest on housing dues arrears'
        };

        const formatted = schemeService.formatSchemeRecord(rawWaiver);
        assert.strictEqual(formatted.state, 'Gujarat');
        assert.strictEqual(formatted.level, 'State');
        assert.strictEqual(formatted.benefit_type, 'Penalty Waiver');
        // Critical: waiver must not expose max_benefit as guaranteed cash entitlement
        assert.strictEqual(formatted.max_benefit, null);
        assert.strictEqual(formatted.financial_benefit.category, BenefitCategories.PENALTY_OR_INTEREST_WAIVER);
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
    });

    await t.test('2. Fellowship / scholarship scheme: recurring frequency, no lump-sum max_benefit claim', () => {
        const rawScholarship = {
            id: 'kerala_biotech_fellowship_02',
            slug: 'kerala_biotech_fellowship_02',
            name: 'State Biotechnology Research Fellowship',
            state: 'Kerala',
            level: 'State',
            benefit_type: 'Composite',
            max_benefit: 45000,
            brief_description: 'Monthly fellowship stipend of Rs 45,000 per month and research grant'
        };

        const formatted = schemeService.formatSchemeRecord(rawScholarship);
        assert.strictEqual(formatted.max_benefit, null, 'Monthly stipend must not be presented as total lump-sum cash');
        assert.strictEqual(formatted.financial_benefit.isPeriodic, true);
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
    });

    await t.test('3. Credit-linked capital subsidy scheme: loan calculator enabled with margin money parameters', () => {
        const rawCredit = {
            id: 'msme_credit_subsidy_03',
            slug: 'msme_credit_subsidy_03',
            name: 'Prime Minister Employment Generation Programme',
            benefit_type: 'Credit Linked Subsidy',
            is_loan_scheme: true,
            max_benefit: 1000000,
            details: { subsidy_percent: 35 },
            brief_description: '15% to 35% margin money subsidy on project cost'
        };

        const formatted = schemeService.formatSchemeRecord(rawCredit);
        assert.strictEqual(formatted.financial_benefit.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, true);
    });

    await t.test('4. Direct cash assistance: scalar cash total is preserved', () => {
        const rawCash = {
            id: 'kisan_cash_04',
            slug: 'kisan_cash_04',
            name: 'PM Kisan Samman Nidhi',
            benefit_type: 'Cash',
            max_benefit: 6000,
            brief_description: 'Direct cash grant of Rs 6,000 disbursed via DBT'
        };

        const formatted = schemeService.formatSchemeRecord(rawCash);
        assert.strictEqual(formatted.max_benefit, 6000, 'Direct one-time or annual scalar cash total preserved');
        assert.strictEqual(formatted.financial_benefit.isScalarCashGrant, true);
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
    });

    await t.test('5. Incomplete canonical data: honest nulls without fabricated fallbacks', () => {
        const rawSparse = {
            id: 'sparse_welfare_05',
            slug: 'sparse_welfare_05',
            name: 'Unspecified Welfare Program',
            benefit_type: null,
            max_benefit: null,
            source_url: null,
            documents_required: null
        };

        const formatted = schemeService.formatSchemeRecord(rawSparse);
        assert.strictEqual(formatted.source_url, null, 'Must NOT default to generic government portal');
        assert.strictEqual(formatted.max_benefit, null);
        assert.deepStrictEqual(formatted.documents_required, []);
        assert.strictEqual(formatted.financial_benefit.category, BenefitCategories.UNKNOWN_OR_NOT_SPECIFIED);
        assert.strictEqual(formatted.financial_benefit.amountDisplay, 'Amount Specified in Guidelines');
    });

    await t.test('6. Unregistered scheme: deterministic fail-closed MANUAL_REVIEW with 0 rules executed', async () => {
        const result = await eligibilityService.checkEligibility(
            'applicant_test_123',
            'arbitrary_unregistered_scheme_999'
        );

        assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        assert.strictEqual(result.status, 'UNKNOWN');
        assert.strictEqual(result.isEligible, false);
        assert.strictEqual(result.rules.length, 0);
        assert.ok(result.verdictReason.includes('not registered') || result.verdictReason.includes('manual') || result.verdictReason.includes('Manual'));
    });

    await t.test('7. Official URL resolution: trusted government domains accepted, untrusted rejected', () => {
        const trustedUrls = [
            'https://myscheme.gov.in/schemes/pmkisan',
            'https://digitalgujarat.gov.in/housing',
            'https://scholarships.gov.in/post-matric'
        ];
        for (const url of trustedUrls) {
            const formatted = schemeService.formatSchemeRecord({ id: 't1', source_url: url });
            assert.strictEqual(formatted.source_url, url);
        }

        const untrustedUrls = [
            'https://sarkariyojana.com/apply',
            'https://www.google.com/search?q=yojana',
            'javascript:steal()',
            'http://clear-tax.in/yojana'
        ];
        for (const url of untrustedUrls) {
            const formatted = schemeService.formatSchemeRecord({ id: 'u1', source_url: url });
            assert.strictEqual(formatted.source_url, null, `Untrusted URL must be rejected: ${url}`);
        }
    });

    await t.test('8. Cross-scheme state isolation: consecutive formatting calls never leak properties', () => {
        const recordAlpha = schemeService.formatSchemeRecord({
            id: 'alpha_scheme',
            slug: 'alpha_scheme',
            name: 'Alpha Scheme',
            state: 'Punjab',
            level: 'State',
            benefit_type: 'Scholarship',
            max_benefit: 25000,
            source_url: 'https://punjab.gov.in/alpha'
        });

        const recordBeta = schemeService.formatSchemeRecord({
            id: 'beta_scheme',
            slug: 'beta_scheme',
            name: 'Beta Scheme',
            state: 'Assam',
            level: 'State',
            benefit_type: 'In Kind',
            max_benefit: null,
            source_url: null
        });

        // Invariant: Alpha properties must NOT leak into Beta
        assert.strictEqual(recordAlpha.id, 'alpha_scheme');
        assert.strictEqual(recordBeta.id, 'beta_scheme');
        assert.strictEqual(recordAlpha.state, 'Punjab');
        assert.strictEqual(recordBeta.state, 'Assam');
        assert.strictEqual(recordAlpha.source_url, 'https://punjab.gov.in/alpha');
        assert.strictEqual(recordBeta.source_url, null);
        assert.notStrictEqual(recordAlpha.financial_benefit.category, recordBeta.financial_benefit.category);
    });
});
