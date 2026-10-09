const { test, describe } = require('node:test');
const assert = require('node:assert');
const schemeService = require('../src/services/schemeService');
const {
    interpretFinancialBenefit,
    parseBenefitComponents,
    cleanPolicyText,
    BenefitCategories
} = require('../src/services/financialBenefitService');

describe('FIN Phase D3.9: Final Scheme Details Integrity Test Suite (Backend)', () => {

    // 1. YIPB: Canonical References & 5-Component Benefit Decomposition
    test('1. YIPB: Canonical references include authoritative portal and guidelines, 5 distinct benefit components', async () => {
        const canonicalMeta = schemeService.getCanonicalSchemeMetadata('yipb');
        assert.ok(canonicalMeta, 'YIPB canonical metadata must be present');
        assert.ok(Array.isArray(canonicalMeta.references), 'YIPB references must be an array');

        // Check authoritative URLs
        const hasPortal = canonicalMeta.references.some(r => r.includes('keralabiotech.kerala.gov.in'));
        const hasGuidelines = canonicalMeta.references.some(r => r.includes('YIPB_guidelines.pdf'));
        assert.ok(hasPortal, 'YIPB references must include https://keralabiotech.kerala.gov.in/?page_id=643');
        assert.ok(hasGuidelines, 'YIPB references must include verified guidelines PDF');

        // Benefits Decomposition
        const comps = parseBenefitComponents(canonicalMeta.benefits);
        assert.ok(comps.length >= 5, `Expected at least 5 components for YIPB, got ${comps.length}`);

        const fellowship = comps.find(c => c.benefitType === 'Fellowship / Stipend');
        assert.ok(fellowship);
        assert.strictEqual(fellowship.amount, 45000);
        assert.strictEqual(fellowship.frequency, 'monthly');
        assert.ok(fellowship.amountDisplay.includes('10% HRA'));

        const operational = comps.find(c => c.benefitType === 'Operational & Research Support');
        assert.ok(operational);
        assert.ok(operational.conditions.some(c => c.includes('Provided as project support')));

        const projectGrant = comps.find(c => c.benefitType === 'Research Project Grant');
        assert.ok(projectGrant);
        assert.strictEqual(projectGrant.amount, 3000000);
        assert.strictEqual(projectGrant.isCeiling, true);
        assert.strictEqual(projectGrant.duration, '3 years');

        const overhead = comps.find(c => c.benefitType === 'Institutional Overhead Charges');
        assert.ok(overhead);
        assert.strictEqual(overhead.isCeiling, true);
        assert.strictEqual(overhead.maxCeiling, '₹1.0 lakh');

        // Financial Safety
        const interp = interpretFinancialBenefit(canonicalMeta);
        assert.strictEqual(interp.isScalarTotal, false, 'YIPB must never be summed into a guaranteed lump sum');
        assert.strictEqual(interp.hasLoanCalculator, false, 'YIPB must never have loan calculator');
    });

    // 2. 1PMY (100% Penalty Mafi Yojana): Waiver Semantics & Safety
    test('2. 1PMY: 100% waiver semantics preserved without loan calculator or personal cash grant', () => {
        const raw1pmy = {
            id: '1pmy',
            scheme_name: '100% Penalty Mafi Yojana',
            department: 'Gujarat Housing Board',
            benefits: '100% complete waiver on interest and penalty arrears for commercial and residential tenements.'
        };

        const interp = interpretFinancialBenefit(raw1pmy);
        assert.strictEqual(interp.benefitType, 'Penalty Waiver');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarTotal, false);
        assert.strictEqual(interp.isScalarCashGrant, false);
    });

    // 3. PMEGP: Supported Credit-Linked Subsidy Grid
    test('3. PMEGP: margin money subsidy preserved with loan calculator and zero cash grant misclassification', () => {
        const pmegp = {
            id: 'pmegp',
            scheme_name: 'Prime Minister Employment Generation Programme',
            benefit_type: 'Credit Linked Subsidy',
            benefits: 'Margin money subsidy of 15% to 35% on project cost up to ₹50 lakhs for manufacturing and ₹20 lakhs for services.',
            brief_description: 'Credit linked subsidy scheme with 15%, 25%, and 35% margin money support'
        };

        const interp = interpretFinancialBenefit(pmegp);
        assert.strictEqual(interp.benefitType, 'Credit Linked Subsidy');
        assert.strictEqual(interp.hasLoanCalculator, true);
        assert.ok(interp.calculatorParameters != null);
        assert.strictEqual(interp.calculatorParameters.subsidyGrid.special.rural, 35);
        assert.strictEqual(interp.calculatorParameters.subsidyGrid.general.urban, 15);
        assert.strictEqual(interp.isScalarCashGrant, false);
    });

    // 4. Scholarship / Fellowship Scheme: Recurring Monthly Entitlement
    test('4. Fellowship scheme: recurring monthly assistance without guaranteed lump-sum claim', () => {
        const scholarship = {
            id: 'national-fellowship',
            scheme_name: 'National Doctoral Fellowship',
            benefit_type: 'Fellowship',
            benefits: 'Monthly fellowship of ₹31,000 plus HRA for eligible junior research scholars.'
        };

        const interp = interpretFinancialBenefit(scholarship);
        assert.strictEqual(interp.benefitType, 'Fellowship / Stipend');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarTotal, false);
        assert.strictEqual(interp.isScalarCashGrant, false);
    });

    // 5. Loan / Subsidy Scheme with Incomplete Parameters: Disabled Calculator
    test('5. Loan scheme with incomplete parameters: keeps calculator disabled without fabrication', () => {
        const unparamLoan = {
            id: 'unparam-loan',
            scheme_name: 'Stand-Up India Scheme',
            benefit_type: 'Loan',
            is_loan_scheme: true,
            brief_description: 'Bank loans between ₹10 lakh and ₹1 crore to at least one SC or ST borrower.'
        };

        const interp = interpretFinancialBenefit(unparamLoan);
        assert.strictEqual(interp.benefitType, 'Loan / Credit Facility');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 6. Scheme with Incomplete Official Data: Honest Unavailable States
    test('6. Incomplete official data: returns safe defaults without fabricating departments or URLs', () => {
        const incomplete = {
            id: 'unspecified-scheme-01',
            title: 'Community Welfare Support'
        };

        const interp = interpretFinancialBenefit(incomplete);
        assert.strictEqual(interp.category, BenefitCategories.UNKNOWN_OR_NOT_SPECIFIED);
        assert.strictEqual(interp.isUnverifiedOrUnavailable, true);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.calculatorParameters, null);
    });

    // 7. Non-Financial / In-Kind Scheme: Cashless Healthcare Classification
    test('7. Non-financial benefit scheme: cashless health coverage classified as in-kind, not cash grant', () => {
        const inKindScheme = {
            id: 'ayushman-bharat-backend',
            scheme_name: 'Ayushman Bharat - PM-JAY',
            benefit_type: 'In-Kind',
            benefits: 'Cashless healthcare coverage up to ₹5,00,000 per family per year for secondary and tertiary care.'
        };

        const interp = interpretFinancialBenefit(inKindScheme);
        assert.strictEqual(interp.benefitType, 'In-Kind Assistance');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarCashGrant, false);
        assert.strictEqual(interp.isScalarTotal, false);
    });
});
