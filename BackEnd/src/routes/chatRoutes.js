const express = require('express');
const { chat } = require('../controllers/chatController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// POST /api/chat — Auth is optional; if token present, response is personalised
// We use a soft auth: try to parse user, continue even if missing
const optionalAuth = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) return next();
    authMiddleware(req, res, next);
};

router.post('/', optionalAuth, chat);

module.exports = router;
