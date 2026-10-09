const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { supabaseAdmin } = require('../config/supabaseConfig');

const DATA_DIR = path.resolve(__dirname, '../../data');
const STORAGE_FILE = path.join(DATA_DIR, 'chat_conversations.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    try {
        fs.mkdirSync(DATA_DIR, { recursive: true });
    } catch (_) {}
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ensureUuid = (val) => {
    if (!val) return crypto.randomUUID();
    if (UUID_REGEX.test(val)) return String(val).toLowerCase();
    const hash = crypto.createHash('md5').update(String(val)).digest('hex');
    return `${hash.slice(0, 8)}-${hash.slice(8, 12)}-4${hash.slice(13, 16)}-8${hash.slice(17, 20)}-${hash.slice(20, 32)}`.toLowerCase();
};

/**
 * In-memory index of conversations, backed by atomic file writes and Supabase sync.
 * Structure: Map of conversationId -> Conversation object
 */
let conversationStore = null;

const loadStore = () => {
    if (conversationStore) return conversationStore;
    conversationStore = new Map();

    try {
        if (fs.existsSync(STORAGE_FILE)) {
            const raw = fs.readFileSync(STORAGE_FILE, 'utf8');
            if (raw.trim()) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                    for (const conv of parsed) {
                        if (conv && conv.id && conv.userId) {
                            conversationStore.set(conv.id, conv);
                        }
                    }
                }
            }
        }
    } catch (err) {
        console.warn('[chatHistoryService] Could not read local chat store:', err.message);
    }

    return conversationStore;
};

const persistStore = () => {
    try {
        if (!fs.existsSync(DATA_DIR)) {
            fs.mkdirSync(DATA_DIR, { recursive: true });
        }
        const store = loadStore();
        const arrayData = Array.from(store.values());
        fs.writeFileSync(STORAGE_FILE, JSON.stringify(arrayData, null, 2), 'utf8');
    } catch (err) {
        console.warn('[chatHistoryService] Failed to persist chat store:', err.message);
    }
};

/**
 * Best-effort sync to Supabase database audit_logs
 */
const syncToDatabase = async (conversation) => {
    if (!supabaseAdmin) return;
    try {
        const entityUuid = ensureUuid(conversation.id);
        const appUuid = UUID_REGEX.test(conversation.userId) ? conversation.userId : null;

        await supabaseAdmin.from('audit_logs').insert({
            applicant_id: appUuid,
            action: 'FIN_CHAT_CONVERSATION',
            entity_type: 'conversation',
            entity_id: entityUuid,
            metadata: {
                userId: conversation.userId,
                conversationId: conversation.id,
                title: conversation.title,
                messageCount: (conversation.messages || []).length,
                updatedAt: conversation.updatedAt
            }
        });
    } catch (_) {
        // Supabase sync failure should not block fast chat operation
    }
};

/**
 * Derive a concise, readable title from the first question
 */
const deriveTitle = (text) => {
    if (!text || typeof text !== 'string') return 'New Conversation';
    const clean = text.replace(/[*#_`~>[\]()]/g, '').trim().split('\n')[0];
    if (clean.length <= 48) return clean;
    return `${clean.slice(0, 45)}...`;
};

/**
 * Record a user + assistant chat turn into a conversation.
 */
const recordChatTurn = async (userId, conversationId, userTurn, assistantTurn) => {
    if (!userId) return { conversationId: conversationId || crypto.randomUUID() };

    const store = loadStore();
    const cleanUserId = String(userId).trim();
    const effectiveConvId = conversationId && String(conversationId).trim() ? String(conversationId).trim() : crypto.randomUUID();

    const now = new Date().toISOString();
    let conv = store.get(effectiveConvId);

    if (!conv) {
        const userText = typeof userTurn === 'string' ? userTurn : userTurn?.text || '';
        conv = {
            id: effectiveConvId,
            userId: cleanUserId,
            title: deriveTitle(userText),
            createdAt: now,
            updatedAt: now,
            messages: []
        };
    } else {
        // Enforce user isolation: if an existing conversation belongs to another user,
        // do not overwrite; create a separate conversation for this user.
        if (conv.userId !== cleanUserId) {
            const newConvId = crypto.randomUUID();
            const userText = typeof userTurn === 'string' ? userTurn : userTurn?.text || '';
            conv = {
                id: newConvId,
                userId: cleanUserId,
                title: deriveTitle(userText),
                createdAt: now,
                updatedAt: now,
                messages: []
            };
        }
    }

    // Format User Message
    const userMsgObj = typeof userTurn === 'string' ? {
        id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sender: 'user',
        text: userTurn,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        createdAt: now
    } : {
        id: userTurn.id || `user-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sender: 'user',
        text: userTurn.text || '',
        time: userTurn.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        createdAt: userTurn.createdAt || now
    };

    // Format Assistant Message
    const botMsgObj = typeof assistantTurn === 'string' ? {
        id: `bot-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sender: 'assistant',
        text: assistantTurn,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        schemes: [],
        citations: [],
        createdAt: now
    } : {
        id: assistantTurn.id || `bot-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sender: 'assistant',
        text: assistantTurn.text || assistantTurn.reply || '',
        time: assistantTurn.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        schemes: assistantTurn.schemes || [],
        showViewAll: assistantTurn.showViewAll || Boolean(assistantTurn.schemes?.length),
        citations: assistantTurn.citations || [],
        detectedLanguage: assistantTurn.detectedLanguage || 'en',
        createdAt: assistantTurn.createdAt || now
    };

    conv.messages.push(userMsgObj, botMsgObj);
    conv.updatedAt = now;

    store.set(conv.id, conv);
    persistStore();
    syncToDatabase(conv);

    return {
        conversationId: conv.id,
        title: conv.title
    };
};

/**
 * List conversations for a specific authenticated user.
 * Strictly enforces user isolation (User A never sees User B's conversations).
 */
const listConversations = async (userId) => {
    if (!userId) return [];
    const cleanUserId = String(userId).trim();
    const store = loadStore();

    const userConvs = [];
    for (const conv of store.values()) {
        if (conv.userId === cleanUserId) {
            const msgCount = (conv.messages || []).length;
            const lastMsg = msgCount > 0 ? conv.messages[msgCount - 1].text : '';
            userConvs.push({
                id: conv.id,
                title: conv.title || 'Untitled Conversation',
                createdAt: conv.createdAt,
                updatedAt: conv.updatedAt,
                messageCount: msgCount,
                lastMessage: lastMsg ? (lastMsg.length > 80 ? `${lastMsg.slice(0, 77)}...` : lastMsg) : ''
            });
        }
    }

    // Sort by latest update first
    userConvs.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    return userConvs;
};

/**
 * Get a specific conversation by ID for an authenticated user.
 * Ensures the conversation belongs to the requested user.
 */
const getConversation = async (userId, conversationId) => {
    if (!userId || !conversationId) return null;
    const cleanUserId = String(userId).trim();
    const cleanConvId = String(conversationId).trim();
    const store = loadStore();

    const conv = store.get(cleanConvId);
    if (!conv) return null;

    // Strict tenant isolation check
    if (conv.userId !== cleanUserId) {
        return null;
    }

    return conv;
};

/**
 * Delete a specific conversation for an authenticated user.
 */
const deleteConversation = async (userId, conversationId) => {
    if (!userId || !conversationId) return false;
    const cleanUserId = String(userId).trim();
    const cleanConvId = String(conversationId).trim();
    const store = loadStore();

    const conv = store.get(cleanConvId);
    if (!conv) return false;

    if (conv.userId !== cleanUserId) {
        return false;
    }

    store.delete(cleanConvId);
    persistStore();
    return true;
};

/**
 * For testing and cleanup
 */
const clearAllConversations = (userId = null) => {
    const store = loadStore();
    if (userId) {
        const cleanUserId = String(userId).trim();
        for (const [id, conv] of store.entries()) {
            if (conv.userId === cleanUserId) {
                store.delete(id);
            }
        }
    } else {
        store.clear();
    }
    persistStore();
};

module.exports = {
    recordChatTurn,
    listConversations,
    getConversation,
    deleteConversation,
    clearAllConversations,
    deriveTitle
};
