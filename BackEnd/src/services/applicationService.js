const profileService = require('./profileService');
const schemeService = require('./schemeService');
const { checkEligibility } = require('./eligibilityService');
const { supabaseAdmin } = require('../config/supabaseConfig');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// Document type → human label
const DOC_LABELS = {
    aadhaar: 'Aadhaar Card',
    pan: 'PAN Card',
    udyam: 'Udyam Registration Certificate',
    itr: 'Income Tax Return (ITR)',
    land: 'Land Ownership Records',
    income_cert: 'Income Certificate',
    caste_cert: 'Caste/Category Certificate',
    disability_cert: 'Disability Certificate',
    domicile: 'Domicile Certificate',
    bank_passbook: 'Bank Passbook',
    photo: 'Passport Size Photo',
    address_proof: 'Address Proof'
};

/**
 * Load all documents from Supabase that belong to the user's applications.
 * Returns a Set of verified/uploaded document types.
 */
const loadUserDocuments = async (userId) => {
    try {
        const profile = await profileService.getProfileById(userId);
        if (!profile) return new Set();

        const { data: applications } = await supabaseAdmin
            .from('applications')
            .select('id')
            .eq('applicant_id', profile.id);

        if (!applications || applications.length === 0) return new Set();

        const appIds = applications.map(a => a.id);
        const { data: docs } = await supabaseAdmin
            .from('documents')
            .select('document_type, verification_status')
            .in('application_id', appIds);

        if (!docs) return new Set();
        return new Set(docs.map(d => d.document_type));
    } catch (_) {
        return new Set();
    }
};

/**
 * POST /api/applications/analyze
 * @param {string} userId - Authenticated user
 * @param {string} schemeId - Scheme to analyze readiness for
 * @param {object} [profileOverride] - Optional profile override
 * @returns Application readiness report
 */
const analyzeApplication = async (userId, schemeId, profileOverride = null) => {
    if (!userId) throw httpError(400, 'User ID is required');
    if (!schemeId) throw httpError(400, 'schemeId is required');

    // Load profile
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) { /* ignore missing profile error */ }
    
    if (!profile) {
        if (profileOverride && typeof profileOverride === 'object') {
            profile = profileOverride;
        } else {
            profile = {};
        }
    } else if (profileOverride && typeof profileOverride === 'object') {
        profile = { ...profile, ...profileOverride };
    }

    // Find scheme
    const { scheme } = await schemeService.getSchemeById(schemeId);

    // Run eligibility check
    let eligibilityResult = null;
    try {
        eligibilityResult = await checkEligibility(userId, schemeId, profileOverride);
    } catch (e) {
        eligibilityResult = { verdict: 'MANUAL_REVIEW', verdictReason: e.message };
    }

    // Check documents
    const uploadedDocs = await loadUserDocuments(userId);
    const requiredDocs = scheme.required_documents || [];

    const documentStatus = requiredDocs.map(docType => ({
        type: docType,
        label: DOC_LABELS[docType] || docType,
        uploaded: uploadedDocs.has(docType),
        status: uploadedDocs.has(docType) ? 'uploaded' : 'missing'
    }));

    const missingDocs = documentStatus.filter(d => !d.uploaded);
    const uploadedCount = documentStatus.filter(d => d.uploaded).length;

    // Profile completeness check
    const profileFields = {
        full_name: !!profile.full_name,
        annual_income: profile.annual_income != null,
        occupation: !!profile.occupation,
        state: !!profile.state,
        gender: !!profile.gender,
        date_of_birth: !!(profile.date_of_birth || profile.dob)
    };
    const profileFilledCount = Object.values(profileFields).filter(Boolean).length;
    const profileCompletion = Math.round((profileFilledCount / Object.keys(profileFields).length) * 100);

    // Readiness score: 40% eligibility, 40% documents, 20% profile
    const eligibilityScore = eligibilityResult?.verdict === 'ELIGIBLE' ? 40 : eligibilityResult?.verdict === 'MANUAL_REVIEW' ? 20 : 0;
    const docsScore = requiredDocs.length > 0 ? Math.round((uploadedCount / requiredDocs.length) * 40) : 40;
    const profileScore = Math.round((profileCompletion / 100) * 20);
    const readinessScore = eligibilityScore + docsScore + profileScore;

    // Derive next actions
    const nextActions = [];
    if (eligibilityResult?.verdict !== 'ELIGIBLE') {
        nextActions.push({ priority: 'high', action: 'Review Eligibility', detail: eligibilityResult?.verdictReason || 'Check eligibility criteria.' });
    }
    if (missingDocs.length > 0) {
        nextActions.push({ priority: 'high', action: 'Upload Missing Documents', detail: `Upload: ${missingDocs.map(d => d.label).join(', ')}` });
    }
    if (profileCompletion < 100) {
        nextActions.push({ priority: 'medium', action: 'Complete Your Profile', detail: `Profile is ${profileCompletion}% complete. Missing: ${Object.entries(profileFields).filter(([, v]) => !v).map(([k]) => k).join(', ')}` });
    }
    if (nextActions.length === 0) {
        nextActions.push({ priority: 'low', action: 'Ready to Apply', detail: 'Your profile and documents appear complete. You can proceed to submit your application.' });
    }

    return {
        schemeId,
        schemeName: scheme.name,
        readinessScore,
        readinessLabel: readinessScore >= 80 ? 'Ready' : readinessScore >= 50 ? 'Almost Ready' : 'Needs Attention',
        eligibility: {
            verdict: eligibilityResult?.verdict,
            reason: eligibilityResult?.verdictReason
        },
        documents: {
            required: requiredDocs.length,
            uploaded: uploadedCount,
            missing: missingDocs.length,
            details: documentStatus
        },
        profile: {
            completionPercent: profileCompletion,
            fields: profileFields
        },
        nextActions,
        analyzedAt: new Date().toISOString()
    };
};

module.exports = { analyzeApplication };
