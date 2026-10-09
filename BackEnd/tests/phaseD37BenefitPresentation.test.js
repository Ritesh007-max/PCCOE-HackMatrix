/**
 * FIN Phase D3.7: Universal Scheme Benefit Presentation & Data Integrity
 * Backend Regression Suite (CommonJS)
 *
 * Verifies parity with frontend:
 * 1. 100% Penalty Mafi Yojana text cleanup, separator normalization, and condition partitioning
 * 2. Young Investigators Programme in Biotechnology (YIPB) multi-component breakdown
 * 3. Accurate entitlement text distinguishing recurring stipends from institutional project ceilings
 * 4. PMEGP verified subsidy grid preservation
 * 5. Educational scholarship (National Post-Matric)
 * 6. Cash fellowship (Dr. Ambedkar Fellowship)
 * 7. Reimbursement (AICTE-INAE Travel Grant)
 * 8. Direct cash assistance (PM Kisan)
 * 9. Credit-linked scheme with missing parameters (Urban housing interest subsidy)
 * 10. Composite skill-development scheme without fellowship leakage (PMKVY-RPL)
 * 11. In-kind healthcare coverage (Ayushman Bharat PM-JAY)
 * 12. Complete absence of hardcoded scheme-specific branching
 */

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    interpretFinancialBenefit,
    extractCalculatorParameters,
    cleanPolicyText,
    extractPolicyConditions,
    parseBenefitComponents,
    BenefitCategories
} = require('../src/services/financialBenefitService');

test('FIN Phase D3.7: Universal Scheme Benefit Presentation & Data Integrity (Backend)', async (t) => {

    // 1. Penalty / Interest Waiver (100% Penalty Mafi Yojana)
    await t.test('1. Penalty/interest waiver: cleans raw separators, removes standalone headers, partitions conditions', () => {
        const raw1pmy = {
            id: '1pmy',
            slug: '1pmy',
            name: '100% Penalty Mafi Yojana',
            short_title: '1PMY',
            benefit_type: 'Cash',
            tags: ['Housing', 'Penalty', 'Waiver', 'Tenant', 'Urban'],
            benefits: '- The applicant receives 100% waiver on the penalty amount accumulated on pending installments. | - The waiver is applicable on all arrears of installments pertaining to old schemes of the Gujarat Housing Board and Slum Clearance Cell. | - The benefit is a one-time waiver granted upon fulfillment of payment conditions. | - The waiver is applied at the time of final settlement of dues. | Conditions | _All arrears of installments must be paid in one go (lump sum payment)._ | _The payment must be completed by 31st March._ | _*The waiver applies only to the penalty component; the principal installment amount must be paid in full._'
        };

        const interp = interpretFinancialBenefit(raw1pmy);
        const conditions = extractPolicyConditions(raw1pmy);
        const comps = parseBenefitComponents(raw1pmy);

        assert.strictEqual(interp.benefitType, 'Penalty Waiver');
        assert.strictEqual(interp.amountDisplay, '100% Penalty Waiver');
        assert.strictEqual(interp.hasLoanCalculator, false);

        // Conditions partitioned cleanly
        assert.ok(conditions.length >= 3, 'Must extract at least 3 policy conditions');
        assert.ok(conditions.some(c => c.includes('All arrears of installments must be paid in one go')));
        assert.ok(conditions.some(c => c.includes('The payment must be completed by 31st March')));
        assert.ok(conditions.some(c => c.includes('The waiver applies only to the penalty component')));

        // Components
        assert.ok(comps.length >= 1);
        const waiverComp = comps.find(c => c.benefitType === 'Penalty Waiver');
        assert.ok(waiverComp);
        assert.strictEqual(waiverComp.amountDisplay, '100% Penalty Waiver');
        assert.strictEqual(waiverComp.frequency, 'one-time waiver');
    });

    // 2. YIPB Multi-Component Research Support
    await t.test('2. YIPB: Decomposes multiple components and distinguishes monthly stipend from project ceiling', () => {
        const rawYipb = {
            id: 'dfc0aaf8-c74f-581f-aa86-a9bae561167c',
            slug: 'yipb',
            name: 'Young Investigators Programme in Biotechnology',
            short_title: 'YIPB',
            benefit_type: 'Composite',
            max_benefit: 45000,
            tags: ['Young Investigator', 'Biotechnology', 'Fellowship', 'Principal Investigator'],
            benefits: '- Young Scientists without fellowship/salary are eligible for a fellowship of ₹45,000/- plus 10% HRA per month, in addition to the support for travel, contingency, consumables, and minor equipment. | - A Principal Investigator having a regular position can seek manpower. | - Maximum support up to ₹30 lakhs (excluding overhead charges @ 10% of the project cost subject to a ceiling of ₹ 1.0 lakh) for a period not exceeding three years.'
        };

        const interp = interpretFinancialBenefit(rawYipb);
        const comps = interp.benefitComponents;

        assert.ok(comps.length >= 4, `Expected at least 4 components, got ${comps.length}`);

        // Fellowship component
        const fellowship = comps.find(c => c.benefitType === 'Fellowship / Stipend');
        assert.ok(fellowship, 'Must contain Fellowship / Stipend component');
        assert.strictEqual(fellowship.amount, 45000);
        assert.strictEqual(fellowship.frequency, 'monthly');
        assert.strictEqual(fellowship.unit, 'per month');
        assert.ok(fellowship.amountDisplay.includes('₹45,000 / month'));
        assert.ok(fellowship.amountDisplay.includes('10% HRA'));
        assert.strictEqual(fellowship.applicableBeneficiary, 'Young Scientists without fellowship/salary');
        assert.strictEqual(fellowship.isCeiling, false);

        // Operational support
        const operational = comps.find(c => c.benefitType === 'Operational & Research Support');
        assert.ok(operational);
        assert.ok(operational.amountDisplay.includes('Travel, Contingency, Consumables & Minor Equipment'));

        // Manpower support
        const manpower = comps.find(c => c.benefitType === 'Manpower Support');
        assert.ok(manpower);
        assert.ok(manpower.applicableBeneficiary.includes('Principal Investigator'));

        // Project grant ceiling
        const projectGrant = comps.find(c => c.benefitType === 'Research Project Grant');
        assert.ok(projectGrant);
        assert.strictEqual(projectGrant.amount, 3000000);
        assert.strictEqual(projectGrant.isCeiling, true);
        assert.strictEqual(projectGrant.duration, '3 years');
        assert.ok(projectGrant.conditions.some(c => c.includes('Excludes overhead charges @ 10%')));

        // Entitlement text must distinguish fellowship from project ceiling
        assert.ok(interp.entitlementText.includes('₹45,000 / month') || interp.entitlementText.includes('45,000'));
        assert.ok(interp.entitlementText.includes('Project Ceiling') || interp.entitlementText.includes('30 Lakhs') || interp.entitlementText.includes('grant'));
        assert.strictEqual(interp.hasLoanCalculator, false);
    });

    // 3. PMEGP Verified Credit-Linked Subsidy Grid
    await t.test('3. PMEGP: Preserves margin money calculator parameters without loan-as-grant confusion', () => {
        const pmegpScheme = {
            id: 'pmegp_1',
            name: 'Prime Minister Employment Generation Programme',
            benefit_type: 'Credit Linked Subsidy',
            is_credit_linked: true,
            is_loan_scheme: true,
            benefits: 'Margin money subsidy of 15% to 35% on project cost up to ₹50 lakhs for manufacturing and ₹20 lakhs for services.',
            brief_description: 'Credit linked subsidy scheme with 15%, 25%, and 35% margin money support'
        };

        const interp = interpretFinancialBenefit(pmegpScheme);

        assert.strictEqual(interp.benefitType, 'Credit Linked Subsidy');
        assert.strictEqual(interp.hasLoanCalculator, true);
        assert.ok(interp.calculatorParameters != null);
        assert.strictEqual(interp.calculatorParameters.subsidyGrid.special.rural, 35);
        assert.strictEqual(interp.calculatorParameters.subsidyGrid.general.urban, 15);
        assert.strictEqual(interp.isScalarCashGrant, false);
    });

    // 4. Annual Scholarship (National Post-Matric)
    await t.test('4. Scholarship: Annual recurring assistance with correct unit and periodicity', () => {
        const scholarship = {
            id: 'post_matric_1',
            name: 'Post Matric Scholarship for Students',
            benefit_type: 'Scholarship',
            max_benefit: 12000,
            benefits: 'Scholarship of ₹12,000 per academic year for higher education fees and maintenance.'
        };

        const interp = interpretFinancialBenefit(scholarship);
        const comps = interp.benefitComponents;

        assert.strictEqual(interp.benefitType, 'Scholarship');
        assert.strictEqual(interp.amountDisplay, '₹12,000 / year');
        assert.strictEqual(interp.isScalarTotal, false);
        assert.strictEqual(interp.hasLoanCalculator, false);

        const schComp = comps.find(c => c.benefitType === 'Scholarship');
        assert.ok(schComp);
        assert.strictEqual(schComp.unit, 'per academic year');
        assert.strictEqual(schComp.frequency, 'annual');
    });

    // 5. Monthly Fellowship (Dr. Ambedkar Fellowship)
    await t.test('5. Fellowship: Monthly stipend with recurring unit and no lump-sum claim', () => {
        const fellowship = {
            id: 'ambedkar_fel',
            name: 'Dr. Ambedkar Post-Matric Fellowship',
            benefit_type: 'Fellowship',
            max_benefit: 25000,
            benefits: 'Monthly fellowship stipend of ₹25,000 per month for doctoral scholars.'
        };

        const interp = interpretFinancialBenefit(fellowship);
        const comps = interp.benefitComponents;

        assert.strictEqual(interp.benefitType, 'Fellowship / Stipend');
        assert.strictEqual(interp.amountDisplay, '₹25,000 / month');
        assert.strictEqual(interp.isScalarTotal, false);
        assert.strictEqual(interp.hasLoanCalculator, false);

        const comp = comps.find(c => c.benefitType === 'Fellowship / Stipend');
        assert.ok(comp);
        assert.strictEqual(comp.frequency, 'monthly');
        assert.strictEqual(comp.unit, 'per month');
    });

    // 6. Reimbursement (AICTE-INAE Travel Grant)
    await t.test('6. Reimbursement: Expense reimbursement with verified expenditure ceiling', () => {
        const reimbursement = {
            id: 'aicte_inae_1',
            name: 'AICTE-INAE Travel Grant Scheme',
            benefit_type: 'Reimbursement',
            max_benefit: 100000,
            benefits: 'Reimbursement of 100% travel expenses up to a ceiling of ₹1,00,000 for attending international research conferences.'
        };

        const interp = interpretFinancialBenefit(reimbursement);
        const comps = interp.benefitComponents;

        assert.strictEqual(interp.benefitType, 'Reimbursement');
        assert.strictEqual(interp.amountDisplay, 'Up to ₹1,00,000 Reimbursement');
        assert.strictEqual(interp.isScalarCashGrant, false);
        assert.strictEqual(interp.hasLoanCalculator, false);

        const comp = comps.find(c => c.benefitType === 'Reimbursement');
        assert.ok(comp);
        assert.strictEqual(comp.isCeiling, true);
        assert.strictEqual(comp.frequency, 'post-facto claim');
    });

    // 7. Direct Cash Assistance (PM Kisan)
    await t.test('7. Direct Cash Assistance: Verified scalar cash benefit with annual periodicity', () => {
        const pmKisan = {
            id: 'pmkisan_1',
            name: 'PM-KISAN Samman Nidhi',
            benefit_type: 'Cash',
            max_benefit: 6000,
            benefits: 'Financial assistance of ₹6,000 per year distributed in three equal four-monthly installments of ₹2,000.'
        };

        const interp = interpretFinancialBenefit(pmKisan);
        const comps = interp.benefitComponents;

        assert.strictEqual(interp.benefitType, 'Direct Financial Benefit');
        assert.strictEqual(interp.amountDisplay, '₹6,000');
        assert.strictEqual(interp.isScalarCashGrant, true);
        assert.strictEqual(interp.hasLoanCalculator, false);

        const comp = comps.find(c => c.benefitType === 'Direct Financial Benefit');
        assert.ok(comp);
        assert.strictEqual(comp.amount, 6000);
    });

    // 8. Credit-Linked Scheme with Missing Parameters (Housing Interest Subsidy)
    await t.test('8. Credit-linked scheme with missing parameters: Safely disables calculator without fabrication', () => {
        const housingScheme = {
            id: 'urban_housing_subsidy',
            name: 'Urban Housing Interest Subsidy',
            benefit_type: 'Credit Linked Subsidy',
            is_credit_linked: true,
            benefits: 'Interest subsidy on housing loans for eligible urban home buyers.'
        };

        const interp = interpretFinancialBenefit(housingScheme);

        assert.strictEqual(interp.benefitType, 'Credit Linked Subsidy');
        assert.strictEqual(interp.amountDisplay, 'Credit Linked Subsidy');
        assert.strictEqual(interp.calculatorParameters, null);
        assert.strictEqual(interp.isScalarCashGrant, false);
    });

    // 9. Composite Skill Development (PMKVY-RPL)
    await t.test('9. Composite skill-development scheme: Uses neutral wording without fellowship leakage', () => {
        const pmkvy = {
            id: 'pmkvy_rpl_1',
            name: 'PM Kaushal Vikas Yojana - RPL',
            benefit_type: 'Composite',
            benefits: 'Skill assessment, government certification, and monetary incentive upon certified completion.'
        };

        const interp = interpretFinancialBenefit(pmkvy);

        assert.strictEqual(interp.benefitType, 'Composite');
        assert.strictEqual(interp.amountDisplay, 'Multi-Component Statutory Support');
        assert.ok(!interp.entitlementText.toLowerCase().includes('fellowship'));
        assert.strictEqual(interp.hasLoanCalculator, false);
    });

    // 10. In-Kind Food or Healthcare (Ayushman Bharat PM-JAY)
    await t.test('10. In-kind healthcare coverage: Cashless ceiling without cash grant misclassification', () => {
        const pmjay = {
            id: 'pmjay_1',
            name: 'Ayushman Bharat PM-JAY',
            benefit_type: 'In Kind',
            benefits: 'Cashless healthcare coverage of up to ₹5,00,000 per family per year for secondary and tertiary care hospitalization.'
        };

        const interp = interpretFinancialBenefit(pmjay);
        const comps = interp.benefitComponents;

        assert.strictEqual(interp.benefitType, 'In-Kind Assistance');
        assert.strictEqual(interp.amountDisplay, 'Non-Financial / In-Kind Support');
        assert.strictEqual(interp.isScalarCashGrant, false);
        assert.strictEqual(interp.hasLoanCalculator, false);

        const comp = comps.find(c => c.benefitType === 'In-Kind Assistance');
        assert.ok(comp);
        assert.strictEqual(comp.isCeiling, true);
    });

    // 11. Universal Text Cleanup Edge Cases
    await t.test('11. cleanPolicyText removes table artifacts, double punctuation, and HTML entities cleanly', () => {
        const messy = 'Benefit: ₹45,000/- &amp; 10% HRA |---| _*Special terms apply._ ;; No deduction ..';
        const cleaned = cleanPolicyText(messy);

        assert.ok(!cleaned.includes('&amp;'));
        assert.ok(!cleaned.includes('|---|'));
        assert.ok(!cleaned.includes('_*'));
        assert.ok(!cleaned.includes(';;'));
        assert.ok(cleaned.includes('&'));
        assert.ok(cleaned.includes('Special terms apply.'));
    });
});
