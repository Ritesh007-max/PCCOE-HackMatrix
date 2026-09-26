const profileService = require('./profileService');
const schemeService = require('./schemeService');
const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// ─── Deterministic rule-based eligibility engine ──────────────────────────────

/**
 * A rule is a function: (profile, scheme) → { pass: bool, reason: string, rule: string }
 * Rules are evaluated top-to-bottom; first failure stops the check (hard gate).
 */
const ELIGIBILITY_RULES = {
    pmegp: [
        {
            id: 'AGE_18',
            description: 'Applicant must be above 18 years of age.',
            source: 'PMEGP Guidelines, Clause 5.1',
            check: (p) => {
                if (!p.date_of_birth && !p.dob) return { pass: null, reason: 'Date of birth not provided — cannot verify age requirement.' };
                const dob = new Date(p.date_of_birth || p.dob);
                const age = Math.floor((Date.now() - dob) / (365.25 * 24 * 3600 * 1000));
                return age >= 18
                    ? { pass: true, reason: `Applicant is ${age} years old, satisfying the minimum age of 18.` }
                    : { pass: false, reason: `Applicant is ${age} years old, below the required minimum of 18.` };
            }
        },
        {
            id: 'NO_EXISTING_GOVT_LOAN',
            description: 'Only new projects are considered; applicant must not be an existing PMEGP/REGP beneficiary.',
            source: 'PMEGP Guidelines, Clause 6',
            check: () => ({ pass: true, reason: 'Applicant has declared no prior PMEGP/REGP benefit (self-certified).' })
        }
    ],
    'mudra-shishu': [
        {
            id: 'NON_FARM_ACTIVITY',
            description: 'Applicant must be engaged in a non-farm income-generating activity.',
            source: 'MUDRA Guidelines, Clause 3',
            check: (p) => {
                const occ = (p.occupation || '').toLowerCase();
                if (occ === 'farmer') return { pass: false, reason: 'MUDRA is for non-farm enterprises; farmer occupation does not qualify.' };
                if (!occ) return { pass: null, reason: 'Occupation not provided — cannot confirm non-farm activity.' };
                return { pass: true, reason: `Occupation '${p.occupation}' qualifies as a non-farm activity.` };
            }
        },
        {
            id: 'LOAN_AMOUNT_RANGE',
            description: 'Shishu category covers loans up to ₹50,000.',
            source: 'MUDRA Guidelines, Clause 4.1',
            check: () => ({ pass: true, reason: 'Shishu category (up to ₹50,000) applies.' })
        }
    ],
    'pm-kisan': [
        {
            id: 'FARMER_OCCUPATION',
            description: 'Applicant must be a farmer / agriculturalist.',
            source: 'PM-KISAN Scheme, Clause 4',
            check: (p) => {
                const occ = (p.occupation || '').toLowerCase();
                return occ === 'farmer'
                    ? { pass: true, reason: "Occupation is 'farmer', satisfying the PM-Kisan eligibility." }
                    : { pass: false, reason: `Occupation '${p.occupation || 'unknown'}' does not qualify for PM-Kisan (farmers only).` };
            }
        },
        {
            id: 'INCOME_THRESHOLD',
            description: 'Family income must not exceed ₹3,00,000 per year.',
            source: 'PM-KISAN Scheme, Clause 5',
            check: (p) => {
                const income = p.annual_income || p.income;
                if (income == null) return { pass: null, reason: 'Annual income not provided — income threshold cannot be verified.' };
                return Number(income) <= 300000
                    ? { pass: true, reason: `Annual income ₹${Number(income).toLocaleString()} is within the ₹3,00,000 threshold.` }
                    : { pass: false, reason: `Annual income ₹${Number(income).toLocaleString()} exceeds the ₹3,00,000 threshold.` };
            }
        }
    ],
    kcc: [
        {
            id: 'FARMER_OCCUPATION',
            description: 'Applicant must be a farmer, tenant farmer, or sharecropper.',
            source: 'KCC Scheme Guidelines, Clause 3',
            check: (p) => {
                const occ = (p.occupation || '').toLowerCase();
                return occ === 'farmer'
                    ? { pass: true, reason: 'Applicant is a farmer — eligible for KCC.' }
                    : { pass: false, reason: `Occupation '${p.occupation || 'unknown'}' does not qualify. KCC is for farmers only.` };
            }
        }
    ],
    'standup-india': [
        {
            id: 'SC_ST_OR_WOMAN',
            description: 'Applicant must be SC/ST or a woman entrepreneur.',
            source: 'Stand-Up India, Clause 3.1',
            check: (p) => {
                const category = (p.caste_category || p.category || '').toUpperCase();
                const isWoman = p.is_woman_entrepreneur === true || p.gender === 'female';
                const isSCST = category === 'SC' || category === 'ST';
                if (isSCST || isWoman) {
                    return { pass: true, reason: `Applicant qualifies as ${isSCST ? category : ''}${isSCST && isWoman ? ' and ' : ''}${isWoman ? 'woman entrepreneur' : ''}.` };
                }
                return { pass: false, reason: 'Applicant is neither SC/ST nor a woman entrepreneur.' };
            }
        },
        {
            id: 'GREENFIELD_ENTERPRISE',
            description: 'Loan is for setting up a new (greenfield) enterprise.',
            source: 'Stand-Up India, Clause 3.2',
            check: () => ({ pass: true, reason: 'Self-certified as a new enterprise (greenfield).' })
        }
    ]
};

/**
 * Returns a generic rule set for schemes without a custom definition.
 */
const genericRules = [
    {
        id: 'PROFILE_EXISTS',
        description: 'Applicant profile must be created.',
        source: 'General Application Requirement',
        check: (p) => p
            ? { pass: true, reason: 'Applicant profile found.' }
            : { pass: false, reason: 'No applicant profile found. Please complete your profile first.' }
    }
];

/**
 * Evaluate a single rule against the profile.
 * Returns { ruleId, description, source, status: 'pass'|'fail'|'review', reason }
 */
const evaluateRule = (rule, profile) => {
    const result = rule.check(profile);
    const status = result.pass === true ? 'pass' : result.pass === false ? 'fail' : 'review';
    return {
        ruleId: rule.id,
        description: rule.description,
        source: rule.source,
        status,
        reason: result.reason
    };
};

const AI_SERVER_URL = process.env.AI_SERVER_URL || 'http://127.0.0.1:8000';

/**
 * Core eligibility check service.
 * @param {string} userId          - Authenticated user id
 * @param {string} schemeId        - Scheme to evaluate against
 * @param {object} [profileOverride] - Optional profile fields passed directly in request body
 *                                    (used when applicant_profiles row does not exist yet)
 * @param {object} [options]         - Optional execution options (e.g. { allowFallback: false })
 * @returns Eligibility report object
 */
const checkEligibility = async (userId, schemeId, profileOverride = null, options = {}) => {
    if (!userId) throw httpError(400, 'User ID is required');
    if (!schemeId) throw httpError(400, 'schemeId is required');

    // 1. Try loading from Supabase applicant_profiles table
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) { /* non-blocking — proceed with override or empty */ }

    // 2. If no DB profile, merge override or use empty object
    if (!profile) {
        if (profileOverride && typeof profileOverride === 'object') {
            profile = profileOverride;
        } else {
            profile = {};
        }
    } else if (profileOverride && typeof profileOverride === 'object') {
        profile = { ...profile, ...profileOverride };
    }

    // --- 3. DYNAMIC AI INTEGRATION ATTEMPT (PHASE 15) ---
    try {
        const applicantFacts = { ...profile };
        if (profile.occupation) applicantFacts.occupation = profile.occupation;
        if (profile.annual_income != null) applicantFacts.annual_income = Number(profile.annual_income);
        if (profile.income != null && applicantFacts.annual_income == null) applicantFacts.annual_income = Number(profile.income);
        if (profile.caste_category || profile.category) applicantFacts.caste_category = profile.caste_category || profile.category;
        if (profile.gender) applicantFacts.gender = profile.gender;
        if (profile.state) applicantFacts.state = profile.state;
        if (profile.date_of_birth || profile.dob) applicantFacts.date_of_birth = profile.date_of_birth || profile.dob;
        if (profile.is_woman_entrepreneur != null) applicantFacts.is_woman_entrepreneur = Boolean(profile.is_woman_entrepreneur);
        if (profile.full_name) applicantFacts.full_name = profile.full_name;
        if (profile.marital_status) applicantFacts.marital_status = profile.marital_status;
        if (profile.land_ownership_acres != null) applicantFacts.land_ownership_acres = Number(profile.land_ownership_acres);
        if (profile.education_level) applicantFacts.education_level = profile.education_level;

        const aiResponse = await intelligenceClient.postJson('/v1/eligibility/check', {
            applicant_facts: applicantFacts,
            scheme_ids: [schemeId]
        }, { timeoutMs: 15000 });

        const evaluation = aiResponse?.evaluations?.[0];
        if (evaluation) {
            const rawStatus = (evaluation.status || 'UNKNOWN').toUpperCase();
            // Invariant: strictly preserve PASS, FAIL, UNKNOWN, REVIEW
            const validStatus = ['PASS', 'FAIL', 'UNKNOWN', 'REVIEW'].includes(rawStatus) ? rawStatus : 'UNKNOWN';

            let verdict;
            let verdictReason;
            if (validStatus === 'PASS') {
                verdict = 'ELIGIBLE';
                verdictReason = `All statutory eligibility criteria passed for ${evaluation.scheme_name || schemeId}.`;
            } else if (validStatus === 'FAIL') {
                verdict = 'NOT_ELIGIBLE';
                const firstFailed = (evaluation.rules_evaluated || []).find(r => r.status === 'FAIL');
                verdictReason = firstFailed?.reason || (evaluation.failed_rules?.length ? `Failed rules: ${evaluation.failed_rules.join(', ')}` : 'One or more statutory criteria were not satisfied.');
            } else {
                // UNKNOWN or REVIEW: DO NOT transform to PASS or ELIGIBLE
                verdict = 'MANUAL_REVIEW';
                const missing = evaluation.missing_fields?.length ? ` Missing fields: ${evaluation.missing_fields.join(', ')}.` : '';
                const conflicted = evaluation.conflicted_fields?.length ? ` Conflicted: ${evaluation.conflicted_fields.join(', ')}.` : '';
                verdictReason = `Statutory review required.${missing}${conflicted}`;
            }

            const mappedRules = (evaluation.rules_evaluated || []).map(r => ({
                id: r.rule_id,
                ruleId: r.rule_id,
                field: r.field,
                operator: r.operator,
                status: r.status === 'PASS' ? 'pass' : (r.status === 'FAIL' ? 'fail' : 'review'),
                rawStatus: r.status,
                reason: r.reason,
                applicantValue: r.applicant_value,
                expectedValue: r.expected_value,
                hardConstraint: r.hard_constraint
            }));

            // Persist to Supabase eligibility_results table
            try {
                await supabaseAdmin.from('eligibility_results').insert({
                    user_id: userId,
                    scheme_id: schemeId,
                    verdict,
                    evaluated_rules: mappedRules,
                    evaluated_at: new Date().toISOString()
                });
            } catch (_) {}

            return {
                source: 'intelligence',
                degraded: false,
                schemeId,
                schemeName: evaluation.scheme_name || schemeId,
                status: validStatus,
                isEligible: Boolean(evaluation.is_eligible),
                verdict,
                verdictReason,
                rules: mappedRules,
                missingFields: evaluation.missing_fields || [],
                conflictedFields: evaluation.conflicted_fields || [],
                matchedRules: evaluation.matched_rules || [],
                failedRules: evaluation.failed_rules || [],
                profileSnapshot: applicantFacts,
                requestId: aiResponse.request_id || null,
                evaluatedAt: new Date().toISOString()
            };
        }
    } catch (err) {
        console.warn(`[eligibilityService] Intelligence /v1/eligibility/check unavailable (${err.message}) - Falling back to local engine`);
        if (options && options.allowFallback === false) {
            throw err;
        }
    }
    // -----------------------------------------------------

    // 4. Resolve scheme metadata
    const { scheme } = await schemeService.getSchemeById(schemeId);

    // 4. Pick rules
    const rules = ELIGIBILITY_RULES[schemeId] || genericRules;

    // 5. Evaluate each rule
    const evaluatedRules = rules.map(rule => evaluateRule(rule, profile));

    // 6. Compute overall verdict
    const hasFail = evaluatedRules.some(r => r.status === 'fail');
    const hasReview = evaluatedRules.some(r => r.status === 'review');

    let verdict, verdictReason;
    if (hasFail) {
        verdict = 'NOT_ELIGIBLE';
        verdictReason = evaluatedRules.find(r => r.status === 'fail').reason;
    } else if (hasReview) {
        verdict = 'MANUAL_REVIEW';
        verdictReason = 'Some eligibility criteria could not be verified due to incomplete profile information. ' +
            'Either complete your profile on the Profile page, or pass a "profile" object in this request body for a quick test.';
    } else {
        verdict = 'ELIGIBLE';
        verdictReason = `Your profile satisfies all ${evaluatedRules.length} eligibility rule(s) for this scheme.`;
    }

    // 7. Persist result to Supabase `eligibility_results` if table exists
    try {
        await supabaseAdmin.from('eligibility_results').insert({
            user_id: userId,
            scheme_id: schemeId,
            verdict,
            evaluated_rules: evaluatedRules,
            evaluated_at: new Date().toISOString()
        });
    } catch (_) { /* table may not exist yet */ }

    return {
        source: 'local_fallback',
        degraded: true,
        schemeId,
        schemeName: scheme.name,
        verdict,
        verdictReason,
        rules: evaluatedRules,
        profileSource: profile.id ? 'database' : (profileOverride ? 'request_body' : 'empty'),
        profileSnapshot: {
            occupation: profile.occupation || null,
            annual_income: profile.annual_income || null,
            category: profile.caste_category || profile.category || null,
            gender: profile.gender || null,
            is_woman_entrepreneur: profile.is_woman_entrepreneur || null,
            date_of_birth: profile.date_of_birth || profile.dob || null
        },
        evaluatedAt: new Date().toISOString()
    };
};

module.exports = { checkEligibility };
