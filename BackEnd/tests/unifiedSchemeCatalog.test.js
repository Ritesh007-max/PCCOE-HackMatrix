const test = require('node:test');
const assert = require('node:assert');
const schemeService = require('../src/services/schemeService');
const dashboardService = require('../src/services/dashboardService');
const profileService = require('../src/services/profileService');

test('FIN — Unified Scheme Catalog & Jurisdiction Parity Suite', async (t) => {
    await t.test('1. Gujarat state schemes are properly loaded from canonical database', async () => {
        const catalog = await schemeService.getApplicableSchemesCatalog('Gujarat');
        assert.ok(catalog, 'Catalog must be returned');
        assert.strictEqual(catalog.state, 'Gujarat');
        assert.strictEqual(typeof catalog.applicableStateCount, 'number');
        assert.strictEqual(catalog.applicableStateCount, 641, 'Gujarat canonical schemes count should be 641');
    });

    await t.test('2. Central raw count is calculated from canonical metadata and territory-restricted schemes are excluded', async () => {
        const catalog = await schemeService.getApplicableSchemesCatalog('Gujarat');
        // 30 Central schemes in DB, 1 territory-restricted (pmsss for J&K/Ladakh) excluded for Gujarat -> 29 applicable
        assert.strictEqual(catalog.applicableCentralCount, 29, 'Applicable Central schemes for Gujarat must be 29');
        
        // Ensure pmsss (J&K / Ladakh) is excluded for Gujarat applicant
        const pmsss = catalog.applicableCentralSchemes.find(s => s.id === 'pmsss' || s.scheme_id === 'pmsss' || s.name?.includes('Prime Minister Special Scholarship Scheme'));
        assert.strictEqual(pmsss, undefined, 'Territory-restricted scheme (pmsss) must be excluded for Gujarat');
    });

    await t.test('3. Deduplicated union matches totalApplicable count and has no duplicate IDs', async () => {
        const catalog = await schemeService.getApplicableSchemesCatalog('Gujarat');
        assert.strictEqual(catalog.totalApplicable, 670, 'Total canonical applicable union must be exactly 670');
        assert.strictEqual(catalog.schemes.length, 670, 'Catalog schemes array length must equal totalApplicable');

        const seenIds = new Set();
        for (const s of catalog.schemes) {
            const id = s.id || s.scheme_id;
            assert.ok(id, 'Scheme must have an ID');
            assert.strictEqual(seenIds.has(id), false, `Scheme ID ${id} must not be duplicated`);
            seenIds.add(id);
        }
    });

    await t.test('4. Missing jurisdiction is not treated as Central and other states are excluded', () => {
        // Test filtering directly
        const missingJurisdiction = [
            { id: 'missing-1', name: 'Unknown Scheme 1', state: null, type: null, tags: [] },
            { id: 'missing-2', name: 'Unknown Scheme 2', state: '', type: '', tags: [] },
            { id: 'other-state', name: 'Maharashtra Scheme', state: 'Maharashtra', type: 'State', tags: ['Maharashtra'] },
            { id: 'valid-gujarat', name: 'Gujarat Scheme', state: 'Gujarat', type: 'State', tags: ['Gujarat'] },
            { id: 'valid-central', name: 'National Scheme', state: 'All India', type: 'Central', tags: ['Central'] }
        ];

        const filtered = schemeService.filterApplicantRelevantSchemes(missingJurisdiction, 'Gujarat');
        const ids = filtered.map(s => s.id);

        assert.strictEqual(ids.includes('missing-1'), false, 'Missing state/type must NOT be treated as Central');
        assert.strictEqual(ids.includes('missing-2'), false, 'Empty state/type must NOT be treated as Central');
        assert.strictEqual(ids.includes('other-state'), false, 'Other state schemes must be excluded');
        assert.strictEqual(ids.includes('valid-gujarat'), true, 'Gujarat state scheme must be included');
        assert.strictEqual(ids.includes('valid-central'), true, 'Valid Central scheme must be included');
    });

    await t.test('5. Dashboard and Catalog count parity (Both report 670 for Gujarat applicant)', async () => {
        const testUserId = 'a0000000-0000-4000-8000-000000000001';
        const origGetProfile = profileService.getProfileById;
        profileService.getProfileById = async () => ({
            id: testUserId,
            state: 'Gujarat'
        });

        try {
            const dashData = await dashboardService.getDashboardData(testUserId);
            const schemeCard = dashData.metrics.find(m => m.key === 'schemes');
            assert.ok(schemeCard, 'Dashboard must have schemes metric card');

            const catalog = await schemeService.getApplicableSchemesCatalog('Gujarat');

            assert.strictEqual(schemeCard.value, String(catalog.totalApplicable), 'Dashboard scheme count must strictly equal catalog totalApplicable');
            assert.strictEqual(schemeCard.value, '670', 'Dashboard metric must dynamically be 670 for Gujarat');
            assert.strictEqual(schemeCard.subtitle, 'Available in Gujarat & Central jurisdiction');
        } finally {
            profileService.getProfileById = origGetProfile;
        }
    });

    await t.test('6. Dynamic change verification: changing catalog dynamically updates Dashboard without hardcoded 670', async () => {
        const testUserId = 'a0000000-0000-4000-8000-000000000002';
        const origGetProfile = profileService.getProfileById;
        const origGetCatalog = schemeService.getApplicableSchemesCatalog;

        profileService.getProfileById = async () => ({
            id: testUserId,
            state: 'Gujarat'
        });

        // Simulate database growth to 700 applicable schemes
        schemeService.getApplicableSchemesCatalog = async (state) => ({
            state,
            applicableStateCount: 660,
            applicableCentralCount: 40,
            totalApplicable: 700,
            applicableStateSchemes: [],
            applicableCentralSchemes: [],
            schemes: []
        });

        try {
            const dashData = await dashboardService.getDashboardData(testUserId);
            const schemeCard = dashData.metrics.find(m => m.key === 'schemes');
            assert.strictEqual(schemeCard.value, '700', 'Dashboard must dynamically reflect changed catalog count without hardcoded value');
        } finally {
            profileService.getProfileById = origGetProfile;
            schemeService.getApplicableSchemesCatalog = origGetCatalog;
        }
    });

    await t.test('7. GET /api/schemes/applicable endpoint returns 200 with canonical 670 count', async () => {
        const http = require('node:http');
        const app = require('../src/app');
        const server = http.createServer(app);
        await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
        const port = server.address().port;
        try {
            const res = await fetch(`http://127.0.0.1:${port}/api/schemes/applicable?state=Gujarat`);
            assert.strictEqual(res.status, 200);
            const json = await res.json();
            assert.strictEqual(json.success, true);
            assert.strictEqual(json.totalApplicable, 670);
            assert.strictEqual(json.applicableStateCount, 641);
            assert.strictEqual(json.applicableCentralCount, 29);
            assert.strictEqual(json.schemes.length, 670);
        } finally {
            await new Promise((resolve) => server.close(resolve));
        }
    });
});
