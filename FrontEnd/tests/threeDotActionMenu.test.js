import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { computeDropdownPosition } from '../src/utils/dropdownPositioning.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Three-Dot Action Menu Positioning and Interaction Suite', async (t) => {

  // =========================================================================
  // 1 & 2. OPENING & NON-CLIPPING VIA PORTAL / POSITIONING
  // =========================================================================

  await t.test('1. Dropdown opens for selected document and renders via portal into document.body', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Trigger button attaches document ID and tracks active menu
    assert.ok(jsxContent.includes('data-doc-menu-btn={doc.id}'), 'Trigger must have data-doc-menu-btn identifier');
    assert.ok(jsxContent.includes('aria-haspopup="menu"'), 'Trigger must have aria-haspopup menu');
    assert.ok(jsxContent.includes('aria-expanded={activeMenu?.id === doc.id}'), 'Trigger must reflect expanded state');

    // Dropdown is rendered via createPortal directly into document.body
    assert.ok(jsxContent.includes('createPortal('), 'Dropdown must be rendered via createPortal');
    assert.ok(jsxContent.includes('document.body'), 'Dropdown must be rendered into document.body to escape table clipping');
  });

  await t.test('2. Menu is not clipped by table card (overflow: hidden) or table wrapper (overflow-x: auto)', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'documents.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    // The portal-positioned dropdown must be position: fixed with z-index >= 1050
    assert.ok(cssContent.includes('.doc-menu-dropdown.portal-positioned {'), 'portal-positioned class must exist');
    assert.ok(cssContent.includes('position: fixed;'), 'portal-positioned dropdown must use position: fixed');
    assert.ok(cssContent.includes('z-index: 1050;'), 'portal-positioned dropdown must use high z-index above table cards');
  });

  // =========================================================================
  // 3 & 4. REPOSITIONING & VIEWPORT BOUNDS
  // =========================================================================

  await t.test('3. Menu repositions upward when viewport space below is insufficient', () => {
    // Scenario: Anchor is near bottom of 800px viewport (bottom: 740px)
    const anchorNearBottom = {
      top: 710,
      bottom: 738,
      left: 1050,
      right: 1078,
      width: 28,
      height: 28,
    };

    const placement = computeDropdownPosition(anchorNearBottom, 1280, 800);
    assert.strictEqual(placement.openUpward, true, 'Must flip upward when space below is < 185px');
    assert.ok(placement.style.bottom, 'style.bottom must be set for upward menu');
    assert.strictEqual(placement.style.top, undefined, 'style.top must not be set when openUpward is true');
    assert.strictEqual(placement.style.position, 'fixed');
  });

  await t.test('4. Menu opens downward when viewport space below is ample', () => {
    // Scenario: Anchor is near top of 800px viewport (bottom: 200px)
    const anchorNearTop = {
      top: 172,
      bottom: 200,
      left: 1050,
      right: 1078,
      width: 28,
      height: 28,
    };

    const placement = computeDropdownPosition(anchorNearTop, 1280, 800);
    assert.strictEqual(placement.openUpward, false, 'Must open downward when space below is ample');
    assert.ok(placement.style.top, 'style.top must be set for downward menu');
    assert.strictEqual(placement.style.bottom, undefined, 'style.bottom must not be set when openUpward is false');
  });

  await t.test('5. Menu remains inside viewport bounds across desktop, laptop, and narrow mobile viewports', () => {
    // Case A: 1440px Desktop
    const rect1440 = { top: 300, bottom: 328, left: 1350, right: 1378, width: 28, height: 28 };
    const p1440 = computeDropdownPosition(rect1440, 1440, 900);
    const right1440 = parseFloat(p1440.style.right);
    assert.ok(right1440 >= 12, 'Must maintain at least 12px margin from right viewport edge at 1440px');

    // Case B: 1280px Laptop
    const rect1280 = { top: 300, bottom: 328, left: 1240, right: 1268, width: 28, height: 28 };
    const p1280 = computeDropdownPosition(rect1280, 1280, 800);
    const right1280 = parseFloat(p1280.style.right);
    assert.ok(right1280 >= 12, 'Must maintain at least 12px margin from right edge at 1280px');

    // Case C: 360px Mobile
    const rect360 = { top: 400, bottom: 428, left: 320, right: 348, width: 28, height: 28 };
    const p360 = computeDropdownPosition(rect360, 360, 640);
    assert.ok(p360.style.width.includes('calc(100vw - 24px)'), 'Must clamp width to viewport on narrow screens');
    assert.strictEqual(p360.style.right, '12px', 'Must clamp right to 12px on narrow mobile');
  });

  // =========================================================================
  // 6 & 7. DISMISSAL: OUTSIDE CLICK & ESCAPE KEY
  // =========================================================================

  await t.test('6. Outside click dismisses the menu', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Window mousedown and touchstart listeners registered for outside click
    assert.ok(jsxContent.includes("window.addEventListener('mousedown', handleOutsideClick)"), 'Must listen for mousedown to dismiss');
    assert.ok(jsxContent.includes("window.addEventListener('touchstart', handleOutsideClick)"), 'Must listen for touchstart on mobile');
    assert.ok(jsxContent.includes("activeMenuRef.current.contains(e.target)"), 'Must check if click is outside menu');
  });

  await t.test('7. Escape key closes the menu', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Escape key listener is registered
    assert.ok(jsxContent.includes("if (e.key === 'Escape')"), 'Must check for Escape key');
    assert.ok(jsxContent.includes("setActiveMenu(null)"), 'Must close menu on Escape');
  });

  await t.test('8. Scroll and resize listeners maintain anchor alignment or dismiss when scrolled offscreen', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Window scroll and resize listeners registered
    assert.ok(jsxContent.includes("window.addEventListener('scroll', handleScrollOrResize, true)"), 'Must capture scroll events');
    assert.ok(jsxContent.includes("window.addEventListener('resize', handleScrollOrResize)"), 'Must listen for window resize');
    assert.ok(jsxContent.includes("rect.bottom < 0 || rect.top > window.innerHeight"), 'Must dismiss when trigger scrolls offscreen');
  });

  // =========================================================================
  // 8. ALL FIVE ACTIONS REMAIN PRESERVED
  // =========================================================================

  await t.test('9. All five actions remain fully available with authentic handlers', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Action 1: View Details
    assert.ok(jsxContent.includes('<span>View Details</span>'), 'View Details action must be present');
    assert.ok(jsxContent.includes('setSelectedDocForView(targetDoc)'), 'View Details must call setSelectedDocForView');

    // Action 2: Download Copy
    assert.ok(jsxContent.includes('<span>Download Copy</span>'), 'Download Copy action must be present');
    assert.ok(jsxContent.includes('handleDownloadDoc(targetDoc)'), 'Download Copy must call handleDownloadDoc');

    // Action 3: Replace Document
    assert.ok(jsxContent.includes('<span>Replace Document</span>'), 'Replace Document action must be present');
    assert.ok(jsxContent.includes('handleOpenUploadModal(targetDoc.id)'), 'Replace Document must call handleOpenUploadModal');

    // Action 4: Apply for Scheme
    assert.ok(jsxContent.includes('<span>Apply for Scheme</span>'), 'Apply for Scheme action must be present');
    assert.ok(jsxContent.includes('handleOpenTicketModal(targetDoc.id)'), 'Apply for Scheme must call handleOpenTicketModal');

    // Action 5: Remove Document
    assert.ok(jsxContent.includes('<span>Remove Document</span>'), 'Remove Document action must be present');
    assert.ok(jsxContent.includes('handleDeleteDoc(targetDoc.id)'), 'Remove Document must call handleDeleteDoc');
  });
});
