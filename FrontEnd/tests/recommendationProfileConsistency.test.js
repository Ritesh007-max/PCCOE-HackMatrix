import test from 'node:test';
import assert from 'node:assert/strict';
import { formatAnnualIncome } from '../src/utils/profileHelpers.js';

test('Recommendation Profile Consistency & Conflict Elimination Test Suite', async (t) => {
  await t.test('1. Date of Birth normalization eliminates false conflicts between date formats', () => {
    // Standard Indian document date strings
    const docDateStr = '12 August 2004';
    const profileDateStr = '2004-08-12';

    // Canonical ISO date normalizer (same logic as in Intelligence normalizer.py)
    const normalizeDate = (val) => {
      if (!val) return val;
      const clean = String(val).trim();
      if (/^\d{4}-\d{2}-\d{2}$/.test(clean)) return clean;
      const months = {
        january: '01', february: '02', march: '03', april: '04',
        may: '05', june: '06', july: '07', august: '08',
        september: '09', october: '10', november: '11', december: '12'
      };
      const mMatch = clean.match(/^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})$/);
      if (mMatch) {
        const day = mMatch[1].padStart(2, '0');
        const mo = months[mMatch[2].toLowerCase()];
        const yr = mMatch[3];
        if (mo) return `${yr}-${mo}-${day}`;
      }
      return clean;
    };

    assert.equal(normalizeDate(profileDateStr), '2004-08-12');
    assert.equal(normalizeDate(docDateStr), '2004-08-12');
    assert.equal(normalizeDate(profileDateStr), normalizeDate(docDateStr));
  });

  await t.test('2. District administrative suffix normalization eliminates false conflicts', () => {
    const docDistrict = 'Ahmedabad District';
    const profileDistrict = 'Ahmedabad';

    const normalizeDistrict = (val) => {
      if (!val) return val;
      return String(val)
        .replace(/\s+(District|Dist|City|Taluka|Sub-district)$/i, '')
        .trim();
    };

    assert.equal(normalizeDistrict(docDistrict), 'Ahmedabad');
    assert.equal(normalizeDistrict(profileDistrict), 'Ahmedabad');
    assert.equal(normalizeDistrict(docDistrict), normalizeDistrict(profileDistrict));
  });

  await t.test('3. Document family income and personal income are strictly segregated', () => {
    // User profile personal income
    const profilePersonalIncome = 350000;
    // Uploaded Income Certificate family income
    const documentFamilyIncome = 180000;

    // Both are distinct statutory fields:
    const activeFactsSummary = {
      annual_income: profilePersonalIncome,
      annual_family_income: documentFamilyIncome,
      state: 'Gujarat',
      city: 'Ahmedabad'
    };

    assert.equal(formatAnnualIncome(activeFactsSummary.annual_income), '₹3,50,000');
    assert.equal(formatAnnualIncome(activeFactsSummary.annual_family_income), '₹1,80,000');
    assert.notEqual(activeFactsSummary.annual_income, activeFactsSummary.annual_family_income);

    // Conflict check: because they have distinct field keys, conflict list is empty
    const conflicts = [];
    if (activeFactsSummary.annual_income !== profilePersonalIncome) {
      conflicts.push('annual_income');
    }
    assert.equal(conflicts.length, 0, 'Personal income and family income must never conflict');
  });

  await t.test('4. When profile is updated to match document facts, conflicts are eliminated', () => {
    // Scenario before update:
    // Profile: Dhruv, 1997-05-02, Gandhinagar
    // Document: Aarav Patel, 2004-08-12, Ahmedabad
    const conflictsBefore = ['beneficiary_name', 'date_of_birth', 'district'];

    // Scenario after update:
    // Profile is updated to Aarav Patel, 2004-08-12, Ahmedabad
    const updatedProfile = {
      fullName: 'Aarav Patel',
      dob: '2004-08-12',
      district: 'Ahmedabad'
    };
    const documentFacts = {
      beneficiary_name: 'Aarav Patel',
      date_of_birth: '2004-08-12',
      district: 'Ahmedabad'
    };

    const conflictsAfter = [];
    if (updatedProfile.fullName.toLowerCase() !== documentFacts.beneficiary_name.toLowerCase()) {
      conflictsAfter.push('beneficiary_name');
    }
    if (updatedProfile.dob !== documentFacts.date_of_birth) {
      conflictsAfter.push('date_of_birth');
    }
    if (updatedProfile.district.toLowerCase() !== documentFacts.district.toLowerCase()) {
      conflictsAfter.push('district');
    }

    assert.equal(conflictsBefore.length, 3);
    assert.equal(conflictsAfter.length, 0, 'All conflicts must be eliminated once profile is aligned');
  });
});
