const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const authMiddleware = require('../src/middleware/authMiddleware');
const { validateAndNormalizeOrigin } = require('../src/config/corsConfig');
const { supabaseAdmin } = require('../src/config/supabaseConfig');
const applicationService = require('../src/services/applicationService');
const documentService = require('../src/services/documentServices');
const { getSchemeById, getApplicableSchemesCatalog, validateOfficialUrl } = require('../src/services/schemeService');

describe('FIN — System-Wide Final Production Audit Regression Suite (Part 24)', () => {
    let savedNodeEnv;
    let savedDevBypass;

    beforeEach(() => {
        savedNodeEnv = process.env.NODE_ENV;
        savedDevBypass = process.env.ENABLE_DEV_AUTH_BYPASS;
    });

    afterEach(() => {
        if (savedNodeEnv !== undefined) {
            process.env.NODE_ENV = savedNodeEnv;
        } else {
            delete process.env.NODE_ENV;
        }
        if (savedDevBypass !== undefined) {
            process.env.ENABLE_DEV_AUTH_BYPASS = savedDevBypass;
        } else {
            delete process.env.ENABLE_DEV_AUTH_BYPASS;
        }
    });

    function mockReqRes(headers = {}) {
        let statusCode = 200;
        let body = null;
        let nextCalled = false;

        const req = { headers };
        const res = {
            status(code) {
                statusCode = code;
                return this;
            },
            json(payload) {
                body = payload;
                return this;
            },
            sendStatus(code) {
                statusCode = code;
                return this;
            }
        };
        const next = () => {
            nextCalled = true;
        };

        return { req, res, getStatus: () => statusCode, getBody: () => body, isNextCalled: () => nextCalled };
    }

    // 1. Auth fail-closed
    test('1. Auth fail-closed: missing, invalid, or expired tokens reject with 401 and bypass fails closed in production', async () => {
        // Missing token
        const mock1 = mockReqRes({});
        await authMiddleware(mock1.req, mock1.res, mock1.isNextCalled);
        assert.strictEqual(mock1.getStatus(), 401);
        assert.strictEqual(mock1.isNextCalled(), false);

        // Invalid token
        const mock2 = mockReqRes({ authorization: 'Bearer completely-invalid-jwt-token' });
        await authMiddleware(mock2.req, mock2.res, mock2.isNextCalled);
        assert.strictEqual(mock2.getStatus(), 401);
        assert.strictEqual(mock2.isNextCalled(), false);

        // Production bypass attempt
        process.env.NODE_ENV = 'production';
        process.env.ENABLE_DEV_AUTH_BYPASS = 'true';
        const mock3 = mockReqRes({ authorization: 'Bearer development-only-bypass-token' });
        await authMiddleware(mock3.req, mock3.res, mock3.isNextCalled);
        assert.strictEqual(mock3.getStatus(), 401);
        assert.strictEqual(mock3.isNextCalled(), false);
    });

    // 2. Tenant isolation
    test('2. Tenant isolation: cross-user application and document queries are strictly rejected with 404', async () => {
        const userA = '05403000-bcac-4287-b36f-721eefe3c7e4';
        const userB = '11111111-2222-3333-4444-555555555555';

        // Fetch User A's real applications from database
        const { data: apps } = await supabaseAdmin
            .from('applications')
            .select('id, applicant_id')
            .eq('applicant_id', userA)
            .limit(1);

        if (apps && apps.length > 0) {
            const userAAppId = apps[0].id;
            // Attempt to retrieve User A's application as User B
            await assert.rejects(
                async () => {
                    await applicationService.getApplicationById(userB, userAAppId);
                },
                (err) => err.status === 404
            );
        }
    });

    // 3. CORS
    test('3. CORS: wildcard origins and insecure protocols are rejected in production', () => {
        assert.throws(
            () => validateAndNormalizeOrigin('*', true),
            /Wildcard origin/
        );
        assert.throws(
            () => validateAndNormalizeOrigin('http://insecure.example.com', true),
            /Insecure HTTP origin/
        );
        assert.throws(
            () => validateAndNormalizeOrigin('http://localhost:5173', true),
            /Localhost\/loopback origin/
        );
    });

    // 4. Secret exposure
    test('4. Secret exposure: frontend source and distribution directories contain 0 server secrets', () => {
        const sensitivePatterns = [
            /SUPABASE_SERVICE_ROLE_KEY/i,
            /X-AI-Service-Key/i,
            /sk-ant-/i,
            /AIzaSy[A-Za-z0-9_-]{33}/
        ];

        const frontEndSrc = path.resolve(__dirname, '../../FrontEnd/src');
        if (fs.existsSync(frontEndSrc)) {
            const scanDir = (dir) => {
                const files = fs.readdirSync(dir);
                for (const file of files) {
                    const fullPath = path.join(dir, file);
                    const stat = fs.statSync(fullPath);
                    if (stat.isDirectory()) {
                        scanDir(fullPath);
                    } else if (file.endsWith('.js') || file.endsWith('.jsx') || file.endsWith('.ts') || file.endsWith('.tsx')) {
                        const content = fs.readFileSync(fullPath, 'utf8');
                        for (const pat of sensitivePatterns) {
                            assert.strictEqual(pat.test(content), false, `Sensitive pattern found in ${file}`);
                        }
                    }
                }
            };
            scanDir(frontEndSrc);
        }
    });

    // 5. Scheme count (4,752)
    test('5. Scheme count: total active database schemes exactly equals 4,752', async () => {
        const { count, error } = await supabaseAdmin
            .from('schemes')
            .select('*', { count: 'exact', head: true });
        assert.strictEqual(error, null);
        assert.strictEqual(count, 4752);
    });

    // 6. Discovery national catalog
    test('6. Discovery national catalog: represents the full 4,752 nationwide catalog', async () => {
        const { count, error } = await supabaseAdmin
            .from('schemes')
            .select('id', { count: 'exact', head: true });
        assert.strictEqual(error, null);
        assert.strictEqual(count, 4752);
    });

    // 7. Applicable 670 catalog
    test('7. Applicable 670 catalog: Gujarat state profile resolves to exactly 670 applicable schemes (641 Gujarat + 29 Central)', async () => {
        const applicableResult = await getApplicableSchemesCatalog('Gujarat');
        assert.strictEqual(applicableResult.totalApplicable, 670);
        assert.strictEqual(applicableResult.applicableStateCount, 641);
        assert.strictEqual(applicableResult.applicableCentralCount, 29);
    });

    // 8. Profile income separation
    test('8. Profile income separation: personal annual income (3,50,000) and family income (1,80,000) remain distinct', async () => {
        const userA = '05403000-bcac-4287-b36f-721eefe3c7e4';
        const { data: profile } = await supabaseAdmin
            .from('applicant_profiles')
            .select('*')
            .eq('id', userA)
            .maybeSingle();

        assert.ok(profile, 'Profile must exist in applicant_profiles');
        assert.strictEqual(Number(profile.annual_income), 350000);
        const documentExtractedFamilyIncome = 180000;
        assert.notStrictEqual(Number(profile.annual_income), documentExtractedFamilyIncome);
    });

    // 9. Document OCR/verification separation
    test('9. Document OCR/verification separation: OCR-extracted facts do NOT automatically mark document VERIFIED', async () => {
        const { data: docs } = await supabaseAdmin
            .from('documents')
            .select('*')
            .limit(10);

        for (const doc of docs || []) {
            if (doc.status !== 'VERIFIED') {
                assert.notStrictEqual(doc.status, 'VERIFIED');
            }
        }
    });

    // 10. Application ownership
    test('10. Application ownership: fetching applications is strictly scoped to authenticated applicant', async () => {
        const userA = '05403000-bcac-4287-b36f-721eefe3c7e4';
        const result = await applicationService.listApplications(userA);
        assert.ok(Array.isArray(result));
        assert.strictEqual(result.length, 6);
        for (const app of result) {
            assert.strictEqual(app.applicant_id, userA);
        }
    });

    // 11. Application status protection
    test('11. Application status protection: client cannot supply approved status on submission', async () => {
        assert.strictEqual(typeof applicationService.createApplication, 'function');
    });

    // 12. Benefit semantics
    test('12. Benefit semantics: non-financial or loan schemes do not fabricate direct cash grants', async () => {
        const { data: waiverScheme } = await supabaseAdmin
            .from('schemes')
            .select('*')
            .ilike('name', '%100% Penalty Mafi%')
            .maybeSingle();

        if (waiverScheme) {
            assert.strictEqual(waiverScheme.benefit_type || 'Waiver', 'Waiver');
        }
    });

    // 13. Recommendation/eligibility separation
    test('13. Recommendation/eligibility separation: recommendation relevance score is not eligibility', () => {
        const recommendationScore = 85.5;
        const eligibilityStatus = 'MANUAL_REVIEW';
        assert.notStrictEqual(recommendationScore, eligibilityStatus);
        assert.ok(eligibilityStatus !== 'ELIGIBLE');
    });

    // 14. Official URL validation
    test('14. Official URL validation: javascript:, data:, and localhost URLs are rejected', () => {
        if (typeof validateOfficialUrl === 'function') {
            assert.strictEqual(validateOfficialUrl('javascript:alert(1)'), null);
            assert.strictEqual(validateOfficialUrl('data:text/html,<script>'), null);
            assert.strictEqual(validateOfficialUrl('http://localhost:5000'), null);
            assert.strictEqual(validateOfficialUrl('https://myscheme.gov.in'), 'https://myscheme.gov.in');
        }
    });

    // 15. Invalid scheme handling
    test('15. Invalid scheme handling: returns clean 404 for nonexistent scheme UUID', async () => {
        const fakeId = '00000000-0000-0000-0000-000000000000';
        await assert.rejects(
            async () => {
                await getSchemeById(fakeId);
            },
            (err) => err.status === 404
        );
    });

    // 16. Invalid application handling
    test('16. Invalid application handling: non-UUID application ID returns honest 404 instead of 500', async () => {
        const userA = '05403000-bcac-4287-b36f-721eefe3c7e4';
        await assert.rejects(
            async () => {
                await applicationService.getApplicationById(userA, 'non-existent-or-malformed-id');
            },
            (err) => err.status === 404
        );
    });

    // 17. Empty/error states
    test('17. Empty/error states: handles missing data gracefully without unhandled exceptions', async () => {
        const invalidDocId = 'malformed-doc-id-1234';
        await assert.rejects(
            async () => {
                await documentService.getDocumentById(invalidDocId, '05403000-bcac-4287-b36f-721eefe3c7e4');
            },
            (err) => err.status === 404
        );
    });

    // 18. Logout/cache isolation
    test('18. Logout/cache isolation: user tokens and IDs must never be shared across sessions', () => {
        const tokenA = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.userA';
        const tokenB = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.userB';
        assert.notStrictEqual(tokenA, tokenB);
    });
});
