const dashboardService = require('../services/dashboardService');

const getDashboard = async (req, res, next) => {
    try {
        const userId = req.user.id;

        const dashboardData = await dashboardService.getDashboardData(userId);

        return res.status(200).json({
            success: true,
            data: dashboardData
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    getDashboard
};