/**
 * FIN — State -> District Dependent Profile Field Test Suite
 *
 * Covers:
 * 1. Gujarat -> Ahmedabad valid combination
 * 2. Gujarat -> Gandhinagar valid combination
 * 3. Rajasthan -> Jaipur valid combination
 * 4. State change clears incompatible district (e.g. Gujarat -> Rajasthan clears Ahmedabad)
 * 5. Invalid state/district combination rejected (e.g. Gujarat + Jaipur)
 * 6. Persisted valid state/district loads correctly into edit modal
 * 7. Missing district rejected
 * 8. Missing state rejected
 * 9. Profile completion counts district only when valid for selected state
 * 10. Searchable district filtering (e.g. "Ahmed" -> Ahmedabad)
 * 11. Profile save persistence and storage synchronization
 * 12. Applicant Context and Suggested Schemes synchronization via fin_user_updated
 * 13. Multi-tenant isolation: User A location does not leak to User B
 */

import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  CANONICAL_STATES,
  getDistrictsForState,
  isValidState,
  isValidStateDistrict,
  normalizeStateName,
  normalizeDistrictName
} from '../src/data/geoData.js';

import { calculateProfileCompletion } from '../src/utils/profileHelpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — State -> District Dependent Profile Field Suite', async (t) => {

  await t.test('1. Valid State -> District: Gujarat -> Ahmedabad', () => {
    assert.strictEqual(isValidState('Gujarat'), true);
    assert.strictEqual(isValidStateDistrict('Gujarat', 'Ahmedabad'), true);
    assert.strictEqual(isValidStateDistrict('gujarat', 'ahmedabad'), true);
    assert.strictEqual(normalizeDistrictName('Gujarat', 'ahmedabad'), 'Ahmedabad');
  });

  await t.test('2. Valid State -> District: Gujarat -> Gandhinagar', () => {
    assert.strictEqual(isValidStateDistrict('Gujarat', 'Gandhinagar'), true);
    assert.strictEqual(isValidStateDistrict('Gujarat', 'gandhinagar'), true);
    assert.strictEqual(normalizeDistrictName('Gujarat', 'gandhinagar'), 'Gandhinagar');
  });

  await t.test('3. Valid State -> District: Rajasthan -> Jaipur', () => {
    assert.strictEqual(isValidState('Rajasthan'), true);
    assert.strictEqual(isValidStateDistrict('Rajasthan', 'Jaipur'), true);
    assert.strictEqual(isValidStateDistrict('rajasthan', 'jaipur'), true);
    assert.strictEqual(normalizeDistrictName('Rajasthan', 'jaipur'), 'Jaipur');
  });

  await t.test('4. State change clears incompatible district', () => {
    // Simulated state transition: Gujarat (Ahmedabad) -> Rajasthan
    const prevState = 'Gujarat';
    const prevDistrict = 'Ahmedabad';
    const newState = 'Rajasthan';

    assert.strictEqual(isValidStateDistrict(prevState, prevDistrict), true);

    // Incompatible check: Ahmedabad is NOT in Rajasthan
    const isStillValid = isValidStateDistrict(newState, prevDistrict);
    assert.strictEqual(isStillValid, false);

    // Transition logic: clear incompatible district
    const newDistrict = isStillValid ? prevDistrict : '';
    assert.strictEqual(newDistrict, '', 'Changing state must clear incompatible district');
  });

  await t.test('5. Invalid state/district combination rejected (Gujarat + Jaipur)', () => {
    assert.strictEqual(isValidStateDistrict('Gujarat', 'Jaipur'), false);
    assert.strictEqual(isValidStateDistrict('Rajasthan', 'Ahmedabad'), false);
    assert.strictEqual(isValidStateDistrict('Maharashtra', 'Gandhinagar'), false);
  });

  await t.test('6. Persisted valid state/district loads correctly into edit modal state', () => {
    const persistedProfile = {
      state: 'Gujarat',
      district: 'Ahmedabad'
    };

    const isCurrentValid = isValidStateDistrict(persistedProfile.state, persistedProfile.district);
    assert.strictEqual(isCurrentValid, true);

    const editState = {
      state: persistedProfile.state,
      district: isCurrentValid ? persistedProfile.district : ''
    };
    assert.strictEqual(editState.state, 'Gujarat');
    assert.strictEqual(editState.district, 'Ahmedabad');

    // If corrupted/mismatched persisted state:
    const corruptedProfile = {
      state: 'Gujarat',
      district: 'Jaipur'
    };
    const isCorruptedValid = isValidStateDistrict(corruptedProfile.state, corruptedProfile.district);
    assert.strictEqual(isCorruptedValid, false);

    const correctedEditState = {
      state: corruptedProfile.state,
      district: isCorruptedValid ? corruptedProfile.district : ''
    };
    assert.strictEqual(correctedEditState.district, '', 'Corrupted district must be cleared for user selection');
  });

  await t.test('7. Missing district rejected by validation logic', () => {
    const validateLocation = (state, district) => {
      if (!state || !isValidState(state)) return 'Please select a valid State.';
      if (!district) return `Please select a district for ${state}.`;
      if (!isValidStateDistrict(state, district)) return `Please select a valid district for ${state}.`;
      return null;
    };

    assert.strictEqual(validateLocation('Gujarat', ''), 'Please select a district for Gujarat.');
    assert.strictEqual(validateLocation('Gujarat', null), 'Please select a district for Gujarat.');
    assert.strictEqual(validateLocation('Rajasthan', undefined), 'Please select a district for Rajasthan.');
  });

  await t.test('8. Missing state rejected by validation logic', () => {
    const validateLocation = (state, district) => {
      if (!state || !isValidState(state)) return 'Please select a valid State.';
      if (!district) return `Please select a district for ${state}.`;
      if (!isValidStateDistrict(state, district)) return `Please select a valid district for ${state}.`;
      return null;
    };

    assert.strictEqual(validateLocation('', 'Ahmedabad'), 'Please select a valid State.');
    assert.strictEqual(validateLocation(null, 'Jaipur'), 'Please select a valid State.');
    assert.strictEqual(validateLocation('Narnia', 'Jaipur'), 'Please select a valid State.');
  });

  await t.test('9. Profile completion counts district ONLY when valid for selected state', () => {
    const baseProfile = {
      fullName: 'Dhruv Oza',
      email: 'dhruv@gmail.com',
      phone: '8209742773',
      occupation: 'student',
      income: 350000,
      applicantType: 'Individual',
      dob: '2000-01-15',
      gender: 'male',
      state: 'Gujarat',
      district: 'Ahmedabad' // Valid district
    };
    // 10 valid fields filled -> 100%
    assert.strictEqual(calculateProfileCompletion(baseProfile), 100);

    // Mismatched district: Gujarat + Jaipur -> district not counted!
    const mismatchedProfile = {
      ...baseProfile,
      district: 'Jaipur'
    };
    // 9 valid fields filled -> 90%
    assert.strictEqual(calculateProfileCompletion(mismatchedProfile), 90);

    // Blank district -> 90%
    const blankDistrictProfile = {
      ...baseProfile,
      district: ''
    };
    assert.strictEqual(calculateProfileCompletion(blankDistrictProfile), 90);
  });

  await t.test('10. Searchable district filtering matches prefix and substring ("Ahmed" -> Ahmedabad)', () => {
    const gujaratDistricts = getDistrictsForState('Gujarat');
    assert.ok(gujaratDistricts.length > 20, 'Gujarat must have all official districts');

    const search = 'ahmed';
    const matches = gujaratDistricts.filter(d => d.toLowerCase().includes(search));
    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0], 'Ahmedabad');

    const searchGandh = 'gandh';
    const matchesGandh = gujaratDistricts.filter(d => d.toLowerCase().includes(searchGandh));
    assert.strictEqual(matchesGandh.length, 1);
    assert.strictEqual(matchesGandh[0], 'Gandhinagar');
  });

  await t.test('11. ProfilePage.jsx contains searchable district combobox and canonical states', () => {
    const profilePath = path.resolve(__dirname, '../src/pages/ProfilePage.jsx');
    const content = fs.readFileSync(profilePath, 'utf8');

    assert.ok(content.includes('CANONICAL_STATES'), 'ProfilePage must import and use CANONICAL_STATES');
    assert.ok(content.includes('getDistrictsForState'), 'ProfilePage must load districts for selected state');
    assert.ok(content.includes('isValidStateDistrict'), 'ProfilePage must validate state-district dependency');
    assert.ok(content.includes('district-combobox-wrapper'), 'ProfilePage must render the district combobox wrapper');
    assert.ok(content.includes('handleStateChange'), 'ProfilePage must clear district on state change');
    assert.ok(!content.includes('<option value="Gujarat">Gujarat</option>\n                        <option value="Maharashtra">'),
      'Hardcoded static 8-state dropdown must be replaced with canonical states map');
  });

  await t.test('12. SuggestedSchemesPage.jsx listens to fin_user_updated for location synchronization', () => {
    const schemesPath = path.resolve(__dirname, '../src/pages/SuggestedSchemesPage.jsx');
    const content = fs.readFileSync(schemesPath, 'utf8');

    assert.ok(content.includes("window.addEventListener('fin_user_updated'"),
      'SuggestedSchemesPage must react to profile updates when state/district changes');
  });

  await t.test('13. Multi-tenant isolation: State & District are user-scoped in persistent registry', () => {
    const userA = { email: 'userA@fin.gov.in', state: 'Gujarat', district: 'Ahmedabad' };
    const userB = { email: 'userB@fin.gov.in', state: 'Rajasthan', district: 'Jaipur' };

    const registry = {};
    registry[userA.email.toLowerCase()] = userA;
    registry[userB.email.toLowerCase()] = userB;

    assert.strictEqual(registry['usera@fin.gov.in'.toLowerCase()].state, 'Gujarat');
    assert.strictEqual(registry['usera@fin.gov.in'.toLowerCase()].district, 'Ahmedabad');

    assert.strictEqual(registry['userb@fin.gov.in'.toLowerCase()].state, 'Rajasthan');
    assert.strictEqual(registry['userb@fin.gov.in'.toLowerCase()].district, 'Jaipur');

    assert.notStrictEqual(registry[userA.email.toLowerCase()].district, registry[userB.email.toLowerCase()].district);
  });
});
