/**
 * FIN Centralized Financial Benefit Interpretation Service (Phase D3.10.2)
 *
 * Universal, data-driven financial benefit interpreter across the entire FIN catalog.
 * Strict non-negotiable principles:
 * 1. AI interprets -> Rules decide -> Evidence proves -> Human reviews uncertainty.
 * 2. Zero scheme-name-specific or slug-specific hardcoding.
 * 3. Categorizes and extracts structured financial characteristics across:
 *    - Fixed one-time grant
 *    - Monthly fellowship or stipend
 *    - Annual scholarship
 *    - Research grant / composite
 *    - Loan principal or credit facility
 *    - Capital / margin money subsidy
 *    - Interest subsidy
 *    - Penalty or interest waiver
 *    - Reimbursement
 *    - In-kind assistance / non-financial
 *    - Unknown / Not Specified
 * 4. Ensures loan debt is never called a grant, monthly stipends are not lump-sum totals,
 *    and dashboard aggregation sums ONLY verified, comparable scalar welfare grants.
 */

const BenefitCategories = Object.freeze({
    PENALTY_OR_INTEREST_WAIVER: 'PENALTY_OR_INTEREST_WAIVER',
    CREDIT_LINKED_SUBSIDY: 'CREDIT_LINKED_SUBSIDY',
    INTEREST_SUBSIDY: 'INTEREST_SUBSIDY',
    LOAN_OR_CREDIT_FACILITY: 'LOAN_OR_CREDIT_FACILITY',
    MONTHLY_FELLOWSHIP_OR_STIPEND: 'MONTHLY_FELLOWSHIP_OR_STIPEND',
    COMPOSITE_FINANCIAL_SUPPORT: 'COMPOSITE_FINANCIAL_SUPPORT',
    ANNUAL_SCHOLARSHIP: 'ANNUAL_SCHOLARSHIP',
    REIMBURSEMENT: 'REIMBURSEMENT',
    IN_KIND_BENEFIT: 'IN_KIND_BENEFIT',
    FIXED_ONE_TIME_GRANT: 'FIXED_ONE_TIME_GRANT',
    DIRECT_CASH_ASSISTANCE: 'DIRECT_CASH_ASSISTANCE',
    UNKNOWN_OR_NOT_SPECIFIED: 'UNKNOWN_OR_NOT_SPECIFIED'
});

/**
 * /**
 * Extract verified credit-linked subsidy calculator parameters from canonical scheme data.
 *
 * Strict safety rules:
 * 1. Parameters must come from explicit structured metadata or traceable statutory policy text.
 * 2. Never infer statutory subsidy percentages from scheme names, slugs, or broad categories.
 * 3. Credit-linked schemes without verified parameters must return null (disabling the calculator).
 */
function extractCalculatorParameters(scheme, textTokens = '') {
    if (!scheme || typeof scheme !== 'object') return null;

    // 1. Explicit structured calculator parameters on scheme
    const explicitParams = scheme.calculator_parameters || scheme.calculatorParameters || scheme.details?.calculator_parameters;
    if (explicitParams && (explicitParams.subsidyGrid || explicitParams.flatSubsidyPercent != null)) {
        return explicitParams;
    }

    // 2. Structured subsidy grid in scheme.details
    if (scheme.details?.subsidy_grid) {
        return {
            subsidyGrid: scheme.details.subsidy_grid,
            ownContributionGrid: scheme.details.own_contribution_grid || { special: 5, general: 10 },
            minProjectCost: scheme.details.min_project_cost || 50000,
            maxProjectCost: scheme.details.max_project_cost || 5000000,
            defaultProjectCost: scheme.details.default_project_cost || 1000000,
            interestRate: scheme.details.interest_rate || 0.09,
            tenureMonths: scheme.details.tenure_months || 84,
            presets: scheme.details.presets || [200000, 500000, 1000000, 2500000, 5000000],
            isGridModel: true
        };
    }

    // 3. Flat subsidy percentage in scheme.details
    if (scheme.details?.subsidy_percent != null && !isNaN(Number(scheme.details.subsidy_percent))) {
        const flatPercent = Number(scheme.details.subsidy_percent);
        return {
            flatSubsidyPercent: flatPercent,
            ownPercent: scheme.details.own_percent != null ? Number(scheme.details.own_percent) : 10,
            minProjectCost: scheme.details.min_project_cost || 50000,
            maxProjectCost: scheme.details.max_project_cost || 5000000,
            defaultProjectCost: scheme.details.default_project_cost || 500000,
            interestRate: scheme.details.interest_rate || 0.09,
            tenureMonths: scheme.details.tenure_months || 84,
            presets: scheme.details.presets || [100000, 250000, 500000, 1000000, 2500000],
            isGridModel: false
        };
    }

    // 4. Traceable statutory margin money policy rules in canonical text
    // Only where policy text explicitly documents the margin money subsidy percentages (15%, 25%, 35%)
    const hasMarginMoney = textTokens.includes('margin money');
    const has15 = textTokens.includes('15%');
    const has25 = textTokens.includes('25%');
    const has35 = textTokens.includes('35%');

    if ((hasMarginMoney && has15 && has35) || (hasMarginMoney && has15 && has25)) {
        return {
            subsidyGrid: {
                special: { rural: 35, urban: 25, own: 5 },
                general: { rural: 25, urban: 15, own: 10 }
            },
            ownContributionGrid: { special: 5, general: 10 },
            minProjectCost: 50000,
            maxProjectCost: 5000000,
            defaultProjectCost: 1000000,
            interestRate: 0.09,
            tenureMonths: 84,
            presets: [200000, 500000, 1000000, 2500000, 5000000],
            isGridModel: true
        };
    }

    return null;
}

const STANDALONE_HEADER_REGEX = /^(conditions?|terms\s*(and|&)\s*conditions?|general\s*conditions?|eligibility\s*conditions?|rules?|important\s*notes?|notes?|benefits?|guidelines?|selection\s*procedure|criteria|disability\s*benefits?|life\s*insurance\s*coverage|application\s*deadline):?$/i;

/**
 * Universal text cleanup:
 * Removes HTML entities, markdown bold/italics, backslash escapes,
 * table separators, and duplicated punctuation while preserving
 * numbers, conditions, and meaningful qualifiers.
 */
function cleanPolicyText(text) {
    if (!text || typeof text !== 'string') return '';
    let cleaned = text
        .replace(/&amp;/g, '&')
        .replace(/&nbsp;/g, ' ')
        .replace(/&quot;/g, '"')
        .replace(/&#39;|&apos;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&ndash;/g, '–')
        .replace(/&mdash;/g, '—')
        .replace(/&#8377;/g, '₹');

    cleaned = cleaned.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '$1');
    cleaned = cleaned.replace(/\*([^*]+)\*/g, '$1');
    cleaned = cleaned.replace(/__([^_]+)__/g, '$1');
    cleaned = cleaned.replace(/_([^_]+)_/g, '$1');
    cleaned = cleaned.replace(/(_\s*\*|\*\s*_)(.+?)(_\s*\*|\*\s*_|\*|_)/g, '$2');
    cleaned = cleaned.replace(/\\([*_~`#|])/g, '$1');
    cleaned = cleaned.replace(/\|[\s\-:]+\|/g, ' ');
    cleaned = cleaned.replace(/;{2,}/g, ';');
    cleaned = cleaned.replace(/\.{3,}/g, '...');
    cleaned = cleaned.replace(/\.{2}/g, '.');
    cleaned = cleaned.replace(/\/{2,}/g, '/');
    return cleaned.trim();
}

/**
 * Extract policy conditions and compliance requirements from benefit text.
 * Strictly separates procedural/eligibility conditions from benefit entitlements.
 */
function extractPolicyConditions(scheme) {
    if (!scheme || typeof scheme !== 'object') return [];
    const rawBenefits = scheme.benefits || scheme.benefit_summary || scheme.financial_assistance || '';
    if (!rawBenefits || typeof rawBenefits !== 'string') return [];

    const items = rawBenefits.split(/[|\n]+/);
    const conditions = [];
    const seen = new Set();
    let inConditionsSection = false;

    for (const rawItem of items) {
        let clean = cleanPolicyText(rawItem);
        clean = clean.replace(/^[\s\-_*•·▪—–#>|]+/, '');
        clean = clean.replace(/^(\d+|[a-zA-Z])[\.\)]\s+/, '');
        clean = clean.replace(/[\s\-_*•·▪—–;,\.\/#>|]+$/, '');
        clean = clean.trim();
        if (!clean || clean.length < 2) continue;

        if (STANDALONE_HEADER_REGEX.test(clean)) {
            if (clean.toLowerCase().includes('condition')) {
                inConditionsSection = true;
            }
            continue;
        }

        if (inConditionsSection) {
            const lower = clean.toLowerCase();
            if (!seen.has(lower)) {
                seen.add(lower);
                conditions.push(clean);
            }
        } else {
            const lower = clean.toLowerCase();
            if (/^(must\s+|payment\s+must|all\s+arrears|subject\s+to|only\s+applicable|the\s+waiver\s+applies\s+only)/i.test(clean) &&
                !lower.includes('eligible for') && !lower.includes('receives') && !lower.includes('maximum support')) {
                if (!seen.has(lower)) {
                    seen.add(lower);
                    conditions.push(clean);
                }
            }
        }
    }

    return conditions;
}

/**
 * Parse canonical benefits into distinct, structured benefit components.
 * Supports grants, fellowships, scholarships, reimbursements, waivers,
 * concessions, loans, in-kind benefits, and composite benefits.
 */
function parseBenefitComponents(scheme) {
    if (!scheme) return [];
    const target = typeof scheme === 'string' ? { benefits: scheme } : scheme;
    if (!target || typeof target !== 'object') return [];

    if (Array.isArray(target.benefit_components) && target.benefit_components.length > 0) {
        return target.benefit_components;
    }
    if (Array.isArray(target.details?.benefit_components) && target.details.benefit_components.length > 0) {
        return target.details.benefit_components;
    }

    const rawBenefits = target.benefits || target.benefit_summary || target.financial_assistance || '';
    const rawDesc = target.detailed_description || target.brief_description || target.description || '';

    const items = rawBenefits ? rawBenefits.split(/[|\n]+/) : (rawDesc ? rawDesc.split(/\.\s+/) : []);
    const cleanClauses = [];
    let inConditionsSection = false;

    for (const rawItem of items) {
        let clean = cleanPolicyText(rawItem);
        clean = clean.replace(/^[\s\-_*•·▪—–#>|]+/, '');
        clean = clean.replace(/^(\d+|[a-zA-Z])[\.\)]\s+/, '');
        clean = clean.replace(/[\s\-_*•·▪—–;,\.\/#>|]+$/, '');
        clean = clean.trim();
        if (!clean || clean.length < 2) continue;

        if (STANDALONE_HEADER_REGEX.test(clean)) {
            if (clean.toLowerCase().includes('condition')) {
                inConditionsSection = true;
            }
            continue;
        }

        if (!inConditionsSection) {
            const lower = clean.toLowerCase();
            // Skip pure conditions from the main benefit component list
            if (!/^(must\s+|payment\s+must|all\s+arrears\s+of\s+installments\s+must|the\s+waiver\s+applies\s+only)/i.test(clean)) {
                cleanClauses.push(clean);
            }
        }
    }

    const components = [];

    const addOrMergeComponent = (comp) => {
        const existing = components.find(c => c.benefitType === comp.benefitType);
        if (existing) {
            if (!existing.amount && comp.amount) existing.amount = comp.amount;
            if (!existing.maxCeiling && comp.maxCeiling) existing.maxCeiling = comp.maxCeiling;
            if (!existing.applicableBeneficiary && comp.applicableBeneficiary) existing.applicableBeneficiary = comp.applicableBeneficiary;
            if (!existing.duration && comp.duration) existing.duration = comp.duration;
            return;
        }
        components.push(comp);
    };

    for (const clause of cleanClauses) {
        const lower = clause.toLowerCase();

        // 1. Fellowship / Stipend
        if (lower.includes('fellowship') || lower.includes('stipend')) {
            const amtMatch = clause.match(/₹\s*([\d,]+)/i) || clause.match(/rs\.?\s*([\d,]+)/i);
            const amount = amtMatch ? parseInt(amtMatch[1].replace(/,/g, ''), 10) : (target.max_benefit || target.maxBenefit || null);
            const hraMatch = clause.match(/(\d+%\s*hra)/i);
            const hra = hraMatch ? hraMatch[1] : null;
            const isMonthly = lower.includes('month') || lower.includes('/ month') || lower.includes('monthly');
            const isAnnual = lower.includes('year') || lower.includes('annual') || lower.includes('per annum') || lower.includes('p.a');
            const unit = isMonthly ? 'per month' : (isAnnual ? 'per year' : null);
            const frequency = isMonthly ? 'monthly' : (isAnnual ? 'annual' : null);

            let amountDisplay = amount ? ('₹' + Number(amount).toLocaleString('en-IN') + (isMonthly ? ' / month' : (isAnnual ? ' / year' : ''))) : 'Fellowship / Stipend';
            if (hra) amountDisplay += ' + ' + hra;

            let beneficiary = null;
            if (lower.includes('young scientist')) beneficiary = 'Young Scientists without fellowship/salary';
            else if (lower.includes('doctoral') || lower.includes('research scholar')) beneficiary = 'Doctoral Research Scholars';

            const conds = [];
            if (lower.includes('without fellowship/salary')) {
                conds.push('Without regular salary or other fellowships');
            }
            if (hra) {
                conds.push('Fellowship plus ' + hra + ', subject to eligibility conditions');
            }

            addOrMergeComponent({
                benefitType: 'Fellowship / Stipend',
                amount: amount ? Number(amount) : null,
                amountDisplay,
                currency: 'INR',
                unit,
                frequency,
                applicableBeneficiary: beneficiary,
                conditions: conds,
                maxCeiling: null,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });

            // Operational breakdown if bundled in same clause
            if (lower.includes('travel') || lower.includes('contingency') || lower.includes('consumables') || lower.includes('equipment')) {
                addOrMergeComponent({
                    benefitType: 'Operational & Research Support',
                    amount: null,
                    amountDisplay: 'Travel, Contingency, Consumables & Minor Equipment',
                    currency: 'INR',
                    unit: 'project support',
                    frequency: 'per project',
                    applicableBeneficiary: beneficiary,
                    conditions: [
                        'Subject to project approval and actual expenditure',
                        'Provided as project support rather than unconditional personal payout'
                    ],
                    maxCeiling: null,
                    duration: null,
                    isCeiling: false,
                    description: 'Support for travel, contingency, consumables, and minor equipment',
                    source: 'canonical_record'
                });
            }
            continue;
        }

        // 2. Manpower Support
        if (lower.includes('manpower') || lower.includes('research associate')) {
            let beneficiary = null;
            if (lower.includes('regular position')) beneficiary = 'Principal Investigator holding a regular position';
            addOrMergeComponent({
                benefitType: 'Manpower Support',
                amount: null,
                amountDisplay: 'Project Manpower Allocation',
                currency: 'INR',
                unit: 'manpower',
                frequency: 'project duration',
                applicableBeneficiary: beneficiary,
                conditions: lower.includes('regular position') ? ['Principal Investigator must hold a regular position'] : [],
                maxCeiling: null,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 3. Research Project Grant / Funding Ceiling
        if (lower.includes('research grant') || lower.includes('project grant') || (lower.includes('maximum support') && (lower.includes('lakh') || lower.includes('crore') || lower.includes('project')))) {
            const numMatch = clause.match(/₹\s*([\d\.]+)\s*(lakhs?|crores?)/i) || clause.match(/([\d\.]+)\s*(lakhs?|crores?)/i);
            let amount = null;
            let amountDisplay = 'Research Project Grant';
            if (numMatch) {
                const val = parseFloat(numMatch[1]);
                const mult = numMatch[2].toLowerCase().startsWith('crore') ? 10000000 : 100000;
                amount = val * mult;
                amountDisplay = 'Up to ₹' + val + ' ' + (mult === 10000000 ? 'Crore' : 'Lakhs') + ' (Project Ceiling)';
            }

            const durMatch = clause.match(/(\d+\s*years?)/i) || clause.match(/(three\s*years)/i);
            const duration = durMatch ? (durMatch[1].toLowerCase().includes('three') ? '3 years' : durMatch[1]) : null;

            const conds = [];
            conds.push('Subject to approval and scheme rules');
            if (lower.includes('overhead')) {
                const ohCeiling = clause.match(/ceiling\s+of\s+₹?\s*([\d\.]+\s*lakh)/i);
                conds.push('Excludes overhead charges @ 10%' + (ohCeiling ? ' (overhead ceiling: ₹' + ohCeiling[1] + ')' : ''));
            }
            if (duration) conds.push('Maximum project duration: ' + duration);

            addOrMergeComponent({
                benefitType: 'Research Project Grant',
                amount,
                amountDisplay,
                currency: 'INR',
                unit: 'project grant',
                frequency: 'per project',
                applicableBeneficiary: 'Selected Research Projects',
                conditions: conds,
                maxCeiling: amountDisplay,
                duration,
                isCeiling: true,
                description: clause,
                source: 'canonical_record'
            });

            // Distinct Overhead Charges component if mentioned
            if (lower.includes('overhead')) {
                const ohCeiling = clause.match(/ceiling\s+of\s+₹?\s*([\d\.]+\s*lakh)/i);
                const ohPct = clause.match(/overhead\s*(?:charges)?\s*@\s*(\d+%)/i);
                const pctStr = ohPct ? ohPct[1] : '10%';
                const ceilStr = ohCeiling ? ('₹' + ohCeiling[1]) : '₹1 Lakh';
                addOrMergeComponent({
                    benefitType: 'Institutional Overhead Charges',
                    amount: null,
                    amountDisplay: `Overhead Charges @ ${pctStr} (Up to ${ceilStr} Ceiling)`,
                    currency: 'INR',
                    unit: 'institutional overhead',
                    frequency: 'project duration',
                    applicableBeneficiary: 'Host Institution',
                    conditions: [
                        `Overhead charges at ${pctStr}, subject to the ${ceilStr} ceiling`,
                        'Subject to host institution approval and scheme rules'
                    ],
                    maxCeiling: ceilStr,
                    duration,
                    isCeiling: true,
                    description: `Overhead charges @ ${pctStr} of the project cost subject to a ceiling of ${ceilStr}`,
                    source: 'canonical_record'
                });
            }
            continue;
        }

        // 4. Penalty or Interest Waiver
        if (lower.includes('waiver') || lower.includes('mafi') || lower.includes('penalty')) {
            const isFull = lower.includes('100%') || lower.includes('complete');
            addOrMergeComponent({
                benefitType: 'Penalty Waiver',
                amount: isFull ? 100 : null,
                amountDisplay: isFull ? '100% Penalty Waiver' : 'Penalty / Interest Waiver',
                currency: null,
                unit: 'percent',
                frequency: 'one-time waiver',
                applicableBeneficiary: lower.includes('tenant') ? 'Tenants and property allottees with pending arrears' : null,
                conditions: [],
                maxCeiling: null,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 5. Margin Money / Capital Subsidy
        if (lower.includes('margin money') || (lower.includes('subsidy') && (lower.includes('credit') || lower.includes('capital')))) {
            const pctMatch = clause.match(/(\d+%\s*(?:to|–|-)\s*\d+%)/i) || clause.match(/(\d+%\s*margin\s*money)/i) || clause.match(/(\d+%\s*capital\s*subsidy)/i) || clause.match(/(\d+%)/i);
            const amountDisplay = pctMatch ? (pctMatch[1].includes('margin') ? pctMatch[1] : pctMatch[1] + ' Margin Money Subsidy') : 'Credit Linked Subsidy';

            const capMatch = clause.match(/₹\s*([\d\.]+)\s*(lakhs?|crores?)/i);
            const maxCeiling = capMatch ? ('Up to ₹' + capMatch[1] + ' ' + capMatch[2]) : null;

            addOrMergeComponent({
                benefitType: 'Credit Linked Subsidy',
                amount: null,
                amountDisplay,
                currency: 'INR',
                unit: 'percent',
                frequency: 'project-linked',
                applicableBeneficiary: null,
                conditions: ['Subject to institutional bank loan appraisal and margin contribution'],
                maxCeiling,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 6. Interest Subsidy / Subvention
        if (lower.includes('interest subvention') || lower.includes('interest subsidy') || lower.includes('interest rebate')) {
            const rateMatch = clause.match(/(\d+%\s*(?:per\s*annum)?)/i);
            const amountDisplay = rateMatch ? (rateMatch[1] + ' Interest Subsidy') : 'Interest Subsidy / Subvention';
            addOrMergeComponent({
                benefitType: 'Interest Subsidy / Subvention',
                amount: null,
                amountDisplay,
                currency: 'INR',
                unit: 'percent per annum',
                frequency: 'annual',
                applicableBeneficiary: null,
                conditions: ['Applicable on eligible institutional borrowing terms'],
                maxCeiling: null,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 7. Reimbursement
        if (lower.includes('reimbursement') || lower.includes('reimbursed') || lower.includes('travel grant')) {
            const amtMatch = clause.match(/₹\s*([\d,]+)/i);
            const amount = amtMatch ? parseInt(amtMatch[1].replace(/,/g, ''), 10) : (scheme.max_benefit || scheme.maxBenefit || null);
            const amountDisplay = amount ? ('Up to ₹' + Number(amount).toLocaleString('en-IN') + ' Reimbursement') : 'Expense Reimbursement';
            addOrMergeComponent({
                benefitType: 'Reimbursement',
                amount: amount ? Number(amount) : null,
                amountDisplay,
                currency: 'INR',
                unit: 'claim reimbursement',
                frequency: 'post-facto claim',
                applicableBeneficiary: null,
                conditions: ['Subject to verified expenditure receipts'],
                maxCeiling: amount ? ('₹' + Number(amount).toLocaleString('en-IN')) : null,
                duration: null,
                isCeiling: true,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 8. Scholarship
        if (lower.includes('scholarship') || (scheme.benefit_type && scheme.benefit_type.toLowerCase() === 'scholarship')) {
            const amtMatch = clause.match(/₹\s*([\d,]+)/i);
            const amount = amtMatch ? parseInt(amtMatch[1].replace(/,/g, ''), 10) : (scheme.max_benefit || scheme.maxBenefit || null);
            const isMonthly = lower.includes('month');
            const frequency = isMonthly ? 'monthly' : 'annual';
            const unit = isMonthly ? 'per month' : 'per academic year';
            const amountDisplay = amount ? ('₹' + Number(amount).toLocaleString('en-IN') + ' / ' + (isMonthly ? 'month' : 'year')) : 'Educational Scholarship';
            addOrMergeComponent({
                benefitType: 'Scholarship',
                amount: amount ? Number(amount) : null,
                amountDisplay,
                currency: 'INR',
                unit,
                frequency,
                applicableBeneficiary: 'Enrolled students',
                conditions: [],
                maxCeiling: null,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 9. In-Kind Assistance
        if (lower.includes('in-kind') || lower.includes('foodgrain') || lower.includes('healthcare') || lower.includes('cashless') || lower.includes('ration') || lower.includes('ambulance') || (scheme.benefit_type && scheme.benefit_type.toLowerCase().includes('in kind'))) {
            const capMatch = clause.match(/₹\s*([\d,]+(?:\s*lakhs?)?)/i);
            const amountDisplay = capMatch ? ('Cashless Coverage up to ₹' + capMatch[1]) : 'Non-Financial / In-Kind Support';
            addOrMergeComponent({
                benefitType: 'In-Kind Assistance',
                amount: null,
                amountDisplay,
                currency: 'INR',
                unit: 'in-kind',
                frequency: lower.includes('month') ? 'monthly' : (lower.includes('year') ? 'annual' : 'as-needed'),
                applicableBeneficiary: null,
                conditions: [],
                maxCeiling: capMatch ? ('Up to ₹' + capMatch[1]) : null,
                duration: null,
                isCeiling: Boolean(capMatch),
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // 10. Direct Cash Assistance / DBT
        if (lower.includes('cash') || lower.includes('dbt') || lower.includes('income support') || (scheme.benefit_type && scheme.benefit_type.toLowerCase() === 'cash')) {
            const amtMatch = clause.match(/₹\s*([\d,]+)/i);
            const amount = amtMatch ? parseInt(amtMatch[1].replace(/,/g, ''), 10) : (scheme.max_benefit || scheme.maxBenefit || null);
            const isAnnual = lower.includes('year') || lower.includes('annual');
            const amountDisplay = amount ? ('₹' + Number(amount).toLocaleString('en-IN') + (isAnnual ? ' / year' : '')) : 'Direct Cash Assistance';
            addOrMergeComponent({
                benefitType: 'Direct Financial Benefit',
                amount: amount ? Number(amount) : null,
                amountDisplay,
                currency: 'INR',
                unit: isAnnual ? 'per year' : 'direct transfer',
                frequency: isAnnual ? 'annual' : 'one-time',
                applicableBeneficiary: null,
                conditions: [],
                maxCeiling: null,
                duration: null,
                isCeiling: false,
                description: clause,
                source: 'canonical_record'
            });
            continue;
        }

        // Default clean clause
        addOrMergeComponent({
            benefitType: 'Statutory Welfare Benefit',
            amount: null,
            amountDisplay: clause,
            currency: 'INR',
            unit: null,
            frequency: null,
            applicableBeneficiary: null,
            conditions: [],
            maxCeiling: null,
            duration: null,
            isCeiling: false,
            description: clause,
            source: 'canonical_record'
        });
    }

    return components;
}

/**
 * Universal, data-driven financial benefit interpreter.
 */
function interpretFinancialBenefit(scheme) {
    if (!scheme || typeof scheme !== 'object') {
        return {
            category: BenefitCategories.UNKNOWN_OR_NOT_SPECIFIED,
            benefitType: 'Benefit Type Not Specified',
            amountDisplay: 'Amount Specified in Guidelines',
            subtitle: '(Refer to Policy Guidelines)',
            entitlementText: 'Financial support details specified in official statutory scheme guidelines.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: null,
            isUnverifiedOrUnavailable: true,
            benefitComponents: [],
            conditions: []
        };
    }

    const benefitComponents = parseBenefitComponents(scheme);
    const conditions = extractPolicyConditions(scheme);

    const textTokens = [
        scheme.scheme_name,
        scheme.name,
        scheme.title,
        scheme.short_title,
        scheme.short_name,
        scheme.brief_description,
        scheme.detailed_description,
        scheme.benefits,
        scheme.benefit_summary,
        scheme.description,
        Array.isArray(scheme.tags) ? scheme.tags.join(' ') : (scheme.tags || ''),
        Array.isArray(scheme.categories) ? scheme.categories.join(' ') : (scheme.categories || ''),
        Array.isArray(scheme.sub_categories) ? scheme.sub_categories.join(' ') : (scheme.sub_categories || '')
    ].filter(Boolean).join(' ').toLowerCase();

    const rawBenefitType = String(scheme.benefit_type || scheme.type || '').trim().toLowerCase();

    const rawMax = scheme.max_benefit != null ? Number(scheme.max_benefit) : (scheme.maxBenefit != null ? Number(scheme.maxBenefit) : null);
    const validMax = (rawMax != null && !isNaN(rawMax) && rawMax > 0) ? rawMax : null;

    const hasAnnualIndicator = textTokens.includes('per year') || textTokens.includes('/ year') || textTokens.includes('per annum') || textTokens.includes('annual');
    const hasMonthlyIndicator = !hasAnnualIndicator && (
        textTokens.includes('per month') ||
        textTokens.includes('/ month') ||
        (/\bmonthly\b/.test(textTokens) && !textTokens.includes('four-monthly') && !textTokens.includes('three-monthly') && !textTokens.includes('bi-monthly'))
    );

    // Explicit cash/financial indicators: canonical benefit_type of cash/fellowship/scholarship/reimbursement/subsidy,
    // or explicit DBT indicators. These explicitly prevent false-positive in-kind classification caused by incidental keywords like "skill training".
    const isExplicitCash = rawBenefitType === 'cash' ||
        rawBenefitType === 'fellowship' ||
        rawBenefitType === 'scholarship' ||
        rawBenefitType === 'reimbursement' ||
        rawBenefitType.includes('dbt') ||
        rawBenefitType.includes('direct benefit') ||
        textTokens.includes('dbt') ||
        textTokens.includes('direct benefit transfer') ||
        scheme.dbt_scheme === true;

    // 1. Penalty or Interest Waiver
    if (textTokens.includes('waiver') || textTokens.includes('mafi') || textTokens.includes('penalty')) {
        const isFullWaiver = textTokens.includes('100%') || textTokens.includes('complete waiver');
        const waiverLabel = isFullWaiver ? '100% Penalty Waiver' : 'Penalty / Fee Waiver';
        return {
            category: BenefitCategories.PENALTY_OR_INTEREST_WAIVER,
            benefitType: 'Penalty Waiver',
            amountDisplay: waiverLabel,
            subtitle: '(Penalty Waiver)',
            entitlementText: isFullWaiver
                ? '100% waiver on accumulated late payment penalty interest on pending arrears.'
                : 'Waiver on penalty or interest arrears subject to departmental scheme terms.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: 'one-time waiver',
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 2. Credit-Linked Capital / Margin Money Subsidy (With verified parameters)
    const isCreditLinked = (rawBenefitType.includes('credit') && rawBenefitType.includes('subsidy')) ||
        (rawBenefitType.includes('credit') && textTokens.includes('subsidy')) ||
        (textTokens.includes('credit-linked') && textTokens.includes('subsidy')) ||
        (textTokens.includes('margin money') && textTokens.includes('subsidy')) ||
        rawBenefitType === 'credit linked subsidy' ||
        rawBenefitType === 'credit-linked subsidy' ||
        (scheme.is_loan_scheme === true && (textTokens.includes('subsidy') || rawBenefitType.includes('subsidy') || scheme.details?.subsidy_percent != null)) ||
        (scheme.is_loan_scheme === true && !rawBenefitType.includes('loan') && !textTokens.includes('micro enterprise credit') && !textTokens.includes('credit facility') && !textTokens.includes('term loan')) ||
        (scheme.details?.subsidy_percent != null);

    if (isCreditLinked) {
        const calcParams = extractCalculatorParameters(scheme, textTokens);

        const amountDisplay = calcParams?.subsidyGrid
            ? '15% – 35% Margin Money Subsidy'
            : (calcParams?.flatSubsidyPercent != null
                ? `${calcParams.flatSubsidyPercent}% Capital Subsidy`
                : 'Credit Linked Subsidy');

        const entitlementText = calcParams?.subsidyGrid
            ? '15% to 35% margin money subsidy on project cost under credit-linked financial model.'
            : (calcParams?.flatSubsidyPercent != null
                ? `${calcParams.flatSubsidyPercent}% margin money subsidy on project cost under credit-linked financial model.`
                : 'Credit-linked capital or interest subsidy on eligible project borrowings as specified in scheme guidelines.');

        return {
            category: BenefitCategories.CREDIT_LINKED_SUBSIDY,
            benefitType: 'Credit Linked Subsidy',
            amountDisplay,
            subtitle: '(Credit Linked Subsidy)',
            entitlementText,
            hasLoanCalculator: true,
            calculatorParameters: calcParams,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: 'project-linked',
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 3. Interest Subsidy / Subvention
    if (textTokens.includes('interest subvention') || textTokens.includes('interest subsidy') || textTokens.includes('interest rebate')) {
        return {
            category: BenefitCategories.INTEREST_SUBSIDY,
            benefitType: 'Interest Subsidy / Subvention',
            amountDisplay: 'Interest Subvention Support',
            subtitle: '(Interest Subsidy)',
            entitlementText: 'Subsidized interest rate or rebate on eligible institutional borrowings.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: hasAnnualIndicator,
            frequency: hasAnnualIndicator ? 'annual subvention' : null,
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 4. Loan / Credit Facility (Debt, not grant)
    const isLoanFacility = rawBenefitType.includes('loan') ||
        textTokens.includes('loan facility') ||
        textTokens.includes('term loan') ||
        textTokens.includes('micro-loan') ||
        textTokens.includes('credit facility') ||
        textTokens.includes('mudra') ||
        textTokens.includes('bank finance');

    if (isLoanFacility) {
        const loanAmountDisplay = validMax ? `Up to ₹${validMax.toLocaleString('en-IN')} (Loan)` : 'Institutional Credit Facility';
        return {
            category: BenefitCategories.LOAN_OR_CREDIT_FACILITY,
            benefitType: 'Loan / Credit Facility',
            amountDisplay: loanAmountDisplay,
            subtitle: '(Credit Facility / Repayable Loan)',
            entitlementText: validMax
                ? `Repayable institutional loan facility up to ₹${validMax.toLocaleString('en-IN')} subject to bank approval.`
                : 'Institutional repayable loan / credit facility subject to bank appraisal.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: null,
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 5. Explicit In-Kind Assistance / Non-Financial Support
    const isInKindExplicit = rawBenefitType === 'in kind' ||
        rawBenefitType === 'in-kind' ||
        rawBenefitType === 'services' ||
        scheme.is_non_financial === true;

    if (isInKindExplicit) {
        return {
            category: BenefitCategories.IN_KIND_BENEFIT,
            benefitType: 'In-Kind Assistance',
            amountDisplay: 'Non-Financial / In-Kind Support',
            subtitle: '(In-Kind / Non-Cash Assistance)',
            entitlementText: 'Statutory welfare assistance provided as goods, healthcare, or services rather than direct cash transfers.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: null,
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 6. Composite Financial Support (Multi-component Statutory Support)
    const isCompositeSupport = rawBenefitType === 'composite' ||
        (textTokens.includes('fellowship') && (textTokens.includes('research grant') || textTokens.includes('lakhs') || textTokens.includes('consumables')));

    if (isCompositeSupport) {
        const fellowshipComp = benefitComponents.find(c => c.benefitType.toLowerCase().includes('fellowship') || c.benefitType.toLowerCase().includes('stipend'));
        const grantComp = benefitComponents.find(c => c.isCeiling || c.benefitType.toLowerCase().includes('research'));

        const hasExplicitFellowship = textTokens.includes('fellowship') || Boolean(fellowshipComp && fellowshipComp.benefitType.toLowerCase().includes('fellowship'));
        const hasResearchContext = Boolean(grantComp) ||
            textTokens.includes('investigator') ||
            textTokens.includes('investigators') ||
            textTokens.includes('scientist') ||
            (textTokens.includes('research') && (textTokens.includes('grant') || textTokens.includes('project') || textTokens.includes('programme') || textTokens.includes('program')));
        const hasFellowshipAndResearch = (hasExplicitFellowship || Boolean(fellowshipComp) || textTokens.includes('investigator') || textTokens.includes('investigators') || textTokens.includes('scientist')) && hasResearchContext;

        let compositeEntitlement = 'Multi-component statutory support combining financial and operational assistance as detailed in departmental guidelines.';
        let compositeAmountDisplay = 'Multi-Component Statutory Support';
        let compositeFrequency = 'composite assistance';
        let isPeriodic = false;

        if (hasFellowshipAndResearch) {
            compositeAmountDisplay = 'Fellowship & Research Grant (See Guidelines)';
            compositeFrequency = 'monthly + project grant';
            isPeriodic = true;
            if (fellowshipComp && grantComp) {
                compositeEntitlement = `Multi-component support: Monthly fellowship stipend (${fellowshipComp.amountDisplay}) + research project grant (${grantComp.amountDisplay}) + operational support. Refer to authoritative breakdown below.`;
            } else {
                compositeEntitlement = 'Multi-component support: Monthly fellowship stipend + research project grant. Refer to authoritative breakdown below.';
            }
        } else if (hasResearchContext) {
            compositeAmountDisplay = 'Research Support (See Guidelines)';
            compositeFrequency = 'project duration';
            isPeriodic = false;
            if (grantComp) {
                compositeEntitlement = `Multi-component research support: Project grant (${grantComp.amountDisplay}) + operational support. Refer to authoritative breakdown below.`;
            } else {
                compositeEntitlement = 'Multi-component research project support. Refer to authoritative breakdown below.';
            }
        } else if (fellowshipComp) {
            compositeAmountDisplay = 'Multi-Component Statutory Support';
            compositeFrequency = fellowshipComp.frequency || 'composite assistance';
            isPeriodic = Boolean(fellowshipComp.frequency);
            compositeEntitlement = `Multi-component support: Stipend (${fellowshipComp.amountDisplay}) + statutory operational support. Refer to authoritative breakdown below.`;
        }

        return {
            category: BenefitCategories.COMPOSITE_FINANCIAL_SUPPORT,
            benefitType: 'Composite',
            amountDisplay: compositeAmountDisplay,
            subtitle: '(Composite Policy Model)',
            entitlementText: compositeEntitlement,
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic,
            frequency: compositeFrequency,
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 7. Monthly Fellowship or Stipend
    const isFellowshipOrStipend = rawBenefitType === 'fellowship' ||
        rawBenefitType === 'stipend' ||
        textTokens.includes('fellowship') ||
        textTokens.includes('stipend') ||
        (hasMonthlyIndicator && !isCreditLinked && !isLoanFacility && !isInKindExplicit && (textTokens.includes('allowance') || textTokens.includes('stipend') || textTokens.includes('fellowship') || isExplicitCash || textTokens.includes('pension')));

    if (isFellowshipOrStipend) {
        const stipendDisplay = validMax && hasMonthlyIndicator
            ? `₹${validMax.toLocaleString('en-IN')} / month`
            : (validMax ? `₹${validMax.toLocaleString('en-IN')} Fellowship` : 'Monthly Fellowship / Stipend');

        return {
            category: BenefitCategories.MONTHLY_FELLOWSHIP_OR_STIPEND,
            benefitType: 'Fellowship / Stipend',
            amountDisplay: stipendDisplay,
            subtitle: '(Monthly Fellowship / Stipend)',
            entitlementText: validMax && hasMonthlyIndicator
                ? `Monthly fellowship stipend of ₹${validMax.toLocaleString('en-IN')} per month for qualified recipients.`
                : 'Recurring monthly fellowship or stipend allowance for qualified recipients.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: true,
            frequency: 'monthly',
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 8. Annual Scholarship
    const isScholarship = rawBenefitType === 'scholarship' ||
        textTokens.includes('scholarship') ||
        textTokens.includes('post-matric') ||
        textTokens.includes('pre-matric');

    if (isScholarship) {
        const scholarshipDisplay = validMax ? `₹${validMax.toLocaleString('en-IN')} / year` : 'Annual Scholarship Support';

        return {
            category: BenefitCategories.ANNUAL_SCHOLARSHIP,
            benefitType: 'Scholarship',
            amountDisplay: scholarshipDisplay,
            subtitle: '(Educational Scholarship)',
            entitlementText: validMax
                ? `Educational scholarship assistance of ₹${validMax.toLocaleString('en-IN')} per academic year.`
                : 'Financial scholarship assistance for tuition, books, and academic maintenance.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: validMax != null,
            isScalarTotal: false,
            isPeriodic: true,
            frequency: 'annual',
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 9. Reimbursement Scheme
    const isReimbursement = rawBenefitType === 'reimbursement' ||
        textTokens.includes('reimbursement') ||
        textTokens.includes('reimbursed') ||
        textTokens.includes('travel grant') ||
        textTokens.includes('fee reimbursement');

    if (isReimbursement) {
        return {
            category: BenefitCategories.REIMBURSEMENT,
            benefitType: 'Reimbursement',
            amountDisplay: validMax ? `Up to ₹${validMax.toLocaleString('en-IN')} Reimbursement` : 'Expense Reimbursement',
            subtitle: '(Expense Reimbursement)',
            entitlementText: validMax
                ? `Reimbursement of verified expenses up to a maximum ceiling of ₹${validMax.toLocaleString('en-IN')}.`
                : 'Reimbursement of verified expenses against eligible expenditure receipts.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: 'post-facto claim',
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 10. In-Kind Assistance by Broad Keywords (Only when NOT explicit cash)
    const isInKindByKeywords = !isExplicitCash && (
        textTokens.includes('in-kind') ||
        textTokens.includes('in kind') ||
        textTokens.includes('foodgrain') ||
        textTokens.includes('free supply') ||
        textTokens.includes('skill training') ||
        textTokens.includes('free healthcare') ||
        textTokens.includes('ration') ||
        textTokens.includes('non-financial')
    );

    if (isInKindByKeywords) {
        return {
            category: BenefitCategories.IN_KIND_BENEFIT,
            benefitType: 'In-Kind Assistance',
            amountDisplay: 'Non-Financial / In-Kind Support',
            subtitle: '(In-Kind / Non-Cash Assistance)',
            entitlementText: 'Statutory welfare assistance provided as goods, healthcare, or services rather than direct cash transfers.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: null,
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 10. Direct Cash Assistance / Fixed One-Time Grant
    if (isExplicitCash || textTokens.includes('cash assistance') || textTokens.includes('financial assistance') || textTokens.includes('grant') || textTokens.includes('subsidy')) {
        if (validMax != null && !hasMonthlyIndicator) {
            return {
                category: BenefitCategories.FIXED_ONE_TIME_GRANT,
                benefitType: 'Direct Financial Benefit',
                amountDisplay: `₹${validMax.toLocaleString('en-IN')}`,
                subtitle: '(Direct Financial Grant)',
                entitlementText: `Direct financial benefit of ₹${validMax.toLocaleString('en-IN')} disbursed to verified beneficiary accounts.`,
                hasLoanCalculator: false,
                calculatorParameters: null,
                isScalarCashGrant: true,
                isScalarTotal: true,
                isPeriodic: hasAnnualIndicator,
                frequency: hasAnnualIndicator ? 'annual' : 'one-time',
                isUnverifiedOrUnavailable: false,
                benefitComponents,
                conditions
            };
        }

        return {
            category: BenefitCategories.DIRECT_CASH_ASSISTANCE,
            benefitType: 'Direct Cash Assistance',
            amountDisplay: 'Amount Specified in Guidelines',
            subtitle: '(Refer to Policy Guidelines)',
            entitlementText: 'Financial assistance disbursed as direct statutory benefit under departmental guidelines.',
            hasLoanCalculator: false,
            calculatorParameters: null,
            isScalarCashGrant: false,
            isScalarTotal: false,
            isPeriodic: false,
            frequency: null,
            isUnverifiedOrUnavailable: false,
            benefitComponents,
            conditions
        };
    }

    // 11. Unknown / Not Specified
    return {
        category: BenefitCategories.UNKNOWN_OR_NOT_SPECIFIED,
        benefitType: 'Benefit Type Not Specified',
        amountDisplay: 'Amount Specified in Guidelines',
        subtitle: '(Refer to Policy Guidelines)',
        entitlementText: 'Financial support details specified in official statutory scheme guidelines.',
        hasLoanCalculator: false,
        calculatorParameters: null,
        isScalarCashGrant: false,
        isScalarTotal: false,
        isPeriodic: false,
        frequency: null,
        isUnverifiedOrUnavailable: true,
        benefitComponents,
        conditions
    };
}

module.exports = {
    BenefitCategories,
    interpretFinancialBenefit,
    extractCalculatorParameters,
    cleanPolicyText,
    extractPolicyConditions,
    parseBenefitComponents
};
