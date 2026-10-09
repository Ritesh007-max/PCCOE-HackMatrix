const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const chatService = require('../src/services/chatService');
const { HEADER_NAME, AI_SERVICE_API_KEY } = require('../src/config/intelligenceConfig');

describe('Chat Backend ↔ Intelligence Integration Tests', () => {
    let mockServer;
    let mockServerPort;
    let receivedPayload = null;
    let receivedHeaders = null;
    let returnError = false;

    before((_, done) => {
        mockServer = http.createServer((req, res) => {
            receivedHeaders = req.headers;
            let body = '';
            req.on('data', chunk => { body += chunk; });
            req.on('end', () => {
                if (returnError) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: { message: 'Internal AI failure' } }));
                    return;
                }

                if (req.url === '/v1/chat' && req.method === 'POST') {
                    receivedPayload = JSON.parse(body);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        request_id: 'chat_test_123',
                        conversation_id: receivedPayload.conversation_id || 'conv_default',
                        answer: 'Eligible citizens can receive financial assistance under PMEGP.',
                        intent: 'SCHEME_DISCOVERY',
                        citations: [
                            {
                                chunk_id: 'chk_001',
                                scheme_id: 'pmegp',
                                url: 'https://kviconline.gov.in/pmegp',
                                excerpt: 'PMEGP provides margin money subsidy up to 35%.'
                            }
                        ],
                        suggested_schemes: [
                            {
                                scheme_id: 'pmegp',
                                scheme_name: 'PMEGP Scheme',
                                relevance_score: 0.95,
                                ministry: 'Ministry of MSME',
                                state: 'All India'
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

    test('Maps chat request to /v1/chat with X-AI-Service-Key and adapts response', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;

        const result = await chatService.chat('user_456', 'How do I apply for PMEGP?');

        // 1. Verify headers sent to Intelligence
        assert.strictEqual(receivedHeaders[HEADER_NAME.toLowerCase()], AI_SERVICE_API_KEY);
        assert.ok(receivedHeaders['x-request-id']);

        // 2. Verify payload mapping
        assert.strictEqual(receivedPayload.query, 'How do I apply for PMEGP?');
        assert.strictEqual(receivedPayload.conversation_id, 'user_456');
        assert.strictEqual(receivedPayload.language, 'en');

        // 3. Verify response adaptation to FrontEnd contract
        assert.strictEqual(result.source, 'intelligence');
        assert.ok(result.reply.includes('PMEGP'));
        assert.strictEqual(result.isGrounded, true);
        assert.strictEqual(result.showViewAll, true);
        assert.strictEqual(result.citations.length, 1);
        assert.strictEqual(result.citations[0].schemeId, 'pmegp');
        assert.strictEqual(result.schemes.length, 1);
        assert.strictEqual(result.schemes[0].id, 'pmegp');
        assert.strictEqual(result.schemes[0].relevanceScore, 95);
        assert.strictEqual(result.schemes[0].matchScore, null);
        assert.strictEqual(result.schemes[0].eligibilityStatus, 'UNKNOWN');
        assert.strictEqual(result.schemes[0].matchType, 'neutral');
    });

    test('Falls back gracefully to local engine when Intelligence is unreachable or fails', async () => {
        returnError = true;

        const result = await chatService.chat('user_789', 'Tell me about student scholarships in Gujarat');

        // Verify fallback succeeded without throwing error to caller
        assert.ok(result);
        assert.ok(result.reply);
        assert.ok(Array.isArray(result.schemes));

        returnError = false;
    });
});
