const express = require('express');
const { chat } = require('../controllers/chatController');
const { supabaseClient } = require('../config/supabaseConfig');

const router = express.Router();

// POST /api/chat — Auth is optional; if valid token present, response is personalised
// Soft auth: try to parse user, continue gracefully even if missing or unverified
const optionalAuth = async (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) return next();

    const token = authHeader.split(' ')[1];
    if (!token) return next();

    try {
        const { data: { user }, error } = await supabaseClient.auth.getUser(token);
        if (!error && user) {
            req.user = user;
            req.token = token;
        }
    } catch (_) {
        // Soft auth: continue without user if token check fails
    }
    next();
};

router.post('/', optionalAuth, chat);

module.exports = router;
