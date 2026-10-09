const crypto = require('crypto');
const profileService = require('./profileService');
const schemeService = require('./schemeService');
const { checkEligibility } = require('./eligibilityService');
const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');
const { interpretFinancialBenefit } = require('./financialBenefitService');

const DOCUMENTS_BUCKET = process.env.SUPABASE_DOCUMENTS_BUCKET || 'documents';

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ensureUuid = (val) => {
    if (val && UUID_REGEX.test(val)) return val;
    if (!val) return crypto.randomUUID();
    const hash = crypto.createHash('md5').update(String(val)).digest('hex');
    return `${hash.slice(0, 8)}-${hash.slice(8, 12)}-4${hash.slice(13, 16)}-8${hash.slice(17, 20)}-${hash.slice(20, 32)}`;
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
                        formData.append('query', scheme.scheme_name || scheme.name || schemeId);
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
                                schemeName: scheme.scheme_name || scheme.name,
                                readinessScore: isEligible ? 95 : 55,
                                readinessLabel: isEligible ? 'Ready' : 'Needs Attention',
                                eligibility: {
                                    verdict,
                                    reason: aiAnalysis.explanation?.summary || 'Evaluated via statutory rules.'
                                },
                                documents: {
                                    required: (scheme.documents_required || scheme.required_documents || []).length,
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
    const requiredDocs = scheme.documents_required || scheme.required_documents || [];

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
        schemeName: scheme.scheme_name || scheme.name,
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

const getApplicantId = async (userId) => {
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) {}
    if (profile && profile.id) return profile.id;

    try {
        const { data: userRow } = await supabaseAdmin
            .from('users')
            .select('full_name, email')
            .eq('id', userId)
            .maybeSingle();

        const fallbackName = userRow?.full_name || (userRow?.email ? userRow.email.split('@')[0] : 'Applicant');

        const { data, error } = await supabaseAdmin
            .from('applicant_profiles')
            .upsert({ id: userId, full_name: fallbackName }, { onConflict: 'id' })
            .select('id')
            .maybeSingle();

        if (!error && data) return data.id;
    } catch (_) {}

    return userId;
};

const isGenericTitle = (title) => {
    if (!title || typeof title !== 'string') return true;
    const clean = title.trim().toLowerCase();
    return clean === 'government scheme application' ||
           clean === 'government scheme' ||
           clean === 'application' ||
           clean.startsWith('scheme #') ||
           clean === 'null' ||
           clean === 'undefined';
};

/**
 * Universal application record hydrator:
 * Attaches authentic scheme identity, canonical metadata, and verified financial benefit.
 * Explicitly marks unlinked schemes as unavailable without inventing titles or amounts.
 */
const hydrateApplicationRecord = async (app) => {
    if (!app) return null;

    let scheme = null;
    let isSchemeAvailable = false;
    let resolvedSchemeName = null;

    // 1. Resolve scheme by scheme_id
    if (app.scheme_id) {
        try {
            const res = await schemeService.getSchemeById(app.scheme_id);
            if (res && res.scheme) {
                scheme = res.scheme;
                isSchemeAvailable = true;
                resolvedSchemeName = scheme.scheme_name || scheme.name || scheme.title;
            }
        } catch (_) {}
    }

    // 2. Resolve scheme by decision_notes if not generic
    if (!scheme && app.decision_notes && !isGenericTitle(app.decision_notes)) {
        try {
            const res = await schemeService.getSchemeById(app.decision_notes);
            if (res && res.scheme) {
                scheme = res.scheme;
                isSchemeAvailable = true;
                resolvedSchemeName = scheme.scheme_name || scheme.name || scheme.title;
            }
        } catch (_) {}
    }

    // 3. Resolve financial benefit & presentation
    let financialBenefit = null;
    let benefitDisplay = 'Not specified';
    let benefitSubtitle = 'Estimated Benefit';
    let benefitNumeric = 0;

    if (scheme) {
        financialBenefit = scheme.financial_benefit || interpretFinancialBenefit(scheme);
        const cat = financialBenefit?.category;

        if (cat === 'UNKNOWN_OR_NOT_SPECIFIED' || financialBenefit?.isUnverifiedOrUnavailable) {
            benefitDisplay = 'Not specified';
            benefitSubtitle = 'Not specified';
            benefitNumeric = 0;
        } else if (cat === 'PENALTY_OR_INTEREST_WAIVER') {
            benefitDisplay = financialBenefit.amountDisplay || '100% Penalty Waiver';
            benefitSubtitle = financialBenefit.subtitle || '(Penalty Waiver)';
            benefitNumeric = 0;
        } else if (cat === 'LOAN_OR_CREDIT_FACILITY') {
            benefitDisplay = financialBenefit.amountDisplay || (scheme.max_benefit ? `Up to ₹${Number(scheme.max_benefit).toLocaleString('en-IN')} (Loan)` : 'Loan Facility');
            benefitSubtitle = financialBenefit.subtitle || '(Credit Facility / Repayable Loan)';
            benefitNumeric = 0;
        } else if (cat === 'INTEREST_SUBSIDY') {
            benefitDisplay = financialBenefit.amountDisplay || 'Interest Subsidy';
            benefitSubtitle = financialBenefit.subtitle || '(Interest Subsidy)';
            benefitNumeric = 0;
        } else if (cat === 'MONTHLY_FELLOWSHIP_OR_STIPEND') {
            benefitDisplay = financialBenefit.amountDisplay || 'Monthly Fellowship';
            benefitSubtitle = financialBenefit.subtitle || '(Monthly Fellowship / Stipend)';
            benefitNumeric = 0;
        } else if (cat === 'COMPOSITE_FINANCIAL_SUPPORT') {
            benefitDisplay = financialBenefit.amountDisplay || 'Multi-Component Support';
            benefitSubtitle = financialBenefit.subtitle || '(Composite Support)';
            benefitNumeric = 0;
        } else if (cat === 'IN_KIND_BENEFIT') {
            benefitDisplay = 'Non-Financial / In-Kind Assistance';
            benefitSubtitle = '(In-Kind / Welfare Service)';
            benefitNumeric = 0;
        } else if (cat === 'REIMBURSEMENT') {
            benefitDisplay = financialBenefit.amountDisplay || 'Expense Reimbursement';
            benefitSubtitle = '(Verified Reimbursement)';
            benefitNumeric = 0;
        } else if (financialBenefit?.amountDisplay && financialBenefit.amountDisplay !== 'Not specified' && financialBenefit.amountDisplay !== '₹0') {
            benefitDisplay = financialBenefit.amountDisplay;
            benefitSubtitle = financialBenefit.subtitle || 'Direct Financial Assistance';
            benefitNumeric = typeof financialBenefit.amount === 'number' ? financialBenefit.amount : 0;
        } else if (app.estimated_benefit && app.estimated_benefit !== 175000) {
            benefitDisplay = `₹${Number(app.estimated_benefit).toLocaleString('en-IN')}`;
            benefitSubtitle = 'Estimated Benefit';
            benefitNumeric = Number(app.estimated_benefit);
        } else {
            benefitDisplay = 'Not specified';
            benefitSubtitle = 'Not specified';
            benefitNumeric = 0;
        }
    } else {
        benefitDisplay = 'Not specified';
        benefitSubtitle = 'Benefit Information Unavailable';
        benefitNumeric = 0;
    }

    // 4. Resolve applicant name
    let applicantName = 'Applicant';
    if (app.applicant_id) {
        try {
            const { data: prof } = await supabaseAdmin
                .from('applicant_profiles')
                .select('full_name')
                .eq('id', app.applicant_id)
                .maybeSingle();
            if (prof?.full_name) {
                applicantName = prof.full_name;
            } else {
                const { data: u } = await supabaseAdmin
                    .from('users')
                    .select('full_name, email')
                    .eq('id', app.applicant_id)
                    .maybeSingle();
                if (u?.full_name) applicantName = u.full_name;
            }
        } catch (_) {}
    }

    // 5. Resolve documents linked to this application
    let submittedDocuments = [];
    if (app.id) {
        try {
            const { data: docRows } = await supabaseAdmin
                .from('documents')
                .select('id, document_type, file_name, file_url, verification_status, uploaded_at, updated_at')
                .eq('application_id', app.id);

            submittedDocuments = (docRows || []).map(d => ({
                id: d.id,
                name: d.file_name || DOC_LABELS[d.document_type] || d.document_type,
                document_type: d.document_type,
                file_name: d.file_name,
                file_url: d.file_url,
                verification_status: (d.verification_status || 'PENDING').toUpperCase(),
                verified: (d.verification_status || '').toUpperCase() === 'VERIFIED',
                reason: (d.verification_status || '').toUpperCase() === 'VERIFIED' ? 'Verified ✓' :
                    (d.verification_status || '').toUpperCase() === 'REJECTED' ? 'Rejected' : 'Pending Verification',
                uploaded_at: d.uploaded_at
            }));
        } catch (_) {}
    }

    const requiredDocuments = scheme?.documents_required || scheme?.required_documents || [];

    const isActionReq = Boolean(
        app.status === 'action_required' ||
        (app.decision_notes && app.decision_notes.startsWith('ACTION_REQUIRED:')) ||
        (app.status === 'under_review' && app.reviewed_at && app.decision_notes)
    );
    const resolvedStatus = isActionReq ? 'action_required' : (app.status || 'under_review');
    const cleanRemarks = app.decision_notes?.startsWith('ACTION_REQUIRED:')
        ? app.decision_notes.replace(/^ACTION_REQUIRED:\s*/i, '').trim()
        : (app.decision_notes || null);

    return {
        ...app,
        status: resolvedStatus,
        applicant_name: applicantName,
        scheme_name: isSchemeAvailable ? resolvedSchemeName : null,
        scheme: isSchemeAvailable ? scheme : null,
        is_scheme_available: isSchemeAvailable,
        financial_benefit: financialBenefit,
        benefit_display: benefitDisplay,
        benefit_subtitle: benefitSubtitle,
        benefit_numeric: benefitNumeric,
        benefit_type: scheme?.benefit_type || financialBenefit?.benefitType || null,
        dbt_scheme: scheme?.dbt_scheme ?? false,
        category: scheme?.category || null,
        submitted_documents: submittedDocuments,
        required_documents: requiredDocuments,
        remarks: cleanRemarks,
        rejection_reason: (resolvedStatus === 'rejected' || resolvedStatus === 'action_required')
            ? (cleanRemarks || app.llm_explanation || 'Pending administrative review')
            : null,
        last_updated: app.updated_at || app.reviewed_at || app.submitted_at || app.created_at
    };
};

/**
 * List applications for a user
 */
const listApplications = async (userId) => {
    const applicantId = await getApplicantId(userId);

    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('*')
        .eq('applicant_id', applicantId)
        .order('created_at', { ascending: false });

    if (error) {
        console.warn('Error fetching applications from DB:', error.message);
        return [];
    }

    return Promise.all((data || []).map(app => hydrateApplicationRecord(app)));
};

/**
 * Create a new application
 */
const createApplication = async (userId, applicationData) => {
    const applicantId = await getApplicantId(userId);

    const rawSchemeId = applicationData.schemeId || applicationData.scheme_id;
    if (!rawSchemeId) {
        throw httpError(400, 'schemeId is required to submit an application');
    }

    let resolvedSchemeName = applicationData.schemeName || applicationData.schemeTitle || applicationData.subject || null;
    let schemeRecord = null;

    try {
        const res = await schemeService.getSchemeById(rawSchemeId);
        if (res && res.scheme) {
            schemeRecord = res.scheme;
            resolvedSchemeName = schemeRecord.scheme_name || schemeRecord.name || schemeRecord.title || resolvedSchemeName;
        }
    } catch (_) {}

    if (!schemeRecord) {
        throw httpError(404, `Invalid scheme ID: '${rawSchemeId}' does not exist in the official scheme catalog.`);
    }

    if (isGenericTitle(resolvedSchemeName)) {
        resolvedSchemeName = schemeRecord.scheme_name || schemeRecord.name || schemeRecord.title || null;
    }

    // Citizen submissions can only initialize as draft or under_review
    const clientStatus = String(applicationData.status || '').toLowerCase();
    const validInitialStatus = (clientStatus === 'draft') ? 'draft' : 'under_review';

    const targetSchemeUuid = ensureUuid(schemeRecord.id || rawSchemeId);

    // Prevent duplicate applications for the same scheme
    const { data: existingApp } = await supabaseAdmin
        .from('applications')
        .select('id')
        .eq('applicant_id', applicantId)
        .eq('scheme_id', targetSchemeUuid)
        .maybeSingle();

    if (existingApp) {
        throw httpError(409, 'An application for this scheme has already been submitted for your profile.');
    }

    const newApp = {
        applicant_id: applicantId,
        scheme_id: targetSchemeUuid,
        status: validInitialStatus,
        estimated_benefit: schemeRecord?.max_benefit ? Number(schemeRecord.max_benefit) : null,
        decision_notes: resolvedSchemeName || null,
        submitted_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    };

    const { data, error } = await supabaseAdmin
        .from('applications')
        .insert(newApp)
        .select()
        .single();

    if (error) {
        if (error.code === '23505' || error.message?.includes('unique constraint')) {
            throw httpError(409, 'An application for this scheme has already been submitted for your profile.');
        }
        throw httpError(500, error.message);
    }
    return hydrateApplicationRecord(data);
};

/**
 * Get application by ID
 */
const getApplicationById = async (userId, applicationId) => {
    const cleanId = String(applicationId || '').trim();
    if (!cleanId || !UUID_REGEX.test(cleanId)) {
        throw httpError(404, 'Application not found');
    }
    const applicantId = await getApplicantId(userId);

    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('*')
        .eq('id', cleanId)
        .eq('applicant_id', applicantId)
        .maybeSingle();

    if (error) {
        if (error.code === '22P02') throw httpError(404, 'Application not found');
        throw httpError(500, error.message);
    }
    if (!data) throw httpError(404, 'Application not found');
    return hydrateApplicationRecord(data);
};

module.exports = {
    analyzeApplication,
    listApplications,
    createApplication,
    getApplicationById,
    hydrateApplicationRecord,
    isGenericTitle
};

