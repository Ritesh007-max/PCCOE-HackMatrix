const schemeService = require('../services/schemeService');

/**
 * POST /api/schemes/search
 * Body: { query?, filters?: { category?, type?, ministry?, tags?, maxBenefit?, state?, socialCategory? }, limit?, offset? }
 */
const searchSchemes = async (req, res, next) => {
    try {
        const query = req.body?.query ?? req.query?.query ?? req.query?.q ?? '';
        const limit = req.body?.limit ?? (req.query?.limit ? Number(req.query.limit) : 50);
        const offset = req.body?.offset ?? (req.query?.offset ? Number(req.query.offset) : 0);
        const filters = {
            ...(req.body?.filters || {}),
            ...(req.query?.category ? { category: req.query.category } : {}),
            ...(req.query?.state ? { state: req.query.state } : {}),
            ...(req.query?.type ? { type: req.query.type } : {}),
            ...(req.query?.ministry ? { ministry: req.query.ministry } : {}),
            ...(req.query?.socialCategory ? { socialCategory: req.query.socialCategory } : {}),
            ...(req.query?.maxBenefit ? { maxBenefit: req.query.maxBenefit } : {}),
            ...(req.query?.databaseOnly === 'true' || req.query?.databaseOnly === true ? { databaseOnly: true } : {})
        };
        const result = await schemeService.searchSchemes({ query, filters, limit, offset });
        return res.status(200).json({
            success: true,
            ...result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/schemes/stats
 * Live scheme stats and category counts from database
 */
const getSchemeStats = async (req, res, next) => {
    try {
        const stats = await schemeService.getSchemeStats();
        return res.status(200).json({
            success: true,
            ...stats
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/schemes/:id
 * Fetches scheme details by ID or Slug
 */
const getSchemeById = async (req, res, next) => {
    try {
        const { id } = req.params;
        const result = await schemeService.getSchemeById(id);
        return res.status(200).json({
            success: true,
            ...result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/schemes/:slug/faqs
 * Fetches FAQs for a specific scheme by slug
 */
const getSchemeFaqs = async (req, res, next) => {
    try {
        const { slug } = req.params;
        if (!slug || !slug.trim()) {
            return res.status(400).json({
                success: false,
                message: 'Scheme slug is required'
            });
        }
        const result = await schemeService.getFaqsBySchemeSlug(slug.trim());
        return res.status(200).json({
            success: true,
            ...result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/schemes/faqs
 * Fetches paginated list of all FAQs
 */
const getAllFaqsHandler = async (req, res, next) => {
    try {
        const limit = req.query?.limit ? Number(req.query.limit) : 50;
        const offset = req.query?.offset ? Number(req.query.offset) : 0;
        const result = await schemeService.getAllFaqs({ limit, offset });
        return res.status(200).json({
            success: true,
            ...result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * POST /api/schemes/recommend
 * Recommends schemes based on authenticated user's canonical facts in Intelligence
 */
const recommendSchemes = async (req, res, next) => {
    try {
        const applicantId = req.user?.id;
        if (!applicantId) {
            return res.status(401).json({
                success: false,
                error: 'Unauthorized: Authentication required for personalized recommendations'
            });
        }
        const query = req.body?.query ?? req.query?.query ?? 'schemes matching my profile and state';
        const top_k = req.body?.top_k ?? (req.query?.top_k ? Number(req.query.top_k) : 10);
        const state_override = req.body?.state_override ?? req.query?.state_override;
        const category_override = req.body?.category_override ?? req.query?.category_override;

        const result = await schemeService.recommendSchemes(applicantId, {
            query,
            top_k,
            state_override,
            category_override
        });

        return res.status(200).json({
            success: true,
            ...result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/schemes/applicable
 * Returns unified canonical catalog of schemes applicable to applicant's state & Central jurisdiction
 */
const getApplicableSchemes = async (req, res, next) => {
    try {
        const state = req.query?.state || req.user?.state || 'Gujarat';
        const catalog = await schemeService.getApplicableSchemesCatalog(state);
        return res.status(200).json({
            success: true,
            ...catalog
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    searchSchemes,
    getSchemeById,
    getSchemeStats,
    recommendSchemes,
    getSchemeFaqs,
    getAllFaqsHandler,
    getApplicableSchemes
};
