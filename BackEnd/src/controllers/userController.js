const userServices = require("../services/userServices");

const registerUser = async (req, res) => {
    try {
        const { email, password, fullName, phone } = req.body;

        if (!email || !password || !fullName) {
            return res.status(400).json({
                success: false,
                message: "Email, password and full name are required"
            });
        }

        const user = await userServices.createUser({
            email,
            password,
            fullName,
            phone
        });

        return res.status(201).json({
            success: true,
            message: "User registered successfully",
            user: {
                id: user.id,
                email: user.email
            }
        });

    } catch (error) {
        return res.status(400).json({
            success: false,
            message: error.message
        });
    }
};

const loginUser = async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({
                success: false,
                message: "Email and password are required"
            });
        }

        const { session, user } = await userServices.loginUser({ email, password });

        return res.status(200).json({
            success: true,
            message: "Login successful",
            session,
            user: {
                id: user.id,
                email: user.email,
                user_metadata: user.user_metadata
            }
        });

    } catch (error) {
        const status = Number.isInteger(error.status) && error.status >= 400 && error.status < 500
            ? error.status
            : 500;

        return res.status(status).json({
            success: false,
            message: error.message
        });
    }
};

module.exports = {
    registerUser,
    loginUser
};