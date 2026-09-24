const { supabaseAdmin } = require('../config/supabaseConfig');

const REQUIRED_FIELDS = [
    'full_name', 'phone', 'age', 'gender', 'category',
    'state', 'district', 'area_type', 'occupation',
    'annual_income', 'dob', 'applicant_type'
];

const OPTIONAL_FIELDS = ['land_acres', 'is_disabled'];

const calculateProfileCompletion = (profile) => {
    let completed = 0;
    for (const field of REQUIRED_FIELDS) {
        const value = profile[field];
        if (value !== null && value !== undefined && value !== '') {
            completed++;
        }
    }
    return Math.round((completed / REQUIRED_FIELDS.length) * 100);
};

const sanitizeProfile = (profile) => {
    if (!profile) return null;
    return {
        id: profile.id,
        full_name: profile.full_name,
        phone: profile.phone,
        age: profile.age,
        gender: profile.gender,
        category: profile.category,
        state: profile.state,
        district: profile.district,
        area_type: profile.area_type,
        occupation: profile.occupation,
        annual_income: profile.annual_income,
        land_acres: profile.land_acres,
        is_disabled: profile.is_disabled,
        dob: profile.dob,
        applicant_type: profile.applicant_type,
        profile_completed_percent: profile.profile_completed_percent,
        created_at: profile.created_at,
        updated_at: profile.updated_at
    };
};

const inMemoryProfiles = new Map();

const isTableMissingError = (err) => {
    return err && (
        err.code === '42P01' ||
        (err.message && (err.message.includes('schema cache') || err.message.includes('does not exist')))
    );
};

const getProfileById = async (userId) => {
    try {
        const { data, error } = await supabaseAdmin
            .from('profiles')
            .select('*')
            .eq('id', userId)
            .single();

        if (error) {
            if (error.code === 'PGRST116') {
                return null;
            }
            if (isTableMissingError(error)) {
                console.warn('[WARN] public.profiles table missing in Supabase. Using in-memory fallback. Run database_setup.sql to persist in DB.');
                return inMemoryProfiles.get(userId) || null;
            }
            const serviceError = new Error(error.message);
            serviceError.status = 500;
            throw serviceError;
        }

        return data ? sanitizeProfile(data) : null;
    } catch (err) {
        if (isTableMissingError(err)) {
            return inMemoryProfiles.get(userId) || null;
        }
        throw err;
    }
};

const createProfile = async (userId, userMetadata = {}) => {
    const initialProfile = {
        id: userId,
        full_name: userMetadata.full_name || null,
        phone: userMetadata.phone || null,
        age: null,
        gender: null,
        category: null,
        state: null,
        district: null,
        area_type: null,
        occupation: null,
        annual_income: null,
        land_acres: 0,
        is_disabled: false,
        dob: null,
        applicant_type: null,
        profile_completed_percent: 0
    };

    try {
        const { data, error } = await supabaseAdmin
            .from('profiles')
            .insert(initialProfile)
            .select()
            .single();

        if (error) {
            if (isTableMissingError(error)) {
                inMemoryProfiles.set(userId, initialProfile);
                return sanitizeProfile(initialProfile);
            }
            const serviceError = new Error(error.message);
            serviceError.status = 500;
            throw serviceError;
        }

        return sanitizeProfile(data);
    } catch (err) {
        if (isTableMissingError(err)) {
            inMemoryProfiles.set(userId, initialProfile);
            return sanitizeProfile(initialProfile);
        }
        throw err;
    }
};

const updateProfile = async (userId, updates) => {
    const existingProfile = await getOrCreateProfile(userId);
    const allowedUpdates = {};
    const allFields = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS, 'dob', 'applicant_type'];

    for (const field of allFields) {
        if (updates[field] !== undefined) {
            allowedUpdates[field] = updates[field];
        }
    }

    if (Object.keys(allowedUpdates).length === 0) {
        return existingProfile;
    }

    allowedUpdates.profile_completed_percent = calculateProfileCompletion({
        ...existingProfile,
        ...allowedUpdates
    });

    try {
        const { data, error } = await supabaseAdmin
            .from('profiles')
            .update(allowedUpdates)
            .eq('id', userId)
            .select()
            .single();

        if (error) {
            if (isTableMissingError(error)) {
                const updated = { ...existingProfile, ...allowedUpdates };
                inMemoryProfiles.set(userId, updated);
                return sanitizeProfile(updated);
            }
            const serviceError = new Error(error.message);
            serviceError.status = 500;
            throw serviceError;
        }

        return sanitizeProfile(data);
    } catch (err) {
        if (isTableMissingError(err)) {
            const updated = { ...existingProfile, ...allowedUpdates };
            inMemoryProfiles.set(userId, updated);
            return sanitizeProfile(updated);
        }
        throw err;
    }
};

const getOrCreateProfile = async (userId, userMetadata = {}) => {
    let profile = await getProfileById(userId);
    if (!profile) {
        profile = await createProfile(userId, userMetadata);
    }
    return profile;
};

module.exports = {
    getProfileById,
    createProfile,
    updateProfile,
    getOrCreateProfile,
    calculateProfileCompletion,
    REQUIRED_FIELDS
};
