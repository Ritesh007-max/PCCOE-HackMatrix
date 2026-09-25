const express = require('express');
const { searchSchemes, getSchemeById } = require('../controllers/schemeController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// POST /api/schemes/search — Search schemes (auth optional but supported)
router.post('/search', searchSchemes);

// GET /api/schemes/:id — Get scheme details by ID
router.get('/:id', getSchemeById);

module.exports = router;
