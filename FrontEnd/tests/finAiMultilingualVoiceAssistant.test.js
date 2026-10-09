import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const modalPath = path.join(__dirname, '..', 'src', 'components', 'chat', 'FinAssistantModal.jsx');
const chatbotCssPath = path.join(__dirname, '..', 'src', 'styles', 'chatbot.css');
const chatControllerPath = path.join(__dirname, '..', '..', 'BackEnd', 'src', 'controllers', 'chatController.js');
const chatServicePath = path.join(__dirname, '..', '..', 'BackEnd', 'src', 'services', 'chatService.js');
const intelligenceChatPath = path.join(__dirname, '..', '..', 'Intelligence', 'src', 'api', 'routes', 'chat.py');

test('FIN AI — Multilingual NLP + Voice Assistant Architecture & Interaction Suite', async (t) => {
  const modalContent = fs.readFileSync(modalPath, 'utf8');
  const cssContent = fs.readFileSync(chatbotCssPath, 'utf8');
  const controllerContent = fs.readFileSync(chatControllerPath, 'utf8');
  const serviceContent = fs.readFileSync(chatServicePath, 'utf8');
  const intelligenceContent = fs.readFileSync(intelligenceChatPath, 'utf8');

  await t.test('1. Strict Question Understanding & Multilingual Invariant in Intelligence Engine', () => {
    assert.ok(
      intelligenceContent.includes('STRICT QUESTION UNDERSTANDING'),
      'Intelligence prompt must mandate strict question understanding without topic drift'
    );
    assert.ok(
      intelligenceContent.includes('MULTILINGUAL INVARIANT'),
      'Intelligence prompt must mandate answering in the exact same language as user query'
    );
    assert.ok(
      intelligenceContent.includes('NO_EVIDENCE_MESSAGES'),
      'Intelligence must maintain clean, verifiable no-evidence messages in multiple languages'
    );
    assert.ok(
      intelligenceContent.includes('is_fin_website_query'),
      'Intelligence must support answering every question regarding FIN website features and navigation'
    );
  });

  await t.test('2. Backend Integration: Dynamic language forwarding and detectedLanguage preservation', () => {
    assert.ok(
      controllerContent.includes('language'),
      'chatController must extract language from request body'
    );
    assert.ok(
      serviceContent.includes('targetLanguage'),
      'chatService must pass dynamic targetLanguage to Intelligence microservice'
    );
    assert.ok(
      serviceContent.includes('detectedLanguage'),
      'chatService must return detectedLanguage to frontend'
    );
  });

  await t.test('3. Voice & Microphone Input: SpeechRecognition setup and language model configuration', () => {
    assert.ok(
      modalContent.includes('window.SpeechRecognition || window.webkitSpeechRecognition'),
      'Modal must instantiate standard Web SpeechRecognition API with webkit fallback'
    );
    assert.ok(
      modalContent.includes('recognition.lang = recLang'),
      'Modal must configure acoustic recognition language dynamically'
    );
    assert.ok(
      modalContent.includes('recognition.onspeechstart'),
      'Modal must transition state to processing upon detecting speech'
    );
    assert.ok(
      modalContent.includes('recognition.onresult'),
      'Modal must automatically capture speech transcript and submit query'
    );
  });

  await t.test('4. Dedicated Microphone Voice Mode: Clean start, stop, and zero continuous hands-free listening', () => {
    assert.ok(
      !modalContent.includes('isHandsFree') && !modalContent.includes('handleToggleHandsFree'),
      'Modal must not contain continuous hands-free listening loops without user action'
    );
    assert.ok(
      modalContent.includes('stopVoiceAndTts'),
      'Modal must provide stop function halting recognition and canceling synthesis'
    );
    assert.ok(
      modalContent.includes('handleToggleVoice'),
      'Modal must provide explicit microphone toggle handler'
    );
  });

  await t.test('5. Voice Response: Text-To-Speech (TTS) matching detected language', () => {
    assert.ok(
      modalContent.includes('window.speechSynthesis'),
      'Modal must utilize SpeechSynthesis for spoken voice responses'
    );
    assert.ok(
      modalContent.includes('SpeechSynthesisUtterance'),
      'Modal must instantiate SpeechSynthesisUtterance'
    );
    assert.ok(
      modalContent.includes('cleanSpeech'),
      'Modal must strip markdown markers and formatting prior to speaking'
    );
    assert.ok(
      modalContent.includes('hi-IN') && modalContent.includes('gu-IN') && modalContent.includes('en-IN'),
      'Modal must map detected languages to regional Indic BCP 47 voice locales'
    );
    assert.ok(
      modalContent.includes('fin-msg-audio-btn'),
      'Modal must provide individual message audio listen buttons'
    );
  });

  await t.test('6. Error Handling: Microphone denied, unsupported browser, and network issues', () => {
    assert.ok(
      modalContent.includes('Microphone access denied'),
      'Modal must display user-friendly message when microphone permission is denied'
    );
    assert.ok(
      modalContent.includes('Speech recognition is not supported'),
      'Modal must warn when speech recognition is unavailable in browser'
    );
    assert.ok(
      modalContent.includes('voiceErrorMessage'),
      'Modal must display dismissible voice error alert'
    );
  });

  await t.test('7. UI: Status bar, indicator badges, stop button, and language selector', () => {
    assert.ok(
      modalContent.includes('fin-voice-status-bar'),
      'Modal must render real-time voice status banner'
    );
    assert.ok(
      modalContent.includes('fin-voice-stop-btn'),
      'Modal must render prominent Stop button'
    );
    assert.ok(
      modalContent.includes('fin-voice-lang-dropdown'),
      'Modal must provide accessible language switcher dropdown'
    );
    assert.ok(
      cssContent.includes('.fin-voice-status-bar') && cssContent.includes('.fin-voice-pulse-badge'),
      'chatbot.css must contain animations and styling for voice status and pulse'
    );
    assert.ok(
      !modalContent.includes('hands-free-active'),
      'Modal must not render hands-free pill'
    );
  });

  await t.test('8. Security & Architecture: Client talks to /api/chat without exposed keys', () => {
    assert.ok(
      modalContent.includes("authenticatedFetch(`${API_BASE_URL}/api/chat`"),
      'Frontend must communicate via authenticated backend proxy /api/chat'
    );
    assert.ok(
      !modalContent.includes('GEMINI_API_KEY') && !modalContent.includes('X-AI-Service-Key'),
      'Frontend must never expose protected AI service keys to browser'
    );
  });
});
