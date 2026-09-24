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
