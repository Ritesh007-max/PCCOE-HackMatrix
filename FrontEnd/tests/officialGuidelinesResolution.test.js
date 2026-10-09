import test from 'node:test';
import assert from 'node:assert/strict';
import { getSchemePortalDetails } from '../src/utils/schemeDetailsHelpers.js';

test('Official Guidelines Resolution & Verification Test Suite', async (t) => {
  await t.test('1. Scheme with verified PDF resolves to PDF guidelines type', () => {
    const schemeWithPdf = {
      id: 'scheme-pdf-1',
      title: 'Pradhan Mantri Awas Yojana',
      source_url: 'https://pmaymis.gov.in/PDF/PMAY_Guidelines.pdf',
      references: [
        { title: 'Guidelines', url: 'https://pmaymis.gov.in/PDF/PMAY_Guidelines.pdf' }
      ]
    };

    const details = getSchemePortalDetails(schemeWithPdf);
    assert.equal(details.isPdf, true);
    assert.equal(details.guidelinesType, 'PDF');
    assert.ok(details.guidelinesUrl.toLowerCase().endsWith('.pdf'));
    assert.ok(details.guidelinesTitle.includes('(PDF)'));
  });

  await t.test('2. Scheme with official rules webpage resolves to WEBPAGE guidelines type', () => {
    const schemeWithWebpage = {
      id: 'scheme-web-1',
      title: 'National Apprenticeship Promotion Scheme',
      source_url: 'https://www.apprenticeshipindia.gov.in/rules-and-regulations',
      references: [
        { title: 'Scheme Rules', url: 'https://www.apprenticeshipindia.gov.in/rules-and-regulations' }
      ]
    };

    const details = getSchemePortalDetails(schemeWithWebpage);
    assert.equal(details.isPdf, false);
    assert.equal(details.guidelinesType, 'WEBPAGE');
    assert.ok(details.officialRulesPageUrl);
    assert.ok(details.guidelinesTitle.includes('Official Guidelines & Rules'));
  });

  await t.test('3. Scheme with no published guidelines resolves to UNAVAILABLE with zero fabricated URLs', () => {
    const schemeWithoutGuidelines = {
      id: 'scheme-none-1',
      title: 'General Welfare Program',
      source_url: null,
      references: []
    };

    const details = getSchemePortalDetails(schemeWithoutGuidelines);
    assert.equal(details.isPdf, false);
    assert.equal(details.guidelinesUrl, null);
    assert.equal(details.officialRulesPageUrl, null);
    assert.equal(details.guidelinesType, 'UNAVAILABLE');
    assert.equal(details.guidelinesTitle, 'Official Scheme Guidelines');
  });

  await t.test('4. Aggregator and mock URLs are rejected and never presented as official documents', () => {
    const schemeWithAggregator = {
      id: 'scheme-agg-1',
      title: 'Scholarship Scheme',
      guidelines_url: 'https://www.myscheme.gov.in/schemes/scholarship',
      references: [
        'https://fake-government-portal.example.org/fake.pdf'
      ]
    };

    const details = getSchemePortalDetails(schemeWithAggregator);
    // myscheme aggregator and invalid domains must not be accepted as official guidelines
    assert.equal(details.isPdf, false);
    assert.equal(details.guidelinesUrl, null);
    assert.equal(details.guidelinesType, 'UNAVAILABLE');
  });
});
