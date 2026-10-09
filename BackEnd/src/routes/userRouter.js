const express = require('express');
const {
    registerUser,
    loginUser,
    refreshToken,
    getMe,
    changePassword
} = require('../controllers/userController');
const authMiddleware = require('../middleware/authMiddleware');
const userServices = require('../services/userServices');

const router = express.Router();

const logoutUser = async (req, res, next) => {
    try {
        await userServices.logoutUser(req.token);

        return res.status(200).json({
            success: true,
            message: 'Logged out successfully'
        });
    } catch (error) {
        next(error);
    }
};

router.post('/register', registerUser);
router.post('/login', loginUser);
router.post('/refresh', refreshToken);
router.get('/me', authMiddleware, getMe);
router.post('/logout', authMiddleware, logoutUser);
router.post('/change-password', authMiddleware, changePassword);

module.exports = router;
