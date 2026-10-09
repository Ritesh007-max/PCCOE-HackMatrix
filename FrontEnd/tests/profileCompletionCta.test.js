/**
 * FIN — Profile Completion CTA & Location/Income Details Logic Test Suite
 *
 * Covers all requirements from FIN — PROFILE COMPLETION CTA AUDIT:
 * 1. Gujarat + Gandhinagar + annual_income 350000 => CTA hidden
 * 2. State missing => CTA visible
 * 3. District missing => CTA visible
 * 4. annual_income missing => CTA visible
 * 5. annual_income = 0 => CTA hidden
 * 6. annual_income = 350000 => CTA hidden
 * 7. income_range populated but annual_income missing => CTA visible
 * 8. annual_income populated but income_range empty => CTA hidden
 * 9. Changing district updates CTA state
 * 10. Changing income updates CTA state
 * 11. Profile Completion 100% cannot coexist with the CTA being shown when all required recommendation fields are complete
 * 12. Profile save + existing fin_user_updated/storage synchronization updates CTA without page reload
 */

import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  isLocationAndIncomeComplete,
  isValidNumericIncome,
  calculateProfileCompletion,
  formatAnnualIncome,
  mapIncomeToRange,
} from '../src/utils/profileHelpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const profilePagePath = path.resolve(__dirname, '../src/pages/ProfilePage.jsx');
const profilePageContent = fs.readFileSync(profilePagePath, 'utf8');

test('FIN — Profile Completion CTA & Location/Income Details Suite', async (t) => {
  // 1. Gujarat + Gandhinagar + annual_income 350000 => CTA hidden
  await t.test('1. Gujarat + Gandhinagar + annual_income 350000 => CTA hidden', () => {
    const profile = {
      state: 'Gujarat',
      district: 'Gandhinagar',
      annual_income: 350000,
    };
    assert.strictEqual(isLocationAndIncomeComplete(profile), true, 'Complete profile must hide CTA');
  });

  // 2. State missing => CTA visible
  await t.test('2. State missing => CTA visible', () => {
    const emptyState = { state: '', district: 'Gandhinagar', annual_income: 350000 };
    const nullState = { state: null, district: 'Gandhinagar', annual_income: 350000 };
    const notAddedState = { state: 'Not added', district: 'Gandhinagar', annual_income: 350000 };

    assert.strictEqual(isLocationAndIncomeComplete(emptyState), false, 'Empty state must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(nullState), false, 'Null state must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(notAddedState), false, 'Not added state must show CTA');
  });

  // 3. District missing => CTA visible
  await t.test('3. District missing => CTA visible', () => {
    const emptyDistrict = { state: 'Gujarat', district: '', annual_income: 350000 };
    const nullDistrict = { state: 'Gujarat', district: null, annual_income: 350000 };
    const notAddedDistrict = { state: 'Gujarat', district: 'Not added', annual_income: 350000 };

    assert.strictEqual(isLocationAndIncomeComplete(emptyDistrict), false, 'Empty district must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(nullDistrict), false, 'Null district must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(notAddedDistrict), false, 'Not added district must show CTA');
  });

  // 4. annual_income missing => CTA visible
  await t.test('4. annual_income missing => CTA visible', () => {
    const nullIncome = { state: 'Gujarat', district: 'Gandhinagar', annual_income: null };
    const undefinedIncome = { state: 'Gujarat', district: 'Gandhinagar', annual_income: undefined };
    const emptyStrIncome = { state: 'Gujarat', district: 'Gandhinagar', annual_income: '' };
    const nanIncome = { state: 'Gujarat', district: 'Gandhinagar', annual_income: NaN };

    assert.strictEqual(isLocationAndIncomeComplete(nullIncome), false, 'Null income must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(undefinedIncome), false, 'Undefined income must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(emptyStrIncome), false, 'Empty string income must show CTA');
    assert.strictEqual(isLocationAndIncomeComplete(nanIncome), false, 'NaN income must show CTA');
  });

  // 5. annual_income = 0 => CTA hidden
  await t.test('5. annual_income = 0 => CTA hidden (zero is valid numeric income)', () => {
    const zeroNum = { state: 'Gujarat', district: 'Gandhinagar', annual_income: 0 };
    const zeroStr = { state: 'Gujarat', district: 'Gandhinagar', annual_income: '0' };

    assert.strictEqual(isValidNumericIncome(0), true, '0 must be valid numeric income');
    assert.strictEqual(isValidNumericIncome('0'), true, '"0" must be valid numeric income');
    assert.strictEqual(isLocationAndIncomeComplete(zeroNum), true, 'Income 0 must hide CTA');
    assert.strictEqual(isLocationAndIncomeComplete(zeroStr), true, 'Income "0" must hide CTA');
  });

  // 6. annual_income = 350000 => CTA hidden
  await t.test('6. annual_income = 350000 => CTA hidden', () => {
    const income350k = { state: 'Gujarat', district: 'Gandhinagar', annual_income: 350000 };
    assert.strictEqual(isValidNumericIncome(350000), true);
    assert.strictEqual(isLocationAndIncomeComplete(income350k), true, 'Income 350000 must hide CTA');
  });

  // 7. income_range populated but annual_income missing => CTA visible
  await t.test('7. income_range populated but annual_income missing => CTA visible', () => {
    const profileWithRangeOnly = {
      state: 'Gujarat',
      district: 'Gandhinagar',
      income_range: '₹2.5 Lakhs - ₹5 Lakhs',
      annual_income: null,
    };
    assert.strictEqual(isValidNumericIncome(profileWithRangeOnly.income_range), false, 'income_range is not numeric');
    assert.strictEqual(
      isLocationAndIncomeComplete(profileWithRangeOnly),
      false,
      'income_range alone without numeric annual_income must show CTA'
    );
  });

  // 8. annual_income populated but income_range empty => CTA hidden
  await t.test('8. annual_income populated but income_range empty => CTA hidden', () => {
    const profileWithNumericOnly = {
      state: 'Gujarat',
      district: 'Gandhinagar',
      annual_income: 350000,
      income_range: '',
    };
    assert.strictEqual(
      isLocationAndIncomeComplete(profileWithNumericOnly),
      true,
      'Numeric annual_income satisfies completion even if income_range is blank'
    );
  });

  // 9. Changing district updates CTA state
  await t.test('9. Changing district updates CTA state', () => {
    const profile = { state: 'Gujarat', district: 'Gandhinagar', annual_income: 350000 };
    assert.strictEqual(isLocationAndIncomeComplete(profile), true, 'Initial state complete');

    // Cleared district
    const districtCleared = { ...profile, district: '' };
    assert.strictEqual(isLocationAndIncomeComplete(districtCleared), false, 'Cleared district shows CTA');

    // Updated to Ahmedabad
    const districtUpdated = { ...profile, district: 'Ahmedabad' };
    assert.strictEqual(isLocationAndIncomeComplete(districtUpdated), true, 'Updated district hides CTA');

    // Incompatible district for Gujarat (e.g. Jaipur)
    const incompatibleDistrict = { ...profile, district: 'Jaipur' };
    assert.strictEqual(isLocationAndIncomeComplete(incompatibleDistrict), false, 'Incompatible district shows CTA');
  });

  // 10. Changing income updates CTA state
  await t.test('10. Changing income updates CTA state', () => {
    const profile = { state: 'Gujarat', district: 'Gandhinagar', annual_income: 350000 };
    assert.strictEqual(isLocationAndIncomeComplete(profile), true);

    // Remove income
    const incomeRemoved = { ...profile, annual_income: null };
    assert.strictEqual(isLocationAndIncomeComplete(incomeRemoved), false, 'Removed income shows CTA');

    // Restore income to 350000
    const incomeRestored = { ...profile, annual_income: 350000 };
    assert.strictEqual(isLocationAndIncomeComplete(incomeRestored), true, 'Restored income hides CTA');

    // Restore income to 0
    const incomeZero = { ...profile, annual_income: 0 };
    assert.strictEqual(isLocationAndIncomeComplete(incomeZero), true, 'Income = 0 hides CTA');
  });

  // 11. Profile Completion 100% cannot coexist with the CTA being shown when all required recommendation fields are complete
  await t.test('11. Profile Completion 100% cannot coexist with CTA shown when required fields are complete', () => {
    const completeProfile = {
      fullName: 'Dhruv',
      email: 'dhruv@gmail.com',
      phone: '8209742773',
      state: 'Gujarat',
      district: 'Gandhinagar',
      occupation: 'Student',
      applicantType: 'Family / Household',
      annual_income: 350000,
      income: 350000,
      dob: '1997-05-02',
      gender: 'Male',
    };

    const completion = calculateProfileCompletion(completeProfile);
    const isComplete = isLocationAndIncomeComplete(completeProfile);

    assert.strictEqual(completion, 100, 'Profile completion is 100%');
    assert.strictEqual(isComplete, true, 'Location and income are complete');
    // If completion is 100%, CTA condition MUST be complete (hidden)
    assert.strictEqual(!isComplete, false, 'CTA must NOT be shown when profile is 100% complete');
  });

  // 12. Profile save + existing fin_user_updated/storage synchronization updates CTA without page reload
  await t.test('12. Profile save + existing fin_user_updated/storage synchronization updates CTA without page reload', () => {
    // Verify ProfilePage listens to fin_user_updated and storage
    assert.ok(
      profilePageContent.includes("window.addEventListener('fin_user_updated'"),
      'ProfilePage must listen to fin_user_updated'
    );
    assert.ok(
      profilePageContent.includes("window.addEventListener('storage'"),
      'ProfilePage must listen to storage'
    );
    // Verify ProfilePage conditionally renders callout banner using isLocationAndIncomeComplete
    assert.ok(
      profilePageContent.includes('!isLocationAndIncomeComplete(profileData)'),
      'ProfilePage must conditionally render callout using !isLocationAndIncomeComplete'
    );
    // Verify dispatch on save
    assert.ok(
      profilePageContent.includes("window.dispatchEvent(new CustomEvent('fin_user_updated'"),
      'handleSaveProfile must dispatch fin_user_updated'
    );
  });
});
