import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const stylesDir = path.join(__dirname, '..', 'src', 'styles');

test('FIN — Complete Responsive Design Pass Audit Suite', async (t) => {
  const readCss = (file) => fs.readFileSync(path.join(stylesDir, file), 'utf8');

  const layoutCss = readCss('layout.css');
  const footerCss = readCss('footer.css');
  const dashboardCss = readCss('dashboard.css');
  const discoverCss = readCss('discover.css');
  const schemeDetailsCss = readCss('schemeDetails.css');
  const suggestedSchemesCss = readCss('suggestedSchemes.css');
  const documentsCss = readCss('documents.css');
  const applicationsCss = readCss('applications.css');
  const profileCss = readCss('profile.css');
  const signupCss = readCss('signup.css');

  await t.test('1. Layout & Header: Responsive navigation drawer & mobile compact header', () => {
    // Drawer slide animation
    assert.ok(layoutCss.includes('transition: transform 0.28s'), 'Sidebar must have smooth slide transition');
    // Mobile menu toggle button
    assert.ok(layoutCss.includes('.menu-toggle-btn'), 'Mobile menu toggle button exists');
    // Mobile drawer state
    assert.ok(layoutCss.includes('.app-sidebar.open'), 'Sidebar open state exists');
    assert.ok(layoutCss.includes('max-width: 85vw'), 'Sidebar width is bounded on small screens');
    // Search shortcut badge hidden on mobile
    assert.ok(layoutCss.includes('.search-shortcut-badge') && layoutCss.includes('display: none'), 'Search shortcut badge hidden on mobile screens');
    // AI button collapses cleanly on small screens
    assert.ok(layoutCss.includes('.navbar-ai-btn-text,') && layoutCss.includes('display: none'), 'AI button text collapses on mobile');
    // Popovers bounded by viewport width
    assert.ok(layoutCss.includes('width: min(340px, calc(100vw - 20px))'), 'Notification popover bounded to viewport width');
    assert.ok(layoutCss.includes('width: min(310px, calc(100vw - 20px))'), 'Profile popover bounded to viewport width');
  });

  await t.test('2. Footer & Panorama: Desktop synchronization preserved and mobile reflow intact', () => {
    // Desktop synchronization preserved
    assert.ok(footerCss.includes('.footer-building-backdrop'), 'Footer backdrop present');
    assert.ok(footerCss.includes('position: fixed'), 'Footer panorama fixed backdrop present');
    // Mobile reflow
    assert.ok(footerCss.includes('@media (max-width: 768px)'), 'Footer 768px media query exists');
    assert.ok(footerCss.includes('@media (max-width: 480px)'), 'Footer 480px media query exists');
    assert.ok(footerCss.includes('height: auto') && footerCss.includes('min-height: 50px'), 'Footer bottom bar has flexible auto height on mobile/tablet');
    assert.ok(footerCss.includes('flex-direction: column'), 'Footer bottom bar stacks vertically on mobile/tablet');
    assert.ok(footerCss.includes('background-size: cover'), 'Mobile backdrop preserves clean cover scaling');
  });

  await t.test('3. Dashboard: Metrics and hero actions stack seamlessly on mobile', () => {
    assert.ok(dashboardCss.includes('@media (max-width: 640px)'), 'Dashboard has 640px breakpoint');
    assert.ok(dashboardCss.includes('@media (max-width: 480px)'), 'Dashboard has 480px breakpoint');
    assert.ok(dashboardCss.includes('@media (max-width: 360px)'), 'Dashboard has 360px breakpoint');
    assert.ok(dashboardCss.includes('.hero-actions-row') && dashboardCss.includes('flex-direction: column'), 'Hero actions stack into columns on mobile');
  });

  await t.test('4. Discover Schemes: Filter sidebar, scheme cards, and metadata reflow naturally', () => {
    assert.ok(discoverCss.includes('@media (max-width: 992px)'), 'Discover has 992px breakpoint');
    assert.ok(discoverCss.includes('@media (max-width: 640px)'), 'Discover has 640px breakpoint');
    assert.ok(discoverCss.includes('@media (max-width: 480px)'), 'Discover has 480px breakpoint');
    assert.ok(discoverCss.includes('.scheme-card-meta-row') && discoverCss.includes('flex-direction: column'), 'Card metadata rows stack on small screens');
    assert.ok(discoverCss.includes('.scheme-card-actions-col') && discoverCss.includes('flex-direction: column'), 'Card action buttons stack on mobile');
  });

  await t.test('5. Scheme Details: Full responsiveness with responsive hero, calculator, and sticky sidebar release', () => {
    assert.ok(schemeDetailsCss.includes('@media (max-width: 1060px)'), 'Scheme details has 1060px breakpoint');
    assert.ok(schemeDetailsCss.includes('.scheme-right-sidebar') && schemeDetailsCss.includes('position: static'), 'Sticky sidebar releases to static flow on tablet/mobile');
    assert.ok(schemeDetailsCss.includes('@media (max-width: 768px)'), 'Scheme details has 768px breakpoint');
    assert.ok(schemeDetailsCss.includes('@media (max-width: 600px)'), 'Scheme details has 600px breakpoint');
    assert.ok(schemeDetailsCss.includes('@media (max-width: 480px)'), 'Scheme details has 480px breakpoint');
    assert.ok(schemeDetailsCss.includes('.scheme-benefits-grid') && schemeDetailsCss.includes('grid-template-columns: 1fr'), 'Benefits grid collapses to 1-col on mobile');
  });

  await t.test('6. Suggested Schemes: Cards and modal reflow cleanly on small screens', () => {
    assert.ok(suggestedSchemesCss.includes('@media (max-width: 768px)'), 'Suggested schemes has 768px breakpoint');
    assert.ok(suggestedSchemesCss.includes('@media (max-width: 480px)'), 'Suggested schemes has 480px breakpoint');
    assert.ok(suggestedSchemesCss.includes('.suggested-card-footer') && suggestedSchemesCss.includes('flex-direction: column'), 'Card footer buttons stack on mobile');
  });

  await t.test('7. My Documents: Metrics, toolbar, and card table adapt without clipping', () => {
    assert.ok(documentsCss.includes('@media (max-width: 1024px)'), 'Documents has 1024px breakpoint');
    assert.ok(documentsCss.includes('@media (max-width: 768px)'), 'Documents has 768px breakpoint');
    assert.ok(documentsCss.includes('@media (max-width: 480px)'), 'Documents has 480px breakpoint');
    assert.ok(documentsCss.includes('.docs-toolbar-actions') && documentsCss.includes('flex-wrap: wrap'), 'Toolbar actions wrap safely on narrow mobile');
  });

  await t.test('8. Applications: Stepper track touch-scrolling, modal, and cards reflow', () => {
    assert.ok(applicationsCss.includes('@media (max-width: 1040px)'), 'Applications has 1040px breakpoint');
    assert.ok(applicationsCss.includes('@media (max-width: 768px)'), 'Applications has 768px breakpoint');
    assert.ok(applicationsCss.includes('@media (max-width: 480px)'), 'Applications has 480px breakpoint');
    assert.ok(applicationsCss.includes('.app-card-stepper-track') && applicationsCss.includes('overflow-x: auto'), 'Stepper track supports horizontal touch-scroll on mobile');
  });

  await t.test('9. Profile & Modals: Hero, details, sprout card, and edit profile modal reflow', () => {
    assert.ok(profileCss.includes('@media (max-width: 820px)'), 'Profile has 820px breakpoint');
    assert.ok(profileCss.includes('@media (max-width: 600px)'), 'Profile has 600px breakpoint');
    assert.ok(profileCss.includes('@media (max-width: 480px)'), 'Profile has 480px breakpoint');
    assert.ok(profileCss.includes('.profile-modal-dialog') && profileCss.includes('max-height: 90vh'), 'Profile modal fits within mobile viewport height');
  });

  await t.test('10. Authentication & Signup: Fluid card padding and scenery suppression on mobile', () => {
    assert.ok(signupCss.includes('@media (max-width: 860px)'), 'Signup has 860px breakpoint');
    assert.ok(signupCss.includes('@media (max-width: 480px)'), 'Signup has 480px breakpoint');
    assert.ok(signupCss.includes('.signup-card') && signupCss.includes('padding: 20px 16px'), 'Auth card padding adjusts for mobile screens');
    assert.ok(signupCss.includes('.signup-form-grid') && signupCss.includes('grid-template-columns: 1fr'), 'Auth form grid collapses to 1-col on mobile');
  });
});
