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

const changePassword = async (userId, userEmail, { currentPassword, newPassword }, isDevBypass = false) => {
    if (!currentPassword || typeof currentPassword !== 'string' || !currentPassword.trim()) {
        const error = new Error('Current password is required');
        error.status = 400;
        throw error;
    }
    if (!newPassword || typeof newPassword !== 'string' || newPassword.length < 6) {
        const error = new Error('New password must be at least 6 characters');
        error.status = 400;
        throw error;
    }
    if (currentPassword === newPassword) {
        const error = new Error('New password must be different from current password');
        error.status = 400;
        throw error;
    }

    if (isDevBypass) {
        return { success: true, message: 'Password changed successfully' };
    }

    // Authenticate current password against Supabase if email is known
    if (userEmail) {
        const { error: signInError } = await supabaseClient.auth.signInWithPassword({
            email: userEmail,
            password: currentPassword
        });
        if (signInError) {
            const error = new Error('Current password is incorrect');
            error.status = 400;
            throw error;
        }
    }

    // Update password with admin client
    const { error: updateError } = await supabaseAdmin.auth.admin.updateUserById(userId, {
        password: newPassword
    });

    if (updateError) {
        const error = new Error(updateError.message || 'Failed to update password');
        error.status = updateError.status || 500;
        throw error;
    }

    return { success: true, message: 'Password changed successfully' };
};

module.exports = {
    registerUser,
    loginUser,
    refreshToken,
    getCurrentUser,
    logoutUser,
    changePassword
};
