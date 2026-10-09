const express = require('express');
const { chat, getChatHistory, getConversation, deleteConversation } = require('../controllers/chatController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// POST /api/chat — Auth is optional; if token present, response is personalised and persisted
// We use a soft auth: try to parse user, continue even if missing
const optionalAuth = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) return next();
    authMiddleware(req, res, next);
};

// Authenticated Chat History Endpoints
router.get('/history', authMiddleware, getChatHistory);
router.get('/history/:id', authMiddleware, getConversation);
router.delete('/history/:id', authMiddleware, deleteConversation);

// Main Chat Endpoint
router.post('/', optionalAuth, chat);

module.exports = router;

