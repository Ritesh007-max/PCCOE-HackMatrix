const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const schemeService = require('../src/services/schemeService');
const { HEADER_NAME, AI_SERVICE_API_KEY } = require('../src/config/intelligenceConfig');

describe('Scheme Search Backend ↔ Intelligence Integration Tests', () => {
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
                    res.end(JSON.stringify({ detail: 'Search engine failed' }));
                    return;
                }

                if (req.url === '/v1/schemes/search' && req.method === 'POST') {
                    receivedPayload = JSON.parse(body);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        request_id: 'sch_test_123',
                        query: receivedPayload.query,
                        total_results: 1,
                        results: [
                            {
                                scheme_id: 'pm-vidyalaxmi',
                                scheme_name: 'PM Vidyalaxmi Scheme',
                                relevance_score: 0.94,
                                source_authority: 'Ministry of Education',
                                source_url: 'https://pmvidyalaxmi.gov.in',
                                evidence_snippets: ['Collateral-free educational loan support up to 10 Lakh.'],
                                state: 'All India',
                                details: {
                                    benefit_summary: 'Up to ₹10 Lakh educational loan assistance.'
                                }
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

    test('Queries Intelligence /v1/schemes/search with filters and returns ranked results', async () => {
        process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;

        const result = await schemeService.searchSchemes({
            query: 'education loan',
            filters: { state: 'Gujarat', type: 'Education' }
        });

        // 1. Verify headers
        assert.strictEqual(receivedHeaders[HEADER_NAME.toLowerCase()], AI_SERVICE_API_KEY);

        // 2. Verify payload forwarded
        assert.strictEqual(receivedPayload.query, 'education loan');
        assert.strictEqual(receivedPayload.state, 'Gujarat');
        assert.strictEqual(receivedPayload.beneficiary_type, 'Education');

        // 3. Verify hybrid output
        assert.strictEqual(result.source, 'hybrid_intelligence');
        assert.ok(result.schemes.length >= 1);
        assert.strictEqual(result.schemes[0].id, 'pm-vidyalaxmi');
        assert.strictEqual(result.schemes[0].matchScore, 94);
    });

    test('Falls back to database when Intelligence search fails', async () => {
        returnError = true;

        const result = await schemeService.searchSchemes({ query: 'PM' });

        assert.strictEqual(result.source, 'database');
        assert.ok(Array.isArray(result.schemes));

        returnError = false;
    });

    test('Retrieves individual scheme by ID directly without AI overhead', async () => {
        const { data: dbSchemes } = await require('../src/config/supabaseConfig').supabaseAdmin
            .from('schemes')
            .select('id')
            .limit(1);

        if (dbSchemes && dbSchemes.length > 0) {
            const schemeId = dbSchemes[0].id;
            const res = await schemeService.getSchemeById(schemeId);
            assert.strictEqual(res.source, 'database');
            assert.strictEqual(res.scheme.id, schemeId);
        }
    });
});
