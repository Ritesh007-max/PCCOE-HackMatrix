const { test, describe } = require('node:test');
const assert = require('node:assert');
const { formatSchemeRecord, getFaqsBySchemeSlug } = require('../src/services/schemeService');
const { interpretFinancialBenefit } = require('../src/services/financialBenefitService');
const { checkEligibility } = require('../src/services/eligibilityService');

describe('Final Cross-Scheme Catalog Audit Backend Suite', () => {

    // 1. Direct Cash Benefit Scheme (e.g., PM-KISAN)
    test('1. Direct cash benefit scheme: derives scalar grant, central level, and valid portal', () => {
        const row = {
            id: 'pm-kisan',
            slug: 'pm-kisan',
            scheme_name: 'Pradhan Mantri Kisan Samman Nidhi',
            level: 'Central',
            state: 'All India',
            benefit_type: 'Cash',
            max_benefit: 6000,
            brief_description: 'Financial assistance of ₹6,000 per year in three equal four-monthly installments.',
            source_url: 'https://pmkisan.gov.in',
            documents_required: 'Aadhaar Card; Land Records; Bank Passbook',
            scheme_open_date: '2019-02-24',
            scheme_close_date: null
        };

        const formatted = formatSchemeRecord(row);
        assert.strictEqual(formatted.scheme_name, 'Pradhan Mantri Kisan Samman Nidhi');
        assert.strictEqual(formatted.level, 'Central');
        assert.strictEqual(formatted.state, 'All India');
        assert.strictEqual(formatted.financial_benefit.benefitType, 'Direct Financial Benefit');
        assert.strictEqual(formatted.financial_benefit.isScalarTotal, true);
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
        assert.strictEqual(formatted.financial_benefit.calculatorParameters, null);
        assert.strictEqual(formatted.source_url, 'https://pmkisan.gov.in');
        assert.strictEqual(formatted.documents_required.length, 3);
    });

    // 2. Scholarship & Fellowship Scheme (e.g., Ambedkar Fellowship / Research Fellowship)
    test('2. Scholarship / Fellowship scheme: identifies recurring stipend without loan calculator or lump-sum claim', () => {
        const row = {
            id: 'ambedkar-fellowship',
            slug: 'ambedkar-fellowship',
            scheme_name: 'Dr. Ambedkar Post-Doctoral Fellowship Scheme',
            level: 'Central',
            benefit_type: 'Fellowship',
            max_benefit: 54000,
            brief_description: 'Fellowship of ₹54,000 per month for SC researchers in social sciences.',
            source_url: 'https://socialjustice.gov.in/schemes/ambedkar-fellowship'
        };

        const formatted = formatSchemeRecord(row);
        assert.strictEqual(formatted.financial_benefit.benefitType, 'Fellowship / Stipend');
        assert.strictEqual(formatted.financial_benefit.isScalarTotal, false, 'Monthly stipend must not be labeled total entitlement');
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
        assert.strictEqual(formatted.financial_benefit.calculatorParameters, null);
    });

    // 3. Loans & Credit-Linked Subsidies (e.g., PMEGP with verified params vs unparameterized credit)
    test('3. Credit-linked scheme: enables calculator ONLY when verified params exist; disables safely when missing', () => {
        // A. Verified PMEGP
        const pmegpRow = {
            id: 'pmegp',
            slug: 'pmegp',
            scheme_name: "Prime Minister's Employment Generation Programme",
            benefit_type: 'Credit Linked Subsidy',
            brief_description: 'Credit-linked capital subsidy for micro-enterprises with 15% to 35% margin money.',
            calculator_parameters: {
                minProjectCost: 20000,
                maxProjectCost: 5000000,
                subsidyGrid: {
                    manufacturing: { rural: { special: 35, general: 25 }, urban: { special: 25, general: 15 } }
                }
            }
        };

        const formattedPmegp = formatSchemeRecord(pmegpRow);
        assert.strictEqual(formattedPmegp.financial_benefit.hasLoanCalculator, true);
        assert.ok(formattedPmegp.financial_benefit.calculatorParameters);

        // B. Unparameterized credit scheme
        const unparamRow = {
            id: 'unparam-credit',
            slug: 'unparam-credit',
            scheme_name: 'Generic Credit Scheme',
            benefit_type: 'Credit Linked Subsidy',
            brief_description: 'Interest subsidy on loans.'
        };

        const formattedUnparam = formatSchemeRecord(unparamRow);
        assert.strictEqual(formattedUnparam.financial_benefit.calculatorParameters, null, 'Must not fabricate parameters');
    });

    // 4. Penalty Waiver & Concession (e.g., 100% Penalty Mafi Yojana)
    test('4. Penalty waiver: categorized strictly as waiver, never loan, never subsidy', () => {
        const row = {
            id: '1pmy',
            slug: '1pmy',
            scheme_name: '100% Penalty Mafi Yojana',
            level: 'State',
            state: 'Gujarat',
            benefit_type: 'Penalty Waiver',
            benefits: '100% waiver on accrued interest and penalty charges for municipal tax arrears.',
            source_url: 'https://gujarat.gov.in/schemes/1pmy'
        };

        const formatted = formatSchemeRecord(row);
        assert.strictEqual(formatted.state, 'Gujarat');
        assert.strictEqual(formatted.level, 'State');
        assert.strictEqual(formatted.financial_benefit.benefitType, 'Penalty Waiver');
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
        assert.strictEqual(formatted.financial_benefit.calculatorParameters, null);
        assert.strictEqual(formatted.financial_benefit.isScalarCashGrant, false);
    });

    // 5. Housing & Social Welfare Scheme (e.g., PMAY)
    test('5. Housing welfare scheme: identifies capital subsidy grant without commercial loan fabrication', () => {
        const row = {
            id: 'pmay-g',
            slug: 'pmay-g',
            scheme_name: 'Pradhan Mantri Awaas Yojana - Gramin',
            level: 'Central',
            benefit_type: 'Direct Financial Benefit',
            max_benefit: 120000,
            brief_description: 'Financial assistance of ₹1,20,000 for construction of rural dwelling houses.'
        };

        const formatted = formatSchemeRecord(row);
        assert.ok(formatted.financial_benefit.benefitType === 'Composite' || formatted.financial_benefit.benefitType === 'Direct Financial Benefit');
        assert.strictEqual(formatted.financial_benefit.hasLoanCalculator, false);
        assert.strictEqual(formatted.financial_benefit.calculatorParameters, null);
    });

    // 6. Central vs State Government Jurisdiction
    test('6. Level and jurisdiction: state scheme preserves state name and state level without defaulting to Central', () => {
        const row = {
            id: 'uk-state-scheme',
            slug: 'uk-state-scheme',
            scheme_name: 'Uttarakhand Rural Mobility Support',
            state: 'Uttarakhand',
            level: 'State'
        };

        const formatted = formatSchemeRecord(row);
        assert.strictEqual(formatted.state, 'Uttarakhand');
        assert.strictEqual(formatted.level, 'State');
    });

    // 7. Schemes with Incomplete Metadata: honest unavailable states
    test('7. Incomplete metadata: missing fields evaluate to honest null/empty states without default placeholders', () => {
        const row = {
            id: 'incomplete-scheme-1',
            slug: 'incomplete-scheme-1',
            name: 'Incomplete Scheme Without Metadata',
            scheme_open_date: null,
            scheme_close_date: null,
            source_url: null,
            documents_required: null
        };

        const formatted = formatSchemeRecord(row);
        assert.strictEqual(formatted.scheme_open_date, null);
        assert.strictEqual(formatted.scheme_close_date, null);
        assert.strictEqual(formatted.source_url, null);
        assert.deepStrictEqual(formatted.documents_required, []);
    });

    // 8. Eligibility Integrity: unregistered scheme produces MANUAL_REVIEW with zero internal sentinels
    test('8. Eligibility integrity: unregistered scheme returns fail-closed MANUAL_REVIEW without automated evaluation claim', async () => {
        const result = await checkEligibility('user-test-123', 'arbitrary-unregistered-scheme', {
            date_of_birth: '1995-01-01',
            occupation: 'Software Engineer',
            annual_income: 500000
        });

        assert.strictEqual(result.status, 'UNKNOWN');
        assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        assert.strictEqual(result.evaluationCategory, 'UNREGISTERED_SCHEME');
        assert.strictEqual(result.isRegistered, false);
        assert.strictEqual(result.isEligible, false);
        assert.deepStrictEqual(result.rules, []);
    });

    // 9. FAQ Service: non-existent FAQs return honest notice, never fabricate Q&A
    test('9. FAQ service: missing FAQs return empty array and clean dataset notice without error', async () => {
        const result = await getFaqsBySchemeSlug('scheme-with-no-faqs-xyz');
        assert.strictEqual(result.total, 0);
        assert.deepStrictEqual(result.faqs, []);
        assert.ok(result.notice.includes('No scheme-specific FAQs'));
    });
});
