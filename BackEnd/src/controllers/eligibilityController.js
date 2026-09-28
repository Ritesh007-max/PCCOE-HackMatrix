const eligibilityService = require('../services/eligibilityService');

const checkEligibility = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const { schemeId, profile } = req.body;

        if (!schemeId) {
            return res.status(400).json({ success: false, message: 'schemeId is required in request body' });
        }

        const result = await eligibilityService.checkEligibility(userId, schemeId, profile);
        return res.status(200).json({
            success: true,
            data: result
        });
    } catch (error) {
        next(error);
    }
};

module.exports = { checkEligibility };
