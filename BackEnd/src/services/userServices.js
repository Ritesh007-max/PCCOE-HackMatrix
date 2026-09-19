const supabase = require("../config/supabaseConfig");

const createUser = async ({ email, password, fullName, phone }) => {
    const { data, error } = await supabase.auth.admin.createUser({
        email,
        password,
        email_confirm: false,
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

module.exports = {
    createUser
};