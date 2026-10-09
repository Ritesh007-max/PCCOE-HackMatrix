const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const intelligenceClient = require('../src/services/intelligenceClient');
const { checkEligibility } = require('../src/services/eligibilityService');

describe('Phase D3.8: Eligibility State Messaging Integrity Backend Suite', () => {

    it('1. 1PMY unregistered scheme returns MANUAL_REVIEW with UNREGISTERED_SCHEME category and zero sentinels', async () => {
        const origPost = intelligenceClient.postJson;
        // Mock Intelligence returning Scenario 17 engine response for 1pmy
        intelligenceClient.postJson = () => Promise.resolve({
            request_id: 'req_1pmy_test',
            evaluated_schemes_count: 1,
            evaluations: [{
                scheme_id: '1pmy',
                scheme_name: '100% Penalty Mafi Yojana',
                status: 'UNKNOWN',
                is_eligible: false,
                rule_version: 'UNREGISTERED',
                rules_evaluated: [],
                matched_rules: [],
                failed_rules: [],
                missing_fields: ['scheme_1pmy_not_registered'],
                review_reasons: ["Scheme '1pmy' is not registered in the statutory rule engine."]
            }]
        });

        try {
            const result = await checkEligibility('usr-d38-1', '1pmy', { full_name: 'Applicant 1' });
            assert.ok(result);
            assert.strictEqual(result.isRegistered, false, '1pmy must be flagged isRegistered: false');
            assert.strictEqual(result.evaluationCategory, 'UNREGISTERED_SCHEME');
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.deepStrictEqual(result.missingFields, [], 'missingFields must NOT contain scheme_1pmy_not_registered');
            assert.deepStrictEqual(result.missingFieldLabels, []);
            assert.ok(!JSON.stringify(result).includes('scheme_1pmy_not_registered'), 'Zero internal registration sentinels may leak');
            assert.ok(result.verdictReason.includes('not registered') && result.verdictReason.includes('Manual'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('2. YIPB unregistered scheme returns MANUAL_REVIEW with UNREGISTERED_SCHEME category and zero sentinels', async () => {
        const origPost = intelligenceClient.postJson;
        // Mock Intelligence returning engine response for yipb
        intelligenceClient.postJson = () => Promise.resolve({
            request_id: 'req_yipb_test',
            evaluated_schemes_count: 1,
            evaluations: [{
                scheme_id: 'yipb',
                scheme_name: 'Yuva Internship Program',
                status: 'UNKNOWN',
                is_eligible: false,
                rule_version: 'UNREGISTERED',
                rules_evaluated: [],
                matched_rules: [],
                failed_rules: [],
                missing_fields: ['scheme_yipb_not_registered'],
                review_reasons: ["Scheme 'yipb' is not registered in the statutory rule engine."]
            }]
        });

        try {
            const result = await checkEligibility('usr-d38-2', 'yipb', { full_name: 'Applicant 2' });
            assert.ok(result);
            assert.strictEqual(result.isRegistered, false);
            assert.strictEqual(result.evaluationCategory, 'UNREGISTERED_SCHEME');
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.deepStrictEqual(result.missingFields, []);
            assert.deepStrictEqual(result.missingFieldLabels, []);
            assert.ok(!JSON.stringify(result).includes('scheme_yipb_not_registered'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('3. Registered scheme (PM-KISAN) with complete qualifying profile returns ELIGIBLE', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('AI Offline'));
        try {
            const profile = { occupation: 'farmer', annual_income: 180000 };
            const result = await checkEligibility('usr-d38-3', 'pm-kisan', profile);
            assert.ok(result);
            assert.strictEqual(result.isRegistered, true);
            assert.strictEqual(result.evaluationCategory, 'ELIGIBLE');
            assert.strictEqual(result.verdict, 'ELIGIBLE');
            assert.strictEqual(result.status, 'PASS');
            assert.strictEqual(result.isEligible, true);
            assert.strictEqual(result.rules.length, 2);
            assert.deepStrictEqual(result.missingFields, []);
            assert.deepStrictEqual(result.missingFieldLabels, []);
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('4. Registered scheme with missing profile facts returns MISSING_APPLICANT_FACTS and clean field labels', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('AI Offline'));
        try {
            // PMEGP requires date_of_birth; when missing, cannot verify age
            const profile = { occupation: 'Artisan' };
            const result = await checkEligibility('usr-d38-4', 'pmegp', profile);
            assert.ok(result);
            assert.strictEqual(result.isRegistered, true);
            assert.strictEqual(result.evaluationCategory, 'MISSING_APPLICANT_FACTS');
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.strictEqual(result.isEligible, false);
            assert.deepStrictEqual(result.missingFields, ['date_of_birth']);
            assert.deepStrictEqual(result.missingFieldLabels, ['Date of Birth']);
            assert.ok(!JSON.stringify(result).includes('scheme_pmegp_not_registered'));
            assert.ok(!JSON.stringify(result).includes('rule_evaluation_error'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('5. Intelligence outage for unregistered scheme falls back cleanly with UNREGISTERED_SCHEME', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Intelligence Gateway Offline'));
        try {
            const result = await checkEligibility('usr-d38-5', '1pmy', { state: 'Gujarat' });
            assert.ok(result);
            assert.strictEqual(result.source, 'local_fallback');
            assert.strictEqual(result.degraded, true);
            assert.strictEqual(result.intelligenceUnavailable, true);
            assert.strictEqual(result.isRegistered, false);
            assert.strictEqual(result.evaluationCategory, 'UNREGISTERED_SCHEME');
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.deepStrictEqual(result.missingFields, []);
            assert.deepStrictEqual(result.missingFieldLabels, []);
            assert.ok(!JSON.stringify(result).includes('scheme_1pmy_not_registered'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('6. Policy snapshot unavailable error is categorized as SNAPSHOT_UNAVAILABLE with zero sentinels', async () => {
        const origPost = intelligenceClient.postJson;
        intelligenceClient.postJson = () => Promise.reject(new Error('Policy snapshot unavailable or corrupted'));
        try {
            const result = await checkEligibility('usr-d38-6', 'nonexistent-policy-scheme', { full_name: 'Test' });
            assert.ok(result);
            assert.strictEqual(result.evaluationCategory, 'SNAPSHOT_UNAVAILABLE');
            assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
            assert.strictEqual(result.status, 'UNKNOWN');
            assert.deepStrictEqual(result.missingFields, []);
            assert.deepStrictEqual(result.missingFieldLabels, []);
            assert.ok(result.verdictReason.includes('snapshot'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });

    it('7. Intelligence response containing mixed sentinels is sanitized to retain only genuine missing facts', async () => {
        const origPost = intelligenceClient.postJson;
        // Mock Intelligence returning a sentinel alongside genuine missing applicant facts
        intelligenceClient.postJson = () => Promise.resolve({
            request_id: 'req_mixed_test',
            evaluated_schemes_count: 1,
            evaluations: [{
                scheme_id: 'custom_registered_scheme',
                scheme_name: 'Custom Scheme',
                status: 'UNKNOWN',
                is_eligible: false,
                rule_version: '1.0.0',
                rules_evaluated: [
                    { rule_id: 'R1', field: 'annual_income', status: 'UNKNOWN', reason: 'Income missing' }
                ],
                matched_rules: [],
                failed_rules: [],
                missing_fields: ['scheme_custom_not_registered', 'annual_income', 'rule_evaluation_error'],
                review_reasons: ['Income information required']
            }]
        });

        try {
            const result = await checkEligibility('usr-d38-7', 'custom_registered_scheme', {});
            assert.ok(result);
            assert.strictEqual(result.isRegistered, true);
            assert.strictEqual(result.evaluationCategory, 'MISSING_APPLICANT_FACTS');
            assert.deepStrictEqual(result.missingFields, ['annual_income'], 'Sentinels must be stripped, genuine field retained');
            assert.deepStrictEqual(result.missingFieldLabels, ['Annual Family Income']);
            assert.ok(!JSON.stringify(result.missingFields).includes('scheme_custom_not_registered'));
            assert.ok(!JSON.stringify(result.missingFields).includes('rule_evaluation_error'));
        } finally {
            intelligenceClient.postJson = origPost;
        }
    });
});
