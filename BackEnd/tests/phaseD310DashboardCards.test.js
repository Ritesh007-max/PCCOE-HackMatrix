/**
 * FIN Phase D3.10: Dashboard Four Summary Cards Dynamic Data Integrity Suite
 *
 * Verifies:
 * 1. Relevant Schemes:
 *    - Accurately counts State + Central jurisdiction schemes without duplication.
 *    - Handles empty/missing profile state gracefully (catalog-wide fallback).
 *    - Subtitle truthfully indicates State & Central jurisdiction, avoiding false personalized claims.
 * 2. Estimated Benefits:
 *    - Aggregates across the entire evaluated candidate pool (eligibility_results + recommendations).
 *    - Strictly counts only confirmed scalar welfare grants (PASS / ELIGIBLE).
 *    - Strictly excludes loans, credit facilities, penalty waivers, stipends, and in-kind benefits.
 *    - Leaves ₹0 when candidates are UNKNOWN, MANUAL_REVIEW, or non-scalar.
 * 3. Documents Verified:
 *    - Data-driven metric based on the authenticated user's actual document vault.
 *    - Replaces arbitrary 10-item checklist with authentic vault counts.
 *    - Handles empty vault state (0 documents uploaded).
 *    - Distinguishes verified, pending, and rejected/action-required statuses.
 *    - Numerator and denominator strictly consistent with status breakdown.
 * 4. Applications:
 *    - Strictly scoped to authenticated user ID (tenant isolation).
 *    - Aggregates under_review, submitted, approved, and rejected statuses.
 *    - Empty state handles zero applications correctly.
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const dashboardService = require('../src/services/dashboardService');
const schemeService = require('../src/services/schemeService');
const profileService = require('../src/services/profileService');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('FIN Phase D3.10: Dashboard Four Summary Cards Suite', () => {

    const testApplicantId = 'd310-applicant-uuid-001';
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

    // ─────────────────────────────────────────────────────────────────────────
    // CARD 1: RELEVANT SCHEMES
    // ─────────────────────────────────────────────────────────────────────────

    test('1. Relevant Schemes combines state-tagged and central schemes truthfully', async () => {
        profileService.getProfileById = async (userId) => ({
            id: userId,
            state: 'Gujarat'
        });

        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'schemes') {
                return {
                    select: () => ({
                        contains: () => Promise.resolve({ data: [], count: 641, error: null }),
                        ilike: () => Promise.resolve({ data: [], count: 30, error: null })
                    })
                };
            }
            return {
                select: () => ({
                    eq: () => ({
                        order: () => Promise.resolve({ data: [], error: null }),
                        then: (resolve) => resolve({ data: [], error: null })
                    }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'schemes');

        // State (641) + Central (29) = 670
        assert.strictEqual(card.value, '670');
        assert.strictEqual(card.subtitle, 'Available in Gujarat & Central jurisdiction');
        assert.strictEqual(card.isWarning, false);
    });

    test('1b. Relevant Schemes handles missing state profile field gracefully', async () => {
        profileService.getProfileById = async (userId) => ({
            id: userId,
            state: null // No state specified
        });

        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'schemes') {
                return {
                    select: () => Promise.resolve({ count: 4752, error: null })
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
        const card = dashData.metrics.find(m => m.key === 'schemes');

        assert.strictEqual(card.value, '4752');
        assert.strictEqual(card.subtitle, 'Active welfare schemes available');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CARD 2: ESTIMATED BENEFITS
    // ─────────────────────────────────────────────────────────────────────────

    test('2. Estimated Benefits aggregates confirmed scalar grants across full evaluation pool', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        // Recommendations with 1 PASS grant, 1 loan, 1 UNKNOWN
        schemeService.recommendSchemes = async () => ({
            recommendations: [
                {
                    scheme_id: 'pm_kisan',
                    scheme_name: 'PM Kisan Samman Nidhi',
                    type: 'Cash',
                    max_benefit: 6000,
                    eligibility_status: 'PASS',
                    is_eligible: true
                },
                {
                    scheme_id: 'mudra',
                    scheme_name: 'PM Mudra Yojana',
                    type: 'Loan',
                    max_benefit: 50000,
                    eligibility_status: 'PASS',
                    is_eligible: true
                },
                {
                    scheme_id: 'unknown_grant',
                    scheme_name: 'Unverified Subsidy',
                    type: 'Cash',
                    max_benefit: 25000,
                    eligibility_status: 'UNKNOWN',
                    is_eligible: null
                }
            ]
        });

        supabaseAdmin.from = (table) => {
            if (table === 'eligibility_results') {
                return {
                    select: () => ({
                        eq: () => ({
                            order: () => Promise.resolve({
                                data: [
                                    // Additional confirmed scholarship in eligibility_results (beyond top-5 recommendations)
                                    {
                                        scheme_id: 'scholarship_postmatric',
                                        verdict: 'ELIGIBLE',
                                        evaluated_at: '2026-10-04T12:00:00Z',
                                        schemes: {
                                            id: 'scholarship_postmatric',
                                            name: 'Post Matric Scholarship',
                                            type: 'Scholarship',
                                            max_benefit: 14000,
                                            benefit_summary: 'Annual educational scholarship'
                                        }
                                    }
                                ],
                                error: null
                            })
                        })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'benefits');

        // PM Kisan (₹6,000) + Post Matric Scholarship (₹14,000) = ₹20,000
        // Mudra (₹50,000 Loan) EXCLUDED
        // Unverified Subsidy (₹25,000 UNKNOWN) EXCLUDED
        assert.strictEqual(card.value, '₹ 20,000');
        assert.strictEqual(card.subtitle, 'Confirmed welfare grants');
    });

    test('2b. Estimated Benefits strictly remains ₹0 when all candidates are UNKNOWN or MANUAL_REVIEW', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        schemeService.recommendSchemes = async () => ({
            recommendations: [
                {
                    scheme_id: 'cand_1',
                    scheme_name: 'Welfare Scheme 1',
                    max_benefit: 10000,
                    eligibility_status: 'UNKNOWN',
                    is_eligible: null
                },
                {
                    scheme_id: 'cand_2',
                    scheme_name: 'Welfare Scheme 2',
                    max_benefit: 50000,
                    eligibility_status: 'UNKNOWN',
                    is_eligible: null
                }
            ]
        });

        supabaseAdmin.from = (table) => {
            if (table === 'eligibility_results') {
                return {
                    select: () => ({
                        eq: () => ({
                            order: () => Promise.resolve({
                                data: [
                                    {
                                        scheme_id: '1pmy',
                                        verdict: 'MANUAL_REVIEW',
                                        evaluated_at: '2026-10-04T10:00:00Z',
                                        schemes: { id: '1pmy', name: '100% Penalty Mafi Yojana', max_benefit: null }
                                    }
                                ],
                                error: null
                            })
                        })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'benefits');

        assert.strictEqual(card.value, '₹ 0');
        assert.strictEqual(card.subtitle, 'Complete verification to calculate grants');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CARD 3: DOCUMENTS VERIFIED
    // ─────────────────────────────────────────────────────────────────────────

    test('3. Documents Verified accurately reflects user document vault status', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [{ id: 'app_1' }], error: null })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        in: () => Promise.resolve({
                            data: [
                                { id: 'd1', document_type: 'aadhaar', verification_status: 'VERIFIED' },
                                { id: 'd2', document_type: 'pan', verification_status: 'VERIFIED' },
                                { id: 'd3', document_type: 'income_cert', verification_status: 'PENDING' }
                            ],
                            error: null
                        })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'documents');

        // 3 unique documents in vault: 2 verified, 1 pending
        assert.strictEqual(card.value, '2 / 3');
        assert.strictEqual(card.subtitle, '1 pending review in vault');
        assert.strictEqual(card.isWarning, false); // verified > 0 and no rejected
    });

    test('3b. Documents Verified handles empty vault state correctly', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [], error: null })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        in: () => Promise.resolve({ data: [], error: null })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'documents');

        assert.strictEqual(card.value, '0');
        assert.strictEqual(card.subtitle, 'No documents uploaded yet');
        assert.strictEqual(card.isWarning, true);
    });

    test('3c. Documents Verified warns when a document is rejected / action required', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [{ id: 'app_1' }], error: null })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        in: () => Promise.resolve({
                            data: [
                                { id: 'd1', document_type: 'caste_cert', verification_status: 'REJECTED' },
                                { id: 'd2', document_type: 'address_proof', verification_status: 'PENDING' }
                            ],
                            error: null
                        })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'documents');

        assert.strictEqual(card.value, '0 / 2');
        assert.strictEqual(card.subtitle, '1 action required, 1 pending review');
        assert.strictEqual(card.isWarning, true);
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CARD 4: APPLICATIONS
    // ─────────────────────────────────────────────────────────────────────────

    test('4. Applications preserves user scoping and aggregates workflow statuses', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        let queriedApplicantId = null;
        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: (col, val) => {
                            queriedApplicantId = val;
                            return Promise.resolve({
                                data: [
                                    { id: 'app_1', applicant_id: val, status: 'under_review' },
                                    { id: 'app_2', applicant_id: val, status: 'under_review' },
                                    { id: 'app_3', applicant_id: val, status: 'under_review' },
                                    { id: 'app_4', applicant_id: val, status: 'submitted' },
                                    { id: 'app_5', applicant_id: val, status: 'under_review' },
                                    { id: 'app_6', applicant_id: val, status: 'under_review' }
                                ],
                                error: null
                            });
                        }
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'applications');

        // Scoped to authenticated user
        assert.strictEqual(queriedApplicantId, testApplicantId, 'Must query strictly by authenticated applicant ID');
        assert.strictEqual(card.value, '6');
        assert.strictEqual(card.subtitle, '6 pending review');
        assert.strictEqual(card.isWarning, false);
    });

    test('4b. Applications displays approved applications count when completed', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({
                            data: [
                                { id: 'app_1', status: 'approved' },
                                { id: 'app_2', status: 'approved' }
                            ],
                            error: null
                        })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'applications');

        assert.strictEqual(card.value, '2');
        assert.strictEqual(card.subtitle, 'All 2 applications approved');
    });

    test('4c. Applications handles zero applications empty state', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId });
        schemeService.recommendSchemes = async () => ({ recommendations: [] });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [], error: null })
                    })
                };
            }
            return {
                select: () => ({
                    contains: () => Promise.resolve({ count: 100, error: null }),
                    eq: () => Promise.resolve({ data: [], error: null }),
                    in: () => Promise.resolve({ data: [], error: null })
                })
            };
        };

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const card = dashData.metrics.find(m => m.key === 'applications');

        assert.strictEqual(card.value, '0');
        assert.strictEqual(card.subtitle, 'No applications submitted');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // TOP OPPORTUNITIES: DEDUPLICATION & DISTINCT POLICY PRESERVATION
    // ─────────────────────────────────────────────────────────────────────────

    test('5a. Top Opportunities removes genuine duplicate records sharing a stable identity', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        // Simulated recommendation engine returning duplicate scheme_id records
        schemeService.recommendSchemes = async () => ({
            recommendations: [
                {
                    scheme_id: '6islbsa',
                    scheme_name: '6% Interest Subsidy on Loans taken through Banks for Study Abroad',
                    eligibility_status: 'UNKNOWN',
                    max_benefit: 150000
                },
                {
                    scheme_id: '6islbsa', // Duplicate of 6islbsa
                    scheme_name: '6% Interest Subsidy on Loans taken through Banks for Study Abroad',
                    eligibility_status: 'UNKNOWN',
                    max_benefit: 150000
                },
                {
                    scheme_id: '1pmy',
                    scheme_name: '100% Penalty Mafi Yojana',
                    eligibility_status: 'UNKNOWN',
                    max_benefit: null
                }
            ]
        });

        supabaseAdmin.from = () => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 100, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const opps = dashData.topOpportunities;

        // Deduplication must collapse the two 6islbsa records into 1
        assert.strictEqual(opps.length, 2, 'Must deduplicate records with identical stable identity');
        const ids = opps.map(o => o.schemeId);
        assert.deepStrictEqual(ids, ['6islbsa', '1pmy']);
    });

    test('5b. Top Opportunities preserves genuinely different schemes sharing title keywords', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        // Three distinct statutory policies sharing the common prefix "6% Interest Subsidy on Loans taken..."
        schemeService.recommendSchemes = async () => ({
            recommendations: [
                {
                    scheme_id: '6islbsa',
                    scheme_name: '6% Interest Subsidy on Loans taken through Banks for Study Abroad',
                    eligibility_status: 'UNKNOWN',
                    max_benefit: 150000,
                    ministry: 'Tribal Development Department'
                },
                {
                    scheme_id: '6islbse',
                    scheme_name: '6% Interest Subsidy on Loans taken through Banks up to a Limit of Rs.5 Lakh for Self-Employment',
                    eligibility_status: 'UNKNOWN',
                    max_benefit: 500000,
                    ministry: 'Tribal Development Department'
                },
                {
                    scheme_id: '6isltvpb',
                    scheme_name: '6% Interest Subsidy on Loans taken for Vehicle Purchase through Banks',
                    eligibility_status: 'UNKNOWN',
                    max_benefit: 300000,
                    ministry: 'Tribal Development Department'
                }
            ]
        });

        supabaseAdmin.from = () => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 100, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const opps = dashData.topOpportunities;

        // All 3 distinct policies must be preserved; stable identity prevents false title-similarity merging
        assert.strictEqual(opps.length, 3, 'Must preserve all 3 distinct statutory policies');
        const ids = opps.map(o => o.schemeId);
        assert.ok(ids.includes('6islbsa'), 'Must include study abroad scheme');
        assert.ok(ids.includes('6islbse'), 'Must include self-employment scheme');
        assert.ok(ids.includes('6isltvpb'), 'Must include vehicle purchase scheme');
    });

    test('5c. Preserves UNKNOWN and MANUAL_REVIEW eligibility states without score fabrication', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        schemeService.recommendSchemes = async () => ({
            recommendations: [
                {
                    scheme_id: 'scheme_unknown_status',
                    scheme_name: 'Policy Awaiting Facts',
                    eligibility_status: 'UNKNOWN',
                    is_eligible: null
                },
                {
                    scheme_id: 'scheme_manual_review',
                    scheme_name: 'Policy Requiring Manual Review',
                    eligibility_status: 'MANUAL_REVIEW',
                    is_eligible: null
                }
            ]
        });

        supabaseAdmin.from = () => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 100, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const opps = dashData.topOpportunities;

        assert.strictEqual(opps[0].eligibilityStatus, 'UNKNOWN');
        assert.strictEqual(opps[0].isEligible, false);
        assert.strictEqual(opps[1].eligibilityStatus, 'MANUAL_REVIEW');
        assert.strictEqual(opps[1].isEligible, false);

        // Invariant: Zero arbitrary scores
        opps.forEach(o => {
            assert.strictEqual(o.matchScore, undefined, 'Must not fabricate percentage scores');
        });
    });
});
