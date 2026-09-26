const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const applicationService = require('../src/services/applicationService');
const { HEADER_NAME, AI_SERVICE_API_KEY } = require('../src/config/intelligenceConfig');

describe('Application Analysis Backend ↔ Intelligence Integration Tests', () => {
    let mockServer;
    let mockServerPort;
    let receivedContentType = null;
    let receivedHeaders = null;
    let returnError = false;

    before((_, done) => {
        mockServer = http.createServer((req, res) => {
            receivedHeaders = req.headers;
            receivedContentType = req.headers['content-type'];
            let body = [];
            req.on('data', chunk => { body.push(chunk); });
            req.on('end', () => {
                if (returnError) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: '21-step pipeline error' }));
                    return;
                }

                if (req.url === '/v1/applications/analyze' && req.method === 'POST') {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        request_id: 'app_test_req_001',
                        application_id: 'app_001',
                        steps_completed: 21,
                        processing_status: 'ANALYSIS_COMPLETE',
                        documents_processed: [{ file_name: 'test.pdf', status: 'VALID' }],
                        applicant_profile: { full_name: 'Test Applicant', annual_income: 250000 },
                        conflicts_detected: [],
                        query_intent: { intent: 'apply' },
                        retrieved_schemes: [],
                        eligibility_decision: {
                            verdict: 'ELIGIBLE',
                            is_eligible: true,
                            rules_evaluated: []
                        },
                        benefit_calculation: { benefit_amount: 50000 },
                        missing_information: { missing_documents: [] },
                        explanation: { summary: 'Applicant meets all guidelines.' },
                        security_audit: { passed: true },
                        telemetry: { execution_time_ms: 120 }
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

    test('Validates user ID and scheme ID before processing', async () => {
        await assert.rejects(
            async () => {
                await applicationService.analyzeApplication(null, 'pmegp');
            },
            { status: 400 }
        );

        await assert.rejects(
            async () => {
                await applicationService.analyzeApplication('user_1', null);
            },
            { status: 400 }
        );
    });

    test('Falls back cleanly to readiness scoring when user has no uploaded documents', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;

        // Generate a random user ID with no uploaded documents
        const randomUserId = '00000000-0000-0000-0000-000000000099';
        const result = await applicationService.analyzeApplication(randomUserId, 'pmegp', {
            full_name: 'Fallback User',
            annual_income: 300000,
            occupation: 'Business'
        });

        assert.ok(result);
        assert.strictEqual(result.source, 'local_readiness');
        assert.strictEqual(result.schemeId, 'pmegp');
        assert.ok(typeof result.readinessScore === 'number');
        assert.ok(result.documents);
        assert.ok(result.profile);
        assert.ok(result.nextActions);
    });
});
