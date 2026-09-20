const { supabaseAdmin } = require('../config/supabaseConfig');
const profileService = require('./profileService');

const REQUIRED_DOC_TYPES = [
    'aadhaar',
    'pan',
    'income_cert',
    'caste_cert',
    'land_records',
    'disability_cert',
    'bank_passbook'
];

const isTableMissingError = (err) => {
    return err && (
        err.code === '42P01' ||
        (err.message && (err.message.includes('schema cache') || err.message.includes('does not exist')))
    );
};

const getDocumentStats = async (userId) => {
    let docs = [];
    try {
        const { data, error } = await supabaseAdmin
            .from('user_documents')
            .select('doc_type, status')
            .eq('user_id', userId);

        if (error) {
            if (!isTableMissingError(error)) {
                const serviceError = new Error(error.message);
                serviceError.status = 500;
                throw serviceError;
            }
        } else {
            docs = data || [];
        }
    } catch (err) {
        if (!isTableMissingError(err)) throw err;
    }

    const docMap = new Map();
    for (const doc of REQUIRED_DOC_TYPES) {
        docMap.set(doc, { doc_type: doc, status: 'missing' });
    }

    for (const doc of docs) {
        docMap.set(doc.doc_type, doc);
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

const getApplicationStats = async (userId) => {
    let apps = [];
    try {
        const { data, error } = await supabaseAdmin
            .from('user_applications')
            .select('id, scheme_id, scheme_name, status, applied_at')
            .eq('user_id', userId)
            .order('applied_at', { ascending: false });

        if (error) {
            if (!isTableMissingError(error)) {
                const serviceError = new Error(error.message);
                serviceError.status = 500;
                throw serviceError;
            }
        } else {
            apps = data || [];
        }
    } catch (err) {
        if (!isTableMissingError(err)) throw err;
    }

    const activeApps = (apps || []).filter(a =>
        ['submitted', 'under_review', 'approved'].includes(a.status)
    );
    const pendingCount = activeApps.filter(a => a.status === 'under_review' || a.status === 'submitted').length;
    const approvedCount = activeApps.filter(a => a.status === 'approved').length;

    return {
        total: activeApps.length,
        pending: pendingCount,
        approved: approvedCount,
        details: activeApps
    };
};

const getTopOpportunities = async (userProfile) => {
    if (!userProfile) return [];

    const opportunities = [
        {
            scheme_id: 'PM-KISAN-2024',
            scheme_name: 'PM Kisan Samman Nidhi',
            ministry: 'Ministry of Agriculture',
            description: 'Income support of Rs. 6,000/year to small and marginal farmers',
            match_score: 95,
            benefit_amount: 6000,
            eligibility: ['Farmer', 'Land holding < 2 hectares'],
            deadline: '2025-03-31',
            application_link: 'https://pmkisan.gov.in'
        },
        {
            scheme_id: 'MSME-REG-2024',
            scheme_name: 'Udyam Registration for MSMEs',
            ministry: 'Ministry of MSME',
            description: 'Official registration for Micro, Small & Medium Enterprises with credit benefits',
            match_score: 88,
            benefit_amount: 0,
            eligibility: ['MSME', 'Business registration'],
            deadline: 'Ongoing',
            application_link: 'https://udyamregistration.gov.in'
        },
        {
            scheme_id: 'STUDENT-SCHOLAR-2024',
            scheme_name: 'National Scholarship Portal',
            ministry: 'Ministry of Education',
            description: 'Scholarships for students from minority/SC/ST/OBC communities',
            match_score: 82,
            benefit_amount: 50000,
            eligibility: ['Student', 'Family income < Rs. 2.5L', 'Category: SC/ST/OBC/Minority'],
            deadline: '2025-10-31',
            application_link: 'https://scholarships.gov.in'
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
    const [profile, docStats, appStats] = await Promise.all([
        profileService.getProfileById(userId),
        getDocumentStats(userId),
        getApplicationStats(userId)
    ]);

    const topOpportunities = await getTopOpportunities(profile);

    const totalEstimatedBenefit = topOpportunities.reduce((sum, o) => sum + (o.benefit_amount || 0), 0);

    const metrics = [
        {
            key: 'schemes',
            label: 'Eligible Schemes',
            value: topOpportunities.length.toString(),
            subtitle: 'Based on your profile',
            icon: 'scheme',
            isWarning: false
        },
        {
            key: 'benefits',
            label: 'Estimated Benefits',
            value: `Rs. ${totalEstimatedBenefit.toLocaleString()}`,
            subtitle: 'Annual potential',
            icon: 'rupee',
            isWarning: false
        },
        {
            key: 'documents',
            label: 'Documents Verified',
            value: `${docStats.verified} / ${docStats.totalRequired}`,
            subtitle: docStats.missing > 0 ? `${docStats.missing} missing` : 'All documents verified',
            icon: 'document',
            isWarning: docStats.missing > 0
        },
        {
            key: 'applications',
            label: 'Active Applications',
            value: appStats.total.toString(),
            subtitle: appStats.pending > 0 ? `${appStats.pending} pending review` : 'No pending applications',
            icon: 'application',
            isWarning: appStats.pending > 0
        }
    ];

    const userDisplay = profile ? {
        fullName: profile.full_name || 'User',
        profileCompleted: profile.profile_completed_percent || 0
    } : {
        fullName: 'User',
        profileCompleted: 0
    };

    return {
        user: userDisplay,
        metrics,
        topOpportunities: topOpportunities.map(o => ({
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
