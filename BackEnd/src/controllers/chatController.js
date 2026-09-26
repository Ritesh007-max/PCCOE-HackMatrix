const chatService = require('../services/chatService');

/**
 * POST /api/chat
 * Body: { message, history?: [{role, content}] }
 * Auth: Optional Bearer token (req.user may be set)
 */
const chat = async (req, res, next) => {
    try {
        const userId = req.user?.id || null;
        const { message, history, conversationId } = req.body;

        if (!message || !message.trim()) {
            return res.status(400).json({ success: false, message: 'message is required in request body' });
        }

        const result = await chatService.chat(userId, message.trim(), history || [], conversationId || null);
        return res.status(200).json({
            success: true,
            data: result
        });
    } catch (error) {
        next(error);
    }
};

module.exports = { chat };
