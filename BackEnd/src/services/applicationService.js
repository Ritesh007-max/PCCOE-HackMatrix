const profileService = require('./profileService');
const schemeService = require('./schemeService');
const { checkEligibility } = require('./eligibilityService');
const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');

const DOCUMENTS_BUCKET = process.env.SUPABASE_DOCUMENTS_BUCKET || 'documents';

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
 * @param {object} [options] - Execution options (e.g. { allowFallback: false })
 * @returns Application readiness report
 */
const analyzeApplication = async (userId, schemeId, profileOverride = null, options = {}) => {
    if (!userId) throw httpError(400, 'User ID is required');
    if (!schemeId) throw httpError(400, 'schemeId is required');

    // 1. Load profile
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

    // 2. Find scheme
    const { scheme } = await schemeService.getSchemeById(schemeId);

    // 3. Attempt 21-Step Pipeline via Intelligence microservice if user has documents
    if (profile.id) {
        try {
            const { data: userApps } = await supabaseAdmin
                .from('applications')
                .select('id, scheme_id')
                .eq('applicant_id', profile.id);

            const appIds = (userApps || []).map(a => a.id);
            if (appIds.length > 0) {
                const { data: docRows } = await supabaseAdmin
                    .from('documents')
                    .select('*')
                    .in('application_id', appIds);

                const validDocRows = (docRows || []).filter(d => Boolean(d.file_url));
                if (validDocRows.length > 0) {
                    const formData = new FormData();
                    let filesAppended = 0;

                    for (const doc of validDocRows) {
                        try {
                            const { data: blob } = await supabaseAdmin.storage
                                .from(DOCUMENTS_BUCKET)
                                .download(doc.file_url);

                            if (blob) {
                                const buffer = Buffer.from(await blob.arrayBuffer());
                                const fileBlob = new Blob([buffer], { type: 'application/octet-stream' });
                                formData.append('files', fileBlob, doc.file_name || 'document.pdf');
                                filesAppended++;
                            }
                        } catch (_) {}
                    }

                    if (filesAppended > 0) {
                        formData.append('query', scheme.name || schemeId);
                        formData.append('target_scheme', schemeId);
                        formData.append('session_id', String(userId));

                        const aiAnalysis = await intelligenceClient.postMultipart('/v1/applications/analyze', formData, {
                            timeoutMs: 60000
                        });

                        if (aiAnalysis && aiAnalysis.steps_completed === 21) {
                            // Persist 21-step decision to Supabase applications table
                            const targetApp = (userApps || []).find(a => a.scheme_id === schemeId) || userApps[0];
                            if (targetApp) {
                                try {
                                    await supabaseAdmin
                                        .from('applications')
                                        .update({
                                            status: aiAnalysis.processing_status || 'under_review',
                                            eligibility_status: aiAnalysis.eligibility_decision?.verdict || 'under_review',
                                            eligibility_score: aiAnalysis.eligibility_decision?.is_eligible ? 100 : 50,
                                            rule_evaluations: aiAnalysis.eligibility_decision?.rules_evaluated || [],
                                            missing_documents: aiAnalysis.missing_information?.missing_documents || [],
                                            estimated_benefit: aiAnalysis.benefit_calculation?.benefit_amount || null,
                                            llm_explanation: aiAnalysis.explanation?.summary || null,
                                            explanation_citations: aiAnalysis.explanation?.citations || [],
                                            decision_notes: `Phase 8/15 21-step pipeline completed | Status: ${aiAnalysis.processing_status}`,
                                            reviewed_at: new Date().toISOString(),
                                            updated_at: new Date().toISOString()
                                        })
                                        .eq('id', targetApp.id);
                                } catch (_) {}
                            }

                            // Adapt response preserving existing FrontEnd contract while enriching with 21-step data
                            const isEligible = Boolean(aiAnalysis.eligibility_decision?.is_eligible);
                            const verdict = aiAnalysis.eligibility_decision?.verdict || (isEligible ? 'ELIGIBLE' : 'MANUAL_REVIEW');

                            return {
                                source: 'intelligence',
                                degraded: false,
                                schemeId,
                                schemeName: scheme.name,
                                readinessScore: isEligible ? 95 : 55,
                                readinessLabel: isEligible ? 'Ready' : 'Needs Attention',
                                eligibility: {
                                    verdict,
                                    reason: aiAnalysis.explanation?.summary || 'Evaluated via statutory rules.'
                                },
                                documents: {
                                    required: (scheme.required_documents || []).length,
                                    uploaded: filesAppended,
                                    missing: (aiAnalysis.missing_information?.missing_documents || []).length,
                                    details: aiAnalysis.documents_processed || []
                                },
                                profile: {
                                    completionPercent: 90,
                                    applicantProfile: aiAnalysis.applicant_profile
                                },
                                nextActions: isEligible
                                    ? [{ priority: 'low', action: 'Ready to Apply', detail: 'Application validated through 21-step pipeline. Ready for submission.' }]
                                    : [{ priority: 'high', action: 'Review Criteria', detail: aiAnalysis.explanation?.summary || 'Check scheme requirements.' }],
                                pipeline_21_step: aiAnalysis,
                                analyzedAt: new Date().toISOString()
                            };
                        }
                    }
                }
            }
        } catch (err) {
            console.warn(`[applicationService] Intelligence /v1/applications/analyze unavailable (${err.message}) - Falling back to local readiness evaluation`);
            if (options && options.allowFallback === false) {
                throw err;
            }
        }
    }

    // 4. Fallback local readiness evaluation
    let eligibilityResult = null;
    try {
        eligibilityResult = await checkEligibility(userId, schemeId, profileOverride);
    } catch (e) {
        eligibilityResult = { verdict: 'MANUAL_REVIEW', verdictReason: e.message };
    }

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

    const eligibilityScore = eligibilityResult?.verdict === 'ELIGIBLE' ? 40 : eligibilityResult?.verdict === 'MANUAL_REVIEW' ? 20 : 0;
    const docsScore = requiredDocs.length > 0 ? Math.round((uploadedCount / requiredDocs.length) * 40) : 40;
    const profileScore = Math.round((profileCompletion / 100) * 20);
    const readinessScore = eligibilityScore + docsScore + profileScore;

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
        source: 'local_readiness',
        degraded: true,
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

/**
 * List applications for a user
 */
const listApplications = async (userId) => {
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) {}

    if (!profile) return [];

    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('*')
        .eq('applicant_id', profile.id)
        .order('created_at', { ascending: false });

    if (error) {
        console.warn('Error fetching applications from DB:', error.message);
        return [];
    }
    return data || [];
};

/**
 * Create a new application
 */
const createApplication = async (userId, applicationData) => {
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) {}

    if (!profile) throw httpError(400, 'Applicant profile required');

    const newApp = {
        applicant_id: profile.id,
        scheme_id: applicationData.schemeId || applicationData.scheme_id,
        status: 'under_review',
        estimated_benefit: applicationData.benefitAmount ? Number(String(applicationData.benefitAmount).replace(/[^0-9]/g, '')) : null,
        submitted_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    };

    const { data, error } = await supabaseAdmin
        .from('applications')
        .insert(newApp)
        .select()
        .single();

    if (error) throw httpError(500, error.message);
    return data;
};

/**
 * Get application by ID
 */
const getApplicationById = async (userId, applicationId) => {
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) {}

    if (!profile) throw httpError(404, 'Profile not found');

    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('*')
        .eq('id', applicationId)
        .eq('applicant_id', profile.id)
        .maybeSingle();

    if (error) throw httpError(500, error.message);
    if (!data) throw httpError(404, 'Application not found');
    return data;
};

module.exports = {
    analyzeApplication,
    listApplications,
    createApplication,
    getApplicationById
};

