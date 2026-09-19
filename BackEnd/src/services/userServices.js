const supabase = require("../config/supabaseConfig");

const createUser = async ({ email, password, fullName, phone }) => {
    const { data, error } = await supabase.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
        user_metadata: {
            full_name: fullName,
            phone: phone
        }
    });

    if (error) {
        throw new Error(error.message);
    }

    return data.user;
};

const loginUser = async ({ email, password }) => {
    const { data, error } = await supabase.auth.signInWithPassword({
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

module.exports = {
    createUser,
    loginUser
};