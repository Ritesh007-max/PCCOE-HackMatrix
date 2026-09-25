const schemeService = require('../services/schemeService');

/**
 * POST /api/schemes/search
 * Body: { query?, filters?: { type?, ministry?, tags?, maxBenefit? }, limit? }
 */
const searchSchemes = async (req, res, next) => {
    try {
        const { query, filters, limit } = req.body;
        const result = await schemeService.searchSchemes({ query, filters, limit });
        return res.status(200).json({
            success: true,
            ...result
        });
    } catch (error) {
        next(error);
    }
};

/**
 * GET /api/schemes/:id
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

module.exports = { searchSchemes, getSchemeById };
