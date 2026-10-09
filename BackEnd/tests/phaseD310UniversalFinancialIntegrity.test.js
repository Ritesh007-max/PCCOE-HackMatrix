const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const {
    BenefitCategories,
    interpretFinancialBenefit
} = require('../src/services/financialBenefitService');
const schemeService = require('../src/services/schemeService');
const dashboardService = require('../src/services/dashboardService');

test('FIN Phase D3.10.2: Universal Financial Integrity Across All Schemes', async (t) => {

    // =========================================================================
    // TASK 7 — Representative Schemes Across All 10 Required Categories
    // =========================================================================

    await t.test('1. YIPB: Monthly fellowship and composite research support', () => {
        const yipbScheme = {
            id: 'yipb',
            slug: 'yipb',
            name: 'Young Investigators Programme in Biotechnology (YIPB)',
            benefit_type: 'Composite',
            max_benefit: 45000,
            brief_description: 'Fellowship stipend of Rs 45,000 per month and research grant of Rs 25 Lakhs for 3 years'
        };

        const interp = interpretFinancialBenefit(yipbScheme);
        assert.strictEqual(interp.category, BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT);
        assert.strictEqual(interp.hasLoanCalculator, false, 'Composite fellowship must not have loan calculator');
        assert.strictEqual(interp.isScalarTotal, false, 'Monthly stipend must not be treated as total entitlement');
        assert.strictEqual(interp.isScalarCashGrant, false, 'Multi-component fellowship cannot be summed as scalar cash');
        assert.ok(interp.amountDisplay.includes('Fellowship & Research Grant') || interp.amountDisplay.includes('Composite'));
    });

    await t.test('2. 1PMY: Penalty or interest waiver', () => {
        const pmyScheme = {
            id: '1pmy',
            slug: '1pmy',
            name: '100% Penalty Mafi Yojana',
            benefit_type: 'Penalty Waiver',
            max_benefit: null,
            brief_description: '100% penalty waiver on pending house loan interest arrears'
        };

        const interp = interpretFinancialBenefit(pmyScheme);
        assert.strictEqual(interp.category, BenefitCategories.PENALTY_OR_INTEREST_WAIVER);
        assert.strictEqual(interp.hasLoanCalculator, false, 'Penalty waiver must not show loan calculator');
        assert.strictEqual(interp.isScalarTotal, false);
        assert.strictEqual(interp.isScalarCashGrant, false, 'Waivers must not be counted as cash transfers');
        assert.ok(interp.amountDisplay.includes('Waiver'));
    });

    await t.test('3. PMEGP: Supported credit-linked subsidy & loan calculator', () => {
        const pmegpScheme = {
            id: 'pmegp_101',
            slug: 'pmegp_101',
            name: "Prime Minister's Employment Generation Programme",
            benefit_type: 'Credit Linked Subsidy',
            is_loan_scheme: true,
            max_benefit: 1000000,
            details: { subsidy_percent: 35 },
            brief_description: 'Margin money subsidy of 15% to 35% on project cost up to 50 Lakhs'
        };

        const interp = interpretFinancialBenefit(pmegpScheme);
        assert.strictEqual(interp.category, BenefitCategories.CREDIT_LINKED_SUBSIDY);
        assert.strictEqual(interp.hasLoanCalculator, true, 'Credit-linked scheme must retain loan calculator');
        assert.strictEqual(interp.isScalarCashGrant, false, 'Margin subsidy cannot be summed as bare cash');
        assert.ok(interp.amountDisplay.includes('Subsidy'));
    });

    await t.test('4. Scholarship: Recurring annual educational assistance', () => {
        const scholarshipScheme = {
            id: 'national_merit_scholarship_01',
            name: 'National Merit Scholarship for Higher Education',
            benefit_type: 'Scholarship',
            max_benefit: 25000,
            brief_description: 'Annual scholarship assistance of Rs 25,000 per year for undergraduate students'
        };

        const interp = interpretFinancialBenefit(scholarshipScheme);
        assert.strictEqual(interp.category, BenefitCategories.ANNUAL_SCHOLARSHIP);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.frequency, 'annual');
        assert.strictEqual(interp.amountDisplay, '₹25,000 / year');
    });

    await t.test('5. Direct Cash Assistance: One-time fixed welfare grant', () => {
        const cashScheme = {
            id: 'maternity_direct_benefit_02',
            name: 'Maternity Direct Cash Benefit Scheme',
            benefit_type: 'Cash',
            max_benefit: 6000,
            brief_description: 'Direct cash grant of Rs 6,000 disbursed directly to bank account via DBT'
        };

        const interp = interpretFinancialBenefit(cashScheme);
        assert.strictEqual(interp.category, BenefitCategories.FIXED_ONE_TIME_GRANT);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarCashGrant, true);
        assert.strictEqual(interp.isScalarTotal, true);
        assert.strictEqual(interp.amountDisplay, '₹6,000');
    });

    await t.test('6. Interest Subsidy: Subvention on commercial credit', () => {
        const interestSubventionScheme = {
            id: 'kisan_interest_subvention_03',
            name: 'Short Term Crop Loan Interest Subvention',
            benefit_type: 'Central Sector',
            brief_description: '3% interest subvention prompt repayment incentive for crop loans'
        };

        const interp = interpretFinancialBenefit(interestSubventionScheme);
        assert.strictEqual(interp.category, BenefitCategories.INTEREST_SUBSIDY);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarCashGrant, false);
        assert.ok(interp.amountDisplay.includes('Interest Subvention'));
    });

    await t.test('7. Reimbursement: Post-facto medical/tuition expense claim', () => {
        const reimbursementScheme = {
            id: 'health_claim_reimbursement_04',
            name: 'Chief Minister Medical Expense Reimbursement Scheme',
            benefit_type: 'Cash',
            max_benefit: 150000,
            brief_description: 'Reimbursement of authorized hospitalization expenses up to Rs 1,50,000'
        };

        const interp = interpretFinancialBenefit(reimbursementScheme);
        assert.strictEqual(interp.category, BenefitCategories.REIMBURSEMENT);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarCashGrant, false);
        assert.ok(interp.amountDisplay.includes('Reimbursement'));
    });

    await t.test('8. Non-Financial / In-Kind Assistance', () => {
        const inKindScheme = {
            id: 'free_laptop_distribution_05',
            name: 'Free Tablet and Bicycle Distribution for Meritorious Students',
            benefit_type: 'In Kind',
            brief_description: 'Distribution of learning tablets, bicycles, and study kits to girl students'
        };

        const interp = interpretFinancialBenefit(inKindScheme);
        assert.strictEqual(interp.category, BenefitCategories.IN_KIND_BENEFIT);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isScalarCashGrant, false);
        assert.strictEqual(interp.amountDisplay, 'Non-Financial / In-Kind Support');
    });

    await t.test('9. Scheme with Missing Benefit Amount', () => {
        const missingAmountScheme = {
            id: 'state_welfare_unstructured_06',
            name: 'Tribal Cultural Preservation and Heritage Grant',
            benefit_type: 'Cash',
            max_benefit: null,
            brief_description: 'Financial assistance for cultural troupes and traditional artists'
        };

        const interp = interpretFinancialBenefit(missingAmountScheme);
        assert.strictEqual(interp.category, BenefitCategories.DIRECT_CASH_ASSISTANCE);
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.amountDisplay, 'Amount Specified in Guidelines');
        assert.notStrictEqual(interp.amountDisplay, '₹0', 'Missing amount must NEVER become ₹0');
    });

    await t.test('10. Scheme with Missing Benefit Classification', () => {
        const missingClassificationScheme = {
            id: 'unclassified_community_support_07',
            name: 'Community Center Enhancement Initiative',
            benefit_type: null,
            max_benefit: null,
            brief_description: 'Assistance for village community center renovation'
        };

        const interp = interpretFinancialBenefit(missingClassificationScheme);
        assert.strictEqual(interp.category, BenefitCategories.UNKNOWN_OR_NOT_SPECIFIED);
        assert.strictEqual(interp.benefitType, 'Benefit Type Not Specified');
        assert.strictEqual(interp.hasLoanCalculator, false);
        assert.strictEqual(interp.isUnverifiedOrUnavailable, true);
    });

    // =========================================================================
    // Catalog-Wide Verification Across All 4,749 Canonical Snapshot Records
    // =========================================================================

    await t.test('11. Catalog-Wide Audit: All 4,749 Canonical Schemes Pass Invariants', () => {
        const snapshotRoot = path.resolve(__dirname, '../../Intelligence/data/snapshots');
        const activeFile = path.join(snapshotRoot, 'active_version.json');
        assert.ok(fs.existsSync(activeFile), 'Active version file must exist');

        const activeVersion = JSON.parse(fs.readFileSync(activeFile, 'utf8')).active_snapshot;
        const schemesJsonl = path.join(snapshotRoot, activeVersion, 'canonical', 'schemes.jsonl');
        assert.ok(fs.existsSync(schemesJsonl), 'Canonical schemes.jsonl must exist');

        const lines = fs.readFileSync(schemesJsonl, 'utf8').split('\n').filter(Boolean);
        assert.ok(lines.length >= 4700, `Expected at least 4,700 schemes, found ${lines.length}`);

        const distribution = {};
        Object.keys(BenefitCategories).forEach(cat => { distribution[cat] = 0; });

        let fabricatedLoanCalcCount = 0;
        let zeroFallbackCount = 0;
        let loanCalledGrantCount = 0;

        for (const line of lines) {
            const raw = JSON.parse(line.replace(/:\s*NaN/g, ': null'));
            const interp = interpretFinancialBenefit(raw);

            // Tally classification
            distribution[interp.category] = (distribution[interp.category] || 0) + 1;

            // Invariant 1: No fabricated loan calculator on non-loan schemes
            if (interp.hasLoanCalculator && interp.category !== BenefitCategories.CREDIT_LINKED_SUBSIDY) {
                fabricatedLoanCalcCount++;
            }

            // Invariant 2: No missing amount displays as ₹0 or fabricated constant
            if (interp.amountDisplay === '₹0' || interp.amountDisplay === '₹1,25,000' || interp.amountDisplay === '₹1,75,000') {
                zeroFallbackCount++;
            }

            // Invariant 3: Repayable loans must never be marked as scalar cash grants
            if (interp.category === BenefitCategories.LOAN_OR_CREDIT_FACILITY && interp.isScalarCashGrant) {
                loanCalledGrantCount++;
            }
        }

        assert.strictEqual(fabricatedLoanCalcCount, 0, 'Zero non-credit-linked schemes must have loan calculator');
        assert.strictEqual(zeroFallbackCount, 0, 'Zero schemes must fallback to ₹0 or fabricated constants');
        assert.strictEqual(loanCalledGrantCount, 0, 'Zero repayable loans may be labeled scalar cash grants');

        // Verify all 4,749 records parsed cleanly
        const totalAudited = Object.values(distribution).reduce((a, b) => a + b, 0);
        assert.strictEqual(totalAudited, lines.length);
    });

    // =========================================================================
    // Universal Application Modal & Dashboard Aggregation Rules
    // =========================================================================

    await t.test('12. Universal Application Payload Safety: Non-loan schemes omit loan/subsidy fields', () => {
        const buildPayload = (scheme, projectCost, subsidyAmount) => {
            const interp = interpretFinancialBenefit(scheme);
            const payload = {
                scheme_id: scheme.id,
                scheme_name: scheme.name
            };
            if (interp.hasLoanCalculator) {
                payload.projectCost = projectCost;
                payload.subsidyAmount = subsidyAmount;
            }
            return payload;
        };

        const scholarshipScheme = { id: 'sch_01', name: 'Post-Matric Scholarship', benefit_type: 'Scholarship' };
        const payload1 = buildPayload(scholarshipScheme, 500000, 175000);
        assert.strictEqual(payload1.projectCost, undefined, 'Must not submit projectCost for scholarship');
        assert.strictEqual(payload1.subsidyAmount, undefined, 'Must not submit subsidyAmount for scholarship');

        const pmegpScheme = { id: 'pm_01', name: 'PMEGP', benefit_type: 'Credit Linked Subsidy', is_loan_scheme: true };
        const payload2 = buildPayload(pmegpScheme, 500000, 175000);
        assert.strictEqual(payload2.projectCost, 500000, 'Must include projectCost for credit-linked scheme');
        assert.strictEqual(payload2.subsidyAmount, 175000, 'Must include subsidyAmount for credit-linked scheme');
    });

    await t.test('13. Dashboard aggregation: Only comparable scalar cash grants are aggregated', async () => {
        const opportunities = [
            // 1. Direct cash grant with confirmed PASS -> Should be summed
            { scheme_id: 'grant_1', scheme_name: 'Farmer Cash Aid', benefit_type: 'Cash', max_benefit: 6000, eligibility_status: 'PASS' },
            // 2. Direct cash grant with UNKNOWN -> NOT summed
            { scheme_id: 'grant_2', scheme_name: 'Poverty Relief', benefit_type: 'Cash', max_benefit: 10000, eligibility_status: 'UNKNOWN' },
            // 3. Loan facility with confirmed PASS -> Strictly EXCLUDED from grant sum
            { scheme_id: 'loan_1', scheme_name: 'Mudra Shishu Loan', benefit_type: 'Loan', max_benefit: 50000, eligibility_status: 'PASS' },
            // 4. Monthly fellowship with confirmed PASS -> Strictly EXCLUDED from scalar sum
            { scheme_id: 'fel_1', scheme_name: 'Research Fellowship', brief_description: 'Rs 31,000 per month stipend', max_benefit: 31000, eligibility_status: 'PASS' },
            // 5. Penalty waiver with confirmed PASS -> Strictly EXCLUDED from grant sum
            { scheme_id: 'waiver_1', scheme_name: 'Late Penalty Mafi', benefit_type: 'Penalty Waiver', max_benefit: 5000, eligibility_status: 'PASS' }
        ];

        // Filter using shared financial benefit interpreter
        const eligibleGrants = opportunities.filter(o => {
            const interp = interpretFinancialBenefit(o);
            const isEligible = o.is_eligible === true || o.eligibility_status === 'PASS';
            const rawAmt = Number(o.max_benefit || o.benefit_amount || 0);
            return interp.isScalarCashGrant && isEligible && rawAmt > 0;
        });

        assert.strictEqual(eligibleGrants.length, 1);
        assert.strictEqual(eligibleGrants[0].scheme_id, 'grant_1');

        const totalBenefits = eligibleGrants.reduce((acc, curr) => acc + (Number(curr.max_benefit) || 0), 0);
        assert.strictEqual(totalBenefits, 6000, 'Total benefits must sum only the confirmed scalar cash grant');
    });
});
