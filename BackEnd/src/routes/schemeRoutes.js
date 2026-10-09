const express = require('express');
const {
    searchSchemes,
    getSchemeById,
    getSchemeStats,
    recommendSchemes,
    getSchemeFaqs,
    getAllFaqsHandler,
    getApplicableSchemes
} = require('../controllers/schemeController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// GET /api/schemes/stats — Category counts & total scheme stats
router.get('/stats', getSchemeStats);

// GET /api/schemes/applicable — Unified canonical catalog for jurisdiction
router.get('/applicable', getApplicableSchemes);

// POST & GET /api/schemes/recommend & /api/schemes/recommended — Personalized scheme recommendations
router.post('/recommend', authMiddleware, recommendSchemes);
router.get('/recommend', authMiddleware, recommendSchemes);
router.post('/recommended', authMiddleware, recommendSchemes);
router.get('/recommended', authMiddleware, recommendSchemes);

// GET /api/schemes and GET /api/schemes/search
router.get('/', searchSchemes);
router.get('/search', searchSchemes);

// POST /api/schemes/search — Search schemes (auth optional but supported)
router.post('/search', searchSchemes);

// GET /api/schemes/faqs — Paginated list of all FAQs (declared before /:id)
router.get('/faqs', getAllFaqsHandler);

// GET /api/schemes/:slug/faqs — Get FAQs for a specific scheme by slug (MUST be declared before /:id)
router.get('/:slug/faqs', getSchemeFaqs);

// GET /api/schemes/:id — Get scheme details by ID or Slug
router.get('/:id', getSchemeById);

module.exports = router;
