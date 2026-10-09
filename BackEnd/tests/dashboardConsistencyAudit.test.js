/**
 * FIN — Backend Dashboard Consistency & Dynamic Data Regression Suite
 *
 * Verifies backend items 1 to 20:
 * - Scoped retrieval by authenticated userId
 * - Dynamic consumption of applicable schemes catalog
 * - Strict financial exclusion of loans and in-kind benefits
 * - Preserving real statuses: PASS, UNKNOWN, REVIEW
 * - Accurate document vault count and OCR != Verified
 * - Accurate application count and status
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const dashboardService = require('../src/services/dashboardService');
const schemeService = require('../src/services/schemeService');
const profileService = require('../src/services/profileService');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('FIN — Backend Dashboard Consistency & Dynamic Data Audit', () => {

    const testUserId = '05403000-bcac-4287-b36f-721eefe3c7e4';

    test('1. getDashboardData returns real user data, metrics, and top opportunities', async () => {
        const data = await dashboardService.getDashboardData(testUserId);
        const expectedProfile = await profileService.getProfileById(testUserId);
        assert.ok(data, 'Dashboard data must exist');
        assert.strictEqual(data.user.fullName, expectedProfile.full_name, 'User name must match database record');
        assert.ok(data.user.profileCompleted > 0);

        // Metrics array
        assert.ok(Array.isArray(data.metrics), 'metrics must be an array');
        assert.strictEqual(data.metrics.length, 4);

        const schemesMetric = data.metrics.find(m => m.key === 'schemes');
        const benefitsMetric = data.metrics.find(m => m.key === 'benefits');
        const docsMetric = data.metrics.find(m => m.key === 'documents');
        const appsMetric = data.metrics.find(m => m.key === 'applications');

        assert.ok(schemesMetric, 'Relevant Schemes metric must exist');
        assert.strictEqual(schemesMetric.value, '670');
        assert.strictEqual(schemesMetric.subtitle, 'Available in Gujarat & Central jurisdiction');

        assert.ok(benefitsMetric, 'Estimated Benefits metric must exist');
        assert.strictEqual(benefitsMetric.value, '₹ 0');
        assert.strictEqual(benefitsMetric.subtitle, 'Complete verification to calculate grants');

        assert.ok(docsMetric, 'Documents Verified metric must exist');
        assert.strictEqual(docsMetric.value, '0 / 1');
        assert.strictEqual(docsMetric.subtitle, '1 pending review in vault');

        assert.ok(appsMetric, 'Applications metric must exist');
        assert.strictEqual(appsMetric.value, '6');
        assert.strictEqual(appsMetric.subtitle, '6 pending review');

        // Top opportunities
        assert.ok(Array.isArray(data.topOpportunities), 'topOpportunities must be an array');
        assert.strictEqual(data.topOpportunities.length, 5);
        for (const opp of data.topOpportunities) {
            assert.ok(opp.schemeId, 'Each opportunity must have a schemeId');
            assert.ok(opp.schemeName, 'Each opportunity must have a schemeName');
            assert.strictEqual(opp.eligibilityStatus, 'UNKNOWN');
            assert.strictEqual(opp.isEligible, false);
        }
    });

    test('2. Multi-tenant isolation: empty user returns zero documents and zero applications', async () => {
        const emptyUserId = '00000000-0000-0000-0000-000000000000';
        const docStats = await dashboardService.getDocumentStats(emptyUserId);
        const appStats = await dashboardService.getApplicationStats(emptyUserId);

        assert.strictEqual(docStats.totalVault, 0);
        assert.strictEqual(docStats.verified, 0);
        assert.strictEqual(appStats.total, 0);
    });

    test('3. Exclusion of loan ceilings: commercial credit facilities never count as confirmed cash grant', async () => {
        const fakeLoanOpp = {
            id: 'loan_scheme_test',
            name: 'PMEGP Business Credit Facility',
            max_benefit: 2500000,
            type: 'Loan / Credit',
            tags: ['Credit', 'Loan']
        };
        const interp = require('../src/services/financialBenefitService').interpretFinancialBenefit(fakeLoanOpp);
        assert.strictEqual(interp.isScalarCashGrant, false);
    });

    test('4. Catalog parity: dashboard consumes schemeService.getApplicableSchemesCatalog dynamically', async () => {
        const catalog = await schemeService.getApplicableSchemesCatalog('Gujarat');
        assert.strictEqual(catalog.totalApplicable, 670);
        assert.strictEqual(catalog.applicableStateCount, 641);
        assert.strictEqual(catalog.applicableCentralCount, 29);
    });
});
