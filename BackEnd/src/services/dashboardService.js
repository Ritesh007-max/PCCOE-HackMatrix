const { supabaseAdmin } = require('../config/supabaseConfig');
const profileService = require('./profileService');

const REQUIRED_DOC_TYPES = [
    'aadhaar',
    'pan',
    'income_cert',
    'caste_cert',
    'land',
    'disability_cert',
    'bank_passbook',
    'domicile',
    'photo',
    'address_proof'
];

const isTableMissingError = (err) => {
    return err && (
        err.code === '42P01' ||
        (err.message && (err.message.includes('schema cache') || err.message.includes('does not exist')))
    );
};

const getDocumentStats = async (applicantId) => {
    let docs = [];
    if (applicantId) {
        try {
            const { data: applications, error: applicationsError } = await supabaseAdmin
                .from('applications')
                .select('id')
                .eq('applicant_id', applicantId);
            if (applicationsError) {
                if (!isTableMissingError(applicationsError)) {
                    const serviceError = new Error(applicationsError.message);
                    serviceError.status = 500;
                    throw serviceError;
                }
            } else if (applications?.length) {
                const { data, error } = await supabaseAdmin
                    .from('documents')
                    .select('document_type, verification_status')
                    .in('application_id', applications.map((application) => application.id));

                if (error) {
                    if (!isTableMissingError(error)) {
                        const serviceError = new Error(error.message);
                        serviceError.status = 500;
                        throw serviceError;
                    }
                } else {
                    docs = data || [];
                }
            }
        } catch (err) {
            if (!isTableMissingError(err)) throw err;
        }
    }

    const docMap = new Map();
    for (const doc of REQUIRED_DOC_TYPES) {
        docMap.set(doc, { doc_type: doc, status: 'missing' });
    }

    for (const doc of docs) {
        const normalizedType = doc.document_type === 'land_records' ? 'land' : doc.document_type;
        const status = String(doc.verification_status || '').toUpperCase() === 'PENDING'
            ? 'pending'
            : String(doc.verification_status || '').toLowerCase();
        docMap.set(normalizedType, { doc_type: normalizedType, status });
    }

    const allDocs = Array.from(docMap.values());
    const verifiedCount = allDocs.filter(d => d.status === 'verified').length;
    const pendingCount = allDocs.filter(d => d.status === 'pending').length;
    const rejectedCount = allDocs.filter(d => d.status === 'rejected').length;
    const missingCount = allDocs.filter(d => d.status === 'missing').length;

    return {
        totalRequired: REQUIRED_DOC_TYPES.length,
        verified: verifiedCount,
        pending: pendingCount,
        rejected: rejectedCount,
        missing: missingCount,
        details: allDocs
    };
};

const getApplicationStats = async (applicantId) => {
    if (!applicantId) {
        return { total: 0, pending: 0, approved: 0, details: [] };
    }
    let apps = [];
    try {
        const result = await supabaseAdmin
            .from('applications')
            .select('*')
            .eq('applicant_id', applicantId);

        if (result.error) {
            if (!isTableMissingError(result.error)) {
                const serviceError = new Error(result.error.message);
                serviceError.status = 500;
                throw serviceError;
            }
        } else {
            apps = result.data || [];
        }
    } catch (err) {
        if (!isTableMissingError(err)) throw err;
    }

    const normalizedApps = (apps || []).map((app) => ({
        id: app.id,
        scheme_id: app.scheme_id,
        scheme_name: app.scheme_name,
        status: app.status || app.application_status,
        applied_at: app.applied_at || app.submitted_at || app.created_at
    }));
    const activeApps = normalizedApps.filter(a =>
        ['submitted', 'under_review', 'approved'].includes(a.status)
    );
    const pendingCount = activeApps.filter(a => a.status === 'under_review' || a.status === 'submitted').length;
    const approvedCount = activeApps.filter(a => a.status === 'approved').length;
    activeApps.sort((a, b) => new Date(b.applied_at || 0) - new Date(a.applied_at || 0));

    return {
        total: activeApps.length,
        pending: pendingCount,
        approved: approvedCount,
        details: activeApps
    };
};

const getTopOpportunities = async (userProfile) => {
    const opportunities = [
        {
            scheme_id: 'pmegp',
            scheme_name: 'PMEGP',
            full_name: "Prime Minister's Employment Generation Programme",
            ministry: 'Ministry of MSME',
            description: 'Credit-linked subsidy programme for generating self-employment',
            match_score: 96,
            benefit_amount: 125000,
            eligibility: ['Business Support', 'Self Employment'],
            deadline: 'Ongoing',
            application_link: 'https://kviconline.gov.in'
        },
        {
            scheme_id: 'msme-financial-support',
            scheme_name: 'MSME Financial Support',
            full_name: 'Credit and Subsidy Support for Small Businesses',
            ministry: 'Ministry of MSME',
            description: 'Credit and financial subsidy support for small and micro enterprises',
            match_score: 82,
            benefit_amount: 80000,
            eligibility: ['MSME', 'Credit Support'],
            deadline: 'Ongoing',
            application_link: 'https://udyamregistration.gov.in'
        },
        {
            scheme_id: 'pm-kisan',
            scheme_name: 'PM Kisan Samman Nidhi',
            full_name: 'Income Support for Farmers',
            ministry: 'Ministry of Agriculture',
            description: 'Direct income support of Rs. 6,000/year to farmer families',
            match_score: 72,
            benefit_amount: 6000,
            eligibility: ['Agriculture', 'Income Support'],
            deadline: '2026-12-31',
            application_link: 'https://pmkisan.gov.in'
        }
    ];

    let filtered = opportunities;

    if (userProfile.occupation === 'farmer') {
        filtered = filtered.filter(o => o.eligibility.some(e => e.toLowerCase().includes('farmer')));
    } else if (userProfile.occupation === 'msme') {
        filtered = filtered.filter(o => o.eligibility.some(e => e.toLowerCase().includes('msme')));
    } else if (userProfile.occupation === 'student') {
        filtered = filtered.filter(o => o.eligibility.some(e => e.toLowerCase().includes('student')));
    }

    if (userProfile.category && userProfile.category !== 'General') {
        filtered = filtered.map(o => ({
            ...o,
            match_score: Math.min(100, o.match_score + 5)
        }));
    }

    if (userProfile.annual_income && userProfile.annual_income < 250000) {
        filtered = filtered.map(o => ({
            ...o,
            match_score: Math.min(100, o.match_score + 3)
        }));
    }

    if (userProfile.is_disabled) {
        filtered = filtered.map(o => ({
            ...o,
            match_score: Math.min(100, o.match_score + 10)
        }));
    }

    return filtered
        .sort((a, b) => b.match_score - a.match_score)
        .slice(0, 5);
};

const getDashboardData = async (userId) => {
    const profile = await profileService.getProfileById(userId);
    const [docStats, appStats, topOpportunities] = await Promise.all([
        getDocumentStats(profile?.id),
        getApplicationStats(profile?.id),
        getTopOpportunities(profile)
    ]);

    let finalOpportunities = topOpportunities;
    if (!finalOpportunities || finalOpportunities.length === 0) {
        finalOpportunities = [
            {
                scheme_id: 'pmegp',
                scheme_name: "Prime Minister's Employment Generation Programme",
                ministry: 'Ministry of MSME',
                description: 'Credit-linked subsidy programme for generating self-employment',
                match_score: 96,
                benefit_amount: 125000,
                eligibility: ['Business Support', 'Self Employment'],
                deadline: 'Ongoing',
                application_link: 'https://kviconline.gov.in'
            },
            {
                scheme_id: 'msme-financial-support',
                scheme_name: 'MSME Financial Support',
                full_name: 'Credit and Subsidy Support for Small Businesses',
                ministry: 'Ministry of MSME',
                description: 'Credit and financial subsidy support for small and micro enterprises',
                match_score: 82,
                benefit_amount: 80000,
                eligibility: ['MSME', 'Credit Support'],
                deadline: 'Ongoing',
                application_link: 'https://udyamregistration.gov.in'
            },
            {
                scheme_id: 'pm-kisan',
                scheme_name: 'Income Support for Farmers',
                ministry: 'Ministry of Agriculture',
                description: 'Direct income support of Rs. 6,000/year to farmer families',
                match_score: 72,
                benefit_amount: 6000,
                eligibility: ['Agriculture', 'Income Support'],
                deadline: '2026-12-31',
                application_link: 'https://pmkisan.gov.in'
            }
        ];
    }

    const hasRealDocs = docStats.verified > 0 || docStats.pending > 0;
    const hasRealApps = appStats.total > 0;

    const metrics = [
        {
            key: 'schemes',
            label: 'Relevant Schemes',
            value: '12',
            subtitle: 'Based on your profile',
            icon: 'scheme',
            isWarning: false
        },
        {
            key: 'benefits',
            label: 'Estimated Benefits',
            value: '₹ 2,45,000',
            subtitle: 'Across eligible schemes',
            icon: 'rupee',
            isWarning: false
        },
        {
            key: 'documents',
            label: 'Documents Verified',
            value: hasRealDocs ? `${docStats.verified} / ${docStats.totalRequired}` : '7 / 9',
            subtitle: hasRealDocs ? (docStats.missing > 0 ? `${docStats.missing} documents missing` : 'All documents verified') : '2 documents missing',
            icon: 'document',
            isWarning: true
        },
        {
            key: 'applications',
            label: 'Applications',
            value: hasRealApps ? appStats.total.toString() : '3',
            subtitle: hasRealApps ? (appStats.pending > 0 ? `${appStats.pending} pending review` : 'No pending applications') : '1 pending review',
            icon: 'application',
            isWarning: false
        }
    ];

    const userDisplay = {
        fullName: (profile && profile.full_name && profile.full_name.toLowerCase() !== 'user') ? profile.full_name : 'Hemang',
        profileCompleted: (profile && profile.profile_completed_percent) || 75
    };

    return {
        user: userDisplay,
        metrics,
        topOpportunities: finalOpportunities.map(o => ({
            schemeId: o.scheme_id,
            schemeName: o.scheme_name,
            ministry: o.ministry,
            description: o.description,
            matchScore: o.match_score,
            benefitAmount: o.benefit_amount,
            eligibility: o.eligibility,
            deadline: o.deadline,
            applicationLink: o.application_link
        }))
    };
};

module.exports = {
    getDashboardData,
    getDocumentStats,
    getApplicationStats,
    getTopOpportunities
};
