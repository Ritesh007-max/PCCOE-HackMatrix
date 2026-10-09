/**
 * FIN Phase D3.6: Universal Financial Benefit Integrity & Dynamic Calculator Refactor
 * Backend Regression Suite (CommonJS)
 *
 * Requirements:
 * 1. Finding 1: Composite Entitlement Text Leakage
 *    - Generic composite schemes use neutral wording without fellowship leakage
 *    - Fellowship wording appears only with explicit evidence
 * 2. Finding 2: Cash Benefits Misclassified as In-Kind
 *    - Cash fellowships remain fellowship/stipend despite training keywords
 *    - Reimbursements remain reimbursement
 *    - Genuine in-kind benefits classify as in-kind
 * 3. Finding 3: Hardcoded PMEGP Calculator Parameters
 *    - Unsupported credit-linked schemes do NOT get PMEGP 15%/25%/35% parameters
 *    - Genuine PMEGP parameters are preserved
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

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    interpretFinancialBenefit,
    extractCalculatorParameters,
    BenefitCategories
} = require('../src/services/financialBenefitService');

test('FIN Phase D3.6: Universal Financial Benefit Integrity & Dynamic Calculator Refactor (Backend)', async (t) => {

    // 1. YIPB Fellowship
    await t.test('1. YIPB: Monthly fellowship and research support preserves fellowship breakdown', () => {
        const scheme = {
            id: 'yipb_01',
            name: 'Young Investigators Programme in Biotechnology',
            benefit_type: 'Composite',
            max_benefit: 45000,
            brief_description: 'Fellowship of Rs 45,000 per month and research project grant of 25 Lakhs'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT);
        assert.strictEqual(interp.benefitType, 'Composite');
        assert.ok(interp.entitlementText.includes('Monthly fellowship stipend + research project grant'));
        assert.strictEqual(interp.isScalarTotal, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 2. Ambedkar Fellowship Scheme
    await t.test('2. Ambedkar Fellowship Scheme: Cash fellowship remains fellowship despite skill training mention', () => {
        const scheme = {
            id: 'ambedkar_02',
            name: 'Dr. Ambedkar National Fellowship for SC Students',
            benefit_type: 'Fellowship',
            max_benefit: 31000,
            brief_description: 'Monthly fellowship allowance of Rs 31,000 per month and skill training support'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.MONTHLY_FELLOWSHIP_OR_STIPEND);
        assert.strictEqual(interp.benefitType, 'Fellowship / Stipend');
        assert.notStrictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT,
            'Cash fellowship must NOT be misclassified as in-kind');
        assert.strictEqual(interp.amountDisplay, '₹31,000 / month');
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 3. AICTE-INAE Travel Grant
    await t.test('3. AICTE-INAE Travel Grant: Reimbursement scheme remains reimbursement', () => {
        const scheme = {
            id: 'aicte_03',
            name: 'AICTE-INAE Travel Grant Scheme',
            benefit_type: 'Reimbursement',
            max_benefit: 100000,
            brief_description: 'Reimbursement of airfare and registration for research presentation'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.REIMBURSEMENT);
        assert.strictEqual(interp.benefitType, 'Reimbursement');
        assert.notStrictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT);
        assert.ok(interp.amountDisplay.includes('Reimbursement'));
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 4. PM Kaushal Vikas Yojana - Recognition of Prior Learning (PMKVY-RPL)
    await t.test('4. PMKVY-RPL: Generic composite scheme uses neutral wording without fellowship leakage', () => {
        const scheme = {
            id: 'pmkvy_04',
            name: 'PM Kaushal Vikas Yojana - Recognition of Prior Learning',
            benefit_type: 'Composite',
            brief_description: 'Skill certification, accidental insurance cover, and monetary reward on successful candidate assessment'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT);
        assert.strictEqual(interp.benefitType, 'Composite');
        assert.strictEqual(interp.amountDisplay, 'Multi-Component Statutory Support');
        assert.ok(interp.entitlementText.includes('Multi-component statutory support combining financial and operational assistance'));
        assert.strictEqual(interp.entitlementText.includes('fellowship'), false,
            'Generic composite scheme must NEVER leak fellowship wording');
        assert.strictEqual(interp.entitlementText.includes('research project grant'), false,
            'Generic composite scheme must NEVER leak research grant wording');
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 5. PMEGP (Supported Credit-Linked Subsidy)
    await t.test('5. PMEGP: Supported credit-linked subsidy preserves margin money parameters', () => {
        const scheme = {
            id: 'pmegp_05',
            name: "Prime Minister's Employment Generation Programme (PMEGP)",
            benefit_type: 'Credit Linked Subsidy',
            is_loan_scheme: true,
            details: {
                subsidy_grid: {
                    special: { rural: 35, urban: 25, own: 5 },
                    general: { rural: 25, urban: 15, own: 10 }
                },
                min_project_cost: 50000,
                max_project_cost: 5000000
            },
            brief_description: 'Margin money subsidy of 15% to 35% on micro enterprise project investments'
        };
        const interp = interpretFinancialBenefit(scheme);
        const params = extractCalculatorParameters(scheme, scheme.name.toLowerCase());

        assert.strictEqual(interp.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
        assert.strictEqual(interp.benefitType, 'Credit Linked Subsidy');
        assert.strictEqual(interp.hasLoanCalculator, true);
        assert.ok(params != null, 'PMEGP parameters must be extracted');
        assert.strictEqual(params.subsidyGrid.special.rural, 35);
        assert.strictEqual(params.subsidyGrid.general.urban, 15);
    });

    // 6. 100% Penalty Mafi Yojana
    await t.test('6. 100% Penalty Mafi Yojana: Waiver behavior preserved without loan calculator', () => {
        const scheme = {
            id: '1pmy_06',
            name: '100% Penalty Mafi Yojana',
            benefit_type: 'Penalty Waiver',
            brief_description: '100% waiver on accumulated late payment penalty interest on pending installments'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.PENALTY_OR_INTEREST_WAIVER);
        assert.strictEqual(interp.benefitType, 'Penalty Waiver');
        assert.strictEqual(interp.amountDisplay, '100% Penalty Waiver');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 7. Agriculture subsidy
    await t.test('7. Agriculture subsidy: Capital grant subsidy without loan calculator fabrication', () => {
        const scheme = {
            id: 'agri_07',
            name: 'Sub-Mission on Agricultural Mechanization (SMAM)',
            benefit_type: 'Direct Financial Benefit',
            dbt_scheme: true,
            max_benefit: 50000,
            brief_description: 'Financial assistance and capital subsidy grant for purchase of modern farm machinery'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.FIXED_ONE_TIME_GRANT);
        assert.strictEqual(interp.benefitType, 'Direct Financial Benefit');
        assert.strictEqual(interp.amountDisplay, '₹50,000');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 8. Housing loan subsidy (without statutory subsidy parameters)
    await t.test('8. Housing loan subsidy: Unparameterized credit scheme produces null calculatorParameters', () => {
        const scheme = {
            id: 'housing_08',
            name: 'Affordable Housing Credit Linked Subsidy Scheme',
            benefit_type: 'Credit Linked Subsidy',
            is_loan_scheme: true,
            brief_description: 'Credit linked subsidy on home loans for eligible urban beneficiaries'
        };
        const interp = interpretFinancialBenefit(scheme);
        const params = extractCalculatorParameters(scheme, scheme.name.toLowerCase());

        assert.strictEqual(interp.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
        assert.strictEqual(interp.benefitType, 'Credit Linked Subsidy');
        assert.strictEqual(interp.hasLoanCalculator, true);
        assert.strictEqual(params, null, 'Must NOT fabricate PMEGP margin money parameters');
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 9. Direct cash assistance
    await t.test('9. Direct cash assistance: Explicit cash assistance preserves scalar grant', () => {
        const scheme = {
            id: 'kisan_09',
            name: 'PM Kisan Samman Nidhi',
            benefit_type: 'Cash',
            dbt_scheme: true,
            max_benefit: 6000,
            brief_description: 'Income support of Rs 6,000 per year directly into bank accounts of farmers'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.FIXED_ONE_TIME_GRANT);
        assert.strictEqual(interp.benefitType, 'Direct Financial Benefit');
        assert.strictEqual(interp.amountDisplay, '₹6,000');
        assert.strictEqual(interp.isScalarCashGrant, true);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 10. Healthcare / In-Kind Benefit
    await t.test('10. Healthcare / In-kind benefit: Accurately classified as in-kind without cash confusion', () => {
        const scheme = {
            id: 'pmjay_10',
            name: 'Ayushman Bharat - PM Jan Arogya Yojana',
            benefit_type: 'In Kind',
            brief_description: 'Cashless access to healthcare services for priority families up to Rs 5 lakh coverage'
        };
        const interp = interpretFinancialBenefit(scheme);

        assert.strictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT);
        assert.strictEqual(interp.benefitType, 'In-Kind Assistance');
        assert.strictEqual(interp.amountDisplay, 'Non-Financial / In-Kind Support');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });
});
