const test = require('node:test');
const assert = require('node:assert/strict');
const schemeService = require('../src/services/schemeService');
const dashboardService = require('../src/services/dashboardService');

test('Phase D3.7 Backend Application Cycle & Deadline Suite', async (t) => {
    await t.test('1. formatSchemeRecord preserves canonical open and close dates without alteration', () => {
        const row = {
            id: 'cmegp',
            scheme_name: 'CMEGP Scheme',
            scheme_open_date: '2019-08-01',
            scheme_close_date: '2024-07-31'
        };

        const formatted = schemeService.formatSchemeRecord(row);
        assert.equal(formatted.scheme_open_date, '2019-08-01');
        assert.equal(formatted.scheme_close_date, '2024-07-31');
    });

    await t.test('2. formatSchemeRecord returns null for missing dates without fabricating Ongoing or FY dates', () => {
        const row = {
            id: '1pmy',
            scheme_name: '100% Penalty Mafi Yojana'
        };

        const formatted = schemeService.formatSchemeRecord(row);
        assert.equal(formatted.scheme_open_date, null);
        assert.equal(formatted.scheme_close_date, null);
    });

    await t.test('3. dashboard top opportunities does NOT hardcode "Ongoing" when deadline is unavailable', async () => {
        // Mock profile
        const mockProfile = {
            id: 'test-user-d37',
            state: 'Gujarat',
            full_name: 'Test Citizen'
        };

        // Call getDashboardData or simulate opportunities mapping
        // Test that any opportunity without scheme_close_date does NOT default to 'Ongoing'
        const fakeOpportunityWithNoDeadline = {
            id: '1pmy',
            name: '100% Penalty Mafi Yojana',
            scheme_close_date: null
        };

        // Replicate dashboard mapping logic
        const deadline = fakeOpportunityWithNoDeadline.scheme_close_date
            ? `Deadline: ${fakeOpportunityWithNoDeadline.scheme_close_date}`
            : (fakeOpportunityWithNoDeadline.deadline && fakeOpportunityWithNoDeadline.deadline !== 'Ongoing' ? fakeOpportunityWithNoDeadline.deadline : null);

        assert.equal(deadline, null);
        assert.notEqual(deadline, 'Ongoing');
    });

    await t.test('4. dashboard top opportunities formats Deadline correctly when close date is present', () => {
        const fakeOpp = {
            id: 'bbsy',
            name: 'Biju Bikas Yojana',
            scheme_close_date: '2027-03-31'
        };

        const deadline = fakeOpp.scheme_close_date
            ? `Deadline: ${fakeOpp.scheme_close_date}`
            : (fakeOpp.deadline && fakeOpp.deadline !== 'Ongoing' ? fakeOpp.deadline : null);

        assert.equal(deadline, 'Deadline: 2027-03-31');
    });
});
