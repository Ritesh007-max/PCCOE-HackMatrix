const reviewerService = require('../services/reviewerService');

const getDashboardStats = async (req, res, next) => {
    try {
        const stats = await reviewerService.getReviewerDashboardStats();
        return res.status(200).json({
            success: true,
            data: stats
        });
    } catch (err) {
        next(err);
    }
};

const getApplicationsQueue = async (req, res, next) => {
    try {
        const { status, page, limit } = req.query;
        const result = await reviewerService.getReviewQueue({
            status,
            page: page ? parseInt(page, 10) : 1,
            limit: limit ? parseInt(limit, 10) : 50
        });
        return res.status(200).json({
            success: true,
            data: result.applications,
            total: result.total
        });
    } catch (err) {
        next(err);
    }
};

const getApplicationDetails = async (req, res, next) => {
    try {
        const { id } = req.params;
        const details = await reviewerService.getApplicationReviewDetails(id);
        return res.status(200).json({
            success: true,
            data: details
        });
    } catch (err) {
        next(err);
    }
};

const submitDecision = async (req, res, next) => {
    try {
        const { id } = req.params;
        const { decision, remark } = req.body || {};
        const result = await reviewerService.submitReviewDecision({
            reviewerId: req.user.id,
            reviewerUser: req.user,
            applicationId: id,
            decision,
            remark
        });
        return res.status(200).json(result);
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getDashboardStats,
    getApplicationsQueue,
    getApplicationDetails,
    submitDecision
};
