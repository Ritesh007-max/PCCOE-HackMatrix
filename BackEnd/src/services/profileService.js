const { supabaseAdmin } = require('../config/supabaseConfig');

// public.users is the application's only persisted user/profile table.
const PERSISTED_FIELDS = ['full_name', 'phone'];
const REQUIRED_FIELDS = ['full_name', 'phone'];

const calculateProfileCompletion = (profile) => {
    const completed = REQUIRED_FIELDS.filter((field) => {
        const value = profile[field];
        return value !== null && value !== undefined && value !== '';
    }).length;
    return Math.round((completed / REQUIRED_FIELDS.length) * 100);
};

const toProfile = (row) => ({
    id: row.id,
    email: row.email,
    full_name: row.full_name,
    phone: row.phone,
    role: row.role,
    age: null,
    dob: null,
    gender: null,
    category: null,
    state: null,
    district: null,
    area_type: null,
    occupation: null,
    annual_income: null,
    income: null,
    applicant_type: null,
    land_acres: null,
    is_disabled: null,
    profile_completed_percent: calculateProfileCompletion(row),
    created_at: row.created_at,
    updated_at: null
});

const throwDatabaseError = (error) => {
    const serviceError = new Error(error.message);
    serviceError.status = 500;
    throw serviceError;
};

const getProfileById = async (userId) => {
    const { data, error } = await supabaseAdmin
        .from('users')
        .select('id, email, full_name, phone, role, created_at')
        .eq('id', userId)
        .maybeSingle();

    if (error) throwDatabaseError(error);
    return data ? toProfile(data) : null;
};

const createProfile = async (userId, userMetadata = {}) => {
    const row = {
        id: userId,
        email: userMetadata.email,
        full_name: userMetadata.full_name || null,
        phone: userMetadata.phone || null,
        role: 'user'
    };

    const { data, error } = await supabaseAdmin
        .from('users')
        .upsert(row, { onConflict: 'id' })
        .select('id, email, full_name, phone, role, created_at')
        .single();

    if (error) throwDatabaseError(error);
    return toProfile(data);
};

const updateProfile = async (userId, updates) => {
    const existing = await getProfileById(userId);
    if (!existing) {
        const error = new Error('User record was not found');
        error.status = 404;
        throw error;
    }

    const changes = {};
    for (const field of PERSISTED_FIELDS) {
        if (updates[field] !== undefined) changes[field] = updates[field];
    }
    if (Object.keys(changes).length === 0) return existing;

    const { data, error } = await supabaseAdmin
        .from('users')
        .update(changes)
        .eq('id', userId)
        .select('id, email, full_name, phone, role, created_at')
        .single();

    if (error) throwDatabaseError(error);
    return toProfile(data);
};

const getOrCreateProfile = async (userId, userMetadata = {}) => {
    const existing = await getProfileById(userId);
    return existing || createProfile(userId, userMetadata);
};

module.exports = {
    getProfileById,
    createProfile,
    updateProfile,
    getOrCreateProfile,
    calculateProfileCompletion,
    REQUIRED_FIELDS,
    PERSISTED_FIELDS
};
