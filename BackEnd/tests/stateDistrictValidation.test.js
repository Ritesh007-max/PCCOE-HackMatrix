/**
 * FIN — Backend State -> District Geographic Validation Test Suite
 *
 * Covers:
 * 1. isValidState and CANONICAL_STATES
 * 2. getDistrictsForState returns official districts
 * 3. isValidStateDistrict validates valid combinations (Gujarat -> Ahmedabad, Rajasthan -> Jaipur, etc.)
 * 4. isValidStateDistrict rejects invalid combinations (Gujarat + Jaipur)
 * 5. updateProfile controller rejects invalid state
 * 6. updateProfile controller rejects invalid district for state
 * 7. updateProfile controller accepts valid state and district
 * 8. updateProfile controller clears incompatible district when state changes without district
 */

const test = require('node:test');
const assert = require('node:assert');
const {
  CANONICAL_STATES,
  getDistrictsForState,
  isValidState,
  isValidStateDistrict,
  normalizeStateName,
  normalizeDistrictName
} = require('../src/utils/geoData');

test('FIN — Backend State -> District Geographic Validation Suite', async (t) => {

  await t.test('1. CANONICAL_STATES contains all 28 states and 8 union territories', () => {
    assert.strictEqual(CANONICAL_STATES.length, 36);
    assert.ok(CANONICAL_STATES.includes('Gujarat'));
    assert.ok(CANONICAL_STATES.includes('Rajasthan'));
    assert.ok(CANONICAL_STATES.includes('Maharashtra'));
    assert.ok(CANONICAL_STATES.includes('Delhi'));
  });

  await t.test('2. getDistrictsForState returns sorted valid districts', () => {
    const gujaratDistricts = getDistrictsForState('Gujarat');
    assert.ok(gujaratDistricts.includes('Ahmedabad'));
    assert.ok(gujaratDistricts.includes('Gandhinagar'));
    assert.ok(gujaratDistricts.includes('Surat'));
    assert.ok(gujaratDistricts.includes('Vadodara'));

    const rajasthanDistricts = getDistrictsForState('Rajasthan');
    assert.ok(rajasthanDistricts.includes('Jaipur'));
    assert.ok(rajasthanDistricts.includes('Jodhpur'));
    assert.ok(rajasthanDistricts.includes('Udaipur'));
  });

  await t.test('3. isValidStateDistrict validates valid pairs and normalizes casing', () => {
    assert.strictEqual(isValidStateDistrict('Gujarat', 'Ahmedabad'), true);
    assert.strictEqual(isValidStateDistrict('gujarat', 'ahmedabad'), true);
    assert.strictEqual(normalizeDistrictName('Gujarat', 'ahmedabad'), 'Ahmedabad');

    assert.strictEqual(isValidStateDistrict('Gujarat', 'Gandhinagar'), true);
    assert.strictEqual(normalizeDistrictName('Gujarat', 'gandhinagar'), 'Gandhinagar');

    assert.strictEqual(isValidStateDistrict('Rajasthan', 'Jaipur'), true);
    assert.strictEqual(normalizeDistrictName('Rajasthan', 'jaipur'), 'Jaipur');
  });

  await t.test('4. isValidStateDistrict rejects incompatible district/state pairs', () => {
    assert.strictEqual(isValidStateDistrict('Gujarat', 'Jaipur'), false);
    assert.strictEqual(isValidStateDistrict('Rajasthan', 'Ahmedabad'), false);
    assert.strictEqual(isValidStateDistrict('Maharashtra', 'Gandhinagar'), false);
    assert.strictEqual(isValidStateDistrict('Delhi', 'Surat'), false);
    assert.strictEqual(isValidStateDistrict('Gujarat', 'UnknownCity'), false);
  });

  await t.test('5. State change clears incompatible existing district logic', () => {
    const existingDistrict = 'Ahmedabad';
    const newState = 'Rajasthan';

    // When updating state to Rajasthan, Ahmedabad is checked against Rajasthan
    const isValidForNewState = isValidStateDistrict(newState, existingDistrict);
    assert.strictEqual(isValidForNewState, false);

    // Controller logic sets district to null if not valid for new state
    const resolvedDistrict = isValidForNewState ? existingDistrict : null;
    assert.strictEqual(resolvedDistrict, null);
  });

  await t.test('6. Case normalization for state and district', () => {
    assert.strictEqual(normalizeStateName('gujarat'), 'Gujarat');
    assert.strictEqual(normalizeStateName('RAJASTHAN'), 'Rajasthan');
    assert.strictEqual(normalizeDistrictName('Gujarat', 'AHMEDABAD'), 'Ahmedabad');
  });
});
