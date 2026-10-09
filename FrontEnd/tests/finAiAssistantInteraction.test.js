import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const headerPath = path.join(__dirname, '..', 'src', 'components', 'layout', 'Header.jsx');
const appLayoutPath = path.join(__dirname, '..', 'src', 'components', 'layout', 'AppLayout.jsx');
const modalPath = path.join(__dirname, '..', 'src', 'components', 'chat', 'FinAssistantModal.jsx');

test('FIN — Ask FIN AI Navbar Button & Assistant Modal Wiring Suite', async (t) => {
  const headerContent = fs.readFileSync(headerPath, 'utf8');
  const appLayoutContent = fs.readFileSync(appLayoutPath, 'utf8');
  const modalContent = fs.readFileSync(modalPath, 'utf8');

  await t.test('1. Header: Ask FIN AI button has resilient click handler and handles both prop names and event fallback', () => {
    // Header must accept onToggleChat and onOpenChat
    assert.match(
      headerContent,
      /export\s+default\s+function\s+Header\(\s*\{[^}]*onToggleChat[^}]*onOpenChat/,
      'Header must accept both onToggleChat and onOpenChat props'
    );
    // Button must call handleChatClick
    assert.match(
      headerContent,
      /<button[^>]*className=\{`navbar-ai-assistant-btn\s+\$\{isChatOpen\s*\?\s*'active'\s*:\s*''\}`\}[^>]*onClick=\{handleChatClick\}/,
      'Ask FIN AI button must trigger handleChatClick'
    );
    // Resilient fallback logic
    assert.ok(
      headerContent.includes("window.dispatchEvent(new CustomEvent('open_fin_chat'))"),
      'Header must include fallback event dispatch to ensure button always functions'
    );
  });

  await t.test('2. AppLayout: Passes valid chat toggle handler to Header and coordinates modal state', () => {
    // Must pass onToggleChat and onOpenChat to Header
    assert.ok(
      appLayoutContent.includes('onToggleChat={toggleChat}'),
      'AppLayout must pass onToggleChat={toggleChat} to Header'
    );
    assert.ok(
      appLayoutContent.includes('onOpenChat={toggleChat}'),
      'AppLayout must pass onOpenChat={toggleChat} to Header'
    );
    // Must listen to open_fin_chat event
    assert.ok(
      appLayoutContent.includes("window.addEventListener('open_fin_chat'"),
      'AppLayout must listen to open_fin_chat event'
    );
    // Must mount FinAssistantModal with isOpen={isChatOpen}
    assert.ok(
      appLayoutContent.includes('<FinAssistantModal'),
      'AppLayout must render FinAssistantModal'
    );
    assert.ok(
      appLayoutContent.includes('isOpen={isChatOpen}'),
      'FinAssistantModal must receive isOpen={isChatOpen}'
    );
  });

  await t.test('3. FinAssistantModal: Supports minimize and close actions seamlessly', () => {
    // Must handle onMinimize and onToggleMinimize
    assert.ok(
      modalContent.includes('handleToggleMinimize'),
      'FinAssistantModal must resolve minimize handler flexibly'
    );
    // Must render when isOpen is true
    assert.ok(
      modalContent.includes('if (!isOpen) return null;'),
      'FinAssistantModal must conditionally render based on isOpen'
    );
  });
});
