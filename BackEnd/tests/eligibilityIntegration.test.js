const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const eligibilityService = require('../src/services/eligibilityService');
const { HEADER_NAME, AI_SERVICE_API_KEY } = require('../src/config/intelligenceConfig');

describe('Eligibility Backend ↔ Intelligence Integration Tests', () => {
    let mockServer;
    let mockServerPort;
    let receivedPayload = null;
    let receivedHeaders = null;
    let currentMockStatus = 'PASS';
    let returnError = false;

    before((_, done) => {
        mockServer = http.createServer((req, res) => {
            receivedHeaders = req.headers;
            let body = '';
            req.on('data', chunk => { body += chunk; });
            req.on('end', () => {
                if (returnError) {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: 'Eligibility engine offline' }));
                    return;
                }

                if (req.url === '/v1/eligibility/check' && req.method === 'POST') {
                    receivedPayload = JSON.parse(body);
                    const isEligible = currentMockStatus === 'PASS';

                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        request_id: 'el_test_123',
                        evaluated_schemes_count: 1,
                        evaluations: [
                            {
                                scheme_id: receivedPayload.scheme_ids[0],
                                scheme_name: 'PMEGP Test Scheme',
                                status: currentMockStatus,
                                is_eligible: isEligible,
                                rules_evaluated: [
                                    {
                                        rule_id: 'AGE_GATE',
                                        field: 'date_of_birth',
                                        operator: '>=',
                                        status: currentMockStatus,
                                        applicant_value: '2000-01-01',
                                        expected_value: '18',
                                        hard_constraint: true,
                                        reason: currentMockStatus === 'PASS' ? 'Age >= 18 satisfied' : 'Age condition not satisfied'
                                    }
                                ],
                                matched_rules: isEligible ? ['AGE_GATE'] : [],
                                failed_rules: currentMockStatus === 'FAIL' ? ['AGE_GATE'] : [],
                                missing_fields: currentMockStatus === 'UNKNOWN' ? ['annual_income'] : [],
                                conflicted_fields: currentMockStatus === 'REVIEW' ? ['occupation'] : []
                            }
                        ]
                    }));
                } else {
                    res.writeHead(404);
                    res.end();
                }
            });
        });

        mockServer.listen(0, '127.0.0.1', () => {
            mockServerPort = mockServer.address().port;
            done();
        });
    });

    after((_, done) => {
        mockServer.close(done);
    });

    test('Maps applicant facts and preserves deterministic PASS status', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        currentMockStatus = 'PASS';

        const profileOverride = {
            occupation: 'Business',
            annual_income: 250000,
            state: 'Gujarat',
            date_of_birth: '2000-01-01'
        };

        const result = await eligibilityService.checkEligibility('user_test', 'pmegp', profileOverride);

        // Verify headers
        assert.strictEqual(receivedHeaders[HEADER_NAME.toLowerCase()], AI_SERVICE_API_KEY);

        // Verify facts forwarded without fabrication
        assert.strictEqual(receivedPayload.applicant_facts.occupation, 'Business');
        assert.strictEqual(receivedPayload.applicant_facts.annual_income, 250000);
        assert.deepStrictEqual(receivedPayload.scheme_ids, ['pmegp']);

        // Verify deterministic PASS status preserved
        assert.strictEqual(result.status, 'PASS');
        assert.strictEqual(result.isEligible, true);
        assert.strictEqual(result.verdict, 'ELIGIBLE');
        assert.strictEqual(result.rules.length, 1);
    });

    test('Preserves deterministic FAIL status and maps to NOT_ELIGIBLE', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        currentMockStatus = 'FAIL';

        const result = await eligibilityService.checkEligibility('user_test', 'pmegp', { occupation: 'student' });

        assert.strictEqual(result.status, 'FAIL');
        assert.strictEqual(result.isEligible, false);
        assert.strictEqual(result.verdict, 'NOT_ELIGIBLE');
        assert.strictEqual(result.failedRules.length, 1);
    });

    test('Preserves deterministic UNKNOWN status and NEVER transforms to PASS', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        currentMockStatus = 'UNKNOWN';

        const result = await eligibilityService.checkEligibility('user_test', 'pmegp', {});

        assert.strictEqual(result.status, 'UNKNOWN');
        assert.strictEqual(result.isEligible, false);
        assert.notStrictEqual(result.verdict, 'ELIGIBLE', 'Invariant violation: UNKNOWN must not become ELIGIBLE');
        assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        assert.ok(result.missingFields.includes('annual_income'));
    });

    test('Preserves deterministic REVIEW status and NEVER transforms to PASS', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        currentMockStatus = 'REVIEW';

        const result = await eligibilityService.checkEligibility('user_test', 'pmegp', {});

        assert.strictEqual(result.status, 'REVIEW');
        assert.strictEqual(result.isEligible, false);
        assert.notStrictEqual(result.verdict, 'ELIGIBLE', 'Invariant violation: REVIEW must not become ELIGIBLE');
        assert.strictEqual(result.verdict, 'MANUAL_REVIEW');
        assert.ok(result.conflictedFields.includes('occupation'));
    });

    test('Falls back to local rules engine when Intelligence service is offline', async () => {
        returnError = true;

        const result = await eligibilityService.checkEligibility('user_test', 'pmegp', {
            date_of_birth: '2000-01-01',
            occupation: 'Business'
        });

        assert.ok(result);
        assert.ok(result.verdict);
        assert.ok(result.rules);

        returnError = false;
    });
});
