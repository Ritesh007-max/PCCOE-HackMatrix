import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isInternalSentinel,
  formatProfileFieldLabel,
  getEligibilityStateDetails
} from '../src/utils/schemeDetailsHelpers.js';

// -----------------------------------------------------------------------------
// Test 1: isInternalSentinel accurately identifies engine sentinels
// -----------------------------------------------------------------------------
test('1. isInternalSentinel accurately detects internal engine sentinels and permits genuine applicant fields', () => {
  const sentinels = [
    'scheme_1pmy_not_registered',
    'scheme_yipb_not_registered',
    'scheme_6islbsa_not_registered',
    'scheme_completely_unknown_scheme_xyz_not_registered',
    'rule_evaluation_error',
    'evaluation_error',
    'unknown'
  ];

  for (const s of sentinels) {
    assert.strictEqual(isInternalSentinel(s), true, `Sentinel '${s}' must be recognized as internal`);
  }

  const validApplicantFields = [
    'date_of_birth',
    'dob',
    'annual_income',
    'occupation',
    'caste_category',
    'gender',
    'state',
    'land_ownership_acres',
    'education_level',
    'is_woman_entrepreneur'
  ];

  for (const f of validApplicantFields) {
    assert.strictEqual(isInternalSentinel(f), false, `Valid field '${f}' must NOT be treated as sentinel`);
  }
});

// -----------------------------------------------------------------------------
// Test 2: formatProfileFieldLabel converts raw keys into human-readable labels
// -----------------------------------------------------------------------------
test('2. formatProfileFieldLabel maps technical database keys to clear human-readable labels', () => {
  assert.strictEqual(formatProfileFieldLabel('date_of_birth'), 'Date of Birth');
  assert.strictEqual(formatProfileFieldLabel('dob'), 'Date of Birth');
  assert.strictEqual(formatProfileFieldLabel('annual_income'), 'Annual Family Income');
  assert.strictEqual(formatProfileFieldLabel('income'), 'Annual Family Income');
  assert.strictEqual(formatProfileFieldLabel('occupation'), 'Occupation');
  assert.strictEqual(formatProfileFieldLabel('caste_category'), 'Social Category');
  assert.strictEqual(formatProfileFieldLabel('gender'), 'Gender');
  assert.strictEqual(formatProfileFieldLabel('land_ownership_acres'), 'Agricultural Land Ownership');
  assert.strictEqual(formatProfileFieldLabel('custom_applicant_attribute'), 'Custom Applicant Attribute');
});

// -----------------------------------------------------------------------------
// Test 3: 1PMY unregistered scheme state messaging integrity
// -----------------------------------------------------------------------------
test('3. 1PMY unregistered scheme produces MANUAL_REVIEW with UNREGISTERED_SCHEME category and zero sentinels', () => {
  const result1pmy = {
    schemeId: '1pmy',
    schemeName: '100% Penalty Mafi Yojana',
    status: 'UNKNOWN',
    isEligible: false,
    verdict: 'MANUAL_REVIEW',
    isRegistered: false,
    evaluationCategory: 'UNREGISTERED_SCHEME',
    rules: [],
    missingFields: [],
    missingFieldLabels: []
  };

  const details = getEligibilityStateDetails(result1pmy);
  assert.ok(details);
  assert.strictEqual(details.category, 'UNREGISTERED_SCHEME');
  assert.strictEqual(details.isRegistered, false);
  assert.strictEqual(details.hasExecutedRules, false);
  assert.strictEqual(details.verdict, 'MANUAL_REVIEW');
  assert.strictEqual(details.status, 'UNKNOWN');
  assert.strictEqual(details.showMissingProfileBox, false, 'Unregistered scheme must NEVER render Missing Profile Information box');
  assert.deepStrictEqual(details.missingFields, []);
  assert.deepStrictEqual(details.missingFieldLabels, []);
  assert.ok(!details.bannerReason.includes('scheme_1pmy_not_registered'));
  assert.ok(!details.tabSubtitle.includes('completed against official statutory'));
  assert.strictEqual(details.tabSubtitle, 'Statutory rules not yet registered in automated engine — manual review applies.');
  assert.strictEqual(details.notice, 'Automated statutory rules are not registered for this scheme. Manual verification is required during departmental application review.');
});

// -----------------------------------------------------------------------------
// Test 4: YIPB unregistered scheme state messaging integrity
// -----------------------------------------------------------------------------
test('4. YIPB unregistered scheme produces MANUAL_REVIEW with zero internal registration identifiers', () => {
  // Simulating an un-sanitized raw payload from engine to ensure helper sanitizes defensively
  const rawPayloadYipb = {
    schemeId: 'yipb',
    schemeName: 'Yuva Internship Program',
    status: 'UNKNOWN',
    isEligible: false,
    verdict: 'MANUAL_REVIEW',
    isRegistered: false,
    evaluationCategory: 'UNREGISTERED_SCHEME',
    rules: [],
    missingFields: ['scheme_yipb_not_registered'],
    review_reasons: ["Scheme 'yipb' is not registered in the statutory rule engine."]
  };

  const details = getEligibilityStateDetails(rawPayloadYipb);
  assert.ok(details);
  assert.strictEqual(details.category, 'UNREGISTERED_SCHEME');
  assert.strictEqual(details.showMissingProfileBox, false);
  assert.deepStrictEqual(details.missingFields, [], 'Internal sentinel scheme_yipb_not_registered must be stripped');
  assert.deepStrictEqual(details.missingFieldLabels, []);
  assert.ok(!JSON.stringify(details).includes('scheme_yipb_not_registered'));
});

// -----------------------------------------------------------------------------
// Test 5: Registered scheme with passing criteria preserves criterion-level evidence
// -----------------------------------------------------------------------------
test('5. Registered scheme with passing criteria produces ELIGIBLE with criterion-level evidence', () => {
  const resultPass = {
    schemeId: 'pm-kisan',
    schemeName: 'PM Kisan Samman Nidhi',
    status: 'PASS',
    isEligible: true,
    verdict: 'ELIGIBLE',
    isRegistered: true,
    evaluationCategory: 'ELIGIBLE',
    rules: [
      { id: 'FARMER_OCCUPATION', status: 'pass', rawStatus: 'PASS', reason: "Occupation is 'farmer'." },
      { id: 'INCOME_THRESHOLD', status: 'pass', rawStatus: 'PASS', reason: 'Annual income is within threshold.' }
    ],
    missingFields: [],
    missingFieldLabels: []
  };

  const details = getEligibilityStateDetails(resultPass);
  assert.ok(details);
  assert.strictEqual(details.category, 'ELIGIBLE');
  assert.strictEqual(details.isRegistered, true);
  assert.strictEqual(details.hasExecutedRules, true);
  assert.strictEqual(details.verdict, 'ELIGIBLE');
  assert.strictEqual(details.status, 'PASS');
  assert.strictEqual(details.badgeClass, 'green');
  assert.strictEqual(details.showMissingProfileBox, false);
  assert.strictEqual(details.tabSubtitle, 'Evaluation completed against official statutory scheme rules.');
});

// -----------------------------------------------------------------------------
// Test 6: Registered scheme with failing criteria produces NOT_ELIGIBLE with evidence
// -----------------------------------------------------------------------------
test('6. Registered scheme with failing criteria produces NOT_ELIGIBLE with criterion-level failure evidence', () => {
  const resultFail = {
    schemeId: 'pm-kisan',
    schemeName: 'PM Kisan Samman Nidhi',
    status: 'FAIL',
    isEligible: false,
    verdict: 'NOT_ELIGIBLE',
    isRegistered: true,
    evaluationCategory: 'NOT_ELIGIBLE',
    rules: [
      { id: 'FARMER_OCCUPATION', status: 'fail', rawStatus: 'FAIL', reason: "Occupation 'Engineer' does not qualify." },
      { id: 'INCOME_THRESHOLD', status: 'pass', rawStatus: 'PASS', reason: 'Income verified.' }
    ],
    missingFields: [],
    missingFieldLabels: []
  };

  const details = getEligibilityStateDetails(resultFail);
  assert.ok(details);
  assert.strictEqual(details.category, 'NOT_ELIGIBLE');
  assert.strictEqual(details.isRegistered, true);
  assert.strictEqual(details.hasExecutedRules, true);
  assert.strictEqual(details.verdict, 'NOT_ELIGIBLE');
  assert.strictEqual(details.status, 'FAIL');
  assert.strictEqual(details.badgeClass, 'red');
  assert.strictEqual(details.showMissingProfileBox, false);
});

// -----------------------------------------------------------------------------
// Test 7: Registered scheme with missing applicant facts renders human-readable labels
// -----------------------------------------------------------------------------
test('7. Registered scheme with missing applicant facts produces MISSING_APPLICANT_FACTS and displays human-readable labels', () => {
  const resultMissingFacts = {
    schemeId: 'pmegp',
    schemeName: 'Prime Minister Employment Generation Programme',
    status: 'UNKNOWN',
    isEligible: false,
    verdict: 'MANUAL_REVIEW',
    isRegistered: true,
    evaluationCategory: 'MISSING_APPLICANT_FACTS',
    rules: [
      { id: 'AGE_18', status: 'review', rawStatus: 'REVIEW', reason: 'Date of birth not provided — cannot verify age requirement.' },
      { id: 'NO_EXISTING_GOVT_LOAN', status: 'pass', rawStatus: 'PASS', reason: 'Self-certified.' }
    ],
    missingFields: ['date_of_birth'],
    missingFieldLabels: ['Date of Birth']
  };

  const details = getEligibilityStateDetails(resultMissingFacts);
  assert.ok(details);
  assert.strictEqual(details.category, 'MISSING_APPLICANT_FACTS');
  assert.strictEqual(details.isRegistered, true);
  assert.strictEqual(details.hasExecutedRules, true);
  assert.strictEqual(details.verdict, 'MANUAL_REVIEW');
  assert.strictEqual(details.showMissingProfileBox, true, 'Missing applicant facts MUST render the Missing Profile Information box');
  assert.deepStrictEqual(details.missingFields, ['date_of_birth']);
  assert.deepStrictEqual(details.missingFieldLabels, ['Date of Birth']);
  assert.strictEqual(details.tabSubtitle, 'Statutory evaluation paused: required applicant profile attributes are missing.');
  assert.ok(!details.tabSubtitle.includes('completed against official statutory'));
});

// -----------------------------------------------------------------------------
// Test 8: Intelligence service outage state messaging
// -----------------------------------------------------------------------------
test('8. Intelligence service outage produces INTELLIGENCE_UNAVAILABLE without claiming evaluation occurred', () => {
  const resultOutage = {
    schemeId: 'custom-scheme',
    schemeName: 'State Youth Scheme',
    status: 'UNKNOWN',
    isEligible: false,
    verdict: 'MANUAL_REVIEW',
    isRegistered: false,
    evaluationCategory: 'INTELLIGENCE_UNAVAILABLE',
    rules: [],
    missingFields: [],
    missingFieldLabels: []
  };

  const details = getEligibilityStateDetails(resultOutage);
  assert.ok(details);
  assert.strictEqual(details.category, 'INTELLIGENCE_UNAVAILABLE');
  assert.strictEqual(details.hasExecutedRules, false);
  assert.strictEqual(details.verdict, 'MANUAL_REVIEW');
  assert.strictEqual(details.status, 'UNKNOWN');
  assert.strictEqual(details.showMissingProfileBox, false);
  assert.strictEqual(details.tabSubtitle, 'Automated eligibility service is temporarily offline — manual review applies.');
  assert.ok(details.notice.includes('temporarily unreachable'));
});

// -----------------------------------------------------------------------------
// Test 9: Policy snapshot unavailable state messaging
// -----------------------------------------------------------------------------
test('9. Policy snapshot unavailable produces SNAPSHOT_UNAVAILABLE with human-readable notice', () => {
  const resultSnapshot = {
    schemeId: 'corrupted-policy-scheme',
    schemeName: 'Housing Scheme',
    status: 'UNKNOWN',
    isEligible: false,
    verdict: 'MANUAL_REVIEW',
    isRegistered: false,
    evaluationCategory: 'SNAPSHOT_UNAVAILABLE',
    rules: [],
    missingFields: [],
    missingFieldLabels: []
  };

  const details = getEligibilityStateDetails(resultSnapshot);
  assert.ok(details);
  assert.strictEqual(details.category, 'SNAPSHOT_UNAVAILABLE');
  assert.strictEqual(details.hasExecutedRules, false);
  assert.strictEqual(details.showMissingProfileBox, false);
  assert.strictEqual(details.tabSubtitle, 'Official policy snapshot is currently unavailable — manual review applies.');
  assert.ok(details.notice.includes('snapshot could not be retrieved'));
});

// -----------------------------------------------------------------------------
// Test 10: Rule evaluation error does NOT expose rule_evaluation_error sentinel
// -----------------------------------------------------------------------------
test('10. Rule evaluation error produces EVALUATION_ERROR and strictly filters rule_evaluation_error', () => {
  const resultError = {
    schemeId: 'pm-kisan',
    schemeName: 'PM Kisan',
    status: 'UNKNOWN',
    isEligible: false,
    verdict: 'MANUAL_REVIEW',
    isRegistered: true,
    evaluationCategory: 'EVALUATION_ERROR',
    rules: [],
    missingFields: ['rule_evaluation_error'],
    missingFieldLabels: []
  };

  const details = getEligibilityStateDetails(resultError);
  assert.ok(details);
  assert.strictEqual(details.category, 'EVALUATION_ERROR');
  assert.strictEqual(details.hasExecutedRules, false);
  assert.strictEqual(details.showMissingProfileBox, false);
  assert.deepStrictEqual(details.missingFields, []);
  assert.deepStrictEqual(details.missingFieldLabels, []);
  assert.strictEqual(details.tabSubtitle, 'Automated evaluation encountered an error — manual review applies.');
});

// -----------------------------------------------------------------------------
// Test 11: Shared, reusable logic across diverse arbitrary schemes without scheme-specific conditionals
// -----------------------------------------------------------------------------
test('11. Shared reusable logic handles arbitrary schemes without scheme-name-specific UI conditions', () => {
  const arbitrarySchemes = [
    { id: 'random-state-grant-777', cat: 'UNREGISTERED_SCHEME' },
    { id: 'kerala-artisan-support', cat: 'UNREGISTERED_SCHEME' },
    { id: 'delhi-clean-air-subsidy', cat: 'UNREGISTERED_SCHEME' }
  ];

  for (const s of arbitrarySchemes) {
    const payload = {
      schemeId: s.id,
      schemeName: s.id,
      status: 'UNKNOWN',
      verdict: 'MANUAL_REVIEW',
      isRegistered: false,
      evaluationCategory: s.cat,
      rules: [],
      missingFields: [`scheme_${s.id}_not_registered`]
    };

    const details = getEligibilityStateDetails(payload);
    assert.strictEqual(details.category, 'UNREGISTERED_SCHEME');
    assert.strictEqual(details.showMissingProfileBox, false);
    assert.deepStrictEqual(details.missingFields, []);
    assert.ok(!JSON.stringify(details).includes(s.id + '_not_registered'));
  }
});
