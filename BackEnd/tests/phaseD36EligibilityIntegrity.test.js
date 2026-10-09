/**
 * Phase D3.6: Critical Eligibility Integrity Remediation Regression Suite
 * 
 * Verifies:
 * 1. Registered scheme with verified passing criteria produces PASS / ELIGIBLE.
 * 2. Registered scheme with a failing criterion produces FAIL / NOT_ELIGIBLE.
 * 3. Unregistered scheme with a complete profile produces UNKNOWN / MANUAL_REVIEW (never PASS).
 * 4. Unregistered scheme with an incomplete profile produces UNKNOWN / MANUAL_REVIEW (never PASS).
 * 5. Intelligence offline for 1PMY produces UNKNOWN / MANUAL_REVIEW (fail-closed).
 * 6. Intelligence offline for PM-KISAN evaluates registered criteria deterministically without fabrication.
 * 7. Intelligence offline for 6islbsa produces UNKNOWN / MANUAL_REVIEW with 0 rules (fail-closed).
 * 8. Intelligence timeout gracefully falls back to fail-closed UNKNOWN / MANUAL_REVIEW.
 * 9. Invalid or unavailable policy snapshot produces fail-closed UNKNOWN / MANUAL_REVIEW without crashing.
 * 10. Missing applicant facts on registered scheme produce UNKNOWN / MANUAL_REVIEW (never assumed PASS).
 * 11. CRITICAL INVARIANT: No unregistered scheme may become ELIGIBLE/PASS due to generic fallback or outage.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const intelligenceClient = require('../src/services/intelligenceClient');
const { checkEligibility } = require('../src/services/eligibilityService');

describe('Phase D3.6: Critical Eligibility Integrity Remediation Suite', () => {

    it('1. Registered scheme with verified passing criteria produces PASS / ELIGIBLE', async () => {
        // PM-KISAN offline local evaluation with passing farmer criteria
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('AI Offline'));
        try {
            const profile = {
                occupation: 'farmer',
                annual_income: 200000,
                full_name: 'Verified Farmer'
            };
            const result = await checkEligibility('usr-1', 'pm-kisan', profile);
            assert.ok(result);
            assert.strictEqual(result.status, 'PASS');
            assert.strictEqual(result.isEligible, true);
            assert.strictEqual(result.verdict, 'ELIGIBLE');
            assert.strictEqual(result.rules.length, 2);
            assert.ok(result.rules.every(r => r.status === 'pass'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('2. Registered scheme with a failing criterion produces FAIL / NOT_ELIGIBLE', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('AI Offline'));
        try {
            // Non-farmer occupation fails PM-KISAN
            const profile = {
                occupation: 'Software Engineer',
                annual_income: 200000
            };
            const result = await checkEligibility('usr-2', 'pm-kisan', profile);
            assert.ok(result);
            assert.strictEqual(result.status, 'FAIL');
            assert.strictEqual(result.isEligible, false);
            assert.strictEqual(result.verdict, 'NOT_ELIGIBLE');
            assert.ok(result.failedRules.includes('FARMER_OCCUPATION'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('3. Unregistered scheme with a complete profile produces UNKNOWN / MANUAL_REVIEW (never PASS)', async () => {
        const completeProfile = {
            full_name: 'Ramesh Patel',
            state: 'Gujarat',
            annual_income: 180000,
            occupation: 'farmer',
            date_of_birth: '1985-06-15',
            gender: 'male',
            caste_category: 'General'
        };

        // Even with a 100% complete profile, unregistered 1PMY MUST NOT pass
        const result = await checkEligibility('usr-3', '1pmy', completeProfile);
        assert.ok(result);
        assert.notStrictEqual(result.status, 'PASS', 'Unregistered scheme must NEVER evaluate to PASS');
        assert.notStrictEqual(result.verdict, 'ELIGIBLE', 'Unregistered scheme must NEVER evaluate to ELIGIBLE');
        assert.strictEqual(result.isEligible, false);
        assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        assert.strictEqual(result.status, 'UNKNOWN');
    });

    it('4. Unregistered scheme with an incomplete profile produces UNKNOWN / MANUAL_REVIEW', async () => {
        const emptyProfile = {};
        const result = await checkEligibility('usr-4', '1pmy', emptyProfile);
        assert.ok(result);
        assert.strictEqual(result.status, 'UNKNOWN');
        assert.strictEqual(result.isEligible, false);
        assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        assert.ok(result.verdictReason.includes('not registered') || result.verdictReason.includes('Manual'));
    });

    it('5. Intelligence offline for 1PMY produces UNKNOWN / MANUAL_REVIEW (fail-closed)', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Intelligence Gateway Offline'));
        try {
            const profile = {
                state: 'Gujarat',
                annual_income: 150000,
                occupation: 'artisan'
            };
            const result = await checkEligibility('usr-5', '1pmy', profile);
            assert.ok(result);
            assert.strictEqual(result.source, 'local_fallback');
            assert.strictEqual(result.degraded, true);
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.rules.length, 0);
            assert.ok(result.verdictReason.includes('not registered'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('6. Intelligence offline for PM-KISAN evaluates registered criteria deterministically', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Intelligence Gateway Offline'));
        try {
            // Case A: Valid farmer and income <= 3L
            const passProfile = { occupation: 'farmer', annual_income: 120000 };
            const passRes = await checkEligibility('usr-6a', 'pm-kisan', passProfile);
            assert.strictEqual(passRes.status, 'PASS');
            assert.strictEqual(passRes.verdict, 'ELIGIBLE');

            // Case B: Income > 3L fails
            const failProfile = { occupation: 'farmer', annual_income: 450000 };
            const failRes = await checkEligibility('usr-6b', 'pm-kisan', failProfile);
            assert.strictEqual(failRes.status, 'FAIL');
            assert.strictEqual(failRes.verdict, 'NOT_ELIGIBLE');

            // Case C: Missing income returns UNKNOWN / MANUAL_REVIEW
            const missingProfile = { occupation: 'farmer' };
            const missingRes = await checkEligibility('usr-6c', 'pm-kisan', missingProfile);
            assert.strictEqual(missingRes.status, 'UNKNOWN');
            assert.strictEqual(missingRes.verdict, 'MANUAL_REVIEW');
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('7. Intelligence offline for 6islbsa produces UNKNOWN / MANUAL_REVIEW with 0 rules', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Intelligence Connection Refused'));
        try {
            const profile = { state: 'Gujarat', annual_income: 250000 };
            const result = await checkEligibility('usr-7', '6islbsa', profile);
            assert.ok(result);
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.rules.length, 0);
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('8. Intelligence timeout gracefully falls back to fail-closed UNKNOWN / MANUAL_REVIEW', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => {
            const err = new Error('Gateway Timeout');
            err.code = 'ETIMEDOUT';
            return Promise.reject(err);
        };
        try {
            const result = await checkEligibility('usr-8', '1pmy', { state: 'Gujarat' });
            assert.ok(result);
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('9. Invalid or unavailable policy snapshot produces fail-closed UNKNOWN / MANUAL_REVIEW', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Snapshot Corrupted'));
        try {
            // Evaluating a nonexistent scheme ID
            const result = await checkEligibility('usr-9', 'nonexistent-corrupt-scheme-999', { full_name: 'Test' });
            assert.ok(result);
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.rules.length, 0);
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('10. Missing applicant facts on registered scheme produce UNKNOWN / MANUAL_REVIEW', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('AI Offline'));
        try {
            // PMEGP requires date_of_birth; when missing, cannot verify age
            const profileWithoutDob = { occupation: 'Business' };
            const result = await checkEligibility('usr-10', 'pmegp', profileWithoutDob);
            assert.ok(result);
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.ok(result.verdictReason.includes('Date of birth not provided') || result.verdictReason.includes('Manual'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('11. CRITICAL INVARIANT: No unregistered scheme may become ELIGIBLE/PASS because of generic fallback', async () => {
        const arbitraryUnregisteredSchemes = [
            '1pmy',
            '6islbsa',
            '108easuk',
            '25-ciss',
            'scheme-random-welfare-123',
            'gujarat-housing-waiver'
        ];

        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Complete AI Outage'));

        try {
            const superCompleteProfile = {
                full_name: 'Eligible Citizen',
                occupation: 'farmer',
                annual_income: 100000,
                income: 100000,
                state: 'Gujarat',
                date_of_birth: '1990-01-01',
                dob: '1990-01-01',
                gender: 'female',
                caste_category: 'SC',
                category: 'SC',
                is_woman_entrepreneur: true,
                marital_status: 'married',
                education_level: 'Graduate',
                land_ownership_acres: 2
            };

            for (const sId of arbitraryUnregisteredSchemes) {
                const res = await checkEligibility('usr-invariant', sId, superCompleteProfile);
                assert.notStrictEqual(res.status, 'PASS', `Scheme ${sId} MUST NEVER have status PASS in fallback`);
                assert.notStrictEqual(res.verdict, 'ELIGIBLE', `Scheme ${sId} MUST NEVER have verdict ELIGIBLE in fallback`);
                assert.strictEqual(res.isEligible, false, `Scheme ${sId} isEligible MUST be false in fallback`);
                assert.strictEqual(res.verdict, 'MANUAL_REVIEW');
                assert.strictEqual(res.status, 'UNKNOWN');
                assert.strictEqual(res.rules.length, 0);
            }
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });
});
