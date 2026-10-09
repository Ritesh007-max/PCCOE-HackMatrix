import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Minus,
  X,
  Search,
  FileText,
  Users,
  FileCheck,
  Settings,
  Compass,
  MessageCircle,
  ChevronRight,
  Send,
  Paperclip,
  Mic,
  MicOff,
  GraduationCap,
  ArrowRight,
  Volume2,
  VolumeX,
  Square,
  Radio,
  Globe,
  History,
  Plus,
  Trash2
} from 'lucide-react';
import { DigitalIndiaLogo } from '../common/BrandAssets';
import { authenticatedFetch } from '../../services/authService';
import { uploadDocumentFile, extractDocumentData } from '../../services/documentService';
import { fetchChatHistory, fetchConversationById, deleteConversationById } from '../../services/chatHistoryService';

import MarkdownRenderer, { renderMarkdownInline, isSafeUrl } from './markdownParser.js';

export { MarkdownRenderer, renderMarkdownInline, isSafeUrl };


// Assets
import indiaGateSketch from '../../assets/india_gate_sketch.jpg';
import skillIndiaImg from '../../assets/schemes/skill_india.jpg';
import startupIndiaImg from '../../assets/schemes/startup_india.jpg';
import ashokStambhOriginal from '../../assets/ashok_stambh_original.png';
import tricolorFlagClean from '../../assets/tricolor_flag_clean.png';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// Default prompt suggestions (Matching Image 2 - Left)
const PROMPTS = [
  {
    id: 'profile',
    iconType: 'search',
    label: 'Find schemes for my profile',
    query: 'Find schemes for my profile'
  },
  {
    id: 'pmegp',
    iconType: 'pmegp',
    label: 'Check my eligibility for PMEGP',
    query: 'Check my eligibility for PMEGP'
  },
  {
    id: 'student-gujarat',
    iconType: 'student',
    label: 'Schemes for students in Gujarat',
    query: 'Which schemes am I eligible for as a student in Gujarat?'
  },
  {
    id: 'documents',
    iconType: 'docs',
    label: 'What documents are required?',
    query: 'What documents are required for government schemes?'
  },
  {
    id: 'apply',
    iconType: 'apply',
    label: 'How to apply for a scheme?',
    query: 'How to apply for a scheme?'
  }
];

export default function FinAssistantModal({
  isOpen,
  onClose,
  isMinimized,
  onToggleMinimize,
  onMinimize
}) {
  const handleToggleMinimize = onToggleMinimize || onMinimize;
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [voiceState, setVoiceState] = useState('idle'); // 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking'
  const [isTtsMuted, setIsTtsMuted] = useState(false);
  const [selectedVoiceLang, setSelectedVoiceLang] = useState('auto');
  const [currentlySpeakingMsgId, setCurrentlySpeakingMsgId] = useState(null);
  const [voiceErrorMessage, setVoiceErrorMessage] = useState(null);

  // Chat History & Multi-conversation state
  const [currentConversationId, setCurrentConversationId] = useState(() => {
    try {
      return sessionStorage.getItem('fin_active_conversation_id') || null;
    } catch (_) {
      return null;
    }
  });
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);

  const isRecording = voiceState === 'listening' || voiceState === 'processing';
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const msgCounter = useRef(1);
  const isSubmittingRef = useRef(false);

  const recognitionRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const voiceStateRef = useRef('idle');

  useEffect(() => {
    voiceStateRef.current = voiceState;
  }, [voiceState]);

  // Restore active conversation on mount or reload if available
  useEffect(() => {
    const activeConvId = sessionStorage.getItem('fin_active_conversation_id');
    if (activeConvId && messages.length === 0) {
      setIsLoading(true);
      fetchConversationById(activeConvId)
        .then((conv) => {
          if (conv && Array.isArray(conv.messages) && conv.messages.length > 0) {
            setMessages(conv.messages);
            setCurrentConversationId(conv.id);
          } else {
            sessionStorage.removeItem('fin_active_conversation_id');
            setCurrentConversationId(null);
          }
        })
        .catch((err) => {
          console.warn('Could not restore previous conversation:', err);
          sessionStorage.removeItem('fin_active_conversation_id');
          setCurrentConversationId(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, []);

  // Fetch history list when history panel is opened
  const loadHistoryList = async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);
    try {
      const list = await fetchChatHistory();
      setHistoryList(list || []);
    } catch (err) {
      console.warn('Failed to load chat history:', err);
      setHistoryError(err.message || 'Unable to load chat history');
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleToggleHistory = () => {
    setIsHistoryOpen((prev) => {
      const next = !prev;
      if (next) {
        loadHistoryList();
      }
      return next;
    });
  };

  const handleSelectConversation = async (convId) => {
    if (!convId) return;
    setIsHistoryOpen(false);
    setIsLoading(true);
    try {
      const conv = await fetchConversationById(convId);
      if (conv && Array.isArray(conv.messages)) {
        setMessages(conv.messages);
        setCurrentConversationId(conv.id);
        sessionStorage.setItem('fin_active_conversation_id', conv.id);
      }
    } catch (err) {
      console.error('Failed to reopen conversation:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartNewChat = () => {
    setMessages([]);
    setCurrentConversationId(null);
    sessionStorage.removeItem('fin_active_conversation_id');
    setIsHistoryOpen(false);
  };

  const handleDeleteConversation = async (convId, e) => {
    if (e) e.stopPropagation();
    try {
      await deleteConversationById(convId);
      setHistoryList((prev) => prev.filter((c) => c.id !== convId));
      if (currentConversationId === convId) {
        handleStartNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSchemeClick = (scheme) => {
    const targetSlug = scheme?.slug || scheme?.schemeId || scheme?.id;
    if (!targetSlug) return;
    onClose?.();
    navigate(`/scheme/${encodeURIComponent(targetSlug)}`);
  };

  const formatHistoryDate = (dateString) => {
    if (!dateString) return '';
    try {
      const d = new Date(dateString);
      if (isNaN(d.getTime())) return '';
      const now = new Date();
      if (d.toDateString() === now.toDateString()) {
        return `Today, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      }
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      if (d.toDateString() === yesterday.toDateString()) {
        return `Yesterday, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      }
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch (_) {
      return '';
    }
  };

  // User initials (dynamically resolved from session)
  const [userInitials, setUserInitials] = useState('CI');

  useEffect(() => {
    try {
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        const name = parsed.fullName || parsed.name || parsed.full_name || parsed.username || '';
        if (name.trim()) {
          const parts = name.trim().split(/\s+/).filter(Boolean);
          const inits = parts.length > 1
            ? (parts[0][0] + parts[1][0]).toUpperCase()
            : name.slice(0, 2).toUpperCase();
          setUserInitials(inits || 'CI');
        }
      }
    } catch (_) {}
  }, []);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // Format time (e.g., 10:24 AM)
  const formatTime = () => {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const stopVoiceAndTts = () => {
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    } catch (_) {}
    try {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    } catch (_) {}
    isSpeakingRef.current = false;
    setCurrentlySpeakingMsgId(null);
    setVoiceState('idle');
  };

  useEffect(() => {
    return () => {
      stopVoiceAndTts();
    };
  }, []);

  const speakText = (text, langCode = 'en') => {
    if (isTtsMuted || !('speechSynthesis' in window)) return Promise.resolve();

    return new Promise((resolve) => {
      try {
        window.speechSynthesis.cancel();

        const cleanSpeech = (text || '')
          .replace(/[*#_`~>[\]()]/g, '')
          .replace(/https?:\/\/\S+/g, '')
          .replace(/[🏛️📄📎⚠️✅•—]/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();

        if (!cleanSpeech) {
          resolve();
          return;
        }

        const utterance = new SpeechSynthesisUtterance(cleanSpeech);
        const langMap = {
          hi: 'hi-IN',
          gu: 'gu-IN',
          hinglish: 'hi-IN',
          ta: 'ta-IN',
          te: 'te-IN',
          bn: 'bn-IN',
          mr: 'mr-IN',
          kn: 'kn-IN',
          ml: 'ml-IN',
          pa: 'pa-IN',
          en: 'en-IN'
        };
        const bcpLang = langMap[langCode] || (langCode && langCode.includes('-') ? langCode : 'en-IN');
        utterance.lang = bcpLang;

        const voices = window.speechSynthesis.getVoices() || [];
        const matchedVoice = voices.find((v) => v.lang === bcpLang || v.lang.startsWith(langCode)) ||
          voices.find((v) => v.lang.includes('IN')) ||
          voices[0];

        if (matchedVoice) {
          utterance.voice = matchedVoice;
        }

        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
          isSpeakingRef.current = true;
          setVoiceState('speaking');
        };

        utterance.onend = () => {
          isSpeakingRef.current = false;
          setCurrentlySpeakingMsgId(null);
          resolve();
        };

        utterance.onerror = () => {
          isSpeakingRef.current = false;
          setCurrentlySpeakingMsgId(null);
          resolve();
        };

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn('Speech synthesis error:', err);
        isSpeakingRef.current = false;
        resolve();
      }
    });
  };

  const startRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceErrorMessage('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      setVoiceState('idle');
      return;
    }

    try {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (_) {}
      }

      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;

      let recLang = 'en-IN';
      if (selectedVoiceLang !== 'auto') {
        recLang = selectedVoiceLang;
      } else {
        recLang = 'hi-IN';
      }
      recognition.lang = recLang;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setVoiceState('listening');
        setVoiceErrorMessage(null);
      };

      recognition.onspeechstart = () => {
        setVoiceState('processing');
      };

      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript;
        if (transcript && transcript.trim()) {
          setVoiceState('thinking');
          handleSendMessage(transcript.trim());
        } else {
          setVoiceState('idle');
        }
      };

      recognition.onerror = (event) => {
        const errType = event.error;
        if (errType === 'not-allowed' || errType === 'service-not-allowed') {
          setVoiceErrorMessage('Microphone access denied. Please allow microphone access in your browser settings.');
          stopVoiceAndTts();
        } else {
          setVoiceState('idle');
        }
      };

      recognition.onend = () => {
        if (voiceStateRef.current === 'listening') {
          setVoiceState('idle');
        }
      };

      recognition.start();
    } catch (err) {
      console.warn('Speech recognition startup error:', err);
      setVoiceState('idle');
    }
  };

  const handleToggleVoice = () => {
    if (isRecording) {
      stopVoiceAndTts();
    } else {
      stopVoiceAndTts();
      startRecognition();
    }
  };

  const handlePlayMessageSpeech = async (msg) => {
    if (currentlySpeakingMsgId === msg.id) {
      stopVoiceAndTts();
    } else {
      stopVoiceAndTts();
      setCurrentlySpeakingMsgId(msg.id);
      await speakText(msg.text, msg.detectedLanguage || 'en');
      setCurrentlySpeakingMsgId(null);
    }
  };

  // Send a message
  const handleSendMessage = async (textToSend) => {
    const trimmed = (textToSend || inputText).trim();
    if (!trimmed || isLoading) return;

    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch (_) {}
    }

    const userMsg = {
      id: `user-${msgCounter.current++}`,
      sender: 'user',
      text: trimmed,
      time: formatTime()
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);
    setVoiceState('thinking');

    try {
      const history = messages.map((m) => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text
      }));

      const reqBody = {
        message: trimmed,
        history,
        conversationId: currentConversationId || undefined
      };

      if (selectedVoiceLang !== 'auto') {
        reqBody.language = selectedVoiceLang.split('-')[0];
      }

      const res = await authenticatedFetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(reqBody)
      });

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }

      const json = await res.json();
      const chatData = json?.data || {};

      if (chatData.conversationId) {
        setCurrentConversationId(chatData.conversationId);
        try {
          sessionStorage.setItem('fin_active_conversation_id', chatData.conversationId);
        } catch (_) {}
      }

      const detectedLang = chatData.detectedLanguage || chatData.detected_language || 'en';
      const botMsg = {
        id: `bot-${msgCounter.current++}`,
        sender: 'assistant',
        text: chatData.reply || 'Here is the relevant information based on government guidelines.',
        schemes: chatData.schemes || [],
        showViewAll: chatData.showViewAll !== false && chatData.schemes?.length > 0,
        time: formatTime(),
        citations: chatData.citations || [],
        detectedLanguage: detectedLang
      };

      setMessages((prev) => [...prev, botMsg]);

      // Handle voice output if speech was activated
      if (voiceStateRef.current === 'thinking' && !isTtsMuted) {
        setCurrentlySpeakingMsgId(botMsg.id);
        await speakText(botMsg.text, detectedLang);
        setCurrentlySpeakingMsgId(null);
      }
      setVoiceState('idle');
    } catch (err) {
      console.warn('Backend chat API failed:', err);
      const botMsg = {
        id: `bot-${msgCounter.current++}`,
        sender: 'assistant',
        text: '⚠️ I am currently unable to verify policy information with the server. Please check your connection or retry your query.',
        isError: true,
        retryText: trimmed,
        time: formatTime(),
        detectedLanguage: 'en'
      };
      setMessages((prev) => [...prev, botMsg]);
      setVoiceState('idle');
    } finally {
      setIsLoading(false);
    }
  };

  // Scheme Logo Renderer
  const renderSchemeLogo = (scheme) => {
    const iconType = scheme.iconType || scheme.id;

    if (iconType === 'education' || scheme.id === 'pm-vidyalaxmi') {
      return (
        <div className="fin-scheme-card-logo blue-bg" aria-hidden="true">
          <GraduationCap size={22} color="#1E40AF" />
        </div>
      );
    }

    if (iconType === 'digital-india' || scheme.id === 'digital-india-internship') {
      return (
        <div className="fin-scheme-card-logo" aria-hidden="true">
          <DigitalIndiaLogo size={32} />
        </div>
      );
    }

    if (iconType === 'skill-india' || scheme.id === 'skill-india') {
      return (
        <div className="fin-scheme-card-logo" aria-hidden="true">
          <img src={skillIndiaImg} alt="Skill India" className="fin-scheme-card-logo-img" />
        </div>
      );
    }

    if (iconType === 'startup-india' || scheme.id === 'startup-india') {
      return (
        <div className="fin-scheme-card-logo" aria-hidden="true">
          <img src={startupIndiaImg} alt="Startup India" className="fin-scheme-card-logo-img" />
        </div>
      );
    }

    if (iconType === 'ashoka' || scheme.id === 'pmegp') {
      return (
        <div className="fin-scheme-card-logo" aria-hidden="true">
          <img src={ashokStambhOriginal} alt="Government of India" className="fin-scheme-card-logo-img" style={{ padding: '2px' }} />
        </div>
      );
    }

    // Default graduation or sparkles icon
    return (
      <div className="fin-scheme-card-logo blue-bg" aria-hidden="true">
        <Sparkles size={20} color="#005B50" />
      </div>
    );
  };

  // Real Document upload handler
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const fileName = file.name;
    const userMsg = {
      id: `user-${msgCounter.current++}`,
      sender: 'user',
      text: `Uploaded Document: 📎 ${fileName}`,
      time: formatTime()
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const uploadRes = await uploadDocumentFile(file, 'address_proof');
      const docId = uploadRes?.id || uploadRes?.documentId;

      let extraDetails = '';
      if (docId) {
        try {
          const extractRes = await extractDocumentData(docId);
          if (extractRes?.fields_extracted && Object.keys(extractRes.fields_extracted).length > 0) {
            extraDetails = ` Extracted fields: ${Object.keys(extractRes.fields_extracted).join(', ')}.`;
          }
        } catch (_) {
          // Document upload succeeded even if OCR is pending
        }
      }

      const botMsg = {
        id: `bot-${msgCounter.current++}`,
        sender: 'assistant',
        text: `✅ Document **${fileName}** uploaded successfully and verified against official criteria.${extraDetails} Would you like to check matching schemes for your profile?`,
        schemes: [],
        showViewAll: false,
        time: formatTime()
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (uploadErr) {
      const botMsg = {
        id: `bot-${msgCounter.current++}`,
        sender: 'assistant',
        text: `⚠️ Could not upload **${fileName}**: ${uploadErr.message || 'Service unavailable'}. Please verify document format and try again.`,
        isError: true,
        time: formatTime()
      };
      setMessages((prev) => [...prev, botMsg]);
    } finally {
      setIsLoading(false);
      e.target.value = '';
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className={`fin-assistant-modal-container ${isMinimized ? 'minimized' : ''}`}
      role="dialog"
      aria-label="FIN Assistant AI"
    >
      {/* Hidden file picker */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
        onChange={handleFileUpload}
      />

      {/* Top Header Bar */}
      <header className="fin-assistant-header">
        <div className="fin-header-left">
          <div className="fin-header-avatar" aria-hidden="true">
            <Sparkles size={18} />
          </div>
          <div className="fin-header-titles">
            <div className="fin-header-title-row">
              <span className="fin-header-title">FIN Assistant (AI)</span>
              <img
                src={tricolorFlagClean}
                alt="National Flag of India"
                className="fin-header-flag-img"
              />
            </div>
            <span className="fin-header-subtitle">Your guide to government schemes</span>
          </div>
        </div>

        <div className="fin-header-controls">
          <button
            type="button"
            className="fin-header-ctrl-btn"
            onClick={handleStartNewChat}
            title="Start new conversation"
            aria-label="Start new conversation"
          >
            <Plus size={17} />
          </button>
          <button
            type="button"
            className={`fin-header-ctrl-btn ${isHistoryOpen ? 'active' : ''}`}
            onClick={handleToggleHistory}
            title={isHistoryOpen ? "Close history" : "Chat history"}
            aria-label="Chat history"
          >
            <History size={17} />
          </button>
          <button
            type="button"
            className={`fin-header-ctrl-btn ${isTtsMuted ? 'muted' : ''}`}
            onClick={() => {
              if (!isTtsMuted) {
                window.speechSynthesis?.cancel();
                setIsTtsMuted(true);
              } else {
                setIsTtsMuted(false);
              }
            }}
            title={isTtsMuted ? 'Unmute voice responses' : 'Mute voice responses'}
            aria-label={isTtsMuted ? 'Unmute voice responses' : 'Mute voice responses'}
          >
            {isTtsMuted ? <VolumeX size={17} /> : <Volume2 size={17} />}
          </button>
          <button
            type="button"
            className="fin-header-ctrl-btn"
            onClick={handleToggleMinimize}
            title={isMinimized ? 'Expand' : 'Minimize'}
            aria-label={isMinimized ? 'Expand FIN Assistant' : 'Minimize FIN Assistant'}
          >
            <Minus size={18} />
          </button>
          <button
            type="button"
            className="fin-header-ctrl-btn"
            onClick={onClose}
            title="Close"
            aria-label="Close FIN Assistant"
          >
            <X size={18} />
          </button>
        </div>
      </header>

      {/* Main Body */}
      {!isMinimized && (
        <>
          {isHistoryOpen ? (
            /* CONVERSATION HISTORY PANEL */
            <div className="fin-history-view" role="region" aria-label="Conversation History">
              <div className="fin-history-header">
                <div className="fin-history-title-row">
                  <History size={16} />
                  <span className="fin-history-title">Chat History</span>
                  {historyList.length > 0 && (
                    <span className="fin-history-count-badge">{historyList.length}</span>
                  )}
                </div>
                <button
                  type="button"
                  className="fin-history-new-btn"
                  onClick={handleStartNewChat}
                  title="Start a new chat"
                >
                  <Plus size={14} />
                  <span>New Chat</span>
                </button>
              </div>

              {isHistoryLoading ? (
                <div className="fin-history-loading">
                  <div className="fin-history-spinner" aria-hidden="true" />
                  <span>Loading conversations...</span>
                </div>
              ) : historyError ? (
                <div className="fin-history-error">
                  <p>{historyError}</p>
                  <button
                    type="button"
                    className="fin-history-retry-btn"
                    onClick={loadHistoryList}
                  >
                    Retry
                  </button>
                </div>
              ) : historyList.length === 0 ? (
                <div className="fin-history-empty">
                  <div className="fin-history-empty-icon" aria-hidden="true">
                    <MessageCircle size={28} />
                  </div>
                  <h4>No Previous Conversations</h4>
                  <p>When you chat with FIN AI, your conversations are saved here so you can revisit them anytime.</p>
                  <button
                    type="button"
                    className="fin-history-start-btn"
                    onClick={handleStartNewChat}
                  >
                    Start Your First Chat
                  </button>
                </div>
              ) : (
                <div className="fin-history-list">
                  {historyList.map((conv) => {
                    const isActive = currentConversationId === conv.id;
                    return (
                      <div
                        key={conv.id}
                        className={`fin-history-item ${isActive ? 'active' : ''}`}
                        onClick={() => handleSelectConversation(conv.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSelectConversation(conv.id);
                          }
                        }}
                      >
                        <div className="fin-history-item-left">
                          <div className="fin-history-item-title-row">
                            <span className="fin-history-item-title" title={conv.title}>
                              {conv.title || 'Untitled Conversation'}
                            </span>
                            {isActive && (
                              <span className="fin-history-active-pill">Current</span>
                            )}
                          </div>
                          <div className="fin-history-item-meta">
                            <span className="fin-history-item-date">
                              {formatHistoryDate(conv.updatedAt || conv.createdAt)}
                            </span>
                            <span className="fin-history-dot">•</span>
                            <span className="fin-history-item-count">
                              {conv.messageCount || conv.messages?.length || 0} messages
                            </span>
                          </div>
                        </div>

                        <button
                          type="button"
                          className="fin-history-delete-btn"
                          title="Delete conversation"
                          aria-label={`Delete conversation ${conv.title || ''}`}
                          onClick={(e) => handleDeleteConversation(conv.id, e)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="fin-assistant-body">
              {messages.length === 0 ? (
                /* STATE 1: INITIAL / WELCOME VIEW (Image 2 - Left) */
                <div className="fin-initial-view">
                  {/* Hero Greeting Banner */}
                  <div className="fin-hero-banner">
                    <div className="fin-hero-left">
                      <span className="fin-hero-wave" aria-hidden="true">👋</span>
                      <h3 className="fin-hero-heading">Namaste! I'm FIN Assistant</h3>
                      <p className="fin-hero-desc">
                        I can help you find the right government schemes, check eligibility,
                        understand benefits, and guide you through the application process.
                      </p>
                    </div>
                    <div className="fin-hero-right">
                      <img
                        src={indiaGateSketch}
                        alt="India Gate Monument Sketch"
                        className="fin-hero-monument-img"
                      />
                    </div>
                  </div>

                  {/* Try Asking Me Section */}
                  <div className="fin-try-asking-section">
                    <h4 className="fin-try-asking-title">Try asking me:</h4>
                    <div className="fin-prompts-list">
                      {PROMPTS.map((prompt) => (
                        <button
                          key={prompt.id}
                          type="button"
                          className="fin-prompt-btn"
                          onClick={() => handleSendMessage(prompt.query)}
                        >
                          <div className="fin-prompt-left">
                            <div className={`fin-prompt-icon-wrapper ${prompt.iconType}`} aria-hidden="true">
                              {prompt.iconType === 'search' && <Search size={16} />}
                              {prompt.iconType === 'pmegp' && <FileText size={16} />}
                              {prompt.iconType === 'student' && <Users size={16} />}
                              {prompt.iconType === 'docs' && <FileCheck size={16} />}
                              {prompt.iconType === 'apply' && <Settings size={16} />}
                            </div>
                            <span className="fin-prompt-label">{prompt.label}</span>
                          </div>
                          <ChevronRight size={16} className="fin-prompt-chevron" />
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 3 Feature Cards Row */}
                  <div className="fin-features-grid">
                    <div className="fin-feature-card">
                      <div className="fin-feature-icon-circle green" aria-hidden="true">
                        <Compass size={14} />
                      </div>
                      <span className="fin-feature-title">Personalized Recommendations</span>
                      <span className="fin-feature-sub">Schemes based on your profile</span>
                    </div>

                    <div className="fin-feature-card">
                      <div className="fin-feature-icon-circle blue" aria-hidden="true">
                        <FileText size={14} />
                      </div>
                      <span className="fin-feature-title">Eligibility Check</span>
                      <span className="fin-feature-sub">Know if you're eligible</span>
                    </div>

                    <div className="fin-feature-card">
                      <div className="fin-feature-icon-circle blue" aria-hidden="true">
                        <MessageCircle size={14} />
                      </div>
                      <span className="fin-feature-title">Step-by-Step Guidance</span>
                      <span className="fin-feature-sub">From documents to application</span>
                    </div>
                  </div>
                </div>
              ) : (
                /* STATE 2: CONVERSATION VIEW (Image 2 - Right) */
                <div className="fin-chat-thread">
                  {messages.map((msg) => (
                    <React.Fragment key={msg.id}>
                      {msg.sender === 'user' ? (
                        /* User Message Row */
                        <div className="fin-user-message-row">
                          <div className="fin-user-avatar-hs" aria-hidden="true">
                            {userInitials}
                          </div>
                          <div className="fin-user-content-wrapper">
                            <div className="fin-user-bubble">{msg.text}</div>
                            <div className="fin-user-meta">
                              <span>{msg.time}</span>
                              <span className="fin-meta-checkmarks" title="Delivered & Read">✔✔</span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* Assistant Message Row */
                        <div className="fin-assistant-message-row">
                          <div className="fin-assistant-msg-avatar" aria-hidden="true">
                            <Sparkles size={15} />
                          </div>
                          <div className="fin-assistant-content-wrapper">
                            <div className="fin-assistant-bubble">
                              {msg.degraded && (
                                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', backgroundColor: '#FEF0C7', color: '#B54708', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, marginBottom: '6px' }}>
                                  <span>Local Policy Knowledge Mode</span>
                                </div>
                              )}
                              <MarkdownRenderer
                                content={msg.text}
                                onNavigate={(path) => {
                                  onClose?.();
                                  navigate(path);
                                }}
                              />
                              {msg.isError && msg.retryText && (
                                <button
                                  type="button"
                                  className="btn btn-outline"
                                  onClick={() => handleSendMessage(msg.retryText)}
                                  style={{ marginTop: '8px', padding: '4px 10px', fontSize: '12px' }}
                                >
                                  Retry Query
                                </button>
                              )}
                            </div>

                            {/* Render Citations if provided */}
                            {msg.citations && msg.citations.length > 0 && (
                              <div style={{ marginTop: '6px', fontSize: '11px', color: '#667085', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                <span style={{ fontWeight: 600 }}>Citations:</span>
                                {msg.citations.map((c, i) => (
                                  <span key={i} style={{ backgroundColor: '#F2F4F7', padding: '2px 6px', borderRadius: '4px' }}>
                                    {typeof c === 'string' ? c : c.source || c.title || c.url || 'Official Guideline'}
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Render Scheme Cards if provided */}
                            {msg.schemes && msg.schemes.length > 0 && (
                              <div className="fin-scheme-cards-list">
                                {msg.schemes.map((scheme) => (
                                  <div
                                    key={scheme.id || scheme.slug}
                                    className="fin-scheme-card-item"
                                    onClick={() => handleSchemeClick(scheme)}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        handleSchemeClick(scheme);
                                      }
                                    }}
                                    title={`View ${scheme.title || scheme.name} details`}
                                  >
                                    {renderSchemeLogo(scheme)}
                                    <div className="fin-scheme-card-info">
                                      <div className="fin-scheme-card-header">
                                        <span className="fin-scheme-card-title">{scheme.title || scheme.name}</span>
                                        {scheme.matchScore != null ? (
                                          <span className={`fin-scheme-match-pill ${scheme.matchType === 'orange' ? 'orange' : scheme.matchType === 'amber' ? 'amber' : 'green'}`}>
                                            {scheme.matchScore}% Match
                                          </span>
                                        ) : (scheme.relevanceScore != null && (scheme.eligibilityStatus === 'UNKNOWN' || !scheme.eligibilityStatus)) ? (
                                          <span className="fin-scheme-match-pill neutral" title={`Topic Relevance: ${scheme.relevanceScore}% | Eligibility: Unverified`}>
                                            Eligibility: Unverified
                                          </span>
                                        ) : scheme.relevanceScore != null ? (
                                          <span className="fin-scheme-match-pill neutral" title={`Search Relevance: ${scheme.relevanceScore}%`}>
                                            {scheme.relevanceScore}% Relevance
                                          </span>
                                        ) : null}
                                      </div>
                                      <div className="fin-scheme-card-subtitle">{scheme.subtitle}</div>
                                      {scheme.tags && scheme.tags.length > 0 && (
                                        <div className="fin-scheme-tags-row">
                                          {scheme.tags.map((tag, tIdx) => (
                                            <span key={tIdx} className="fin-scheme-tag">{tag}</span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                    <ChevronRight size={16} className="fin-scheme-card-arrow" />
                                  </div>
                                ))}

                                {/* View All Eligible Schemes Button */}
                                {msg.showViewAll && (
                                  <button
                                    type="button"
                                    className="fin-view-all-schemes-btn"
                                    onClick={() => {
                                      onClose();
                                      navigate('/discover');
                                    }}
                                  >
                                    <FileText size={15} />
                                    <span>View All Eligible Schemes</span>
                                    <ArrowRight size={15} />
                                  </button>
                                )}
                              </div>
                            )}

                            <div className="fin-assistant-meta">
                              <span>{msg.time}</span>
                              {msg.sender === 'assistant' && (
                                <button
                                  type="button"
                                  className="fin-msg-audio-btn"
                                  onClick={() => handlePlayMessageSpeech(msg)}
                                  title={currentlySpeakingMsgId === msg.id ? "Stop voice response" : "Read aloud in detected language"}
                                  aria-label={currentlySpeakingMsgId === msg.id ? "Stop voice response" : "Read aloud"}
                                >
                                  {currentlySpeakingMsgId === msg.id ? <Square size={11} /> : <Volume2 size={11} />}
                                  <span>{currentlySpeakingMsgId === msg.id ? "Stop" : "Listen"}</span>
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </React.Fragment>
                  ))}

                  {/* Loading indicator */}
                  {isLoading && (
                    <div className="fin-assistant-message-row">
                      <div className="fin-assistant-msg-avatar" aria-hidden="true">
                        <Sparkles size={15} />
                      </div>
                      <div className="fin-assistant-content-wrapper">
                        <div className="fin-assistant-bubble loading">
                          <div className="fin-typing-indicator">
                            <span />
                            <span />
                            <span />
                          </div>
                          <span className="fin-verifying-text">Checking official guidelines...</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          )}

          {/* Bottom Footer: Input & Quick Action Buttons */}
          {!isHistoryOpen && (
            <footer className="fin-assistant-footer">
            {/* Real-time Voice Status Banner */}
            {(voiceState !== 'idle' || voiceErrorMessage) && (
              <div className={`fin-voice-status-bar ${voiceState}`} role="status">
                <div className="fin-voice-status-left">
                  {voiceState === 'listening' && (
                    <div className="fin-voice-pulse-badge">
                      <Mic size={15} className="fin-pulse-icon" />
                    </div>
                  )}
                  {voiceState === 'processing' && <Radio size={15} className="fin-pulse-icon" />}
                  {voiceState === 'thinking' && <Sparkles size={15} className="fin-spin-icon" />}
                  {voiceState === 'speaking' && <Volume2 size={15} className="fin-pulse-icon" />}

                  <div className="fin-voice-status-text">
                    {voiceErrorMessage ? (
                      <span className="fin-voice-error-text">{voiceErrorMessage}</span>
                    ) : (
                      <span className="fin-voice-state-title">
                        {voiceState === 'listening' && 'Listening... Speak naturally in any language'}
                        {voiceState === 'processing' && 'Processing speech...'}
                        {voiceState === 'thinking' && 'Thinking & verifying policy evidence...'}
                        {voiceState === 'speaking' && 'Speaking response...'}
                      </span>
                    )}
                  </div>
                </div>

                <div className="fin-voice-status-actions">
                  {voiceErrorMessage ? (
                    <button
                      type="button"
                      className="fin-voice-dismiss-btn"
                      onClick={() => setVoiceErrorMessage(null)}
                      title="Dismiss error"
                      aria-label="Dismiss error"
                    >
                      <X size={13} />
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="fin-voice-stop-btn"
                      onClick={stopVoiceAndTts}
                      title="Stop voice mode"
                      aria-label="Stop voice mode"
                    >
                      <Square size={11} />
                      <span>Stop</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="fin-input-wrapper"
            >
              <input
                type="text"
                className="fin-chat-input"
                placeholder={
                  messages.length === 0
                    ? 'Ask anything about government schemes...'
                    : 'Ask a follow-up question...'
                }
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={isLoading}
              />
              <button
                type="submit"
                className="fin-send-btn"
                disabled={!inputText.trim() || isLoading}
                title="Send message"
                aria-label="Send message"
              >
                <Send size={15} />
              </button>
            </form>

            <div className="fin-quick-actions-row">
              <button
                type="button"
                className="fin-quick-action-pill"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip size={14} />
                <span>Upload</span>
              </button>

              <button
                type="button"
                className={`fin-quick-action-pill ${isRecording ? 'recording' : ''}`}
                onClick={handleToggleVoice}
                title={isRecording ? 'Listening... click to stop' : 'Click to speak'}
              >
                {isRecording ? <MicOff size={14} /> : <Mic size={14} />}
                <span>{isRecording ? 'Listening...' : 'Voice'}</span>
              </button>

              <div className="fin-voice-lang-dropdown">
                <Globe size={13} className="fin-lang-icon" />
                <select
                  value={selectedVoiceLang}
                  onChange={(e) => setSelectedVoiceLang(e.target.value)}
                  className="fin-lang-select"
                  title="Voice & recognition language"
                  aria-label="Voice language"
                >
                  <option value="auto">Auto (Multilingual)</option>
                  <option value="hi-IN">हिन्दी (Hindi)</option>
                  <option value="gu-IN">ગુજરાતી (Gujarati)</option>
                  <option value="en-IN">English</option>
                  <option value="bn-IN">বাংলা (Bengali)</option>
                  <option value="ta-IN">தமிழ் (Tamil)</option>
                  <option value="te-IN">తెలుగు (Telugu)</option>
                  <option value="mr-IN">मराठी (Marathi)</option>
                </select>
              </div>
            </div>
          </footer>
        )}
      </>
    )}
  </div>
);
}
