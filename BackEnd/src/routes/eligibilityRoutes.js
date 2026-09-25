const express = require('express');
const { checkEligibility } = require('../controllers/eligibilityController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// POST /api/eligibility/check — Requires authentication (profile is loaded from req.user.id)
router.post('/check', authMiddleware, checkEligibility);

module.exports = router;
