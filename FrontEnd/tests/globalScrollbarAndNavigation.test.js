import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Site-wide Scrollbar Appearance & Global Route Navigation Suite', async (t) => {
  const indexCssPath = path.join(__dirname, '..', 'src', 'index.css');
  const indexCssContent = fs.readFileSync(indexCssPath, 'utf8');

  const appJsxPath = path.join(__dirname, '..', 'src', 'App.jsx');
  const appJsxContent = fs.readFileSync(appJsxPath, 'utf8');

  const scrollToTopPath = path.join(__dirname, '..', 'src', 'components', 'common', 'ScrollToTop.jsx');
  const scrollToTopContent = fs.readFileSync(scrollToTopPath, 'utf8');

  await t.test('1. index.css hides browser main scrollbar on html and body across all rendering engines', () => {
    // Firefox
    assert.ok(
      indexCssContent.includes('scrollbar-width: none'),
      'index.css must specify scrollbar-width: none for Firefox'
    );
    // IE / Edge
    assert.ok(
      indexCssContent.includes('-ms-overflow-style: none'),
      'index.css must specify -ms-overflow-style: none for IE/Edge'
    );
    // Chromium / Webkit
    assert.ok(
      indexCssContent.includes('html::-webkit-scrollbar') &&
      indexCssContent.includes('body::-webkit-scrollbar'),
      'index.css must target html::-webkit-scrollbar and body::-webkit-scrollbar'
    );
    assert.ok(
      indexCssContent.includes('display: none'),
      'index.css must hide webkit-scrollbar with display: none'
    );
  });

  await t.test('2. index.css does NOT disable scrolling on html or body', () => {
    // Must NOT disable scrolling
    const bodyDeclMatch = indexCssContent.match(/html,\s*body\s*\{([^}]+)\}/);
    assert.ok(bodyDeclMatch, 'html, body block must exist in index.css');
    const bodyProps = bodyDeclMatch[1];
    assert.ok(
      !bodyProps.includes('overflow: hidden'),
      'Must NOT set overflow: hidden on html, body - scrolling must remain fully functional'
    );
    assert.ok(
      !bodyProps.includes('overflow-y: hidden'),
      'Must NOT set overflow-y: hidden on html, body'
    );
  });

  await t.test('3. Scrollbar suppression is strictly scoped to main page/body, preserving internal components', () => {
    // Must not do * { scrollbar-width: none }
    assert.ok(
      !indexCssContent.includes('* {') || !indexCssContent.includes('* {\n  scrollbar-width: none'),
      'Must not apply scrollbar-width: none to universal selector *'
    );
    assert.ok(
      !indexCssContent.includes('*::-webkit-scrollbar'),
      'Must not suppress scrollbars universally with *::-webkit-scrollbar'
    );
  });

  await t.test('4. App.jsx mounts ScrollToTop within BrowserRouter', () => {
    assert.ok(
      appJsxContent.includes("import ScrollToTop from './components/common/ScrollToTop'"),
      'App.jsx must import ScrollToTop'
    );
    assert.ok(
      appJsxContent.includes('<ScrollToTop />'),
      'App.jsx must mount <ScrollToTop /> component'
    );
    // Must be inside BrowserRouter
    const routerIndex = appJsxContent.indexOf('<BrowserRouter>');
    const scrollToTopIndex = appJsxContent.indexOf('<ScrollToTop />');
    const closeRouterIndex = appJsxContent.indexOf('</BrowserRouter>');
    assert.ok(routerIndex !== -1, 'BrowserRouter must be rendered');
    assert.ok(
      routerIndex < scrollToTopIndex && scrollToTopIndex < closeRouterIndex,
      '<ScrollToTop /> must be rendered inside <BrowserRouter>'
    );
  });

  await t.test('5. ScrollToTop automatically resets window scroll position to (0, 0) on pathname change', () => {
    assert.ok(
      scrollToTopContent.includes('useLocation()'),
      'ScrollToTop must use useLocation to listen to route transitions'
    );
    assert.ok(
      scrollToTopContent.includes('window.scrollTo('),
      'ScrollToTop must invoke window.scrollTo'
    );
    assert.ok(
      scrollToTopContent.includes('top: 0') || scrollToTopContent.includes('(0, 0)'),
      'ScrollToTop must target coordinates top: 0'
    );
    assert.ok(
      scrollToTopContent.includes('document.documentElement.scrollTop = 0') &&
      scrollToTopContent.includes('document.body.scrollTop = 0'),
      'ScrollToTop must also reset documentElement and body scrollTop for maximum browser compatibility'
    );
    assert.ok(
      scrollToTopContent.includes('[pathname]'),
      'ScrollToTop effect must depend on [pathname] to trigger on route change'
    );
  });
});
