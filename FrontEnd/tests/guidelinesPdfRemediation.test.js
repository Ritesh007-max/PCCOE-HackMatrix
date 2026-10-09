import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  adaptSchemeDetails,
  getSchemePortalDetails,
  validateOfficialUrl
} from '../src/utils/schemeDetailsHelpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Guidelines PDF Action Remediation Test Suite', async (t) => {

  await t.test('1. validateOfficialUrl: strictly accepts trusted government domains and rejects untrusted or malicious URLs', () => {
    // Valid government and educational domains
    assert.strictEqual(
      validateOfficialUrl('https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf'),
      'https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf'
    );
    assert.strictEqual(
      validateOfficialUrl('https://kscste.kerala.gov.in/wp-content/uploads/2025/05/YIPB_guidelines.pdf'),
      'https://kscste.kerala.gov.in/wp-content/uploads/2025/05/YIPB_guidelines.pdf'
    );
    assert.strictEqual(
      validateOfficialUrl('https://msme.gov.in/sites/default/files/Revisedguidelines07.12.2023.pdf'),
      'https://msme.gov.in/sites/default/files/Revisedguidelines07.12.2023.pdf'
    );

    // Invalid / untrusted / non-http schemes rejected safely
    assert.strictEqual(validateOfficialUrl('javascript:alert(1)'), null);
    assert.strictEqual(validateOfficialUrl('data:text/html,<script>alert(1)</script>'), null);
    assert.strictEqual(validateOfficialUrl('https://cleartax.in/fake_guidelines.pdf'), null);
    assert.strictEqual(validateOfficialUrl('https://sarkariyojana.com/guidelines.pdf'), null);
    assert.strictEqual(validateOfficialUrl('https://google.com/search?q=pmkisan+guidelines'), null);
    assert.strictEqual(validateOfficialUrl(''), null);
    assert.strictEqual(validateOfficialUrl(null), null);
    assert.strictEqual(validateOfficialUrl(undefined), null);
  });

  await t.test('2. getSchemePortalDetails: derives verified guidelinesUrl from explicit fields or canonical references', () => {
    // Case A: From explicit guidelines_url
    const schemeWithExplicit = {
      title: 'PMEGP',
      guidelines_url: 'https://msme.gov.in/sites/default/files/Revisedguidelines07.12.2023.pdf'
    };
    const portalA = getSchemePortalDetails(schemeWithExplicit);
    assert.strictEqual(portalA.guidelinesUrl, 'https://msme.gov.in/sites/default/files/Revisedguidelines07.12.2023.pdf');

    // Case B: From canonical references
    const schemeWithRefs = {
      title: 'YIPB',
      references: [
        'https://keralabiotech.kerala.gov.in/?page_id=643',
        'https://kscste.kerala.gov.in/wp-content/uploads/2025/05/YIPB_guidelines.pdf'
      ]
    };
    const portalB = getSchemePortalDetails(schemeWithRefs);
    assert.strictEqual(portalB.guidelinesUrl, 'https://kscste.kerala.gov.in/wp-content/uploads/2025/05/YIPB_guidelines.pdf');

    // Case C: Aggregator (myscheme.gov.in) URLs are never returned as guidelines document
    const schemeWithAggregator = {
      title: 'Aggregator Scheme',
      source_url: 'https://myscheme.gov.in/schemes/xyz',
      references: ['https://myscheme.gov.in/schemes/xyz']
    };
    const portalC = getSchemePortalDetails(schemeWithAggregator);
    assert.strictEqual(portalC.guidelinesUrl, null);
  });

  await t.test('3. adaptSchemeDetails: preserves canonical guidelines and document URL fields', () => {
    const raw = {
      id: 'sch-doc-1',
      title: 'National Scholarship',
      guidelines_url: 'https://scholarships.gov.in/docs/guidelines.pdf',
      document_url: 'https://scholarships.gov.in/docs/annexure.pdf',
      pdf_url: 'https://scholarships.gov.in/docs/manual.pdf'
    };
    const adapted = adaptSchemeDetails(raw);
    assert.strictEqual(adapted.guidelines_url, 'https://scholarships.gov.in/docs/guidelines.pdf');
    assert.strictEqual(adapted.document_url, 'https://scholarships.gov.in/docs/annexure.pdf');
    assert.strictEqual(adapted.pdf_url, 'https://scholarships.gov.in/docs/manual.pdf');
  });

  await t.test('4. Missing or invalid guidelines URL yields null and displays honest unavailable status', () => {
    const schemeWithoutDoc = {
      title: 'Scheme Without Documents',
      source_url: 'https://myscheme.gov.in/schemes/sample'
    };
    const portal = getSchemePortalDetails(schemeWithoutDoc);
    assert.strictEqual(portal.guidelinesUrl, null);

    const schemeWithUntrusted = {
      title: 'Scheme With Phishing Doc',
      guidelines_url: 'https://untrusted-scam-blog.org/scheme.pdf'
    };
    const portalUntrusted = getSchemePortalDetails(schemeWithUntrusted);
    assert.strictEqual(portalUntrusted.guidelinesUrl, null);
  });

  await t.test('5. Guidelines Action Handler: opens valid URL with safe rel flags and sets genuine success feedback', () => {
    let openedUrl = null;
    let openedTarget = null;
    let openedFeatures = null;

    const mockWindow = {
      open: (url, target, features) => {
        openedUrl = url;
        openedTarget = target;
        openedFeatures = features;
        return { closed: false };
      },
      document: {}
    };

    let downloadSuccess = false;
    let downloadNotice = null;

    // Simulate handleDownloadGuidelines with a valid official URL
    const validUrl = 'https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf';
    const executeAction = (url) => {
      const verifiedUrl = validateOfficialUrl(url);
      if (!verifiedUrl) {
        downloadSuccess = false;
        downloadNotice = 'Official guidelines document link is not available in the current policy record.';
        return;
      }

      try {
        const win = mockWindow.open(verifiedUrl, '_blank', 'noopener,noreferrer');
        if (win === null && typeof mockWindow.document !== 'undefined') {
          downloadSuccess = false;
          downloadNotice = 'Pop-up was blocked by browser. Please allow pop-ups to open the official guidelines.';
          return;
        }
        downloadNotice = null;
        downloadSuccess = true;
      } catch (e) {
        downloadSuccess = false;
        downloadNotice = 'Unable to open official document link.';
      }
    };

    executeAction(validUrl);
    assert.strictEqual(openedUrl, 'https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf');
    assert.strictEqual(openedTarget, '_blank');
    assert.strictEqual(openedFeatures, 'noopener,noreferrer');
    assert.strictEqual(downloadSuccess, true, 'Genuine success toast must be emitted when URL opens');
    assert.strictEqual(downloadNotice, null);
  });

  await t.test('6. Guidelines Action Handler: missing URL rejects safely with honest notice and NO fake success toast', () => {
    let windowOpenCalled = false;
    const mockWindow = {
      open: () => {
        windowOpenCalled = true;
        return {};
      }
    };

    let downloadSuccess = false;
    let downloadNotice = null;

    const executeAction = (url) => {
      const verifiedUrl = validateOfficialUrl(url);
      if (!verifiedUrl) {
        downloadSuccess = false;
        downloadNotice = 'Official guidelines document link is not available in the current policy record.';
        return;
      }
      mockWindow.open(verifiedUrl, '_blank', 'noopener,noreferrer');
      downloadSuccess = true;
    };

    executeAction(null);
    assert.strictEqual(windowOpenCalled, false, 'window.open must not be called when URL is missing');
    assert.strictEqual(downloadSuccess, false, 'No fake success toast when URL is missing');
    assert.ok(downloadNotice && downloadNotice.includes('not available'), 'Must display honest unavailable notice');
  });

  await t.test('7. Guidelines Action Handler: invalid URL is safely rejected with NO fake success toast', () => {
    let windowOpenCalled = false;
    const mockWindow = {
      open: () => {
        windowOpenCalled = true;
        return {};
      }
    };

    let downloadSuccess = false;
    let downloadNotice = null;

    const executeAction = (url) => {
      const verifiedUrl = validateOfficialUrl(url);
      if (!verifiedUrl) {
        downloadSuccess = false;
        downloadNotice = 'Official guidelines document link is not available in the current policy record.';
        return;
      }
      mockWindow.open(verifiedUrl, '_blank', 'noopener,noreferrer');
      downloadSuccess = true;
    };

    executeAction('https://cleartax.in/fake_guidelines.pdf');
    assert.strictEqual(windowOpenCalled, false, 'window.open must not be called for untrusted domain');
    assert.strictEqual(downloadSuccess, false, 'No fake success toast for invalid URL');
    assert.ok(downloadNotice);
  });

  await t.test('8. Guidelines Action Handler: pop-up blocker suppression prevents fake success toast', () => {
    const mockWindowBlocked = {
      open: () => null, // Pop-up blocker returns null
      document: {}
    };

    let downloadSuccess = false;
    let downloadNotice = null;

    const executeAction = (url) => {
      const verifiedUrl = validateOfficialUrl(url);
      if (!verifiedUrl) {
        downloadSuccess = false;
        downloadNotice = 'Official guidelines document link is not available in the current policy record.';
        return;
      }

      try {
        const win = mockWindowBlocked.open(verifiedUrl, '_blank', 'noopener,noreferrer');
        if (win === null && typeof mockWindowBlocked.document !== 'undefined') {
          downloadSuccess = false;
          downloadNotice = 'Pop-up was blocked by browser. Please allow pop-ups to open the official guidelines.';
          return;
        }
        downloadNotice = null;
        downloadSuccess = true;
      } catch (e) {
        downloadSuccess = false;
        downloadNotice = 'Unable to open official document link.';
      }
    };

    executeAction('https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf');
    assert.strictEqual(downloadSuccess, false, 'Success toast must NOT be shown when pop-up is blocked');
    assert.ok(downloadNotice && downloadNotice.includes('Pop-up was blocked'), 'Pop-up blocked notice must be shown');
  });

  await t.test('9. Static code inspection of SchemeDetailsPage.jsx ensures UI truthfulness and integrity', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    // 1. Must import and use validateOfficialUrl
    assert.ok(content.includes('validateOfficialUrl'), 'Must import validateOfficialUrl');

    // 2. handleDownloadGuidelines must validate the URL before opening
    assert.ok(
      content.includes('const verifiedUrl = validateOfficialUrl(guidelineDocumentUrl);'),
      'Must re-validate guidelineDocumentUrl inside handleDownloadGuidelines'
    );

    // 3. No unconditional fake success toast
    assert.ok(
      !content.match(/handleDownloadGuidelines\s*=\s*\(\)\s*=>\s*\{\s*setDownloadSuccess\(true\)/),
      'Must not set downloadSuccess(true) unconditionally without verified execution'
    );

    // 4. Safe window.open with noopener,noreferrer
    assert.ok(
      content.includes("window.open(verifiedUrl, '_blank', 'noopener,noreferrer')"),
      'Must open verified URL with safe noopener,noreferrer'
    );

    // 5. Card 4 subtitle shows honest message when document is unavailable
    assert.ok(
      content.includes("guidelineDocumentUrl ? portalDetails.guidelinesTitle : 'Official document link not available in record'"),
      'Card 4 subtitle must indicate unavailable state when URL is missing'
    );

    // 6. Tab 5 displays honest unavailable state when guideline document is missing
    assert.ok(
      content.includes('Official guideline PDF is not indexed or available in the current policy record.'),
      'Tab 5 must provide honest unavailable state rather than omitting document source'
    );
  });
});
