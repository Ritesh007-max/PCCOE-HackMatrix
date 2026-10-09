/**
 * Dashboard Dynamic Data & Integrity Test Suite (Phase D3.2)
 *
 * Verifies:
 * 1. Applicant-specific recommendation retrieval.
 * 2. Profile and document facts reaching the Intelligence recommendation pipeline.
 * 3. Preservation of canonical eligibility statuses: PASS, FAIL, UNKNOWN, REVIEW.
 * 4. No fabricated match percentages or arbitrary addition heuristics.
 * 5. Correct separation of retrieval relevance and statutory eligibility.
 * 6. Correct benefit calculation and exclusion of commercial loan ceilings.
 * 7. Profile-scoped relevant scheme count (location/state scope, not global 4,752).
 * 8. Applicant data isolation (tenant isolation).
 * 9. Pending versus verified document calculation integrity.
 * 10. Existing application stats integrity.
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const dashboardService = require('../src/services/dashboardService');
const schemeService = require('../src/services/schemeService');
const profileService = require('../src/services/profileService');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('Dashboard Dynamic Data & Pipeline Integrity Suite', () => {

    const testApplicantId = 'app-user-test-uuid-001';

    let originalRecommendSchemes;
    let originalGetProfileById;
    let originalFrom;

    beforeEach(() => {
        originalRecommendSchemes = schemeService.recommendSchemes;
        originalGetProfileById = profileService.getProfileById;
        originalFrom = supabaseAdmin.from;
    });

    afterEach(() => {
        schemeService.recommendSchemes = originalRecommendSchemes;
        profileService.getProfileById = originalGetProfileById;
        supabaseAdmin.from = originalFrom;
    });

    test('1 & 2 & 8: Recommendations are scoped to authenticated applicant and pass profile/document facts', async () => {
        let capturedApplicantId = null;
        let capturedOptions = null;

        profileService.getProfileById = async (userId) => {
            return {
                id: userId,
                full_name: 'Rajesh Patel',
                state: 'Gujarat',
                district: 'Ahmedabad',
                occupation: 'student',
                annual_income: 350000,
                profile_completed_percent: 90
            };
        };

        schemeService.recommendSchemes = async (applicantId, options) => {
            capturedApplicantId = applicantId;
            capturedOptions = options;
            return {
                source: 'intelligence',
                recommendations: [
                    {
                        scheme_id: 'post_matric_gujarat',
                        scheme_name: 'Post Matric Scholarship for ST/SC Students',
                        ministry: 'Tribal Development Department',
                        description: 'Direct scholarship grant for students',
                        max_benefit: 25000,
                        type: 'Cash',
                        eligibility_status: 'UNKNOWN',
                        is_eligible: null,
                        tags: ['Student', 'Scholarship', 'Gujarat'],
                        recommendation_reasons: ['Profile matched student occupation']
                    }
                ],
                total: 1
            };
        };

        // Mock Supabase counts & documents
        supabaseAdmin.from = (table) => {
            if (table === 'schemes') {
                return {
                    select: () => ({
                        contains: () => Promise.resolve({ count: 641, error: null })
                    })
                };
            }
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: (col, val) => {
                            assert.strictEqual(val, testApplicantId, 'Applicant isolation violated in applications query');
                            return Promise.resolve({
                                data: [
                                    { id: 'app_1', applicant_id: val, status: 'under_review' }
                                ],
                                error: null
                            });
                        }
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        in: () => Promise.resolve({
                            data: [
                                { document_type: 'address_proof', verification_status: 'PENDING' }
                            ],
                            error: null
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);

        // 1 & 8: Scoped to test applicant
        assert.strictEqual(capturedApplicantId, testApplicantId, 'Must pass authenticated applicant ID');
        assert.strictEqual(capturedOptions.state_override, 'Gujarat', 'Must pass applicant state');
        assert.ok(dashData, 'Dashboard data returned');
        assert.strictEqual(dashData.user.fullName, 'Rajesh Patel');
    });

    test('3, 4 & 5: Preservation of canonical eligibility states and removal of fabricated percentages', async () => {
        profileService.getProfileById = async (userId) => ({
            id: userId,
            full_name: 'Rajesh Patel',
            state: 'Gujarat',
            occupation: 'student'
        });

        schemeService.recommendSchemes = async () => ({
            source: 'intelligence',
            recommendations: [
                {
                    scheme_id: 'scheme_pass',
                    scheme_name: 'Confirmed Eligible Scheme',
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    max_benefit: 12000,
                    type: 'Cash',
                    tags: ['Direct Benefit']
                },
                {
                    scheme_id: 'scheme_review',
                    scheme_name: 'Conflicting Income Scheme',
                    eligibility_status: 'REVIEW',
                    is_eligible: null,
                    max_benefit: 20000,
                    type: 'Cash',
                    tags: ['Student']
                },
                {
                    scheme_id: 'scheme_unknown',
                    scheme_name: 'Missing DOB Scheme',
                    eligibility_status: 'UNKNOWN',
                    is_eligible: null,
                    max_benefit: 5000,
                    type: 'Cash',
                    tags: ['Welfare']
                },
                {
                    scheme_id: 'scheme_fail',
                    scheme_name: 'High Income Ineligible Scheme',
                    eligibility_status: 'FAIL',
                    is_eligible: false,
                    max_benefit: 15000,
                    type: 'Cash',
                    tags: ['BPL']
                }
            ]
        });

        supabaseAdmin.from = (table) => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 641, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const opps = dashData.topOpportunities;

        assert.strictEqual(opps.length, 4);

        // Invariant: Exact statutory states preserved
        assert.strictEqual(opps[0].eligibilityStatus, 'PASS');
        assert.strictEqual(opps[0].isEligible, true);

        assert.strictEqual(opps[1].eligibilityStatus, 'REVIEW');
        assert.strictEqual(opps[1].isEligible, false);

        assert.strictEqual(opps[2].eligibilityStatus, 'UNKNOWN');
        assert.strictEqual(opps[2].isEligible, false);

        assert.strictEqual(opps[3].eligibilityStatus, 'FAIL');
        assert.strictEqual(opps[3].isEligible, false);

        // Invariant: No arbitrary match scores (e.g. 95, 80, 75) present
        opps.forEach(o => {
            assert.strictEqual(o.matchScore, undefined, 'Fabricated matchScore percentage must not exist');
        });
    });

    test('6: Estimated benefits excludes commercial loan ceilings and sums only verified grants', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        schemeService.recommendSchemes = async () => ({
            source: 'intelligence',
            recommendations: [
                {
                    scheme_id: 'standup_india',
                    scheme_name: 'Stand-Up India Scheme',
                    type: 'Loan',
                    max_benefit: 10000000, // 1 Crore commercial loan ceiling
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    tags: ['loan', 'msme']
                },
                {
                    scheme_id: 'pm_kisan',
                    scheme_name: 'PM Kisan Samman Nidhi',
                    type: 'Cash',
                    max_benefit: 6000, // Direct welfare grant
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    tags: ['Farmer', 'DBT']
                },
                {
                    scheme_id: 'unverified_grant',
                    scheme_name: 'Unverified Subsidy',
                    type: 'Cash',
                    max_benefit: 50000,
                    eligibility_status: 'UNKNOWN', // Unverified: Must NOT sum as confirmed
                    is_eligible: null,
                    tags: ['Direct Benefit']
                }
            ]
        });

        supabaseAdmin.from = () => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 641, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const benefitsMetric = dashData.metrics.find(m => m.key === 'benefits');

        // Only PM-Kisan (₹6,000) is a confirmed PASS grant.
        // Stand-Up India (₹1,00,00,000 loan) must be EXCLUDED from grant benefits.
        // Unverified Subsidy (₹50,000 UNKNOWN) must NOT be counted as confirmed.
        assert.strictEqual(benefitsMetric.value, '₹ 6,000');
        assert.strictEqual(benefitsMetric.subtitle, 'Confirmed welfare grants');

        // Check individual card presentation
        const standUpCard = dashData.topOpportunities.find(o => o.schemeId === 'standup_india');
        assert.strictEqual(standUpCard.isLoan, true);
        assert.ok(standUpCard.benefitDisplay.includes('(Loan)'), 'Must indicate loan ceiling on card');
    });

    test('7: Relevant Schemes metric is profile-scoped, including state and central jurisdiction', async () => {
        profileService.getProfileById = async (userId) => ({
            id: userId,
            state: 'Gujarat'
        });

        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        let filterUsed = null;
        supabaseAdmin.from = (table) => {
            if (table === 'schemes') {
                return {
                    select: (fields, opts) => ({
                        contains: (col, val) => {
                            filterUsed = { col, val };
                            return Promise.resolve({ data: [], count: 641, error: null });
                        },
                        ilike: () => Promise.resolve({ data: [], count: 30, error: null })
                    })
                };
            }
            return {
                select: () => ({
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const schemesMetric = dashData.metrics.find(m => m.key === 'schemes');

        // Dynamic jurisdiction count includes State (641) + Central (29) = 670
        assert.strictEqual(schemesMetric.value, '670', 'Must reflect profile-scoped state + central count, not 4,752');
        assert.strictEqual(filterUsed.val[0], 'Gujarat');
        assert.strictEqual(schemesMetric.subtitle, 'Available in Gujarat & Central jurisdiction');
    });

    test('9: Pending vs verified document calculations preserve actual verification status in vault', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({
                            data: [{ id: 'app_single' }],
                            error: null
                        })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        in: () => Promise.resolve({
                            data: [
                                // 1 pending document, 0 verified
                                { document_type: 'address_proof', verification_status: 'PENDING' }
                            ],
                            error: null
                        })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const docMetric = dashData.metrics.find(m => m.key === 'documents');

        // Data-driven vault: 1 document in vault, 0 verified, 1 pending
        assert.strictEqual(docMetric.value, '0 / 1');
        assert.ok(docMetric.subtitle.includes('1 pending review'), 'Must explicitly indicate pending review');
        assert.strictEqual(docMetric.isWarning, true);
    });
});
