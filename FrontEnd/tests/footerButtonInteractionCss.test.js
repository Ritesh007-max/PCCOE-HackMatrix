import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const footerCssPath = path.join(__dirname, '..', 'src', 'styles', 'footer.css');

test('FIN — Footer Button Interaction & Focus Styling Suite', async (t) => {
  const footerCss = fs.readFileSync(footerCssPath, 'utf8');

  await t.test('1. Footer links and buttons have clean focus reset for mouse clicks', () => {
    assert.ok(
      footerCss.includes('.footer-link:focus') && footerCss.includes('.footer-link-btn:focus'),
      'footer.css must define :focus for .footer-link and .footer-link-btn'
    );
    assert.ok(
      footerCss.includes('.footer-link:focus:not(:focus-visible)'),
      'footer.css must remove outline for mouse focus on .footer-link'
    );
  });

  await t.test('2. Footer links and buttons have accessible, subtle :focus-visible', () => {
    assert.ok(
      footerCss.includes('.footer-link:focus-visible') && footerCss.includes('.footer-link-btn:focus-visible'),
      'footer.css must define :focus-visible for keyboard navigation'
    );
    assert.ok(
      footerCss.includes('outline: 2px solid #005B50'),
      'footer.css must use clean brand outline for keyboard focus-visible'
    );
  });

  await t.test('3. Footer links and buttons have responsive, non-distorting :active states', () => {
    assert.ok(
      footerCss.includes('.footer-link:active') && footerCss.includes('.footer-link-btn:active'),
      'footer.css must define clean :active states for .footer-link and .footer-link-btn'
    );
    assert.ok(
      footerCss.includes('.footer-brand-link:active'),
      'footer.css must define clean :active state for .footer-brand-link'
    );
    assert.ok(
      footerCss.includes('.footer-social-btn:active'),
      'footer.css must define clean :active state for .footer-social-btn'
    );
  });

  await t.test('4. Modal buttons have clean focus and active states', () => {
    assert.ok(
      footerCss.includes('.footer-modal-close-btn:focus-visible'),
      'Close button must support accessible :focus-visible'
    );
    assert.ok(
      footerCss.includes('.footer-modal-btn-primary:focus-visible'),
      'Primary modal button must support accessible :focus-visible'
    );
  });

  await t.test('5. Focus styles do not propagate blur, filter, or distortions to parent containers', () => {
    assert.ok(
      footerCss.includes('.site-footer:focus-within') &&
      footerCss.includes('.footer-body-wrapper:focus-within') &&
      footerCss.includes('.footer-col:focus-within'),
      'Parent containers must explicitly guard against focus-within filter distortions'
    );
  });

  await t.test('6. Modal backdrop overlay is isolated and does not permanently distort underlying footer', () => {
    assert.ok(
      footerCss.includes('isolation: isolate'),
      'Modal backdrop must declare isolation: isolate to scope backdrop rendering'
    );
    assert.ok(
      footerCss.includes('contain: layout style'),
      'Modal backdrop must contain layout and style rendering'
    );
  });

  await t.test('7. No unintended :has() pseudo-class affecting footer ancestors', () => {
    assert.doesNotMatch(
      footerCss,
      /:has\(/,
      'footer.css must not use complex :has() rules that cause ancestor visual side effects'
    );
  });

  await t.test('8. Footer layout, height, and synchronized panorama remain 100% intact', () => {
    assert.ok(footerCss.includes('.site-footer'), 'site-footer class preserved');
    assert.ok(footerCss.includes('.footer-building-backdrop'), 'footer building backdrop preserved');
    assert.ok(footerCss.includes('.site-footer.is-synced'), 'synchronized footer panorama animation preserved');
    assert.ok(footerCss.includes('--fin-panorama-height'), 'panorama height token preserved');
    assert.ok(footerCss.includes('.footer-grid-5cols'), '5-column grid layout preserved');
  });

  await t.test('9. Modal backdrop renders via portal into document.body to uniformly blur sidebar and canvas', () => {
    const footerJsxPath = path.join(__dirname, '..', 'src', 'components', 'layout', 'Footer.jsx');
    const footerJsx = fs.readFileSync(footerJsxPath, 'utf8');
    assert.ok(
      footerJsx.includes("createPortal(") && footerJsx.includes("document.body"),
      'Footer.jsx must portal modal to document.body so backdrop covers sidebar'
    );
  });
});

