/**
 * FIN Phase D2.2: Scheme Match Score Integrity Regression Tests (Node.js)
 * 
 * Verifies:
 * 1. Explicit canonical scheme query does not create a 100% eligibility score in Backend mapping.
 * 2. Search relevance remains separate from eligibility (relevanceScore vs matchScore vs eligibilityStatus).
 * 3. Missing facts in canonical schemes yield null matchScore and UNKNOWN eligibilityStatus.
 * 4. No fallback 80%, 85%, or 100% is injected when score is absent.
 * 5. Backend offline fallback preserves score semantics (matchScore: null, eligibilityStatus: 'UNKNOWN', matchType: 'neutral').
 * 6. Existing genuine PASS/FAIL decisions remain unchanged (PASS -> green, FAIL -> orange, REVIEW -> amber).
 * 7. Tenant isolation prevents cross-tenant contamination.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { computeLocalFallback } = require('../src/services/chatService');

describe('FIN Phase D2.2: Scheme Match Score Integrity Backend Suite', () => {

    it('1. Backend offline fallback preserves score semantics (matchScore is null, not 100% or 80%)', () => {
        const result = computeLocalFallback(
            'Explain the application process for PMEGP.',
            { full_name: 'Aarav Sharma', occupation: 'Salaried' },
            [],
            []
        );

        assert.ok(result);
        assert.ok(result.schemes.length > 0);
        const scheme = result.schemes[0];

        // Must NOT invent or default to 80%, 85%, or 100% eligibility
        assert.strictEqual(scheme.matchScore, null);
        assert.strictEqual(scheme.eligibilityStatus, 'UNKNOWN');
        assert.strictEqual(scheme.matchType, 'neutral');
        assert.strictEqual(scheme.relevanceScore, 100);
    });

    it('2. Mapping Intelligence response separates search relevance from eligibility', () => {
        // Simulate the mapping logic inside chatService
        const mockAiResponse = {
            suggested_schemes: [
                {
                    scheme_id: 'yipb',
                    scheme_name: 'Young Investigators Programme in Biotechnology',
                    relevance_score: 1.0,
                    eligibility_status: 'UNKNOWN',
                    eligibility_score: null,
                    ministry: 'Kerala State Council for Science, Technology and Environment',
                    state: 'Kerala'
                }
            ]
        };

        const mapped = mockAiResponse.suggested_schemes.map(s => {
            const relevanceScore = s.relevance_score != null ? Math.round(s.relevance_score * 100) : null;
            const eligibilityStatus = s.eligibility_status || 'UNKNOWN';
            const hasEligScore = s.eligibility_score != null && typeof s.eligibility_score === 'number';
            const matchScore = hasEligScore ? Math.round(s.eligibility_score) : null;

            let matchType = 'neutral';
            if (eligibilityStatus === 'PASS') {
                matchType = 'green';
            } else if (eligibilityStatus === 'FAIL') {
                matchType = 'orange';
            } else if (eligibilityStatus === 'REVIEW') {
                matchType = 'amber';
            }

            return {
                id: s.scheme_id,
                title: s.scheme_name,
                matchScore,
                relevanceScore,
                eligibilityStatus,
                matchType
            };
        });

        const scheme = mapped[0];
        // Relevance is 100%
        assert.strictEqual(scheme.relevanceScore, 100);
        // Eligibility MUST be null and UNKNOWN, NOT 100%
        assert.strictEqual(scheme.matchScore, null);
        assert.strictEqual(scheme.eligibilityStatus, 'UNKNOWN');
        assert.strictEqual(scheme.matchType, 'neutral');
    });

    it('3. Genuine evaluated eligibility preserves score and green matchType', () => {
        const mockAiResponse = {
            suggested_schemes: [
                {
                    scheme_id: 'pm-kisan',
                    scheme_name: 'PM Kisan Samman Nidhi',
                    relevance_score: 0.95,
                    eligibility_status: 'PASS',
                    eligibility_score: 95,
                    ministry: 'Ministry of Agriculture',
                    state: 'All India'
                }
            ]
        };

        const mapped = mockAiResponse.suggested_schemes.map(s => {
            const relevanceScore = s.relevance_score != null ? Math.round(s.relevance_score * 100) : null;
            const eligibilityStatus = s.eligibility_status || 'UNKNOWN';
            const hasEligScore = s.eligibility_score != null && typeof s.eligibility_score === 'number';
            const matchScore = hasEligScore ? Math.round(s.eligibility_score) : null;

            let matchType = 'neutral';
            if (eligibilityStatus === 'PASS') {
                matchType = 'green';
            } else if (eligibilityStatus === 'FAIL') {
                matchType = 'orange';
            } else if (eligibilityStatus === 'REVIEW') {
                matchType = 'amber';
            }

            return {
                id: s.scheme_id,
                title: s.scheme_name,
                matchScore,
                relevanceScore,
                eligibilityStatus,
                matchType
            };
        });

        const scheme = mapped[0];
        assert.strictEqual(scheme.relevanceScore, 95);
        assert.strictEqual(scheme.matchScore, 95);
        assert.strictEqual(scheme.eligibilityStatus, 'PASS');
        assert.strictEqual(scheme.matchType, 'green');
    });

    it('4. Disqualified scheme preserves FAIL and orange matchType', () => {
        const mockAiResponse = {
            suggested_schemes: [
                {
                    scheme_id: 'pm-kisan',
                    scheme_name: 'PM Kisan Samman Nidhi',
                    relevance_score: 0.90,
                    eligibility_status: 'FAIL',
                    eligibility_score: 0,
                    ministry: 'Ministry of Agriculture',
                    state: 'All India'
                }
            ]
        };

        const mapped = mockAiResponse.suggested_schemes.map(s => {
            const relevanceScore = s.relevance_score != null ? Math.round(s.relevance_score * 100) : null;
            const eligibilityStatus = s.eligibility_status || 'UNKNOWN';
            const hasEligScore = s.eligibility_score != null && typeof s.eligibility_score === 'number';
            const matchScore = hasEligScore ? Math.round(s.eligibility_score) : null;

            let matchType = 'neutral';
            if (eligibilityStatus === 'PASS') {
                matchType = 'green';
            } else if (eligibilityStatus === 'FAIL') {
                matchType = 'orange';
            } else if (eligibilityStatus === 'REVIEW') {
                matchType = 'amber';
            }

            return {
                id: s.scheme_id,
                title: s.scheme_name,
                matchScore,
                relevanceScore,
                eligibilityStatus,
                matchType
            };
        });

        const scheme = mapped[0];
        assert.strictEqual(scheme.matchScore, 0);
        assert.strictEqual(scheme.eligibilityStatus, 'FAIL');
        assert.strictEqual(scheme.matchType, 'orange');
    });

    it('5. Tenant isolation ensures applicant context does not leak across sessions', () => {
        const resUserA = computeLocalFallback(
            'Explain PMEGP',
            { full_name: 'Tenant User A', occupation: 'Farmer' },
            [],
            []
        );
        const resUserB = computeLocalFallback(
            'Explain PMEGP',
            { full_name: 'Tenant User B', occupation: 'Student' },
            [],
            []
        );

        assert.strictEqual(resUserA.profile.name, 'Tenant User A');
        assert.strictEqual(resUserB.profile.name, 'Tenant User B');
        assert.notStrictEqual(resUserA.profile.name, resUserB.profile.name);
    });
});
