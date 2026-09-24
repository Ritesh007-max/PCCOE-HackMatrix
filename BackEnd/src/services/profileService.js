const { supabaseAdmin } = require('../config/supabaseConfig');

// Applicant details are optional and live in applicant_profiles. The row ID is
// the corresponding public.users ID; ordinary account reads never create it.
const FIELD_TO_COLUMN = {
    full_name: 'full_name',
    phone: 'phone',
    dob: 'date_of_birth',
    date_of_birth: 'date_of_birth',
    gender: 'gender',
    address_line1: 'address_line1',
    address_line2: 'address_line2',
    district: 'city',
    city: 'city',
    state: 'state',
    pincode: 'pincode',
    country: 'country',
    pan_number: 'pan_number',
    aadhaar_number: 'aadhaar_number',
    annual_income: 'annual_income',
    income: 'annual_income',
    employment_status: 'employment_status',
    occupation: 'occupation',
    employer_name: 'employer_name',
    category: 'caste_category',
    caste_category: 'caste_category',
    is_disabled: 'disability_status',
    disability_status: 'disability_status',
    disability_percentage: 'disability_percentage',
    land_acres: 'land_holding_acres',
    land_holding_acres: 'land_holding_acres',
    is_minority: 'is_minority',
    is_woman_entrepreneur: 'is_woman_entrepreneur',
    is_ex_serviceman: 'is_ex_serviceman'
};

const PERSISTED_FIELDS = Object.keys(FIELD_TO_COLUMN);
const ACCEPTED_FIELDS = [...new Set(PERSISTED_FIELDS)];
const PROFILE_SELECT = [
    'id', 'full_name', 'phone', 'date_of_birth', 'gender', 'address_line1',
    'address_line2', 'city', 'state', 'pincode', 'country', 'pan_number',
    'aadhaar_number', 'annual_income', 'employment_status', 'occupation',
    'employer_name', 'caste_category', 'disability_status',
    'disability_percentage', 'land_holding_acres', 'is_minority',
    'is_woman_entrepreneur', 'is_ex_serviceman', 'created_at', 'updated_at'
].join(', ');

const COMPLETION_FIELDS = [
    'full_name', 'phone', 'date_of_birth', 'gender', 'address_line1', 'city',
    'state', 'pincode', 'annual_income', 'occupation', 'caste_category'
];

const calculateProfileCompletion = (profile) => {
    const completed = COMPLETION_FIELDS.filter((field) => {
        const value = profile[field];
        return value !== null && value !== undefined && value !== '';
    }).length;
    return Math.round((completed / COMPLETION_FIELDS.length) * 100);
};

const toProfile = (row) => row ? ({
    ...row,
    dob: row.date_of_birth,
    district: row.city,
    category: row.caste_category,
    is_disabled: row.disability_status,
    land_acres: row.land_holding_acres,
    income: row.annual_income,
    profile_completed_percent: calculateProfileCompletion(row)
}) : null;

const throwDatabaseError = (error) => {
    const serviceError = new Error(error.message);
    serviceError.status = 500;
    throw serviceError;
};

const getProfileById = async (userId) => {
    const { data, error } = await supabaseAdmin
        .from('applicant_profiles')
        .select(PROFILE_SELECT)
        .eq('id', userId)
        .maybeSingle();

    if (error) throwDatabaseError(error);
    return toProfile(data);
};

const mapUpdatesToColumns = (updates) => {
    const row = {};
    const aliases = new Set([
        'date_of_birth', 'city', 'income', 'caste_category',
        'disability_status', 'land_holding_acres'
    ]);
    const entries = Object.entries(updates).sort(([left], [right]) =>
        Number(aliases.has(right)) - Number(aliases.has(left))
    );
    for (const [field, value] of entries) {
        const column = FIELD_TO_COLUMN[field];
        // If both a UI alias and a physical/canonical field are supplied, the
        // canonical value wins.
        if (column && value !== undefined) row[column] = value;
    }
    return row;
};

// Called only by an explicit applicant profile save, never during signup/login.
const updateProfile = async (userId, updates) => {
    const changes = mapUpdatesToColumns(updates);
    if (Object.keys(changes).length === 0) {
        const existing = await getProfileById(userId);
        if (existing) return existing;
        const error = new Error('No applicant profile fields were provided');
        error.status = 400;
        throw error;
    }

    const { data: existing, error: lookupError } = await supabaseAdmin
        .from('applicant_profiles')
        .select('id')
        .eq('id', userId)
        .maybeSingle();
    if (lookupError) throwDatabaseError(lookupError);

    let query;
    if (existing) {
        query = supabaseAdmin
            .from('applicant_profiles')
            .update(changes)
            .eq('id', userId);
    } else {
        if (!changes.full_name) {
            const error = new Error('Full name is required to create an applicant profile');
            error.status = 400;
            throw error;
        }
        query = supabaseAdmin
            .from('applicant_profiles')
            .insert({ id: userId, ...changes });
    }

    const { data, error } = await query.select(PROFILE_SELECT).single();
    if (error) throwDatabaseError(error);
    return toProfile(data);
};

module.exports = {
    getProfileById,
    updateProfile,
    calculateProfileCompletion,
    PERSISTED_FIELDS,
    ACCEPTED_FIELDS
};
