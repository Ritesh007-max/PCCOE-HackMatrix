const express = require('express');
const { analyzeApplication } = require('../controllers/applicationController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// POST /api/applications/analyze — Requires authentication
router.post('/analyze', authMiddleware, analyzeApplication);

module.exports = router;
