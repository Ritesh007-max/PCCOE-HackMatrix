const { supabaseClient } = require('../config/supabaseConfig');

const authMiddleware = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                success: false,
                message: 'Authorization header missing or invalid format. Expected: Bearer <token>'
            });
        }

        const token = authHeader.split(' ')[1];

        if (!token) {
            return res.status(401).json({
                success: false,
                message: 'Access token is missing'
            });
        }

        const isDevToken = token === 'development-only-bypass-token' || token === 'google-oauth-demo-token';

        // Normalize NODE_ENV safely to prevent case-variation or whitespace bypass
        const rawNodeEnv = process.env.NODE_ENV !== undefined && process.env.NODE_ENV !== null
            ? String(process.env.NODE_ENV).trim().toLowerCase()
            : '';

        const isExplicitDevEnv = rawNodeEnv === 'development';
        const isProductionOrStaging = rawNodeEnv === 'production' || rawNodeEnv === 'staging';
        const isBypassFlagEnabled = process.env.ENABLE_DEV_AUTH_BYPASS === 'true' || process.env.VITE_ENABLE_DEV_AUTH_BYPASS === 'true';

        // Bypass is strictly allowed ONLY in explicit development mode with opt-in flag enabled
        const isDevBypassAllowed = isExplicitDevEnv && isBypassFlagEnabled && !isProductionOrStaging;

        if (isDevToken) {
            if (!isDevBypassAllowed) {
                const envName = rawNodeEnv || 'unset';
                return res.status(401).json({
                    success: false,
                    message: `Development authentication bypass is strictly prohibited in ${envName} environment. Genuine authentication is required.`
                });
            }
            const devUserId = process.env.DEV_USER_ID || '05403000-bcac-4287-b36f-721eefe3c7e4';
            const devUserEmail = process.env.DEV_USER_EMAIL || 'dev@fin.gov.in';
            req.user = { id: devUserId, email: devUserEmail };
            req.token = token;
            return next();
        }

        const { data: { user }, error } = await supabaseClient.auth.getUser(token);

        if (error || !user) {
            return res.status(401).json({
                success: false,
                message: 'Invalid or expired token'
            });
        }

        req.user = user;
        req.token = token;
        next();
    } catch (error) {
        return res.status(401).json({
            success: false,
            message: 'Token verification failed'
        });
    }
};

module.exports = authMiddleware;
