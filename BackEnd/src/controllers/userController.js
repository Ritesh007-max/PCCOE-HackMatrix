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

module.exports = {
    registerUser
};