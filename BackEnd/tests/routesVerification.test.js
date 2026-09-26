const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const app = require('../src/app');

describe('22 Backend Routes Mounted & Verification Tests', () => {
    let server;
    let baseUrl;

    before((_, done) => {
        server = http.createServer(app);
        server.listen(0, '127.0.0.1', () => {
            const port = server.address().port;
            baseUrl = `http://127.0.0.1:${port}`;
            done();
        });
    });

    after((_, done) => {
        server.close(done);
    });

    const routesToCheck = [
        { method: 'GET', path: '/', expectedStatus: [200] },
        { method: 'POST', path: '/api/users/register', expectedStatus: [400, 422] },
        { method: 'POST', path: '/api/users/login', expectedStatus: [400, 422] },
        { method: 'POST', path: '/api/users/refresh', expectedStatus: [400, 401] },
        { method: 'GET', path: '/api/users/me', expectedStatus: [401] },
        { method: 'POST', path: '/api/users/logout', expectedStatus: [200, 401] },
        { method: 'GET', path: '/api/users/profile', expectedStatus: [401] },
        { method: 'PUT', path: '/api/users/profile', expectedStatus: [401] },
        { method: 'GET', path: '/api/dashboard', expectedStatus: [401] },
        { method: 'POST', path: '/api/documents/process', expectedStatus: [401] },
        { method: 'POST', path: '/api/documents/extract', expectedStatus: [401] },
        { method: 'GET', path: '/api/documents', expectedStatus: [401] },
        { method: 'GET', path: '/api/documents/00000000-0000-0000-0000-000000000001', expectedStatus: [401] },
        { method: 'DELETE', path: '/api/documents/00000000-0000-0000-0000-000000000001', expectedStatus: [401] },
        { method: 'POST', path: '/api/schemes/search', expectedStatus: [200] },
        { method: 'GET', path: '/api/schemes/test-scheme-id', expectedStatus: [404, 500, 200] },
        { method: 'POST', path: '/api/eligibility/check', expectedStatus: [401] },
        { method: 'POST', path: '/api/chat', expectedStatus: [200, 400] },
        { method: 'GET', path: '/api/applications', expectedStatus: [401] },
        { method: 'POST', path: '/api/applications', expectedStatus: [401] },
        { method: 'GET', path: '/api/applications/00000000-0000-0000-0000-000000000001', expectedStatus: [401] },
        { method: 'POST', path: '/api/applications/analyze', expectedStatus: [401] }
    ];

    test('All 22 Backend routes are mounted and not returning 404 (Route not found)', async () => {
        assert.strictEqual(routesToCheck.length, 22, 'Must test exactly 22 documented routes');

        for (const route of routesToCheck) {
            const res = await fetch(`${baseUrl}${route.path}`, {
                method: route.method,
                headers: { 'Content-Type': 'application/json' },
                body: ['POST', 'PUT'].includes(route.method) ? JSON.stringify({}) : undefined
            });

            // If a route returns 404 with "Route not found", then the router failed to mount it
            if (res.status === 404) {
                const text = await res.text();
                assert.ok(
                    !text.includes('Route not found'),
                    `Route ${route.method} ${route.path} is not mounted! Got: ${text}`
                );
            }

            assert.ok(
                route.expectedStatus.includes(res.status),
                `Route ${route.method} ${route.path} returned unexpected status ${res.status}. Expected one of: ${route.expectedStatus.join(', ')}`
            );
        }
    });
});
