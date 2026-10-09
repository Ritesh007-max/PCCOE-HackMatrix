import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getSchemeApplicationCycle,
  parseDateInIST,
  formatDisplayDate,
  adaptSchemeDetails
} from '../src/utils/schemeDetailsHelpers.js';

// Constant reference date for deterministic testing: 3 October 2026, 21:36:53 IST (UTC+05:30)
const NOW_IST_STR = '2026-10-03T21:36:53+05:30';
const NOW_REF = new Date(NOW_IST_STR);

test('1. OPEN state: Active deadline within open and close window', () => {
  const scheme = {
    id: 'test-open-1',
    scheme_name: 'Solar Rooftop Subsidy Scheme',
    scheme_open_date: '2026-01-01',
    scheme_close_date: '2027-03-31'
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'OPEN');
  assert.equal(cycle.isLive, true);
  assert.equal(cycle.badgeClass, 'open');
  assert.equal(cycle.label, 'Applications Open');
  assert.equal(cycle.detailedStatus, 'Open (Deadline: 31 Mar 2027)');
  assert.match(cycle.badgeText, /Applications Open/);
  assert.match(cycle.badgeText, /31 Mar 2027/);
  assert.equal(cycle.formattedCloseDate, '31 Mar 2027');
  assert.ok(cycle.daysRemaining > 0);
  assert.doesNotMatch(cycle.label, /2025/);
});

test('2. OPEN state: Only close date is provided and deadline is in the future', () => {
  const scheme = {
    id: 'bbsy',
    scheme_name: 'Biju Bikas Yojana',
    scheme_open_date: null,
    scheme_close_date: '2027-03-31'
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'OPEN');
  assert.equal(cycle.isLive, true);
  assert.equal(cycle.badgeClass, 'open');
  assert.equal(cycle.label, 'Applications Open');
  assert.equal(cycle.closeDate, '2027-03-31');
  assert.equal(cycle.formattedCloseDate, '31 Mar 2027');
});

test('3. CLOSED state: Canonical scheme with expired deadline in the past', () => {
  // Canonical CMEGP: closed on 2024-07-31
  const scheme = {
    id: 'cmegp',
    scheme_name: 'Chief Minister Employment Generation Programme',
    scheme_open_date: '2019-08-01',
    scheme_close_date: '2024-07-31'
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'CLOSED');
  assert.equal(cycle.isLive, false);
  assert.equal(cycle.badgeClass, 'closed');
  assert.equal(cycle.label, 'Applications Closed');
  assert.equal(cycle.detailedStatus, 'Closed on 31 Jul 2024');
  assert.equal(cycle.badgeText, 'Applications Closed');
  assert.equal(cycle.daysRemaining, 0);
  assert.match(cycle.cycleDescription, /closed on 31 Jul 2024/i);
});

test('4. CLOSED state: Only close date provided and expired', () => {
  const scheme = {
    id: 'aasra',
    scheme_name: 'Aasra Pension Scheme',
    scheme_open_date: null,
    scheme_close_date: '2020-01-01'
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'CLOSED');
  assert.equal(cycle.isLive, false);
  assert.equal(cycle.badgeClass, 'closed');
  assert.equal(cycle.label, 'Applications Closed');
  assert.equal(cycle.detailedStatus, 'Closed on 1 Jan 2020');
});

test('5. UPCOMING state: Opening date is in the future', () => {
  const scheme = {
    id: 'future-scholarship',
    scheme_name: 'National Higher Studies Fellowship 2027',
    scheme_open_date: '2027-01-01',
    scheme_close_date: '2027-06-30'
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'UPCOMING');
  assert.equal(cycle.isLive, false);
  assert.equal(cycle.badgeClass, 'upcoming');
  assert.equal(cycle.label, 'Upcoming Applications');
  assert.equal(cycle.detailedStatus, 'Upcoming (Opens 1 Jan 2027)');
  assert.equal(cycle.badgeText, 'Upcoming (Opens 1 Jan 2027)');
});

test('6. ONGOING state: Open date in past with no close date (continuous enrollment)', () => {
  // Canonical 15DSUGT: open since 2013-08-27, no closing date
  const scheme = {
    id: '15dsugt',
    scheme_name: '15 Days Skill Up-gradation Training',
    scheme_open_date: '2013-08-27',
    scheme_close_date: null
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'ONGOING');
  assert.equal(cycle.isLive, true);
  assert.equal(cycle.badgeClass, 'ongoing');
  assert.equal(cycle.label, 'Ongoing Applications');
  assert.equal(cycle.detailedStatus, 'Ongoing (Since 27 Aug 2013)');
  assert.equal(cycle.badgeText, 'Ongoing Applications');
  assert.equal(cycle.openDate, '2013-08-27');
  assert.equal(cycle.closeDate, null);
});

test('7. NOT_SPECIFIED state: 1pmy and schemes with neither open nor close date', () => {
  const scheme = {
    id: '1pmy',
    scheme_name: '100% Penalty Mafi Yojana',
    scheme_open_date: null,
    scheme_close_date: null
  };

  const cycle = getSchemeApplicationCycle(scheme, NOW_REF);

  assert.equal(cycle.status, 'NOT_SPECIFIED');
  assert.equal(cycle.isLive, false);
  assert.equal(cycle.badgeClass, 'unspecified');
  assert.equal(cycle.label, 'Status Not Specified');
  assert.equal(cycle.detailedStatus, 'Status Not Specified');
  assert.equal(cycle.badgeText, 'Status Not Specified');
  assert.doesNotMatch(cycle.label, /2025/);
  assert.doesNotMatch(cycle.label, /Ongoing/);
  assert.doesNotMatch(cycle.label, /Active Deadline/);
});

test('8. Inconsistent and malformed metadata handled cleanly without crashing or inventing status', () => {
  const malformedScheme = {
    id: 'malformed-1',
    scheme_open_date: 'NaN',
    scheme_close_date: 'null'
  };

  const cycle = getSchemeApplicationCycle(malformedScheme, NOW_REF);

  assert.equal(cycle.status, 'NOT_SPECIFIED');
  assert.equal(cycle.label, 'Status Not Specified');
  assert.equal(cycle.isLive, false);
});

test('9. Timezone & Date Boundary: IST Open start of day (00:00:00+05:30)', () => {
  const scheme = {
    id: 'boundary-open-test',
    scheme_open_date: '2026-10-03',
    scheme_close_date: '2026-10-31'
  };

  // 1 second before midnight IST: 2026-10-02T23:59:59+05:30 -> UPCOMING
  const justBeforeOpen = new Date('2026-10-02T23:59:59+05:30');
  const cycleBefore = getSchemeApplicationCycle(scheme, justBeforeOpen);
  assert.equal(cycleBefore.status, 'UPCOMING');

  // Exact midnight IST: 2026-10-03T00:00:00+05:30 -> OPEN
  const exactOpen = new Date('2026-10-03T00:00:00+05:30');
  const cycleOpen = getSchemeApplicationCycle(scheme, exactOpen);
  assert.equal(cycleOpen.status, 'OPEN');
});

test('10. Timezone & Date Boundary: IST Close end of day (23:59:59.999+05:30)', () => {
  const scheme = {
    id: 'boundary-close-test',
    scheme_open_date: '2026-09-01',
    scheme_close_date: '2026-10-03'
  };

  // 21:36:53 IST on 2026-10-03 -> Still OPEN (same day, before 23:59:59.999)
  const currentEvening = new Date('2026-10-03T21:36:53+05:30');
  const cycleEvening = getSchemeApplicationCycle(scheme, currentEvening);
  assert.equal(cycleEvening.status, 'OPEN');
  assert.equal(cycleEvening.isLive, true);

  // Exact next day midnight IST: 2026-10-04T00:00:00+05:30 -> CLOSED
  const nextDayMidnight = new Date('2026-10-04T00:00:00+05:30');
  const cycleClosed = getSchemeApplicationCycle(scheme, nextDayMidnight);
  assert.equal(cycleClosed.status, 'CLOSED');
  assert.equal(cycleClosed.isLive, false);
});

test('11. Explicit verified status metadata is respected when dates are absent', () => {
  const closedScheme = {
    id: 'explicit-closed',
    application_status: 'CLOSED'
  };
  assert.equal(getSchemeApplicationCycle(closedScheme, NOW_REF).status, 'CLOSED');

  const upcomingScheme = {
    id: 'explicit-upcoming',
    application_status: 'UPCOMING'
  };
  assert.equal(getSchemeApplicationCycle(upcomingScheme, NOW_REF).status, 'UPCOMING');

  const ongoingScheme = {
    id: 'explicit-ongoing',
    application_status: 'ONGOING'
  };
  assert.equal(getSchemeApplicationCycle(ongoingScheme, NOW_REF).status, 'ONGOING');
});

test('12. CRITICAL INVARIANT: Zero universal FY 2025–26 fallback exists across any scheme', () => {
  const testCatalog = [
    { id: '1pmy', scheme_open_date: null, scheme_close_date: null },
    { id: 'unknown-catalog-item', name: 'Unknown Scheme' },
    { id: 'cmegp', scheme_open_date: '2019-08-01', scheme_close_date: '2024-07-31' },
    { id: '15dsugt', scheme_open_date: '2013-08-27', scheme_close_date: null },
    { id: 'bbsy', scheme_open_date: null, scheme_close_date: '2027-03-31' },
    {}
  ];

  for (const s of testCatalog) {
    const cycle = getSchemeApplicationCycle(s, NOW_REF);
    assert.doesNotMatch(cycle.label, /2025/i, `Scheme ${s.id || 'empty'} must not contain 2025`);
    assert.doesNotMatch(cycle.badgeText, /2025/i, `Scheme ${s.id || 'empty'} badgeText must not contain 2025`);
    assert.doesNotMatch(cycle.detailedStatus, /2025/i, `Scheme ${s.id || 'empty'} detailedStatus must not contain 2025`);
    assert.doesNotMatch(cycle.cycleDescription, /2025/i, `Scheme ${s.id || 'empty'} cycleDescription must not contain 2025`);
  }
});

test('13. adaptSchemeDetails attaches sanitized application_cycle object', () => {
  const raw = {
    id: '1pmy',
    scheme_name: '100% Penalty Mafi Yojana',
    scheme_open_date: 'NaN',
    scheme_close_date: null
  };

  const adapted = adaptSchemeDetails(raw);
  assert.ok(adapted.application_cycle);
  assert.equal(adapted.application_cycle.status, 'NOT_SPECIFIED');
  assert.equal(adapted.application_cycle.label, 'Status Not Specified');
  assert.equal(adapted.scheme_open_date, null);
  assert.equal(adapted.scheme_close_date, null);
});
