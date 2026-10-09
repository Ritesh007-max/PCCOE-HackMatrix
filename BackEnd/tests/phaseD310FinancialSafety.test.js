/**
 * FIN Phase D3.10.1 — Financial Safety & Integrity Backend Regression Tests
 *
 * Verifies:
 * 1. YIPB canonical record does not expose unanchored ₹45,000 monthly stipend as scalar max_benefit.
 * 2. 1PMY penalty waiver canonical metadata and benefit_type are preserved.
 * 3. Dashboard estimated benefits aggregation strictly excludes loans, penalty waivers, composite schemes, and stipends.
 * 4. Dashboard top opportunities displays honest benefit descriptors rather than arbitrary cash claims.
 * 5. Generic beneficiary type ('Individual') does not overwrite missing benefit_type.
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const schemeService = require('../src/services/schemeService');
const dashboardService = require('../src/services/dashboardService');
const profileService = require('../src/services/profileService');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('FIN Phase D3.10.1: Financial Safety & Integrity Backend Suite', () => {

    const testApplicantId = 'fin-test-user-d310-001';
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

    test('1. YIPB canonical record does not expose unanchored ₹45,000 as scalar max_benefit', async () => {
        // Mock database row with legacy seed regex artifact
        const mockDbRow = {
            id: 'yipb',
            slug: 'yipb',
            name: 'Young Investigators Programme in Biotechnology',
            max_benefit: 45000, // Legacy unanchored regex artifact in Postgres
            type: 'Individual',
            tags: ['Biotechnology', 'Research']
        };

        const formatted = schemeService.formatSchemeRecord(mockDbRow);

        // Invariant: YIPB max_benefit MUST be null because ₹45,000 is a monthly fellowship stipend, not a total ceiling
        assert.strictEqual(formatted.max_benefit, null, 'YIPB max_benefit must be null to prevent bare 45k lump-sum presentation');
        assert.strictEqual(formatted.benefit_type, 'Composite', 'YIPB canonical benefit_type must be Composite');
        assert.notStrictEqual(formatted.benefit_type, 'Individual', 'Beneficiary type Individual must not become benefit_type');
    });

    test('2. 1PMY canonical metadata and null max_benefit are preserved', async () => {
        const mockDbRow = {
            id: '1pmy',
            slug: '1pmy',
            name: '100% Penalty Mafi Yojana',
            max_benefit: null,
            type: 'Individual',
            tags: ['Housing', 'Gujarat']
        };

        const formatted = schemeService.formatSchemeRecord(mockDbRow);

        assert.strictEqual(formatted.benefit_type, 'Cash', '1PMY canonical benefit_type in snapshot is Cash');
        assert.strictEqual(formatted.max_benefit, null, '1PMY max_benefit must be null');
    });

    test('3. Dashboard estimated benefits aggregation strictly excludes loans, penalty waivers, and composite stipends', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        schemeService.recommendSchemes = async () => ({
            source: 'intelligence',
            recommendations: [
                {
                    scheme_id: 'mudra_shishu',
                    scheme_name: 'Pradhan Mantri Mudra Yojana',
                    type: 'Loan',
                    benefit_type: 'Loan',
                    max_benefit: 50000,
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    tags: ['loan', 'credit']
                },
                {
                    scheme_id: 'yipb',
                    scheme_name: 'Young Investigators Programme in Biotechnology',
                    type: 'Individual',
                    benefit_type: 'Composite',
                    max_benefit: 45000, // Monthly stipend - must NOT sum into cash grant aggregate
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    tags: ['Fellowship', 'Research']
                },
                {
                    scheme_id: '1pmy',
                    scheme_name: '100% Penalty Mafi Yojana',
                    type: 'Individual',
                    benefit_type: 'Penalty Waiver',
                    max_benefit: null,
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    tags: ['Waiver', 'Housing']
                },
                {
                    scheme_id: 'pm_kisan',
                    scheme_name: 'PM Kisan Samman Nidhi',
                    type: 'Direct Cash',
                    benefit_type: 'Direct Cash Transfer',
                    max_benefit: 6000,
                    eligibility_status: 'PASS',
                    is_eligible: true,
                    tags: ['Farmer', 'DBT']
                }
            ]
        });

        supabaseAdmin.from = () => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 120, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const benefitsMetric = dashData.metrics.find(m => m.key === 'benefits');

        // Only PM-Kisan (₹6,000) is a genuine scalar cash grant.
        // Mudra (₹50,000 Loan) must NOT be added.
        // YIPB (₹45,000 monthly fellowship / Composite) must NOT be added.
        // 1PMY (Penalty Waiver) must NOT be added.
        assert.strictEqual(benefitsMetric.value, '₹ 6,000', 'Must not add loan principal, waivers, or monthly stipends to cash grants');
        assert.strictEqual(benefitsMetric.subtitle, 'Confirmed welfare grants');
    });

    test('4. Dashboard top opportunities displays honest benefit descriptors for non-scalar schemes', async () => {
        profileService.getProfileById = async (userId) => ({ id: userId, state: 'Gujarat' });

        schemeService.recommendSchemes = async () => ({
            source: 'intelligence',
            recommendations: [
                {
                    scheme_id: 'yipb',
                    scheme_name: 'Young Investigators Programme in Biotechnology',
                    benefit_type: 'Composite',
                    max_benefit: 45000,
                    eligibility_status: 'UNKNOWN'
                },
                {
                    scheme_id: '1pmy',
                    scheme_name: '100% Penalty Mafi Yojana',
                    benefit_type: 'Penalty Waiver',
                    max_benefit: null,
                    eligibility_status: 'UNKNOWN'
                }
            ]
        });

        supabaseAdmin.from = () => ({
            select: () => ({
                contains: () => Promise.resolve({ count: 50, error: null }),
                eq: () => Promise.resolve({ data: [], error: null }),
                in: () => Promise.resolve({ data: [], error: null })
            })
        });

        const dashData = await dashboardService.getDashboardData(testApplicantId);
        const yipbCard = dashData.topOpportunities.find(o => o.schemeId === 'yipb');
        const pmyCard = dashData.topOpportunities.find(o => o.schemeId === '1pmy');

        assert.strictEqual(yipbCard.benefitDisplay, 'Fellowship & Research Grant (See Guidelines)', 'YIPB must indicate multi-component nature');
        assert.ok(pmyCard.benefitDisplay === '100% Penalty Waiver' || pmyCard.benefitDisplay === 'Penalty Waiver (See Terms)', '1PMY must indicate penalty waiver');
    });

    test('5. Generic beneficiary type does not overwrite absent benefit_type', () => {
        const rawRowWithoutCanonical = {
            id: 'generic_welfare_xyz',
            slug: 'generic_welfare_xyz',
            name: 'Generic Scheme Without Canonical Snapshot',
            type: 'Individual', // beneficiary type
            benefit_type: null,
            max_benefit: null
        };

        const formatted = schemeService.formatSchemeRecord(rawRowWithoutCanonical);

        // Invariant: benefit_type should be null, not 'Individual'
        assert.strictEqual(formatted.benefit_type, null, 'Must not assign beneficiary type Individual as benefit_type');
    });
});
