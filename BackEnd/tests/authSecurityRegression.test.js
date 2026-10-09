const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const authMiddleware = require('../src/middleware/authMiddleware');
const { supabaseClient } = require('../src/config/supabaseConfig');

describe('FIN — Auth Security & Development Bypass Regression Suite', () => {
    let originalNodeEnv;
    let originalDevBypass;
    let originalViteDevBypass;
    let originalDevUserId;
    let originalDevUserEmail;

    beforeEach(() => {
        originalNodeEnv = process.env.NODE_ENV;
        originalDevBypass = process.env.ENABLE_DEV_AUTH_BYPASS;
        originalViteDevBypass = process.env.VITE_ENABLE_DEV_AUTH_BYPASS;
        originalDevUserId = process.env.DEV_USER_ID;
        originalDevUserEmail = process.env.DEV_USER_EMAIL;
    });

    afterEach(() => {
        if (originalNodeEnv !== undefined) {
            process.env.NODE_ENV = originalNodeEnv;
        } else {
            delete process.env.NODE_ENV;
        }

        if (originalDevBypass !== undefined) {
            process.env.ENABLE_DEV_AUTH_BYPASS = originalDevBypass;
        } else {
            delete process.env.ENABLE_DEV_AUTH_BYPASS;
        }

        if (originalViteDevBypass !== undefined) {
            process.env.VITE_ENABLE_DEV_AUTH_BYPASS = originalViteDevBypass;
        } else {
            delete process.env.VITE_ENABLE_DEV_AUTH_BYPASS;
        }

        if (originalDevUserId !== undefined) {
            process.env.DEV_USER_ID = originalDevUserId;
        } else {
            delete process.env.DEV_USER_ID;
        }

        if (originalDevUserEmail !== undefined) {
            process.env.DEV_USER_EMAIL = originalDevUserEmail;
        } else {
            delete process.env.DEV_USER_EMAIL;
        }
    });

    function createMockReqRes(token, customHeaders = null) {
        let statusCode = null;
        let jsonResponse = null;
        let nextCalled = false;

        const headers = customHeaders || (token !== null ? { authorization: `Bearer ${token}` } : {});
        const req = { headers };
        const res = {
            status: (code) => {
                statusCode = code;
                return {
                    json: (data) => {
                        jsonResponse = data;
                        return data;
                    }
                };
            }
        };
        const next = () => {
            nextCalled = true;
        };

        return { req, res, next, getStatus: () => statusCode, getResponse: () => jsonResponse, wasNextCalled: () => nextCalled };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 1. Missing or Empty NODE_ENV Rejection
    // ─────────────────────────────────────────────────────────────────────────
    test('1. Missing NODE_ENV: development bypass tokens are strictly rejected with 401', async () => {
        delete process.env.NODE_ENV;
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('development-only-bypass-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false, 'Next must not be called when NODE_ENV is unset');
        assert.strictEqual(getStatus(), 401, 'Must return HTTP 401');
        assert.strictEqual(getResponse()?.success, false);
        assert.ok(getResponse()?.message?.includes('strictly prohibited'), 'Must explain rejection reason');
    });

    test('2. Empty string or whitespace NODE_ENV: development bypass tokens are strictly rejected with 401', async () => {
        process.env.NODE_ENV = '   ';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('google-oauth-demo-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false, 'Next must not be called when NODE_ENV is whitespace');
        assert.strictEqual(getStatus(), 401, 'Must return HTTP 401');
        assert.strictEqual(getResponse()?.success, false);
        assert.ok(getResponse()?.message?.includes('strictly prohibited'));
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 2. Production Environment Strict Gating
    // ─────────────────────────────────────────────────────────────────────────
    test('3. Production NODE_ENV: bypass token is strictly rejected even if bypass flags are set to true', async () => {
        process.env.NODE_ENV = 'production';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';
        process.env.VITE_ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('development-only-bypass-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false, 'Bypass must never activate in production');
        assert.strictEqual(getStatus(), 401, 'Must return HTTP 401 in production');
        assert.strictEqual(getResponse()?.success, false);
        assert.ok(getResponse()?.message?.includes('strictly prohibited in production environment'));
    });

    test('4. Case-insensitive Production ("Production" / "PRODUCTION"): bypass token is strictly rejected', async () => {
        process.env.NODE_ENV = 'Production';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('google-oauth-demo-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false);
        assert.strictEqual(getStatus(), 401);
        assert.strictEqual(getResponse()?.success, false);
        assert.ok(getResponse()?.message?.includes('strictly prohibited in production environment'));
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 3. Staging Environment Strict Gating
    // ─────────────────────────────────────────────────────────────────────────
    test('5. Staging NODE_ENV: bypass token is strictly rejected even if bypass flags are set to true', async () => {
        process.env.NODE_ENV = 'staging';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';
        process.env.VITE_ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('development-only-bypass-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false, 'Bypass must never activate in staging');
        assert.strictEqual(getStatus(), 401, 'Must return HTTP 401 in staging');
        assert.strictEqual(getResponse()?.success, false);
        assert.ok(getResponse()?.message?.includes('strictly prohibited in staging environment'));
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 4. Safe Development Mode Configuration
    // ─────────────────────────────────────────────────────────────────────────
    test('6. Explicit development mode without opt-in flag: bypass token is rejected with 401', async () => {
        process.env.NODE_ENV = 'development';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'false';
        process.env.VITE_ENABLE_DEV_AUTH_BYPASS = 'false';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('development-only-bypass-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false, 'Bypass must require explicit opt-in flag in development');
        assert.strictEqual(getStatus(), 401);
        assert.strictEqual(getResponse()?.success, false);
    });

    test('7. Explicit development mode with explicit opt-in flag: bypass token succeeds and populates req.user', async () => {
        process.env.NODE_ENV = 'development';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';
        delete process.env.VITE_ENABLE_DEV_AUTH_BYPASS;
        process.env.DEV_USER_ID = '05403000-bcac-4287-b36f-721eefe3c7e4';
        process.env.DEV_USER_EMAIL = 'dev@fin.gov.in';

        const { req, res, next, wasNextCalled } = createMockReqRes('development-only-bypass-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), true, 'Next must be called when development configuration is explicit and safe');
        assert.strictEqual(req.user.id, '05403000-bcac-4287-b36f-721eefe3c7e4');
        assert.strictEqual(req.user.email, 'dev@fin.gov.in');
        assert.strictEqual(req.token, 'development-only-bypass-token');
    });

    test('8. Explicit development mode with google-oauth-demo-token succeeds when flag is enabled', async () => {
        process.env.NODE_ENV = 'development';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, wasNextCalled } = createMockReqRes('google-oauth-demo-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), true);
        assert.strictEqual(req.user.email, 'dev@fin.gov.in');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 5. Malformed, Missing, and Invalid Tokens
    // ─────────────────────────────────────────────────────────────────────────
    test('9. Missing Authorization header returns 401 with expected format message', async () => {
        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes(null);
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false);
        assert.strictEqual(getStatus(), 401);
        assert.ok(getResponse()?.message?.includes('Authorization header missing or invalid format'));
    });

    test('10. Non-Bearer Authorization header returns 401', async () => {
        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes(null, { authorization: 'Basic dXNlcjpwYXNz' });
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false);
        assert.strictEqual(getStatus(), 401);
        assert.ok(getResponse()?.message?.includes('Authorization header missing or invalid format'));
    });

    test('11. Bearer with empty token returns 401 Access token is missing', async () => {
        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes(null, { authorization: 'Bearer ' });
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false);
        assert.strictEqual(getStatus(), 401);
        assert.ok(getResponse()?.message?.includes('Access token is missing'));
    });

    test('12. Arbitrary invalid JWT token in production is forwarded to Supabase and rejected', async () => {
        process.env.NODE_ENV = 'production';

        const { req, res, next, getStatus, getResponse, wasNextCalled } = createMockReqRes('invalid-fabricated-jwt-token-xyz');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false);
        assert.strictEqual(getStatus(), 401);
        assert.ok(getResponse()?.message?.includes('Invalid or expired token') || getResponse()?.message?.includes('Token verification failed'));
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 6. Preservation of Legitimate Supabase Authentication
    // ─────────────────────────────────────────────────────────────────────────
    test('13. Preserves legitimate Supabase JWT authentication session', async () => {
        process.env.NODE_ENV = 'production';

        // Mock Supabase getUser response for legitimate user session
        const originalGetUser = supabaseClient.auth.getUser;
        supabaseClient.auth.getUser = async (token) => {
            if (token === 'genuine-valid-supabase-session-jwt') {
                return {
                    data: {
                        user: {
                            id: 'c1234567-89ab-cdef-0123-456789abcdef',
                            email: 'citizen@example.gov.in',
                            role: 'authenticated'
                        }
                    },
                    error: null
                };
            }
            return { data: { user: null }, error: new Error('Invalid token') };
        };

        try {
            const { req, res, next, wasNextCalled } = createMockReqRes('genuine-valid-supabase-session-jwt');
            await authMiddleware(req, res, next);

            assert.strictEqual(wasNextCalled(), true, 'Valid Supabase user session must proceed through middleware');
            assert.strictEqual(req.user.id, 'c1234567-89ab-cdef-0123-456789abcdef');
            assert.strictEqual(req.user.email, 'citizen@example.gov.in');
            assert.strictEqual(req.token, 'genuine-valid-supabase-session-jwt');
        } finally {
            supabaseClient.auth.getUser = originalGetUser;
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 7. Tenant Isolation Verification
    // ─────────────────────────────────────────────────────────────────────────
    test('14. Tenant Isolation: Dev user identity is never assigned when bypass is rejected', async () => {
        process.env.NODE_ENV = 'production';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';

        const { req, res, next, wasNextCalled } = createMockReqRes('development-only-bypass-token');
        await authMiddleware(req, res, next);

        assert.strictEqual(wasNextCalled(), false);
        assert.strictEqual(req.user, undefined, 'req.user must NOT be populated with dev user identity');
    });
});
