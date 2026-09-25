const applicationService = require('../services/applicationService');

/**
 * POST /api/applications/analyze
 * Body: { schemeId }
 * Auth: Bearer token required
 */
const analyzeApplication = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const { schemeId, profile } = req.body;

        if (!schemeId) {
            return res.status(400).json({ success: false, message: 'schemeId is required in request body' });
        }

        const result = await applicationService.analyzeApplication(userId, schemeId, profile);
        return res.status(200).json({
            success: true,
            data: result
        });
    } catch (error) {
        next(error);
    }
};

const listApplications = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const applications = await applicationService.listApplications(userId);
        return res.status(200).json({
            success: true,
            count: applications.length,
            data: applications
        });
    } catch (error) {
        next(error);
    }
};

const createApplication = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const application = await applicationService.createApplication(userId, req.body);
        return res.status(201).json({
            success: true,
            message: 'Application submitted successfully',
            data: application
        });
    } catch (error) {
        next(error);
    }
};

const getApplicationById = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const application = await applicationService.getApplicationById(userId, req.params.id);
        return res.status(200).json({
            success: true,
            data: application
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    analyzeApplication,
    listApplications,
    createApplication,
    getApplicationById
};

