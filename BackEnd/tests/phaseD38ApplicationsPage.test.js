/**
 * FIN Phase D3.8: Applications Page Universal Data Integrity & Financial Safety Test Suite
 *
 * Verifies universal accuracy across 12 mandatory cases:
 * 1. Grant scheme: Scalar grant / financial assistance with verified grant amount
 * 2. Fellowship scheme: Monthly fellowship/stipend with recurring unit without lump-sum confusion
 * 3. Loan scheme: Credit facility/loan limit clearly distinguished from cash grant
 * 4. Interest subsidy: Interest subsidy rate/support properly identified
 * 5. Waiver scheme: Penalty/interest waiver with zero cash grant confusion
 * 6. Non-financial scheme: In-kind / non-financial assistance without fabricated amounts
 * 7. Missing scheme relationship: Transparently unavailable state without generic fallback invention
 * 8. Missing benefit amount: Explicitly displays "Not specified"
 * 9. Pending application: Persisted status under_review / submitted
 * 10. Approved application: Persisted status approved
 * 11. Rejected application: Persisted status rejected
 * 12. Action-required application: Persisted status action_required
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const applicationService = require('../src/services/applicationService');
const schemeService = require('../src/services/schemeService');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('FIN Phase D3.8: Applications Page Universal Data Integrity Suite', () => {

    const testApplicantId = 'd38-applicant-uuid-001';
    let originalFrom;
    let originalGetSchemeById;

    beforeEach(() => {
        originalFrom = supabaseAdmin.from;
        originalGetSchemeById = schemeService.getSchemeById;
    });

    afterEach(() => {
        supabaseAdmin.from = originalFrom;
        schemeService.getSchemeById = originalGetSchemeById;
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 1: GRANT SCHEME
    // ─────────────────────────────────────────────────────────────────────────
    test('1. Grant scheme: Verified scalar cash grant displays authentic amount without generic fallback', async () => {
        const mockApp = {
            id: 'app-grant-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-grant-01',
            status: 'submitted',
            estimated_benefit: 50000,
            decision_notes: null,
            submitted_at: '2026-10-01T10:00:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: 'National Innovation Project Grant',
                category: 'Business & Entrepreneurship',
                benefit_type: 'Direct Cash Grant',
                max_benefit: 50000,
                benefits: 'Direct financial assistance grant of ₹50,000 for approved innovative prototypes.',
                dbt_scheme: true
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, 'National Innovation Project Grant');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.strictEqual(hydrated.dbt_scheme, true);
        assert.ok(hydrated.benefit_display.includes('50,000'), `Expected ₹50,000 in benefit_display, got ${hydrated.benefit_display}`);
        assert.notStrictEqual(hydrated.scheme_name, 'Government Scheme Application');
        assert.notStrictEqual(hydrated.benefit_display, '₹1,75,000');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 2: FELLOWSHIP SCHEME
    // ─────────────────────────────────────────────────────────────────────────
    test('2. Fellowship scheme: Monthly fellowship displays recurring rate without lump-sum grant confusion', async () => {
        const mockApp = {
            id: 'app-fellowship-01',
            applicant_id: testApplicantId,
            scheme_id: '5eac33bf-db6b-4bb6-8945-3d10de188dd6', // wsbcas
            status: 'under_review',
            estimated_benefit: 150,
            decision_notes: null,
            submitted_at: '2026-09-26T23:47:46Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'canonical_snapshot',
            scheme: {
                id,
                scheme_name: 'Schemes for welfare of School Children: Monthly Stipend for BC-A Students',
                category: 'Education & Learning',
                benefit_type: 'Fellowship / Stipend',
                max_benefit: null,
                benefits: 'Monthly fellowship stipend of ₹150/- per month for eligible BC-A students.',
                dbt_scheme: true
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, 'Schemes for welfare of School Children: Monthly Stipend for BC-A Students');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.ok(hydrated.benefit_display.includes('150') || hydrated.benefit_display.includes('Fellowship') || hydrated.benefit_display.includes('month'),
            `Expected monthly fellowship in benefit_display, got ${hydrated.benefit_display}`);
        assert.strictEqual(hydrated.benefit_subtitle, '(Monthly Fellowship / Stipend)');
        assert.notStrictEqual(hydrated.benefit_display, '₹1,75,000');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 3: LOAN SCHEME
    // ─────────────────────────────────────────────────────────────────────────
    test('3. Loan scheme: Credit facility/loan ceiling clearly distinguished and never called a cash grant', async () => {
        const mockApp = {
            id: 'app-loan-01',
            applicant_id: testApplicantId,
            scheme_id: 'ffadd6c3-6a0a-4d7b-829e-7cc838099b79', // pm-vidyalaxmi
            status: 'under_review',
            estimated_benefit: 750000,
            decision_notes: null,
            submitted_at: '2026-10-02T10:20:29Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'canonical_snapshot',
            scheme: {
                id,
                scheme_name: 'PM Vidyalaxmi Education Support Scheme',
                category: 'Education & Learning',
                benefit_type: 'Loan',
                max_benefit: 750000,
                benefits: 'Collateral-free education loan support up to ₹7,50,000 for higher education.',
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, 'PM Vidyalaxmi Education Support Scheme');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.strictEqual(hydrated.dbt_scheme, false);
        assert.ok(hydrated.benefit_display.includes('Loan'), `Expected Loan label in benefit_display, got: ${hydrated.benefit_display}`);
        assert.ok(hydrated.benefit_subtitle.includes('Loan') || hydrated.benefit_subtitle.includes('Credit'),
            `Expected Loan/Credit in benefit_subtitle, got: ${hydrated.benefit_subtitle}`);
        assert.strictEqual(hydrated.benefit_numeric, 0); // Loan debt is not personal grant
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 4: INTEREST SUBSIDY
    // ─────────────────────────────────────────────────────────────────────────
    test('4. Interest subsidy: Distinguishes interest subsidy and does not represent ceiling as guaranteed cash', async () => {
        const mockApp = {
            id: 'app-subsidy-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-interest-subsidy-01',
            status: 'under_review',
            estimated_benefit: 150000,
            decision_notes: null,
            submitted_at: '2026-10-03T11:00:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: '6% Interest Subsidy on Loans taken through Banks for Study Abroad',
                category: 'Education & Learning',
                benefit_type: 'Interest Subsidy',
                max_benefit: 150000,
                benefits: 'Interest subsidy of 6% per annum on loans taken through banks for foreign education. Maximum subsidy of ₹1,50,000 for 3 years.',
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, '6% Interest Subsidy on Loans taken through Banks for Study Abroad');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.ok(hydrated.benefit_display.includes('Subsidy') || hydrated.benefit_display.includes('Subvention') || hydrated.benefit_display.includes('Interest'),
            `Expected interest subsidy wording, got: ${hydrated.benefit_display}`);
        assert.ok(hydrated.benefit_subtitle.includes('Subsidy') || hydrated.benefit_subtitle.includes('Subvention') || hydrated.benefit_subtitle.includes('Interest'),
            `Expected interest subtitle, got: ${hydrated.benefit_subtitle}`);
        assert.notStrictEqual(hydrated.benefit_display, '₹1,75,000');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 5: WAIVER SCHEME
    // ─────────────────────────────────────────────────────────────────────────
    test('5. Waiver scheme: 100% Penalty Mafi Yojana preserves waiver semantics without ₹1,75,000 cash grant', async () => {
        const mockApp = {
            id: 'app-waiver-01',
            applicant_id: testApplicantId,
            scheme_id: '32198bb9-6b92-493f-8d45-9ba7f5807148', // 1pmy
            status: 'under_review',
            estimated_benefit: null,
            decision_notes: null,
            submitted_at: '2026-10-03T12:16:08Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'canonical_snapshot',
            scheme: {
                id,
                scheme_name: '100% Penalty Mafi Yojana',
                category: 'Housing & Shelter',
                benefit_type: 'Penalty Waiver',
                max_benefit: null,
                benefits: 'The applicant receives 100% waiver on the penalty amount accumulated on pending installments.',
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, '100% Penalty Mafi Yojana');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.strictEqual(hydrated.benefit_display, '100% Penalty Waiver');
        assert.strictEqual(hydrated.benefit_subtitle, '(Penalty Waiver)');
        assert.strictEqual(hydrated.benefit_numeric, 0);
        assert.notStrictEqual(hydrated.benefit_display, '₹1,75,000');
        assert.notStrictEqual(hydrated.scheme_name, 'Government Scheme Application');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 6: NON-FINANCIAL / IN-KIND SCHEME
    // ─────────────────────────────────────────────────────────────────────────
    test('6. Non-financial scheme: Classified as In-Kind / Non-Financial without fabricated cash amounts', async () => {
        const mockApp = {
            id: 'app-inkind-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-ambulance-01',
            status: 'under_review',
            estimated_benefit: null,
            decision_notes: null,
            submitted_at: '2026-10-01T08:00:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: '108 Emergency Ambulance Service',
                category: 'Health & Wellness',
                benefit_type: 'In Kind',
                max_benefit: null,
                benefits: 'Free state-wide emergency medical transport and first aid facilities.',
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, '108 Emergency Ambulance Service');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.strictEqual(hydrated.benefit_display, 'Non-Financial / In-Kind Assistance');
        assert.strictEqual(hydrated.benefit_subtitle, '(In-Kind / Welfare Service)');
        assert.strictEqual(hydrated.benefit_numeric, 0);
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 7: MISSING SCHEME RELATIONSHIP
    // ─────────────────────────────────────────────────────────────────────────
    test('7. Missing scheme relationship: Displays transparent unavailable state rather than inventing a name', async () => {
        const mockApp = {
            id: 'app-missing-scheme-01',
            applicant_id: testApplicantId,
            scheme_id: '00000000-0000-0000-0000-000000000000',
            status: 'under_review',
            estimated_benefit: 175000,
            decision_notes: 'Government Scheme Application',
            submitted_at: '2026-09-26T23:46:12Z'
        };

        schemeService.getSchemeById = async () => {
            const err = new Error("Scheme not found");
            err.status = 404;
            throw err;
        };

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, null);
        assert.strictEqual(hydrated.scheme, null);
        assert.strictEqual(hydrated.is_scheme_available, false);
        assert.strictEqual(hydrated.benefit_display, 'Not specified');
        assert.strictEqual(hydrated.benefit_subtitle, 'Benefit Information Unavailable');
        assert.strictEqual(hydrated.benefit_numeric, 0);
        assert.notStrictEqual(hydrated.scheme_name, 'Government Scheme Application');
        assert.notStrictEqual(hydrated.benefit_display, '₹1,75,000');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 8: MISSING BENEFIT AMOUNT
    // ─────────────────────────────────────────────────────────────────────────
    test('8. Missing benefit amount: Displays "Not specified" when authoritative scheme data has no amount', async () => {
        const mockApp = {
            id: 'app-no-amt-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-no-amt-01',
            status: 'submitted',
            estimated_benefit: null,
            decision_notes: null,
            submitted_at: '2026-10-04T09:00:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: 'Gujarat Rural Artisans Empowerment Programme',
                category: 'Skills & Employment',
                benefit_type: 'Assistance',
                max_benefit: null,
                benefits: null,
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.scheme_name, 'Gujarat Rural Artisans Empowerment Programme');
        assert.strictEqual(hydrated.benefit_display, 'Not specified');
        assert.strictEqual(hydrated.benefit_numeric, 0);
        assert.notStrictEqual(hydrated.benefit_display, 'Eligible for Subsidy');
        assert.notStrictEqual(hydrated.benefit_display, '₹1,75,000');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 9: PENDING APPLICATION
    // ─────────────────────────────────────────────────────────────────────────
    test('9. Pending application: Persists status under_review / submitted without fabricated progress', async () => {
        const mockApp = {
            id: 'app-pending-01',
            applicant_id: testApplicantId,
            scheme_id: '32198bb9-6b92-493f-8d45-9ba7f5807148',
            status: 'under_review',
            estimated_benefit: null,
            decision_notes: '100% Penalty Mafi Yojana',
            submitted_at: '2026-10-03T12:16:08Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'canonical_snapshot',
            scheme: {
                id,
                scheme_name: '100% Penalty Mafi Yojana',
                benefit_type: 'Penalty Waiver'
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.status, 'under_review');
        assert.strictEqual(hydrated.scheme_name, '100% Penalty Mafi Yojana');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 10: APPROVED APPLICATION
    // ─────────────────────────────────────────────────────────────────────────
    test('10. Approved application: Reflects persisted approved status faithfully', async () => {
        const mockApp = {
            id: 'app-approved-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-approved-01',
            status: 'approved',
            estimated_benefit: 25000,
            decision_notes: 'Post-Matric Scholarship Scheme',
            submitted_at: '2026-09-15T10:00:00Z',
            reviewed_at: '2026-09-22T14:30:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: 'Post-Matric Scholarship Scheme',
                benefit_type: 'Scholarship',
                max_benefit: 25000,
                benefits: 'Annual scholarship assistance of ₹25,000.',
                dbt_scheme: true
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.status, 'approved');
        assert.strictEqual(hydrated.scheme_name, 'Post-Matric Scholarship Scheme');
        assert.ok(hydrated.benefit_display.includes('25,000'));
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 11: REJECTED APPLICATION
    // ─────────────────────────────────────────────────────────────────────────
    test('11. Rejected application: Accurately preserves rejected status without inventing approval or disbursement', async () => {
        const mockApp = {
            id: 'app-rejected-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-rejected-01',
            status: 'rejected',
            estimated_benefit: null,
            decision_notes: 'Mudra Shishu Scheme',
            submitted_at: '2026-09-20T10:00:00Z',
            reviewed_at: '2026-09-25T11:00:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: 'Pradhan Mantri MUDRA Yojana – Shishu',
                benefit_type: 'Loan',
                max_benefit: 50000,
                benefits: 'Collateral-free micro-loan up to ₹50,000.',
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.status, 'rejected');
        assert.strictEqual(hydrated.scheme_name, 'Pradhan Mantri MUDRA Yojana – Shishu');
        assert.ok(hydrated.benefit_display.includes('Loan'));
    });

    // ─────────────────────────────────────────────────────────────────────────
    // CASE 12: ACTION-REQUIRED APPLICATION
    // ─────────────────────────────────────────────────────────────────────────
    test('12. Action-required application: Accurately preserves action_required status and does not falsely mark under_review', async () => {
        const mockApp = {
            id: 'app-action-01',
            applicant_id: testApplicantId,
            scheme_id: 'scheme-action-01',
            status: 'action_required',
            estimated_benefit: null,
            decision_notes: 'PMEGP Subsidy Scheme',
            submitted_at: '2026-10-01T12:00:00Z',
            rule_evaluations: [
                { name: 'Income Certificate', verified: false, reason: 'Blurred upload; re-upload clear certificate' }
            ]
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                scheme_name: "Prime Minister's Employment Generation Programme",
                benefit_type: 'Credit Linked Subsidy',
                max_benefit: 2500000,
                benefits: '15% to 35% margin money subsidy on project loans.',
                dbt_scheme: false
            }
        });

        const hydrated = await applicationService.hydrateApplicationRecord(mockApp);
        assert.strictEqual(hydrated.status, 'action_required');
        assert.strictEqual(hydrated.scheme_name, "Prime Minister's Employment Generation Programme");
        assert.strictEqual(hydrated.rule_evaluations.length, 1);
        assert.strictEqual(hydrated.rule_evaluations[0].verified, false);
    });

    // ─────────────────────────────────────────────────────────────────────────
    // GENERIC FALLBACK FILTERING
    // ─────────────────────────────────────────────────────────────────────────
    test('13. Generic titles "Government Scheme Application" and "Scheme #XXXX" are rejected as scheme names', () => {
        assert.strictEqual(applicationService.isGenericTitle('Government Scheme Application'), true);
        assert.strictEqual(applicationService.isGenericTitle('government scheme application'), true);
        assert.strictEqual(applicationService.isGenericTitle('Government Scheme'), true);
        assert.strictEqual(applicationService.isGenericTitle('Application'), true);
        assert.strictEqual(applicationService.isGenericTitle('Scheme #32198BB9'), true);
        assert.strictEqual(applicationService.isGenericTitle('100% Penalty Mafi Yojana'), false);
        assert.strictEqual(applicationService.isGenericTitle('PM Vidyalaxmi Education Support Scheme'), false);
    });
});
