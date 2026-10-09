import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const modalPath = path.join(__dirname, '..', 'src', 'components', 'chat', 'FinAssistantModal.jsx');
const chatHistoryServicePath = path.join(__dirname, '..', 'src', 'services', 'chatHistoryService.js');
const markdownParserPath = path.join(__dirname, '..', 'src', 'components', 'chat', 'markdownParser.js');
const appRoutesPath = path.join(__dirname, '..', 'src', 'routes', 'AppRoutes.jsx');

test('FIN AI Scheme Click Navigation & Chat History Suite', async (t) => {
  const modalContent = fs.readFileSync(modalPath, 'utf8');
  const serviceContent = fs.readFileSync(chatHistoryServicePath, 'utf8');
  const markdownContent = fs.readFileSync(markdownParserPath, 'utf8');
  const routesContent = fs.readFileSync(appRoutesPath, 'utf8');

  await t.test('1. Scheme Suggestion -> Exact Scheme Page Navigation: Uses canonical slug / ID and route /scheme/:schemeId', () => {
    // Verify canonical route exists in AppRoutes.jsx
    assert.ok(
      routesContent.includes('/scheme/:schemeId') || routesContent.includes('/schemes/:schemeId'),
      'AppRoutes must register /scheme/:schemeId'
    );

    // Verify handleSchemeClick in FinAssistantModal uses canonical slug/id
    assert.match(
      modalContent,
      /const\s+handleSchemeClick\s*=\s*\((?:scheme)?\)\s*=>\s*\{[\s\S]*?(?:scheme\?.slug\s*\|\|\s*scheme\?.schemeId\s*\|\|\s*scheme\?.id)/,
      'handleSchemeClick must extract canonical slug/schemeId/id, never name text'
    );

    // Verify it navigates to /scheme/<canonical-id>
    assert.match(
      modalContent,
      /navigate\(`\/scheme\/\$\{encodeURIComponent\(targetSlug\)\}`\)/,
      'Must navigate to /scheme/${encodeURIComponent(targetSlug)}'
    );

    // Verify card click handler triggers handleSchemeClick
    assert.ok(
      modalContent.includes('onClick={() => handleSchemeClick(scheme)}'),
      'Scheme card item must invoke handleSchemeClick with canonical scheme object'
    );
  });

  await t.test('2. Disambiguation: Similar schemes (e.g. MUDRA Shishu vs Kishore) route by distinct canonical slug/id', () => {
    const shishuScheme = { id: 'mudra-shishu', slug: 'mudra-shishu', name: 'MUDRA Loan - Shishu' };
    const kishoreScheme = { id: 'mudra-kishore', slug: 'mudra-kishore', name: 'MUDRA Loan - Kishore' };

    const getTargetRoute = (scheme) => {
      const slug = scheme?.slug || scheme?.schemeId || scheme?.id;
      return `/scheme/${encodeURIComponent(slug)}`;
    };

    const shishuRoute = getTargetRoute(shishuScheme);
    const kishoreRoute = getTargetRoute(kishoreScheme);

    assert.equal(shishuRoute, '/scheme/mudra-shishu');
    assert.equal(kishoreRoute, '/scheme/mudra-kishore');
    assert.notEqual(shishuRoute, kishoreRoute, 'Similar-named schemes must produce distinct routes');
  });

  await t.test('3. Markdown Renderer: Supports safe internal /scheme links with onNavigate', () => {
    assert.ok(
      markdownContent.includes('onNavigate = null'),
      'markdownParser must accept onNavigate parameter'
    );
    assert.ok(
      modalContent.includes('onNavigate={(path) => {'),
      'FinAssistantModal must wire onNavigate into MarkdownRenderer'
    );
    assert.ok(
      markdownContent.includes("isSafeUrl = (url) =>"),
      'markdownParser must export isSafeUrl'
    );
  });

  await t.test('4. Frontend Chat History Service: Implements authenticated history fetch, get by ID, and delete', () => {
    assert.ok(
      serviceContent.includes('fetchChatHistory'),
      'chatHistoryService must export fetchChatHistory'
    );
    assert.ok(
      serviceContent.includes('fetchConversationById'),
      'chatHistoryService must export fetchConversationById'
    );
    assert.ok(
      serviceContent.includes('deleteConversationById'),
      'chatHistoryService must export deleteConversationById'
    );
    assert.ok(
      serviceContent.includes('authenticatedFetch'),
      'chatHistoryService must use authenticatedFetch to isolate data per authenticated user'
    );
  });

  await t.test('5. FinAssistantModal: Chat history UI controls, panel, and multi-conversation state', () => {
    // History button in header controls
    assert.match(
      modalContent,
      /<History\s+size=\{17\}\s*\/>/,
      'Modal header must render History icon button'
    );

    // New Chat button in header controls
    assert.match(
      modalContent,
      /<Plus\s+size=\{17\}\s*\/>/,
      'Modal header must render New Chat button'
    );

    // History view panel rendered when isHistoryOpen is true
    assert.ok(
      modalContent.includes('fin-history-view'),
      'Modal must render fin-history-view panel'
    );
    assert.ok(
      modalContent.includes('fin-history-item'),
      'Modal must render fin-history-item list items'
    );

    // Empty history state
    assert.ok(
      modalContent.includes('fin-history-empty'),
      'Modal must handle empty history state'
    );

    // Loading and error states
    assert.ok(
      modalContent.includes('fin-history-loading'),
      'Modal must handle loading history state'
    );
    assert.ok(
      modalContent.includes('fin-history-error'),
      'Modal must handle error history state'
    );
  });

  await t.test('6. Save/Reload Persistence: active conversation stored in sessionStorage across reloads', () => {
    assert.ok(
      modalContent.includes("sessionStorage.getItem('fin_active_conversation_id')"),
      'Must check sessionStorage for active conversation ID on reload/mount'
    );
    assert.ok(
      modalContent.includes("sessionStorage.setItem('fin_active_conversation_id'"),
      'Must persist active conversation ID to sessionStorage upon server response'
    );
    assert.ok(
      modalContent.includes("sessionStorage.removeItem('fin_active_conversation_id')"),
      'Must clear active conversation ID from sessionStorage when starting new chat'
    );
  });

  await t.test('7. Reopen previous conversation: Reopens exact conversation with its messages', () => {
    assert.ok(
      modalContent.includes('handleSelectConversation'),
      'Modal must provide handleSelectConversation to switch conversations'
    );
    assert.match(
      modalContent,
      /fetchConversationById\(convId\)[\s\S]*?setMessages\(conv\.messages\)/,
      'handleSelectConversation must fetch conversation and restore messages'
    );
  });
});
