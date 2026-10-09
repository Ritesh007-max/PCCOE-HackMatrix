const profileService = require('./profileService');
const schemeService = require('./schemeService');
const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// ─── Helpers for Eligibility State Messaging Integrity (Phase D3.8) ──────────

const isInternalSentinel = (field) => {
    if (typeof field !== 'string') return true;
    const lower = field.toLowerCase().trim();
    return lower.includes('not_registered') ||
           lower.startsWith('scheme_') ||
           lower.endsWith('_error') ||
           lower === 'rule_evaluation_error' ||
           lower === 'unknown';
};

const PROFILE_FIELD_LABELS = {
    date_of_birth: 'Date of Birth',
    dob: 'Date of Birth',
    age: 'Age / Date of Birth',
    annual_income: 'Annual Family Income',
    income: 'Annual Family Income',
    occupation: 'Occupation',
    caste_category: 'Social Category',
    category: 'Social Category',
    gender: 'Gender',
    state: 'State of Residence',
    land_ownership_acres: 'Agricultural Land Ownership',
    education_level: 'Education Level',
    is_woman_entrepreneur: 'Woman Entrepreneur Status',
    marital_status: 'Marital Status'
};

const formatFieldLabel = (field) => {
    if (!field || typeof field !== 'string') return '';
    const clean = field.toLowerCase().trim();
    if (PROFILE_FIELD_LABELS[clean]) return PROFILE_FIELD_LABELS[clean];
    return clean
        .replace(/_/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/\b\w/g, c => c.toUpperCase());
};

const RULE_TO_PROFILE_FIELDS = {
    'AGE_18': ['date_of_birth'],
    'NON_FARM_ACTIVITY': ['occupation'],
    'FARMER_OCCUPATION': ['occupation'],
    'INCOME_THRESHOLD': ['annual_income'],
    'SC_ST_OR_WOMAN': ['caste_category', 'gender']
};

// ─── Deterministic rule-based eligibility engine ──────────────────────────────

/**
 * A rule is a function: (profile, scheme) → { pass: bool|null, reason: string, rule: string }
 * Rules are evaluated deterministically; missing required applicant facts evaluate to pass: null (review).
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
                if (isNaN(dob.getTime())) return { pass: null, reason: 'Invalid date of birth provided — cannot verify age requirement.' };
                const age = Math.floor((Date.now() - dob.getTime()) / (365.25 * 24 * 3600 * 1000));
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
                const occ = (p.occupation || '').toLowerCase().trim();
                if (!occ) return { pass: null, reason: 'Occupation not provided — cannot confirm non-farm activity.' };
                if (occ === 'farmer' || occ === 'farming' || occ === 'agriculture') {
                    return { pass: false, reason: 'MUDRA is for non-farm enterprises; farming occupation does not qualify.' };
                }
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
                const occ = (p.occupation || '').toLowerCase().trim();
                if (!occ) return { pass: null, reason: 'Occupation not provided — farmer status cannot be verified.' };
                return (occ === 'farmer' || occ === 'farming' || occ === 'agriculture')
                    ? { pass: true, reason: "Occupation is 'farmer', satisfying PM-KISAN eligibility." }
                    : { pass: false, reason: `Occupation '${p.occupation}' does not qualify for PM-KISAN (farmers only).` };
            }
        },
        {
            id: 'INCOME_THRESHOLD',
            description: 'Family income must not exceed ₹3,00,000 per year.',
            source: 'PM-KISAN Scheme, Clause 5',
            check: (p) => {
                const income = p.annual_income != null ? p.annual_income : p.income;
                if (income == null || income === '') return { pass: null, reason: 'Annual income not provided — income threshold cannot be verified.' };
                const num = Number(income);
                if (isNaN(num)) return { pass: null, reason: 'Invalid annual income value — income threshold cannot be verified.' };
                return num <= 300000
                    ? { pass: true, reason: `Annual income ₹${num.toLocaleString('en-IN')} is within the ₹3,00,000 threshold.` }
                    : { pass: false, reason: `Annual income ₹${num.toLocaleString('en-IN')} exceeds the ₹3,00,000 threshold.` };
            }
        }
    ],
    kcc: [
        {
            id: 'FARMER_OCCUPATION',
            description: 'Applicant must be a farmer, tenant farmer, or sharecropper.',
            source: 'KCC Scheme Guidelines, Clause 3',
            check: (p) => {
                const occ = (p.occupation || '').toLowerCase().trim();
                if (!occ) return { pass: null, reason: 'Occupation not provided — farmer status cannot be verified.' };
                return (occ === 'farmer' || occ === 'farming' || occ === 'agriculture')
                    ? { pass: true, reason: 'Applicant is a farmer — eligible for KCC.' }
                    : { pass: false, reason: `Occupation '${p.occupation}' does not qualify. KCC is for farmers only.` };
            }
        }
    ],
    'standup-india': [
        {
            id: 'SC_ST_OR_WOMAN',
            description: 'Applicant must be SC/ST or a woman entrepreneur.',
            source: 'Stand-Up India, Clause 3.1',
            check: (p) => {
                const category = (p.caste_category || p.category || '').toUpperCase().trim();
                const gender = (p.gender || '').toLowerCase().trim();
                const isWoman = p.is_woman_entrepreneur === true || gender === 'female' || gender === 'woman';
                const isSCST = category === 'SC' || category === 'ST';
                if (!category && !gender && p.is_woman_entrepreneur == null) {
                    return { pass: null, reason: 'Social category and gender not provided — cannot verify SC/ST or woman entrepreneur requirement.' };
                }
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
 * Normalizes scheme identifier and retrieves registered deterministic rules.
 * Returns null if scheme is not registered (strict fail-closed).
 */
const getRegisteredRules = (schemeId) => {
    if (!schemeId) return null;
    const cleanId = String(schemeId).toLowerCase().trim();
    if (ELIGIBILITY_RULES[cleanId]) return ELIGIBILITY_RULES[cleanId];
    const withDash = cleanId.replace(/_/g, '-');
    if (ELIGIBILITY_RULES[withDash]) return ELIGIBILITY_RULES[withDash];
    const withUnderscore = cleanId.replace(/-/g, '_');
    if (ELIGIBILITY_RULES[withUnderscore]) return ELIGIBILITY_RULES[withUnderscore];
    if (cleanId === 'pmkisan') return ELIGIBILITY_RULES['pm-kisan'];
    if (cleanId === 'mudrashishu') return ELIGIBILITY_RULES['mudra-shishu'];
    if (cleanId === 'standupindia') return ELIGIBILITY_RULES['standup-india'];
    return null;
};

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
    let intelligenceError = null;
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

            // Sanitize raw missing fields: filter out internal sentinels (e.g. scheme_1pmy_not_registered)
            const rawMissing = Array.isArray(evaluation.missing_fields) ? evaluation.missing_fields : [];
            const sanitizedMissing = rawMissing.filter(f => !isInternalSentinel(f));

            const hasRules = Array.isArray(evaluation.rules_evaluated) && evaluation.rules_evaluated.length > 0;
            const isUnregistered = (evaluation.rule_version === 'UNREGISTERED') ||
                (evaluation.completeness === 'UNSTRUCTURED') ||
                (!hasRules && rawMissing.some(f => typeof f === 'string' && f.includes('not_registered'))) ||
                (!hasRules && validStatus === 'UNKNOWN');

            let isRegistered = !isUnregistered;
            let evaluationCategory;
            let verdict;
            let verdictReason;
            let missingFields = [];
            let missingFieldLabels = [];

            if (validStatus === 'PASS') {
                isRegistered = true;
                evaluationCategory = 'ELIGIBLE';
                verdict = 'ELIGIBLE';
                verdictReason = `All statutory eligibility criteria passed for ${evaluation.scheme_name || schemeId}.`;
                missingFields = [];
                missingFieldLabels = [];
            } else if (validStatus === 'FAIL') {
                isRegistered = true;
                evaluationCategory = 'NOT_ELIGIBLE';
                verdict = 'NOT_ELIGIBLE';
                const firstFailed = (evaluation.rules_evaluated || []).find(r => r.status === 'FAIL');
                verdictReason = firstFailed?.reason || (evaluation.failed_rules?.length ? `Failed rules: ${evaluation.failed_rules.join(', ')}` : 'One or more statutory criteria were not satisfied.');
                missingFields = [];
                missingFieldLabels = [];
            } else if (isUnregistered) {
                isRegistered = false;
                evaluationCategory = 'UNREGISTERED_SCHEME';
                verdict = 'MANUAL_REVIEW';
                verdictReason = 'Automated statutory rules are not registered for this scheme. Manual verification is required during departmental application review.';
                missingFields = [];
                missingFieldLabels = [];
            } else if (sanitizedMissing.length > 0) {
                isRegistered = true;
                evaluationCategory = 'MISSING_APPLICANT_FACTS';
                verdict = 'MANUAL_REVIEW';
                missingFields = sanitizedMissing;
                missingFieldLabels = sanitizedMissing.map(formatFieldLabel);
                verdictReason = `Additional profile information is required to evaluate statutory eligibility: ${missingFieldLabels.join(', ')}. Manual verification is required.`;
            } else {
                isRegistered = true;
                evaluationCategory = 'MANUAL_REVIEW';
                verdict = 'MANUAL_REVIEW';
                if (evaluation.review_reasons && evaluation.review_reasons.length > 0) {
                    verdictReason = evaluation.review_reasons.join(' ');
                } else {
                    verdictReason = 'Statutory guidelines mandate qualitative departmental review and manual officer verification.';
                }
                missingFields = [];
                missingFieldLabels = [];
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
                intelligenceUnavailable: false,
                isRegistered,
                evaluationCategory,
                schemeId,
                schemeName: evaluation.scheme_name || schemeId,
                status: validStatus,
                isEligible: validStatus === 'PASS',
                verdict,
                verdictReason,
                rules: mappedRules,
                missingFields,
                missingFieldLabels,
                conflictedFields: evaluation.conflicted_fields || [],
                matchedRules: evaluation.matched_rules || [],
                failedRules: evaluation.failed_rules || [],
                profileSnapshot: applicantFacts,
                requestId: aiResponse.request_id || null,
                evaluatedAt: new Date().toISOString()
            };
        }
    } catch (err) {
        intelligenceError = err;
        console.warn(`[eligibilityService] Intelligence /v1/eligibility/check unavailable (${err.message}) - Falling back to local engine`);
        if (options && options.allowFallback === false) {
            throw err;
        }
    }
    // -----------------------------------------------------

    // 4. Local Deterministic Fail-Closed Engine (Phase D3.6 Remediation)
    const cleanSchemeId = String(schemeId).toLowerCase().trim();
    const rules = getRegisteredRules(cleanSchemeId);

    // Fail-Closed Guard: Schemes without registered rules MUST NEVER evaluate to PASS/ELIGIBLE
    if (!rules || !Array.isArray(rules) || rules.length === 0) {
        let schemeName = schemeId;
        try {
            const res = await schemeService.getSchemeById(schemeId);
            schemeName = res?.scheme?.scheme_name || res?.scheme?.name || res?.scheme?.title || schemeId;
        } catch (_) {}

        const isSnapshotUnavailable = intelligenceError && /snapshot/i.test(intelligenceError.message || '');
        const evaluationCategory = isSnapshotUnavailable ? 'SNAPSHOT_UNAVAILABLE' : 'UNREGISTERED_SCHEME';
        const verdictReason = isSnapshotUnavailable
            ? 'Official policy rules snapshot is currently unavailable for this scheme. Manual verification is required.'
            : 'Automated statutory rules are not registered for this scheme. Manual verification is required during departmental application review.';

        const unregisteredResult = {
            source: 'local_fallback',
            degraded: true,
            intelligenceUnavailable: Boolean(intelligenceError),
            isRegistered: false,
            evaluationCategory,
            schemeId,
            schemeName,
            status: 'UNKNOWN',
            isEligible: false,
            verdict: 'MANUAL_REVIEW',
            verdictReason,
            rules: [],
            missingFields: [],
            missingFieldLabels: [],
            conflictedFields: [],
            matchedRules: [],
            failedRules: [],
            profileSource: profile.id ? 'database' : (profileOverride ? 'request_body' : 'empty'),
            profileSnapshot: {
                occupation: profile.occupation || null,
                annual_income: profile.annual_income != null ? Number(profile.annual_income) : (profile.income != null ? Number(profile.income) : null),
                category: profile.caste_category || profile.category || null,
                gender: profile.gender || null,
                is_woman_entrepreneur: profile.is_woman_entrepreneur || null,
                date_of_birth: profile.date_of_birth || profile.dob || null
            },
            evaluatedAt: new Date().toISOString()
        };

        try {
            await supabaseAdmin.from('eligibility_results').insert({
                user_id: userId,
                scheme_id: schemeId,
                verdict: 'MANUAL_REVIEW',
                evaluated_rules: [],
                evaluated_at: new Date().toISOString()
            });
        } catch (_) {}

        return unregisteredResult;
    }

    // 5. Evaluate registered deterministic rules safely
    let evaluatedRules = [];
    try {
        evaluatedRules = rules.map(rule => evaluateRule(rule, profile));
    } catch (_) {
        let schemeName = schemeId;
        try {
            const res = await schemeService.getSchemeById(schemeId);
            schemeName = res?.scheme?.scheme_name || res?.scheme?.name || res?.scheme?.title || schemeId;
        } catch (_) {}

        return {
            source: 'local_fallback',
            degraded: true,
            intelligenceUnavailable: Boolean(intelligenceError),
            isRegistered: true,
            evaluationCategory: 'EVALUATION_ERROR',
            schemeId,
            schemeName,
            status: 'UNKNOWN',
            isEligible: false,
            verdict: 'MANUAL_REVIEW',
            verdictReason: 'Automated statutory rules could not be evaluated due to an execution error. Manual verification is required.',
            rules: [],
            missingFields: [],
            missingFieldLabels: [],
            conflictedFields: [],
            matchedRules: [],
            failedRules: [],
            profileSource: profile.id ? 'database' : (profileOverride ? 'request_body' : 'empty'),
            profileSnapshot: {
                occupation: profile.occupation || null,
                annual_income: profile.annual_income != null ? Number(profile.annual_income) : (profile.income != null ? Number(profile.income) : null),
                category: profile.caste_category || profile.category || null,
                gender: profile.gender || null,
                is_woman_entrepreneur: profile.is_woman_entrepreneur || null,
                date_of_birth: profile.date_of_birth || profile.dob || null
            },
            evaluatedAt: new Date().toISOString()
        };
    }

    // 6. Compute overall verdict with strict fail-closed logic
    const hasFail = evaluatedRules.some(r => r.status === 'fail');
    const hasReview = evaluatedRules.some(r => r.status === 'review');

    let status, isEligible, verdict, verdictReason, evaluationCategory;
    let missingFields = [];
    let missingFieldLabels = [];

    if (hasFail) {
        status = 'FAIL';
        isEligible = false;
        verdict = 'NOT_ELIGIBLE';
        evaluationCategory = 'NOT_ELIGIBLE';
        verdictReason = evaluatedRules.find(r => r.status === 'fail')?.reason || 'One or more statutory criteria were not satisfied.';
        missingFields = [];
        missingFieldLabels = [];
    } else if (hasReview) {
        status = 'UNKNOWN';
        isEligible = false;
        verdict = 'MANUAL_REVIEW';

        const reviewRules = evaluatedRules.filter(r => r.status === 'review');
        const extractedMissing = [];
        reviewRules.forEach(r => {
            const mapped = RULE_TO_PROFILE_FIELDS[r.ruleId];
            if (mapped) {
                mapped.forEach(f => {
                    const val = profile[f];
                    if ((val == null || val === '') && !extractedMissing.includes(f)) {
                        extractedMissing.push(f);
                    }
                });
            }
        });

        if (extractedMissing.length > 0) {
            evaluationCategory = 'MISSING_APPLICANT_FACTS';
            missingFields = extractedMissing;
            missingFieldLabels = extractedMissing.map(formatFieldLabel);
            verdictReason = reviewRules[0]?.reason || `Additional profile information is required to evaluate statutory eligibility: ${missingFieldLabels.join(', ')}. Manual verification is required.`;
        } else {
            evaluationCategory = 'MANUAL_REVIEW';
            missingFields = [];
            missingFieldLabels = [];
            verdictReason = reviewRules[0]?.reason || 'Some eligibility criteria could not be verified due to incomplete profile information. Manual verification is required.';
        }
    } else {
        status = 'PASS';
        isEligible = true;
        verdict = 'ELIGIBLE';
        evaluationCategory = 'ELIGIBLE';
        verdictReason = evaluatedRules.length > 0
            ? `Your profile satisfies all ${evaluatedRules.length} statutory eligibility criteria for this scheme.`
            : 'Statutory criteria evaluated successfully.';
        missingFields = [];
        missingFieldLabels = [];
    }

    let schemeName = schemeId;
    try {
        const res = await schemeService.getSchemeById(schemeId);
        schemeName = res?.scheme?.scheme_name || res?.scheme?.name || res?.scheme?.title || schemeId;
    } catch (_) {}

    const mappedRules = evaluatedRules.map(r => ({
        id: r.ruleId,
        ruleId: r.ruleId,
        description: r.description,
        source: r.source,
        status: r.status,
        rawStatus: r.status === 'pass' ? 'PASS' : (r.status === 'fail' ? 'FAIL' : 'UNKNOWN'),
        reason: r.reason
    }));

    // Persist result to Supabase `eligibility_results` if table exists
    try {
        await supabaseAdmin.from('eligibility_results').insert({
            user_id: userId,
            scheme_id: schemeId,
            verdict,
            evaluated_rules: mappedRules,
            evaluated_at: new Date().toISOString()
        });
    } catch (_) { /* table may not exist yet */ }

    return {
        source: 'local_fallback',
        degraded: true,
        intelligenceUnavailable: Boolean(intelligenceError),
        isRegistered: true,
        evaluationCategory,
        schemeId,
        schemeName,
        status,
        isEligible,
        verdict,
        verdictReason,
        rules: mappedRules,
        matchedRules: mappedRules.filter(r => r.status === 'pass').map(r => r.ruleId),
        failedRules: mappedRules.filter(r => r.status === 'fail').map(r => r.ruleId),
        missingFields,
        missingFieldLabels,
        conflictedFields: [],
        profileSource: profile.id ? 'database' : (profileOverride ? 'request_body' : 'empty'),
        profileSnapshot: {
            occupation: profile.occupation || null,
            annual_income: profile.annual_income != null ? Number(profile.annual_income) : (profile.income != null ? Number(profile.income) : null),
            category: profile.caste_category || profile.category || null,
            gender: profile.gender || null,
            is_woman_entrepreneur: profile.is_woman_entrepreneur || null,
            date_of_birth: profile.date_of_birth || profile.dob || null
        },
        evaluatedAt: new Date().toISOString()
    };
};

module.exports = { checkEligibility };
