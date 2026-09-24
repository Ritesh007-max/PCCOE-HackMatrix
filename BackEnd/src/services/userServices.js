const { supabaseClient, supabaseAdmin } = require('../config/supabaseConfig');

const registerUser = async ({ email, password, fullName, phone }) => {
    const { data, error } = await supabaseAdmin.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
        user_metadata: {
            full_name: fullName,
            phone
        }
    });

    if (error) {
        const serviceError = new Error(error.message);
        serviceError.status = error.status;
        throw serviceError;
    }

    if (data.user) {
        const { error: userRowError } = await supabaseAdmin
            .from('users')
            .upsert({
                id: data.user.id,
                email: data.user.email,
                full_name: fullName,
                phone: phone || null,
                role: 'user'
            }, { onConflict: 'id' });

        if (userRowError) {
            const serviceError = new Error(`Account created but user record could not be saved: ${userRowError.message}`);
            serviceError.status = 500;
            throw serviceError;
        }
    }

    const { data: authData, error: signInError } = await supabaseClient.auth.signInWithPassword({
        email,
        password
    });

    if (signInError || !authData.session) {
        const serviceError = new Error(signInError?.message || 'Account created, but automatic sign-in failed');
        serviceError.status = signInError?.status || 401;
        throw serviceError;
    }

    return { user: authData.user || data.user, session: authData.session };
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
