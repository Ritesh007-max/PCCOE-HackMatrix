const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('http');

const intelligenceClient = require('../src/services/intelligenceClient');
const chatService = require('../src/services/chatService');
const eligibilityService = require('../src/services/eligibilityService');
const schemeService = require('../src/services/schemeService');
const applicationService = require('../src/services/applicationService');
const documentServices = require('../src/services/documentServices');

describe('Step 10: Backend Failure Modes & Security Boundary Verification', () => {
    let mockServer;
    let mockServerPort;
    let mockStatusCode = 200;
    let mockResponseBody = '{}';
    let delayMs = 0;

    before((_, done) => {
        mockServer = http.createServer((req, res) => {
            setTimeout(() => {
                res.writeHead(mockStatusCode, { 'Content-Type': 'application/json' });
                res.end(mockResponseBody);
            }, delayMs);
        });

        mockServer.listen(0, '127.0.0.1', () => {
            mockServerPort = mockServer.address().port;
            done();
        });
    });

    after((_, done) => {
        mockServer.close(done);
    });

    test('Failure Mode 2: Intelligence unavailable (connection refused) is handled safely', async () => {
        // Point to an unopened dead port
        process.env.AI_SERVER_URL = 'http://127.0.0.1:59999';

        await assert.rejects(
            async () => {
                await intelligenceClient.postJson('/v1/chat', { query: 'test' });
            },
            (err) => {
                assert.strictEqual(err.status, 503);
                assert.ok(!err.message.includes('AI_SERVICE_API_KEY'));
                assert.ok(!err.message.includes('Traceback'));
                return true;
            }
        );
    });

    test('Failure Mode 3: Wrong service key (401 Unauthorized) sanitizes without leaking secrets', async () => {
        const testSecret = 'secret_testing_token_999';
        process.env.AI_SERVICE_API_KEY = testSecret;
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        mockStatusCode = 401;
        mockResponseBody = JSON.stringify({ detail: `Invalid or missing API key: ${testSecret}` });
        delayMs = 0;

        await assert.rejects(
            async () => {
                await intelligenceClient.postJson('/v1/chat', { query: 'test' });
            },
            (err) => {
                assert.strictEqual(err.status, 401);
                assert.ok(!err.message.includes(testSecret), 'Must sanitize secret tokens');
                assert.ok(err.message.includes('[REDACTED_KEY]'));
                return true;
            }
        );
    });

    test('Failure Mode 4: Timeout aborts cleanly and returns 504 without server crash', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        mockStatusCode = 200;
        mockResponseBody = JSON.stringify({ answer: 'delayed' });
        delayMs = 200; // Delay longer than custom timeout

        await assert.rejects(
            async () => {
                await intelligenceClient.postJson('/v1/chat', { query: 'test' }, { timeoutMs: 50 });
            },
            (err) => {
                assert.strictEqual(err.status, 504);
                assert.ok(err.message.includes('timed out'));
                return true;
            }
        );
    });

    test('Failure Mode 5: Malformed Intelligence response is caught and handled safely', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
        mockStatusCode = 200;
        mockResponseBody = '<<< Not Valid JSON XML >>>';
        delayMs = 0;

        await assert.rejects(
            async () => {
                await intelligenceClient.postJson('/v1/chat', { query: 'test' });
            },
            (err) => {
                assert.strictEqual(err.status, 503);
                assert.ok(err.message.includes('communication error') || err.message.includes('JSON'));
                return true;
            }
        );
    });

    test('Failure Mode 6: Unauthorized user input is rejected with 400', async () => {
        await assert.rejects(
            async () => {
                await documentServices.extractDocument({ documentId: 'doc_1', userId: null });
            },
            { status: 400 }
        );

        await assert.rejects(
            async () => {
                await applicationService.analyzeApplication(null, 'pmegp');
            },
            { status: 400 }
        );
    });

    test('Failure Mode 7: Unauthorized / non-existent document access is rejected with 404', async () => {
        const fakeUserId = '00000000-0000-0000-0000-000000000099';
        const fakeDocId = '00000000-0000-0000-0000-000000000088';

        await assert.rejects(
            async () => {
                await documentServices.extractDocument({ documentId: fakeDocId, userId: fakeUserId });
            },
            { status: 404 }
        );
    });

    test('Failure Mode 8: Unauthorized / non-existent application access is rejected safely', async () => {
        const fakeUserId = '00000000-0000-0000-0000-000000000099';
        const nonExistentScheme = 'invalid-scheme-xyz-123';

        await assert.rejects(
            async () => {
                await applicationService.analyzeApplication(fakeUserId, nonExistentScheme);
            },
            (err) => {
                assert.ok(err.status === 404 || err.message.includes('not found'));
                return true;
            }
        );
    });
});
