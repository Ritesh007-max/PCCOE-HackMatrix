const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const intelligenceClient = require('../src/services/intelligenceClient');
const { HEADER_NAME, AI_SERVICE_API_KEY } = require('../src/config/intelligenceConfig');

describe('Intelligence Client & Security Boundary Tests', () => {
    let mockServer;
    let mockServerPort;
    let lastHeaders = null;
    let lastBody = null;

    before((_, done) => {
        mockServer = http.createServer((req, res) => {
            lastHeaders = req.headers;
            let body = '';
            req.on('data', chunk => { body += chunk; });
            req.on('end', () => {
                lastBody = body;
                if (req.url === '/v1/chat') {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        request_id: 'req_123',
                        answer: 'Verified statutory answer',
                        citations: [{ chunk_id: 'c1', scheme_id: 's1', url: 'https://gov.in', excerpt: 'text' }],
                        suggested_schemes: [{ scheme_id: 's1', scheme_name: 'Scheme 1', relevance_score: 0.95 }]
                    }));
                } else if (req.url === '/v1/error/401') {
                    res.writeHead(401, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: 'Invalid service API key.' }));
                } else if (req.url === '/v1/error/500') {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: `Traceback on C:\\SecretPath\\app.py with key ${AI_SERVICE_API_KEY}` }));
                } else {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ status: 'ok' }));
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

    test('Attaches internal X-AI-Service-Key and correlation headers to requests', async () => {
        // Override URL temporarily for this test
        const originalUrl = intelligenceClient.AI_SERVER_URL;
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;

        const res = await intelligenceClient.postJson('/v1/chat', { query: 'test' });
        assert.ok(res);
        assert.strictEqual(res.answer, 'Verified statutory answer');

        // Verify headers sent to mock server
        assert.strictEqual(lastHeaders[HEADER_NAME.toLowerCase()], AI_SERVICE_API_KEY);
        assert.ok(lastHeaders['x-request-id']);

        process.env.AI_SERVER_URL = originalUrl;
    });

    test('Sanitizes error responses and redacts service keys and internal paths', async () => {
        const originalUrl = intelligenceClient.AI_SERVER_URL;
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;

        await assert.rejects(
            async () => {
                await intelligenceClient.postJson('/v1/error/500', {});
            },
            (err) => {
                assert.strictEqual(err.status, 500);
                assert.strictEqual(err.code, 'INTELLIGENCE_SERVER_ERROR');
                // Ensure secret key is NOT in error message
                assert.ok(!err.message.includes(AI_SERVICE_API_KEY), 'Secret key leaked in error message!');
                // Ensure local file path is redacted
                assert.ok(!err.message.includes('C:\\SecretPath'), 'Local path leaked in error message!');
                return true;
            }
        );

        process.env.AI_SERVER_URL = originalUrl;
    });

    test('Handles 401 unauthorized gracefully', async () => {
        const originalUrl = intelligenceClient.AI_SERVER_URL;
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;

        await assert.rejects(
            async () => {
                await intelligenceClient.postJson('/v1/error/401', {});
            },
            (err) => {
                assert.strictEqual(err.status, 401);
                assert.strictEqual(err.code, 'INTELLIGENCE_AUTH_ERROR');
                return true;
            }
        );

        process.env.AI_SERVER_URL = originalUrl;
    });
});
