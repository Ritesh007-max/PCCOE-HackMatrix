const { supabaseClient, supabaseAdmin } = require('../config/supabaseConfig');

const registerUser = async ({ email, password, fullName, phone }) => {
    const { data, error } = await supabaseAdmin.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
        user_metadata: {
            full_name: fullName,
            phone: phone
        }
    });

    if (error) {
        const serviceError = new Error(error.message);
        serviceError.status = error.status;
        throw serviceError;
    }

    return data.user;
};

const loginUser = async ({ email, password }) => {
    const { data, error } = await supabaseClient.auth.signInWithPassword({
        email,
        password
    });

    if (error) {
        const serviceError = new Error(error.message);
        serviceError.status = error.status;
        throw serviceError;
    }

    return data;
};

const refreshToken = async (refreshToken) => {
    const { data, error } = await supabaseClient.auth.refreshSession({
        refresh_token: refreshToken
    });

    if (error) {
        const serviceError = new Error(error.message);
        serviceError.status = error.status;
        throw serviceError;
    }

    return data;
};

const getCurrentUser = async (token) => {
    const { data: { user }, error } = await supabaseClient.auth.getUser(token);

    if (error) {
        const serviceError = new Error(error.message);
        serviceError.status = error.status;
        throw serviceError;
    }

    return user;
};

const logoutUser = async (token) => {
    const { error } = await supabaseAdmin.auth.admin.signOut(token);

    if (error) {
        const serviceError = new Error(error.message);
        serviceError.status = error.status;
        throw serviceError;
    }
};

module.exports = {
    registerUser,
    loginUser,
    refreshToken,
    getCurrentUser,
    logoutUser
};
