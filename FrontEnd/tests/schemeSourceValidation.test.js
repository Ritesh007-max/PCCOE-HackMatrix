import test from 'node:test';
import assert from 'node:assert/strict';

import { validateOfficialUrl, TRUSTED_GOV_DOMAINS, UNTRUSTED_DOMAIN_PATTERNS } from '../src/utils/schemeDetailsHelpers.js';

test('FIN — Official Source URL Validation & Security Rules Suite', async (t) => {
  await t.test('1. Validates genuine Indian government portals with HTTPS/HTTP', () => {
    assert.strictEqual(
      validateOfficialUrl('https://pmkisan.gov.in'),
      'https://pmkisan.gov.in'
    );
    assert.strictEqual(
      validateOfficialUrl('https://www.myscheme.gov.in/schemes/108easuk'),
      'https://www.myscheme.gov.in/schemes/108easuk'
    );
    assert.strictEqual(
      validateOfficialUrl('https://digitalgujarat.gov.in/Citizen/CitizenService.aspx'),
      'https://digitalgujarat.gov.in/Citizen/CitizenService.aspx'
    );
    assert.strictEqual(
      validateOfficialUrl('https://scholarships.gov.in'),
      'https://scholarships.gov.in'
    );
    assert.strictEqual(
      validateOfficialUrl('http://swayam.gov.in'),
      'http://swayam.gov.in'
    );
  });

  await t.test('2. Rejects malicious protocols (javascript:, data:, file:)', () => {
    assert.strictEqual(validateOfficialUrl('javascript:alert("pwned")'), null);
    assert.strictEqual(validateOfficialUrl('data:text/html,<script>alert(1)</script>'), null);
    assert.strictEqual(validateOfficialUrl('file:///etc/passwd'), null);
    assert.strictEqual(validateOfficialUrl('ftp://ftp.gov.in'), null);
  });

  await t.test('3. Rejects search engines and lead-generation domains', () => {
    assert.strictEqual(validateOfficialUrl('https://www.google.com/search?q=pmegp'), null);
    assert.strictEqual(validateOfficialUrl('https://bing.com/search?q=mudra'), null);
    assert.strictEqual(validateOfficialUrl('https://cleartax.in/s/pmegp-scheme'), null);
    assert.strictEqual(validateOfficialUrl('https://bankbazaar.com/mudra-loan.html'), null);
    assert.strictEqual(validateOfficialUrl('https://sarkariyojana.com/pm-kisan'), null);
  });

  await t.test('4. Rejects blogs, ad networks, and commercial websites', () => {
    assert.strictEqual(validateOfficialUrl('https://schemeblog.wordpress.com'), null);
    assert.strictEqual(validateOfficialUrl('https://yojana-news.blogspot.com'), null);
    assert.strictEqual(validateOfficialUrl('https://medium.com/@author/scheme-details'), null);
    assert.strictEqual(validateOfficialUrl('https://timesofindia.indiatimes.com/article.cms'), null);
  });

  await t.test('5. Handles null, empty, undefined, and malformed inputs gracefully without throwing', () => {
    assert.strictEqual(validateOfficialUrl(null), null);
    assert.strictEqual(validateOfficialUrl(undefined), null);
    assert.strictEqual(validateOfficialUrl(''), null);
    assert.strictEqual(validateOfficialUrl('   '), null);
    assert.strictEqual(validateOfficialUrl('htp:/bad-url'), null);
    assert.strictEqual(validateOfficialUrl(12345), null);
    assert.strictEqual(validateOfficialUrl({}), null);
  });
});
