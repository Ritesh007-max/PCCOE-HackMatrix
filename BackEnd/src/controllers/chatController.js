const chatService = require('../services/chatService');
const chatHistoryService = require('../services/chatHistoryService');

/**
 * POST /api/chat
 * Body: { message, history?: [{role, content}], conversationId?, language? }
 * Auth: Optional Bearer token (req.user may be set)
 */
const chat = async (req, res, next) => {
    try {
        const userId = req.user?.id || null;
        const { message, history, conversationId, language } = req.body;

        if (!message || !message.trim()) {
            return res.status(400).json({ success: false, message: 'message is required in request body' });
        }

        const result = await chatService.chat(userId, message.trim(), history || [], conversationId || null, { language });
        return res.status(200).json({
            success: true,
            data: result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/chat/history
 * Auth: Required Bearer token
 * Returns array of previous conversations for the authenticated user only.
 */
const getChatHistory = async (req, res, next) => {
    try {
        const userId = req.user?.id;
        if (!userId) {
            return res.status(401).json({ success: false, message: 'Authentication required to view chat history' });
        }
        const history = await chatHistoryService.listConversations(userId);
        return res.status(200).json({
            success: true,
            data: history
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/chat/history/:id
 * Auth: Required Bearer token
 * Returns full conversation messages for the authenticated user only.
 */
const getConversation = async (req, res, next) => {
    try {
        const userId = req.user?.id;
        if (!userId) {
            return res.status(401).json({ success: false, message: 'Authentication required to view conversation' });
        }
        const { id } = req.params;
        const conversation = await chatHistoryService.getConversation(userId, id);
        if (!conversation) {
            return res.status(404).json({ success: false, message: 'Conversation not found or access denied' });
        }
        return res.status(200).json({
            success: true,
            data: conversation
        });
    } catch (error) {
        next(error);
    }
};

/**
 * DELETE /api/chat/history/:id
 * Auth: Required Bearer token
 * Deletes a conversation for the authenticated user.
 */
const deleteConversation = async (req, res, next) => {
    try {
        const userId = req.user?.id;
        if (!userId) {
            return res.status(401).json({ success: false, message: 'Authentication required to delete conversation' });
        }
        const { id } = req.params;
        const deleted = await chatHistoryService.deleteConversation(userId, id);
        if (!deleted) {
            return res.status(404).json({ success: false, message: 'Conversation not found or access denied' });
        }
        return res.status(200).json({
            success: true,
            message: 'Conversation deleted successfully'
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    chat,
    getChatHistory,
    getConversation,
    deleteConversation
};

