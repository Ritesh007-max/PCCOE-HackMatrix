const fs = require('fs');
const path = require('path');
const { supabaseAdmin } = require('../config/supabaseConfig');
const profileService = require('./profileService');
const schemeService = require('./schemeService');
const { interpretFinancialBenefit, BenefitCategories } = require('./financialBenefitService');

const isTableMissingError = (err) => {
    return err && (
        err.code === '42P01' ||
        (err.message && (err.message.includes('schema cache') || err.message.includes('does not exist')))
    );
};

/**
 * In-memory index of canonical scheme jurisdiction levels from the active snapshot.
 * Resolves verified Central vs State schemes to provide an accurate, non-duplicated
 * count of active welfare schemes applicable to a citizen's jurisdiction.
 */
let canonicalJurisdictionIndex = null;

const getCanonicalJurisdictionIndex = () => {
    if (canonicalJurisdictionIndex) return canonicalJurisdictionIndex;
    canonicalJurisdictionIndex = {
        centralIds: new Set(),
        stateSchemeMap: new Map()
    };
    try {
        const snapshotsRoot = path.resolve(__dirname, '../../../Intelligence/data/snapshots');
        const activeJson = path.join(snapshotsRoot, 'active_version.json');
        if (fs.existsSync(activeJson)) {
            const activeData = JSON.parse(fs.readFileSync(activeJson, 'utf8'));
            if (activeData.active_snapshot) {
                const canonicalFile = path.join(snapshotsRoot, activeData.active_snapshot, 'canonical', 'schemes.jsonl');
                if (fs.existsSync(canonicalFile)) {
                    const content = fs.readFileSync(canonicalFile, 'utf8');
                    const lines = content.split('\n');
                    for (const line of lines) {
                        if (!line || !line.trim()) continue;
                        try {
                            const json = JSON.parse(line.replace(/:\s*NaN/g, ': null'));
                            const id = json.slug || json.id;
                            if (!id) continue;
                            if (json.level === 'Central' && !json.beneficiary_type) {
                                const formatted = schemeService.formatSchemeRecord ? schemeService.formatSchemeRecord(json) : json;
                                if (schemeService.isCentralScheme && schemeService.isCentralScheme(formatted)) {
                                    const relevant = schemeService.filterApplicantRelevantSchemes ? schemeService.filterApplicantRelevantSchemes([formatted], 'Gujarat') : [formatted];
                                    if (relevant.length > 0) {
                                        canonicalJurisdictionIndex.centralIds.add(id);
                                    }
                                }
                            } else if (json.level === 'State' && json.state) {
                                const st = String(json.state).trim().toLowerCase();
                                if (!canonicalJurisdictionIndex.stateSchemeMap.has(st)) {
                                    canonicalJurisdictionIndex.stateSchemeMap.set(st, new Set());
                                }
                                canonicalJurisdictionIndex.stateSchemeMap.get(st).add(id);
                            }
                        } catch (_) {}
                    }
                }
            }
        }
    } catch (_) {}
    return canonicalJurisdictionIndex;
};

/**
 * Data-driven document metrics for the authenticated applicant's document vault.
 * Removes universal hardcoded checklists. Deduplicates records by document type
 * and preserves authentic verification statuses (VERIFIED, PENDING, REJECTED).
 */
const getDocumentStats = async (applicantId) => {
    if (!applicantId) {
        return { totalVault: 0, totalRequired: 0, verified: 0, pending: 0, rejected: 0, missing: 0, details: [] };
    }

    let rawDocs = [];
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
            let docQuery = supabaseAdmin
                .from('documents')
                .select('id, document_type, verification_status, uploaded_at')
                .in('application_id', applications.map((application) => application.id));

            if (typeof docQuery.order === 'function') {
                docQuery = docQuery.order('uploaded_at', { ascending: false });
            }

            const { data, error } = await docQuery;

            if (error) {
                if (!isTableMissingError(error)) {
                    const serviceError = new Error(error.message);
                    serviceError.status = 500;
                    throw serviceError;
                }
            } else {
                rawDocs = data || [];
            }
        }
    } catch (err) {
        if (!isTableMissingError(err)) throw err;
    }

    // Deduplicate by document_type (keeping most recent or highest verification status)
    // Priority: verified (3) > pending / review_required (2) > rejected (1)
    const STATUS_PRIORITY = { verified: 3, pending: 2, review_required: 2, rejected: 1 };
    const docMap = new Map();

    for (const doc of rawDocs) {
        const rawType = (doc.document_type || 'other').trim().toLowerCase();
        const normType = rawType === 'land_records' ? 'land' : rawType;
        const rawStatus = String(doc.verification_status || 'PENDING').toLowerCase();
        const status = rawStatus === 'verified' ? 'verified' : (rawStatus === 'rejected' ? 'rejected' : 'pending');

        if (!docMap.has(normType)) {
            docMap.set(normType, { id: doc.id, doc_type: normType, status });
        } else {
            const existing = docMap.get(normType);
            if ((STATUS_PRIORITY[status] || 0) > (STATUS_PRIORITY[existing.status] || 0)) {
                docMap.set(normType, { id: doc.id, doc_type: normType, status });
            }
        }
    }

    const uniqueDocs = Array.from(docMap.values());
    const verifiedCount = uniqueDocs.filter(d => d.status === 'verified').length;
    const pendingCount = uniqueDocs.filter(d => d.status === 'pending').length;
    const rejectedCount = uniqueDocs.filter(d => d.status === 'rejected').length;
    const totalVault = uniqueDocs.length;

    return {
        totalVault,
        totalRequired: totalVault,
        verified: verifiedCount,
        pending: pendingCount,
        rejected: rejectedCount,
        missing: 0,
        details: uniqueDocs
    };
};

/**
 * Retrieves and aggregates applications strictly scoped to the authenticated user.
 * Accurately categorizes workflow states: under_review, submitted, approved, rejected.
 */
const getApplicationStats = async (applicantId) => {
    if (!applicantId) {
        return { total: 0, pending: 0, approved: 0, rejected: 0, details: [] };
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
        status: (app.status || app.application_status || 'submitted').toLowerCase(),
        applied_at: app.applied_at || app.submitted_at || app.created_at
    }));

    const pendingCount = normalizedApps.filter(a =>
        ['under_review', 'submitted', 'pending'].includes(a.status)
    ).length;
    const approvedCount = normalizedApps.filter(a =>
        ['approved', 'sanctioned'].includes(a.status)
    ).length;
    const rejectedCount = normalizedApps.filter(a =>
        ['rejected'].includes(a.status)
    ).length;

    normalizedApps.sort((a, b) => new Date(b.applied_at || 0) - new Date(a.applied_at || 0));

    return {
        total: normalizedApps.length,
        pending: pendingCount,
        approved: approvedCount,
        rejected: rejectedCount,
        details: normalizedApps
    };
};

/**
 * Deduplicates opportunities using stable identity (scheme_id / scheme_slug / id).
 * Strictly avoids broad title similarity heuristics to prevent collapsing distinct statutory policies.
 */
const deduplicateOpportunities = (items) => {
    if (!Array.isArray(items)) return [];
    const seenIds = new Set();
    const unique = [];
    for (const item of items) {
        if (!item) continue;
        const stableId = String(item.scheme_id || item.schemeId || item.id || item.scheme_slug || '').trim().toLowerCase();
        if (!stableId) continue;
        if (!seenIds.has(stableId)) {
            seenIds.add(stableId);
            unique.push(item);
        }
    }
    return unique;
};

const getTopOpportunities = async (profile) => {
    if (!profile || !profile.id) return [];

    let opportunities = [];

    // 1. Primary: Canonical recommendation & eligibility pipeline via Intelligence
    try {
        const recResult = await schemeService.recommendSchemes(profile.id, {
            query: 'schemes matching my profile and state',
            top_k: 10,
            state_override: profile.state || undefined,
            category_override: profile.caste_category || profile.category || undefined
        });

        if (recResult && Array.isArray(recResult.recommendations) && recResult.recommendations.length > 0) {
            opportunities = deduplicateOpportunities(recResult.recommendations);
        }
    } catch (err) {
        console.warn('[dashboardService] schemeService.recommendSchemes notice:', err.message);
    }

    // 2. Safe offline fallback: return profile-scoped catalog schemes from Supabase with UNKNOWN eligibility
    // Dynamically ranks schemes by applicant profile relevance (state, occupation, category)
    // rather than taking arbitrary physical disk order.
    if (opportunities.length === 0) {
        try {
            let query = supabaseAdmin.from('schemes').select('*');
            if (profile.state) {
                query = query.contains('tags', [profile.state]);
            }
            const { data: candidates } = await query.limit(100);
            if (candidates && candidates.length > 0) {
                const occTerms = (profile.occupation ? [profile.occupation.toLowerCase(), 'education', 'scholarship', 'student', 'study'] : []);
                const cat = (profile.caste_category || profile.category || '').toLowerCase();
                const isSC = cat.includes('sc') || cat.includes('scheduled caste');
                const isST = cat.includes('st') || cat.includes('scheduled tribe');

                const scored = candidates.map(s => {
                    const tags = (Array.isArray(s.tags) ? s.tags : []).map(t => String(t).toLowerCase());
                    const text = `${s.name || ''} ${s.brief_description || ''} ${tags.join(' ')}`.toLowerCase();

                    let relevanceScore = 0;
                    // Occupation / Role match
                    if (occTerms.length > 0) {
                        if (tags.some(t => occTerms.includes(t)) || occTerms.some(term => text.includes(term))) {
                            relevanceScore += 10;
                        }
                    }
                    // Social category match / conflict penalty
                    if (isSC) {
                        if (tags.includes('sc') || tags.includes('scheduled caste') || text.includes('scheduled caste')) {
                            relevanceScore += 10;
                        }
                        if ((tags.includes('scheduled tribe') || tags.includes('st')) && !tags.includes('sc')) {
                            relevanceScore -= 15;
                        }
                    } else if (isST) {
                        if (tags.includes('scheduled tribe') || tags.includes('st') || text.includes('scheduled tribe')) {
                            relevanceScore += 10;
                        }
                        if ((tags.includes('scheduled caste') || tags.includes('sc')) && !tags.includes('st')) {
                            relevanceScore -= 15;
                        }
                    }

                    return {
                        scheme_id: s.id,
                        scheme_name: s.name,
                        ministry: s.ministry || 'Government of India',
                        description: s.benefit_summary || s.brief_description || '',
                        eligibility_status: 'UNKNOWN',
                        is_eligible: null,
                        max_benefit: s.max_benefit || null,
                        tags: Array.isArray(s.tags) ? s.tags : ['Welfare Scheme'],
                        source_url: null,
                        relevanceScore,
                        recommendation_reasons: ['Profile matched relevant criteria — eligibility verification pending']
                    };
                });

                // Deterministic sort by relevance, breaking ties with scheme_id
                scored.sort((a, b) => b.relevanceScore - a.relevanceScore || a.scheme_id.localeCompare(b.scheme_id));
                opportunities = deduplicateOpportunities(scored);
            }
        } catch (_) {}
    }

    return deduplicateOpportunities(opportunities).slice(0, 5);
};

const getDashboardData = async (userId) => {
    const profile = await profileService.getProfileById(userId);
    const [docStats, appStats, topOpportunities] = await Promise.all([
        getDocumentStats(profile?.id),
        getApplicationStats(profile?.id),
        getTopOpportunities(profile)
    ]);

    const finalOpportunities = topOpportunities || [];

    // 1. Relevant Schemes: Unified canonical catalog count across State & Central statutory schemes
    let relevantSchemesCount = 0;
    let centralCount = 0;
    const userState = profile?.state;

    if (userState) {
        try {
            const catalog = await schemeService.getApplicableSchemesCatalog(userState);
            relevantSchemesCount = catalog.totalApplicable;
            centralCount = catalog.applicableCentralCount;
        } catch (_) {
            const jurisdiction = getCanonicalJurisdictionIndex();
            centralCount = jurisdiction.centralIds.size;
            if (jurisdiction.stateSchemeMap.has(userState.toLowerCase())) {
                const stateSet = jurisdiction.stateSchemeMap.get(userState.toLowerCase()) || new Set();
                relevantSchemesCount = stateSet.size + centralCount;
            } else {
                relevantSchemesCount = centralCount;
            }
        }
    } else {
        try {
            const { count, error } = await supabaseAdmin
                .from('schemes')
                .select('*', { count: 'exact', head: true });
            if (!error && count != null) {
                relevantSchemesCount = count;
            }
        } catch (_) {}
    }

    // 2. Estimated Benefits: Comprehensive evaluation across all evaluated candidate schemes for applicant
    // Reads eligibility_results table and merges with active opportunities to avoid top-5 truncation.
    let evaluatedSchemes = [];
    if (profile?.id) {
        try {
            const { data: evalResults } = await supabaseAdmin
                .from('eligibility_results')
                .select('scheme_id, verdict, evaluated_at, schemes(*)')
                .eq('user_id', profile.id)
                .order('evaluated_at', { ascending: false });

            if (evalResults && evalResults.length > 0) {
                // Keep latest evaluation per scheme
                const latestMap = new Map();
                for (const r of evalResults) {
                    if (!latestMap.has(r.scheme_id)) {
                        latestMap.set(r.scheme_id, r);
                    }
                }
                evaluatedSchemes = Array.from(latestMap.values());
            }
        } catch (_) {}
    }

    const evaluatedPool = new Map();

    // Populate from eligibility_results
    for (const item of evaluatedSchemes) {
        const sId = item.scheme_id;
        const schemeObj = item.schemes || {};
        evaluatedPool.set(sId, {
            scheme_id: sId,
            scheme_name: schemeObj.name || schemeObj.scheme_name,
            max_benefit: schemeObj.max_benefit,
            type: schemeObj.type,
            tags: schemeObj.tags,
            benefit_summary: schemeObj.benefit_summary,
            brief_description: schemeObj.brief_description,
            eligibility_status: item.verdict === 'ELIGIBLE' ? 'PASS' : (item.verdict === 'NOT_ELIGIBLE' ? 'FAIL' : 'UNKNOWN'),
            is_eligible: item.verdict === 'ELIGIBLE' ? true : (item.verdict === 'NOT_ELIGIBLE' ? false : null),
            sourceRecord: schemeObj
        });
    }

    // Merge with topOpportunities recommendations
    for (const o of finalOpportunities) {
        const sId = o.scheme_id || o.id;
        if (sId) {
            const existing = evaluatedPool.get(sId);
            const isEligible = o.is_eligible === true || o.eligibility_status === 'PASS' || existing?.is_eligible === true;
            const status = (o.is_eligible === true || o.eligibility_status === 'PASS') ? 'PASS' : (o.eligibility_status || existing?.eligibility_status || 'UNKNOWN');
            evaluatedPool.set(sId, {
                ...existing,
                ...o,
                scheme_id: sId,
                is_eligible: isEligible,
                eligibility_status: status
            });
        }
    }

    // Strict financial safety rules:
    // Only confirmed non-loan scalar welfare grants (PASS) are summed into estimated cash benefits.
    // Excluded: commercial loans, credit lines, penalty waivers, composite fellowship stipends, reimbursements, and in-kind benefits.
    const allEvaluatedItems = Array.from(evaluatedPool.values());
    const confirmedScalarGrants = allEvaluatedItems.filter(item => {
        const isConfirmedEligible = item.is_eligible === true || item.eligibility_status === 'PASS';
        if (!isConfirmedEligible) return false;

        const interp = interpretFinancialBenefit(item.sourceRecord || item);
        const rawAmt = Number(item.max_benefit || item.benefit_amount || 0);

        return interp.isScalarCashGrant && rawAmt > 0;
    });

    const totalBenefits = confirmedScalarGrants.reduce((acc, curr) => acc + (Number(curr.max_benefit || curr.benefit_amount) || 0), 0);
    const formattedBenefits = totalBenefits > 0 ? `₹ ${totalBenefits.toLocaleString('en-IN')}` : '₹ 0';
    const benefitsSubtitle = totalBenefits > 0
        ? 'Confirmed welfare grants'
        : (allEvaluatedItems.length > 0 ? 'Complete verification to calculate grants' : 'No grants confirmed yet');

    const schemesSubtitle = userState 
        ? (centralCount > 0 ? `Available in ${userState} & Central jurisdiction` : `Available in ${userState} jurisdiction`)
        : 'Active welfare schemes available';

    // 3. Documents subtitle calculation
    let documentsSubtitle = 'No documents uploaded yet';
    if (docStats.totalVault > 0) {
        if (docStats.rejected > 0) {
            documentsSubtitle = `${docStats.rejected} action required, ${docStats.pending} pending review`;
        } else if (docStats.pending > 0) {
            documentsSubtitle = `${docStats.pending} pending review in vault`;
        } else {
            documentsSubtitle = docStats.totalVault === 1 ? '1 document verified in vault' : `All ${docStats.totalVault} documents verified`;
        }
    }

    // 4. Applications subtitle calculation
    let applicationsSubtitle = 'No applications submitted';
    if (appStats.total > 0) {
        if (appStats.pending > 0) {
            applicationsSubtitle = appStats.approved > 0 
                ? `${appStats.pending} pending review, ${appStats.approved} approved`
                : `${appStats.pending} pending review`;
        } else if (appStats.approved > 0) {
            applicationsSubtitle = appStats.approved === 1 ? '1 application approved' : `All ${appStats.approved} applications approved`;
        } else {
            applicationsSubtitle = 'All applications processed';
        }
    }

    const metrics = [
        {
            key: 'schemes',
            label: 'Relevant Schemes',
            value: relevantSchemesCount.toString(),
            subtitle: schemesSubtitle,
            icon: 'scheme',
            isWarning: false
        },
        {
            key: 'benefits',
            label: 'Estimated Benefits',
            value: formattedBenefits,
            subtitle: benefitsSubtitle,
            icon: 'rupee',
            isWarning: false
        },
        {
            key: 'documents',
            label: 'Documents Verified',
            value: docStats.totalVault > 0 ? `${docStats.verified} / ${docStats.totalVault}` : '0',
            subtitle: documentsSubtitle,
            icon: 'document',
            isWarning: docStats.totalVault === 0 || docStats.verified === 0 || docStats.rejected > 0
        },
        {
            key: 'applications',
            label: 'Applications',
            value: appStats.total.toString(),
            subtitle: applicationsSubtitle,
            icon: 'application',
            isWarning: false
        }
    ];

    const userDisplay = {
        fullName: profile?.full_name || 'Citizen',
        profileCompleted: profile?.profile_completed_percent ?? 0
    };

    return {
        user: userDisplay,
        metrics,
        topOpportunities: finalOpportunities.map(o => {
            const interp = interpretFinancialBenefit(o);
            const isEligible = o.is_eligible === true || o.eligibility_status === 'PASS';
            const status = o.eligibility_status || (isEligible ? 'PASS' : 'UNKNOWN');
            const rawAmt = Number(o.max_benefit || o.benefit_amount || 0);
            const isLoan = interp.category === BenefitCategories.LOAN_OR_CREDIT_FACILITY || interp.hasLoanCalculator;

            return {
                schemeId: o.scheme_id || o.id,
                schemeName: o.scheme_name || o.name,
                ministry: o.ministry || 'Government of India',
                description: o.description || o.benefit_summary || '',
                eligibilityStatus: status,
                isEligible: isEligible,
                benefitAmount: rawAmt,
                benefitDisplay: interp.amountDisplay,
                isLoan: isLoan,
                eligibility: {
                    isEligible: isEligible,
                    status: status,
                    reasons: o.recommendation_reasons || []
                },
                tags: Array.isArray(o.tags) && o.tags.length > 0 ? o.tags : ['Welfare Scheme'],
                deadline: o.scheme_close_date ? `Deadline: ${o.scheme_close_date}` : (o.deadline && o.deadline !== 'Ongoing' ? o.deadline : null),
                scheme_open_date: o.scheme_open_date || null,
                scheme_close_date: o.scheme_close_date || null,
                applicationLink: o.source_url || o.application_link || null
            };
        })
    };
};

module.exports = {
    getDashboardData,
    getDocumentStats,
    getApplicationStats,
    getTopOpportunities
};
