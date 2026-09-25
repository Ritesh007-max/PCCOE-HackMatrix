const userServices = require('../services/userServices');
const profileService = require('../services/profileService');

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 6;

const sanitizeUser = (user) => ({
    id: user.id,
    email: user.email,
    user_metadata: user.user_metadata,
    created_at: user.created_at,
    updated_at: user.updated_at
});

const sanitizeUserWithProfile = async (user) => {
    const baseUser = sanitizeUser(user);
    const profile = await profileService.getProfileById(user.id);
    if (profile) {
        baseUser.user_metadata = {
            ...baseUser.user_metadata,
            full_name: profile.full_name || baseUser.user_metadata?.full_name,
            phone: profile.phone || baseUser.user_metadata?.phone
        };
    }
    return baseUser;
};

const validateRegistrationInput = ({ email, password, fullName }) => {
    const errors = [];

    if (!email || !password || !fullName) {
        errors.push('Email, password and full name are required');
    }

    if (email && !EMAIL_REGEX.test(email)) {
        errors.push('Invalid email format');
    }

    const pwdStr = password !== undefined && password !== null ? String(password) : '';
    if (pwdStr && pwdStr.length < MIN_PASSWORD_LENGTH) {
        errors.push(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
    }

    return errors;
};

const validateLoginInput = ({ email, password }) => {
    const errors = [];

    if (!email || password === undefined || password === null || password === '') {
        errors.push('Email and password are required');
    }

    if (email && !EMAIL_REGEX.test(email)) {
        errors.push('Invalid email format');
    }

    return errors;
};

const registerUser = async (req, res, next) => {
    try {
        const email = req.body.email ? String(req.body.email).trim().toLowerCase() : '';
        const password = req.body.password !== undefined && req.body.password !== null ? String(req.body.password) : '';
        const fullName = req.body.fullName || req.body.name || req.body.full_name;
        const phone = req.body.phone || req.body.mobile;

        const validationErrors = validateRegistrationInput({ email, password, fullName });
        if (validationErrors.length > 0) {
            return res.status(400).json({
                success: false,
                message: validationErrors.join(', ')
            });
        }

        const { user, session } = await userServices.registerUser({ email, password, fullName, phone });

        if (!user) {
            return res.status(502).json({
                success: false,
                message: 'Account could not be created'
            });
        }

        const userWithProfile = await sanitizeUserWithProfile(user);

        return res.status(201).json({
            success: true,
            message: 'Account created successfully. You are now signed in.',
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            expires_in: session.expires_in,
            expires_at: session.expires_at,
            token_type: session.token_type,
            user: userWithProfile
        });

    } catch (error) {
        next(error);
    }
};

const loginUser = async (req, res, next) => {
    try {
        const email = req.body.email ? String(req.body.email).trim().toLowerCase() : '';
        const password = req.body.password !== undefined && req.body.password !== null ? String(req.body.password) : '';

        const validationErrors = validateLoginInput({ email, password });
        if (validationErrors.length > 0) {
            return res.status(400).json({
                success: false,
                message: validationErrors.join(', ')
            });
        }

        const { session, user } = await userServices.loginUser({ email, password });

        if (!session) {
            return res.status(401).json({
                success: false,
                message: 'Invalid credentials'
            });
        }

        const userWithProfile = await sanitizeUserWithProfile(user);

        return res.status(200).json({
            success: true,
            message: 'Login successful',
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            expires_in: session.expires_in,
            expires_at: session.expires_at,
            token_type: session.token_type,
            user: userWithProfile
        });

    } catch (error) {
        next(error);
    }
};

const refreshToken = async (req, res, next) => {
    try {
        const refresh_token = req.body.refresh_token || req.body.refreshToken;

        if (!refresh_token) {
            return res.status(400).json({
                success: false,
                message: 'Refresh token is required'
            });
        }

        const { session, user } = await userServices.refreshToken(refresh_token);

        if (!session) {
            return res.status(401).json({
                success: false,
                message: 'Invalid or expired refresh token'
            });
        }

        const userWithProfile = await sanitizeUserWithProfile(user);

        return res.status(200).json({
            success: true,
            message: 'Token refreshed successfully',
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            expires_in: session.expires_in,
            expires_at: session.expires_at,
            token_type: session.token_type,
            user: userWithProfile
        });

    } catch (error) {
        next(error);
    }
};

const getMe = async (req, res, next) => {
    try {
        if (!req.user) {
            return res.status(401).json({
                success: false,
                message: 'User not authenticated'
            });
        }

        const userWithProfile = await sanitizeUserWithProfile(req.user);

        return res.status(200).json({
            success: true,
            user: userWithProfile
        });

    } catch (error) {
        next(error);
    }
};

const logoutUser = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;
        const token = authHeader?.split(' ')[1];

        if (token) {
            await supabaseClient.auth.signOut();
        }

        return res.status(200).json({
            success: true,
            message: 'Logged out successfully'
        });

    } catch (error) {
        next(error);
    }
};

const { supabaseClient } = require('../config/supabaseConfig');

module.exports = {
    registerUser,
    loginUser,
    refreshToken,
    getMe,
    logoutUser
};
