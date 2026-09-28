const express = require('express');
const { chat } = require('../controllers/chatController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

const optionalAuth = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) return next();
    authMiddleware(req, res, next);
};

router.post('/', optionalAuth, chat);

module.exports = router;
