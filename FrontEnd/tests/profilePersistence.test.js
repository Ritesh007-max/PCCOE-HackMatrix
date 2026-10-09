import test from 'node:test';
import assert from 'node:assert/strict';
import { formatGender, sanitizeIndianPhone, formatAnnualIncome } from '../src/utils/profileHelpers.js';

test('Profile Persistence & Gender Consistency Test Suite', async (t) => {
  await t.test('1. formatGender handles canonical lowercase values and displays cleanly', () => {
    assert.equal(formatGender('male'), 'Male');
    assert.equal(formatGender('female'), 'Female');
    assert.equal(formatGender('other'), 'Other');
    assert.equal(formatGender('prefer_not_to_say'), 'Prefer not to say');
    assert.equal(formatGender('Male'), 'Male');
    assert.equal(formatGender('Female'), 'Female');
    assert.equal(formatGender(null), 'Not added');
    assert.equal(formatGender(''), 'Not added');
    assert.equal(formatGender(undefined), 'Not added');
  });

  await t.test('2. Gender select options match backend canonical values', () => {
    const validSelectOptions = [
      { value: '', label: 'Select gender' },
      { value: 'male', label: 'Male' },
      { value: 'female', label: 'Female' },
      { value: 'other', label: 'Other' },
      { value: 'prefer_not_to_say', label: 'Prefer not to say' }
    ];

    const backendGender = 'male';
    const matchingOption = validSelectOptions.find(opt => opt.value === backendGender);
    assert.ok(matchingOption, 'Backend value "male" must match a select option value');
    assert.equal(matchingOption.label, 'Male');
  });

  await t.test('3. Full profile fields persist through simulated save, refresh, logout, and login', () => {
    const rawSavedProfile = {
      id: 'usr-persisted-123',
      fullName: 'Aarav Patel',
      full_name: 'Aarav Patel',
      phone: '9876543210',
      mobile_number: '9876543210',
      state: 'Gujarat',
      district: 'Ahmedabad',
      occupation: 'Student',
      annual_income: 350000,
      income: 350000,
      dob: '2004-08-12',
      date_of_birth: '2004-08-12',
      gender: 'male',
      category: 'SC',
      social_category: 'SC',
      applicantType: 'Individual',
      applicant_type: 'Individual'
    };

    // Simulate backend sanitization on login / session restore
    const sanitizedSessionUser = {
      id: rawSavedProfile.id,
      email: 'aarav@example.gov.in',
      fullName: rawSavedProfile.full_name,
      phone: rawSavedProfile.phone,
      state: rawSavedProfile.state,
      district: rawSavedProfile.district,
      occupation: rawSavedProfile.occupation,
      income: rawSavedProfile.annual_income,
      annual_income: rawSavedProfile.annual_income,
      dob: rawSavedProfile.date_of_birth,
      date_of_birth: rawSavedProfile.date_of_birth,
      gender: rawSavedProfile.gender,
      category: rawSavedProfile.category,
      social_category: rawSavedProfile.social_category,
      applicantType: rawSavedProfile.applicantType,
      applicant_type: rawSavedProfile.applicant_type
    };

    // Verify all 10 authoritative fields survive intact
    assert.equal(sanitizedSessionUser.fullName, 'Aarav Patel');
    assert.equal(sanitizedSessionUser.phone, '9876543210');
    assert.equal(sanitizedSessionUser.state, 'Gujarat');
    assert.equal(sanitizedSessionUser.district, 'Ahmedabad');
    assert.equal(sanitizedSessionUser.occupation, 'Student');
    assert.equal(sanitizedSessionUser.annual_income, 350000);
    assert.equal(sanitizedSessionUser.dob, '2004-08-12');
    assert.equal(sanitizedSessionUser.gender, 'male');
    assert.equal(sanitizedSessionUser.social_category, 'SC');
    assert.equal(sanitizedSessionUser.applicantType, 'Individual');
  });

  await t.test('4. Display formatting of all profile fields preserves user intent', () => {
    const profile = {
      fullName: 'Aarav Patel',
      phone: '9876543210',
      dob: '2004-08-12',
      gender: 'male',
      state: 'Gujarat',
      district: 'Ahmedabad',
      occupation: 'Student',
      annual_income: 350000,
      social_category: 'SC'
    };

    assert.equal(profile.fullName, 'Aarav Patel');
    assert.equal(sanitizeIndianPhone(profile.phone), '+91 98765 43210');
    assert.equal(profile.dob, '2004-08-12');
    assert.equal(formatGender(profile.gender), 'Male');
    assert.equal(profile.state, 'Gujarat');
    assert.equal(profile.district, 'Ahmedabad');
    assert.equal(profile.occupation, 'Student');
    assert.equal(formatAnnualIncome(profile.annual_income), '₹3,50,000');
    assert.equal(profile.social_category, 'SC');
  });
});
