import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const footerPath = path.join(__dirname, '..', 'src', 'components', 'layout', 'Footer.jsx');
const footerCssPath = path.join(__dirname, '..', 'src', 'styles', 'footer.css');
const appRoutesPath = path.join(__dirname, '..', 'src', 'routes', 'AppRoutes.jsx');

test('FIN — Comprehensive Footer Navigation & Interaction Audit Suite', async (t) => {
  const footerContent = fs.readFileSync(footerPath, 'utf8');
  const footerCss = fs.readFileSync(footerCssPath, 'utf8');
  const appRoutesContent = fs.readFileSync(appRoutesPath, 'utf8');

  await t.test('1. Brand Logo: Fully functional navigation to /dashboard', () => {
    // Brand lockup must be wrapped in Link to /dashboard
    assert.match(
      footerContent,
      /<Link\s+to="\/dashboard"\s+className="footer-brand-link"/,
      'FIN brand lockup must be wrapped in <Link to="/dashboard">'
    );
    // CSS must support .footer-brand-link
    assert.ok(
      footerCss.includes('.footer-brand-link'),
      'footer.css must define styling for .footer-brand-link'
    );
  });

  await t.test('2. Explore Links: All 5 links navigate to registered routes', () => {
    const expectedExploreRoutes = [
      { label: 'Dashboard', route: '/dashboard' },
      { label: 'Discover Schemes', route: '/discover' },
      { label: 'Suggested Schemes', route: '/suggested-schemes' },
      { label: 'My Documents', route: '/documents' },
      { label: 'Applications', route: '/applications' }
    ];

    for (const item of expectedExploreRoutes) {
      const linkRegex = new RegExp(`<Link\\s+to="${item.route}"[^>]*>${item.label}<\\/Link>`);
      assert.match(
        footerContent,
        linkRegex,
        `Footer must contain <Link to="${item.route}">${item.label}</Link>`
      );
      // Route must exist in AppRoutes
      assert.ok(
        appRoutesContent.includes(`path="${item.route}"`),
        `Route ${item.route} must be registered in AppRoutes.jsx`
      );
    }
  });

  await t.test('3. Information Links: All modals and assistants trigger properly', () => {
    // About FIN
    assert.match(
      footerContent,
      /onClick=\{\(\)\s*=>\s*openModal\('about'\)\}[^>]*>\s*About FIN/,
      'About FIN must trigger openModal("about")'
    );
    // How It Works
    assert.match(
      footerContent,
      /onClick=\{\(\)\s*=>\s*openModal\('howItWorks'\)\}[^>]*>\s*How It Works/,
      'How It Works must trigger openModal("howItWorks")'
    );
    // Scheme Guidelines
    assert.match(
      footerContent,
      /onClick=\{\(\)\s*=>\s*openModal\('guidelines'\)\}[^>]*>\s*Scheme Guidelines/,
      'Scheme Guidelines must trigger openModal("guidelines")'
    );
    // Help & Support (AI Assistant)
    assert.match(
      footerContent,
      /onClick=\{handleOpenAssistant\}[^>]*>\s*Help & Support/,
      'Help & Support must trigger handleOpenAssistant'
    );
    // FAQs (opens faq modal)
    assert.match(
      footerContent,
      /onClick=\{\(\)\s*=>\s*openModal\('faq'\)\}[^>]*>\s*FAQs/,
      'FAQs must trigger openModal("faq")'
    );
    // Contact Us
    assert.match(
      footerContent,
      /onClick=\{\(\)\s*=>\s*openModal\('contact'\)\}[^>]*>\s*Contact Us/,
      'Contact Us must trigger openModal("contact")'
    );
  });

  await t.test('4. Legal Links: All 6 legal links open dedicated informative modals', () => {
    const legalItems = [
      { key: 'terms', label: 'Terms of Use' },
      { key: 'privacy', label: 'Privacy Policy' },
      { key: 'disclaimer', label: 'Disclaimer' },
      { key: 'accessibility', label: 'Accessibility' },
      { key: 'cookies', label: 'Cookie Policy' },
      { key: 'sitemap', label: 'Sitemap' }
    ];

    for (const item of legalItems) {
      const modalRegex = new RegExp(`onClick=\\{\\(\\)\\s*=>\\s*openModal\\('${item.key}'\\)\\}[^>]*>\\s*${item.label}`);
      assert.match(
        footerContent,
        modalRegex,
        `${item.label} must trigger openModal("${item.key}")`
      );
    }
  });

  await t.test('5. Social Media Icons: Official government & institutional handles', () => {
    // X (Twitter)
    assert.match(
      footerContent,
      /href="https:\/\/x\.com\/mygovindia"/,
      'X link must point to https://x.com/mygovindia'
    );
    // LinkedIn
    assert.match(
      footerContent,
      /href="https:\/\/www\.linkedin\.com\/company\/digital-india"/,
      'LinkedIn link must point to https://www.linkedin.com/company/digital-india'
    );
    // YouTube
    assert.match(
      footerContent,
      /href="https:\/\/www\.youtube\.com\/@MyGovIndia"/,
      'YouTube link must point to https://www.youtube.com/@MyGovIndia'
    );
    // Email
    assert.match(
      footerContent,
      /href="mailto:support@fin\.gov\.in"/,
      'Email link must point to mailto:support@fin.gov.in'
    );

    // External links must have target="_blank" and rel="noopener noreferrer"
    const externalLinks = [
      'https://x.com/mygovindia',
      'https://www.linkedin.com/company/digital-india',
      'https://www.youtube.com/@MyGovIndia'
    ];
    for (const url of externalLinks) {
      const targetRegex = new RegExp(`href="${url.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}"[\\s\\S]*?target="_blank"[\\s\\S]*?rel="noopener noreferrer"`);
      assert.match(
        footerContent,
        targetRegex,
        `External link ${url} must specify target="_blank" and rel="noopener noreferrer"`
      );
    }
  });

  await t.test('6. Contact & FAQ Modals: Actionable phone, email, and internal routes', () => {
    // Contact modal contains tel and mailto links
    assert.ok(
      footerContent.includes('href="tel:1800113464"'),
      'Contact modal must contain clickable toll-free tel link'
    );
    assert.ok(
      footerContent.includes('href="mailto:support@fin.gov.in"'),
      'Contact modal must contain clickable mailto link'
    );

    // FAQ modal contains active links to /documents and /applications
    assert.ok(
      footerContent.includes('to="/documents"'),
      'FAQ modal must link to /documents'
    );
    assert.ok(
      footerContent.includes('to="/applications"'),
      'FAQ modal must link to /applications'
    );

    // Modal body auto-closes on link click to allow smooth in-app navigation
    assert.ok(
      footerContent.includes("if (e.target.closest('a')) closeModal();"),
      'Modal body must close modal when an internal link is clicked'
    );
  });

  await t.test('7. Sitemap Modal: All routes are verified against AppRoutes', () => {
    const sitemapRoutes = [
      '/dashboard',
      '/discover',
      '/suggested-schemes',
      '/documents',
      '/applications',
      '/profile',
      '/signup',
      '/login'
    ];

    for (const route of sitemapRoutes) {
      assert.ok(
        footerContent.includes(`to="${route}"`),
        `Sitemap must include link to ${route}`
      );
      assert.ok(
        appRoutesContent.includes(`path="${route}"`),
        `Sitemap route ${route} must exist in AppRoutes.jsx`
      );
    }
  });

  await t.test('8. Zero dead links or "#" placeholders anywhere in Footer', () => {
    assert.doesNotMatch(
      footerContent,
      /href="#"/,
      'Footer must not contain any href="#" placeholders'
    );
    assert.doesNotMatch(
      footerContent,
      /to="#"/,
      'Footer must not contain any to="#" placeholders'
    );
  });
});
