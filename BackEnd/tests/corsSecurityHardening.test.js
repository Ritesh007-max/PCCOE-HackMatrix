const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const express = require('express');

const {
    validateAndNormalizeOrigin,
    resolveAllowedOrigins,
    getCorsOptions,
    createCorsMiddleware
} = require('../src/config/corsConfig');

describe('FIN — CORS Audit and Hardening Security Test Suite (Backend)', () => {

    // ─────────────────────────────────────────────────────────────────────────
    // 1. Origin Validation & Normalization
    // ─────────────────────────────────────────────────────────────────────────
    describe('1. validateAndNormalizeOrigin', () => {
        test('normalizes origins by stripping whitespace and trailing slashes', () => {
            assert.strictEqual(
                validateAndNormalizeOrigin('  https://fin.gov.in/  ', true),
                'https://fin.gov.in'
            );
            assert.strictEqual(
                validateAndNormalizeOrigin('https://app.fin.gov.in///', true),
                'https://app.fin.gov.in'
            );
            assert.strictEqual(
                validateAndNormalizeOrigin('http://localhost:5173/', false),
                'http://localhost:5173'
            );
        });

        test('strictly rejects wildcard origin in production', () => {
            assert.throws(
                () => validateAndNormalizeOrigin('*', true),
                /Wildcard origin \('\*'\) is strictly prohibited in production/
            );
            assert.throws(
                () => validateAndNormalizeOrigin('https://*.fin.gov.in', true),
                /Wildcard origin/
            );
        });

        test('strictly rejects insecure HTTP origin in production', () => {
            assert.throws(
                () => validateAndNormalizeOrigin('http://fin.gov.in', true),
                /Insecure HTTP origin 'http:\/\/fin\.gov\.in' is strictly prohibited in production/
            );
        });

        test('strictly rejects localhost and loopback origins in production', () => {
            assert.throws(
                () => validateAndNormalizeOrigin('http://localhost:5173', true),
                /Localhost\/loopback origin .* is strictly prohibited in production/
            );
            assert.throws(
                () => validateAndNormalizeOrigin('https://localhost:3000', true),
                /Localhost\/loopback origin/
            );
            assert.throws(
                () => validateAndNormalizeOrigin('http://127.0.0.1:5173', true),
                /Localhost\/loopback origin/
            );
        });

        test('strictly rejects origins with URL path components, queries, or fragments', () => {
            assert.throws(
                () => validateAndNormalizeOrigin('https://fin.gov.in/api/v1', true),
                /cannot include a path/
            );
            assert.throws(
                () => validateAndNormalizeOrigin('https://fin.gov.in?utm_source=gov', true),
                /cannot include query parameters/
            );
            assert.throws(
                () => validateAndNormalizeOrigin('https://fin.gov.in#top', true),
                /cannot include query parameters or hash/
            );
        });

        test('allows valid HTTPS production origin', () => {
            const normalized = validateAndNormalizeOrigin('https://beneficiary.fin.gov.in', true);
            assert.strictEqual(normalized, 'https://beneficiary.fin.gov.in');
        });
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 2. resolveAllowedOrigins Fail-Closed Policy
    // ─────────────────────────────────────────────────────────────────────────
    describe('2. resolveAllowedOrigins fail-closed production policy', () => {
        test('production: fails closed if FRONTEND_ORIGINS is missing or empty', () => {
            assert.throws(
                () => resolveAllowedOrigins('production', undefined),
                /FRONTEND_ORIGINS environment variable is required and must be explicitly configured in production/
            );
            assert.throws(
                () => resolveAllowedOrigins('production', ''),
                /FRONTEND_ORIGINS environment variable is required/
            );
            assert.throws(
                () => resolveAllowedOrigins('production', '   '),
                /FRONTEND_ORIGINS environment variable is required/
            );
        });

        test('production: fails closed if FRONTEND_ORIGINS contains wildcard', () => {
            assert.throws(
                () => resolveAllowedOrigins('production', '*'),
                /Wildcard origin \('\*'\) is strictly prohibited in production/
            );
            assert.throws(
                () => resolveAllowedOrigins('production', 'https://fin.gov.in, *'),
                /Wildcard origin/
            );
        });

        test('production: fails closed if FRONTEND_ORIGINS contains localhost', () => {
            assert.throws(
                () => resolveAllowedOrigins('production', 'http://localhost:5173'),
                /Localhost\/loopback origin/
            );
            assert.throws(
                () => resolveAllowedOrigins('production', 'https://fin.gov.in, http://127.0.0.1:5173'),
                /Localhost\/loopback origin/
            );
        });

        test('production: resolves and normalizes multiple valid HTTPS origins', () => {
            const origins = resolveAllowedOrigins(
                'production',
                'https://fin.gov.in/, https://portal.fin.gov.in, https://fin.gov.in'
            );
            assert.deepStrictEqual(origins, [
                'https://fin.gov.in',
                'https://portal.fin.gov.in'
            ]);
        });

        test('development: permits localhost and 127.0.0.1 development origins', () => {
            const devOrigins = resolveAllowedOrigins('development', '');
            assert.ok(devOrigins.includes('http://localhost:5173'));
            assert.ok(devOrigins.includes('http://127.0.0.1:5173'));
            assert.ok(devOrigins.includes('http://localhost:3000'));
        });
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 3. HTTP Integration with Express and Native HTTP Client
    // ─────────────────────────────────────────────────────────────────────────
    describe('3. Express CORS Middleware HTTP Verification', () => {
        /**
         * Helper to start an Express test server and make HTTP requests.
         */
        function makeRequest(server, options) {
            return new Promise((resolve, reject) => {
                const req = http.request({
                    hostname: '127.0.0.1',
                    port: server.address().port,
                    ...options
                }, (res) => {
                    let data = '';
                    res.on('data', chunk => { data += chunk; });
                    res.on('end', () => {
                        resolve({
                            statusCode: res.statusCode,
                            headers: res.headers,
                            body: data
                        });
                    });
                });
                req.on('error', reject);
                if (options.body) {
                    req.write(options.body);
                }
                req.end();
            });
        }

        test('production mode: trusted origin is accepted with correct CORS headers and credentials', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'production',
                frontendOrigins: 'https://fin.gov.in,https://app.fin.gov.in'
            }));
            app.get('/api/test', (req, res) => res.json({ ok: true }));

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/test',
                    method: 'GET',
                    headers: {
                        'Origin': 'https://fin.gov.in'
                    }
                });

                assert.strictEqual(res.statusCode, 200);
                assert.strictEqual(res.headers['access-control-allow-origin'], 'https://fin.gov.in');
                assert.strictEqual(res.headers['access-control-allow-credentials'], 'true');
            } finally {
                server.close();
            }
        });

        test('production mode: untrusted origin is rejected with 403 and NO allow-origin header', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'production',
                frontendOrigins: 'https://fin.gov.in'
            }));
            app.get('/api/test', (req, res) => res.json({ ok: true }));
            app.use((err, req, res, next) => {
                res.status(err.status || 500).json({ error: err.message });
            });

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/test',
                    method: 'GET',
                    headers: {
                        'Origin': 'https://evil-phishing-site.com'
                    }
                });

                assert.strictEqual(res.statusCode, 403);
                assert.strictEqual(res.headers['access-control-allow-origin'], undefined);
                assert.ok(res.body.includes('CORS error: Origin https://evil-phishing-site.com not allowed'));
            } finally {
                server.close();
            }
        });

        test('production mode: localhost is rejected even if sent as origin header', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'production',
                frontendOrigins: 'https://fin.gov.in'
            }));
            app.get('/api/test', (req, res) => res.json({ ok: true }));
            app.use((err, req, res, next) => {
                res.status(err.status || 500).json({ error: err.message });
            });

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/test',
                    method: 'GET',
                    headers: {
                        'Origin': 'http://localhost:5173'
                    }
                });

                assert.strictEqual(res.statusCode, 403);
                assert.strictEqual(res.headers['access-control-allow-origin'], undefined);
                assert.ok(res.body.includes('Localhost origin http://localhost:5173 is strictly prohibited in production'));
            } finally {
                server.close();
            }
        });

        test('preflight OPTIONS request: trusted origin receives 204, allowed methods, and allowed headers', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'production',
                frontendOrigins: 'https://fin.gov.in'
            }));
            app.post('/api/applications', (req, res) => res.json({ created: true }));

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/applications',
                    method: 'OPTIONS',
                    headers: {
                        'Origin': 'https://fin.gov.in',
                        'Access-Control-Request-Method': 'POST',
                        'Access-Control-Request-Headers': 'Content-Type, Authorization, X-Requested-With'
                    }
                });

                assert.strictEqual(res.statusCode, 204);
                assert.strictEqual(res.headers['access-control-allow-origin'], 'https://fin.gov.in');
                assert.strictEqual(res.headers['access-control-allow-credentials'], 'true');
                
                const allowedMethods = res.headers['access-control-allow-methods'];
                assert.ok(allowedMethods.includes('POST'));
                assert.ok(allowedMethods.includes('GET'));
                assert.ok(allowedMethods.includes('OPTIONS'));

                const allowedHeaders = res.headers['access-control-allow-headers'];
                assert.ok(allowedHeaders.toLowerCase().includes('content-type'));
                assert.ok(allowedHeaders.toLowerCase().includes('authorization'));
            } finally {
                server.close();
            }
        });

        test('preflight OPTIONS request: untrusted origin does NOT receive access-control-allow-origin', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'production',
                frontendOrigins: 'https://fin.gov.in'
            }));
            app.post('/api/applications', (req, res) => res.json({ created: true }));
            app.use((err, req, res, next) => {
                res.status(err.status || 500).json({ error: err.message });
            });

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/applications',
                    method: 'OPTIONS',
                    headers: {
                        'Origin': 'https://attacker.com',
                        'Access-Control-Request-Method': 'POST'
                    }
                });

                assert.strictEqual(res.headers['access-control-allow-origin'], undefined);
            } finally {
                server.close();
            }
        });

        test('development mode: allows local development origin http://localhost:5173', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'development',
                frontendOrigins: ''
            }));
            app.get('/api/test', (req, res) => res.json({ dev: true }));

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/test',
                    method: 'GET',
                    headers: {
                        'Origin': 'http://localhost:5173'
                    }
                });

                assert.strictEqual(res.statusCode, 200);
                assert.strictEqual(res.headers['access-control-allow-origin'], 'http://localhost:5173');
                assert.strictEqual(res.headers['access-control-allow-credentials'], 'true');
            } finally {
                server.close();
            }
        });

        test('requests without Origin header (curl, mobile native, server-to-server) pass through cleanly', async () => {
            const app = express();
            app.use(createCorsMiddleware({
                env: 'production',
                frontendOrigins: 'https://fin.gov.in'
            }));
            app.get('/api/test', (req, res) => res.json({ noOriginAllowed: true }));

            const server = app.listen(0);
            try {
                const res = await makeRequest(server, {
                    path: '/api/test',
                    method: 'GET'
                });

                assert.strictEqual(res.statusCode, 200);
                assert.strictEqual(res.headers['access-control-allow-origin'], undefined);
                assert.ok(res.body.includes('"noOriginAllowed":true'));
            } finally {
                server.close();
            }
        });
    });
});
