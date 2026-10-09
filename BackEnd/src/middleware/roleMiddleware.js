const { supabaseAdmin } = require('../config/supabaseConfig');

/**
 * Ensures user role is hydrated from the authoritative database record.
 * Never trusts frontend or client-provided role hints.
 */
const attachUserRole = async (req) => {
    if (req.user && (!req.user.appRole || req.user.role === 'authenticated')) {
        try {
            const { data } = await supabaseAdmin
                .from('users')
                .select('role, full_name, email')
                .eq('id', req.user.id)
                .maybeSingle();

            const realRole = data?.role || 'user';
            req.user.role = realRole;
            req.user.appRole = realRole;
            req.user.full_name = data?.full_name || req.user.user_metadata?.full_name || 'User';
        } catch (_) {
            req.user.role = 'user';
            req.user.appRole = 'user';
        }
    }
    return req.user?.appRole || req.user?.role || 'user';
};

/**
 * Strict Reviewer authorization middleware.
 * Verifies that the authenticated user has role === 'reviewer' in the database.
 */
const requireReviewer = async (req, res, next) => {
    try {
        if (!req.user) {
            return res.status(401).json({
                success: false,
                message: 'Authentication required'
            });
        }

        const role = await attachUserRole(req);
        if (role !== 'reviewer') {
            return res.status(403).json({
                success: false,
                message: 'Access denied: Government reviewer privileges required'
            });
        }

        next();
    } catch (err) {
        next(err);
    }
};

/**
 * Citizen route middleware.
 */
const requireCitizen = async (req, res, next) => {
    try {
        if (!req.user) {
            return res.status(401).json({
                success: false,
                message: 'Authentication required'
            });
        }

        const role = await attachUserRole(req);
        if (role === 'reviewer') {
            return res.status(403).json({
                success: false,
                message: 'Reviewer accounts cannot submit or modify citizen-only personal applications'
            });
        }

        next();
    } catch (err) {
        next(err);
    }
};

module.exports = {
    attachUserRole,
    requireReviewer,
    requireCitizen
};
