const chatService = require('../services/chatService');

const chat = async (req, res, next) => {
    try {
        const userId = req.user?.id || null;
        const { message, history } = req.body;

        if (!message || !message.trim()) return res.status(400).json({ success: false, message: 'message is required in request body' });

        const result = await chatService.chat(userId, message.trim(), history || []);
        return res.status(200).json({
            success: true,
            data: result
        });
    } catch (error) {
        next(error);
    }
};

module.exports = { chat };
