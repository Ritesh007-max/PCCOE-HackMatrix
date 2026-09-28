const profileService = require('../services/profileService');

const parseBoolean = (value) => {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        if (normalized === 'true') return true;
        if (normalized === 'false') return false;
    }
    return null;
};

const isValidDateOnly = (value) => {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const date = new Date(`${value}T00:00:00.000Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
};

const getProfile = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const profile = await profileService.getProfileById(userId);

        return res.status(200).json({
            success: true,
            data: profile
        });
    } catch (error) {
        next(error);
    }
};

const updateProfile = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const updates = req.body;
        if (!updates || typeof updates !== 'object' || Array.isArray(updates)) return res.status(400).json({ success: false, message: 'Profile updates must be a JSON object' });
        

        const allowedFields = profileService.ACCEPTED_FIELDS;
        const unsupportedFields = Object.keys(updates).filter((field) => !allowedFields.includes(field));
        if (unsupportedFields.length > 0) {
            return res.status(400).json({
                success: false,
                message: `Unsupported profile fields: ${unsupportedFields.join(', ')}`
            });
        }

        const filteredUpdates = {};
        for (const field of allowedFields) {
            if (updates[field] !== undefined) {
                filteredUpdates[field] = updates[field];
            }
        }

        if (filteredUpdates.date_of_birth !== undefined && filteredUpdates.dob === undefined) filteredUpdates.dob = filteredUpdates.date_of_birth;
    
        delete filteredUpdates.date_of_birth;
        if (filteredUpdates.city !== undefined && filteredUpdates.district === undefined) filteredUpdates.district = filteredUpdates.city;
    
        delete filteredUpdates.city;
        if (filteredUpdates.caste_category !== undefined && filteredUpdates.category === undefined) {
            filteredUpdates.category = filteredUpdates.caste_category;
        }
        delete filteredUpdates.caste_category;
        if (filteredUpdates.disability_status !== undefined && filteredUpdates.is_disabled === undefined) {
            filteredUpdates.is_disabled = filteredUpdates.disability_status;
        }
        delete filteredUpdates.disability_status;
        if (filteredUpdates.land_holding_acres !== undefined && filteredUpdates.land_acres === undefined) {
            filteredUpdates.land_acres = filteredUpdates.land_holding_acres;
        }
        delete filteredUpdates.land_holding_acres;

        if (Object.keys(filteredUpdates).length === 0) {
            return res.status(400).json({
                success: false,
                message: 'No valid fields provided for update'
            });
        }

        const validateText = (field, maxLength, { required = false } = {}) => {
            const value = filteredUpdates[field];
            if (value === undefined) return null;
            if (!required && (value === null || value === '')) {
                filteredUpdates[field] = null;
                return null;
            }
            if (typeof value !== 'string' || value.trim().length === 0 || value.trim().length > maxLength) {
                return `${field} must be ${required ? 'a non-empty' : 'a'} string of at most ${maxLength} characters`;
            }
            filteredUpdates[field] = value.trim();
            return null;
        };
        for (const [field, max, required] of [
            ['full_name', 120, true], ['state', 100], ['district', 100],
            ['address_line1', 200], ['address_line2', 200], ['pincode', 20],
            ['country', 100], ['pan_number', 10], ['aadhaar_number', 12],
            ['employment_status', 60], ['employer_name', 150]
        ]) {
            const validationMessage = validateText(field, max, { required });
            if (validationMessage) return res.status(400).json({ success: false, message: validationMessage });
        }
        if (filteredUpdates.phone !== undefined &&
            (typeof filteredUpdates.phone !== 'string' || !/^\+?[0-9][0-9\s()-]{6,19}$/.test(filteredUpdates.phone.trim()))) {
            return res.status(400).json({ success: false, message: 'Phone must be a valid phone number' });
        }
        if (filteredUpdates.phone !== undefined) filteredUpdates.phone = filteredUpdates.phone.trim();

        // Empty date inputs are used to clear the stored date.
        if (filteredUpdates.dob === '') filteredUpdates.dob = null;

        // Normalize income strings like "Below ₹1 Lakh" or numeric
        if (filteredUpdates.income !== undefined && filteredUpdates.annual_income === undefined) {
            const incomeMap = {
                'Below ₹1 Lakh': 80000,
                '₹1 Lakh - ₹2.5 Lakhs': 180000,
                '₹2.5 Lakhs - ₹5 Lakhs': 350000,
                '₹5 Lakhs - ₹10 Lakhs': 750000,
                'Above ₹10 Lakhs': 1200000,
            };
            if (incomeMap[filteredUpdates.income]) {
                filteredUpdates.annual_income = incomeMap[filteredUpdates.income];
            } else {
                const numericOnly = parseFloat(String(filteredUpdates.income).replace(/[^0-9.]/g, ''));
                if (!isNaN(numericOnly)) filteredUpdates.annual_income = numericOnly;
            }
        }

        if (filteredUpdates.annual_income !== undefined && filteredUpdates.annual_income !== null) {
            const income = typeof filteredUpdates.annual_income === 'number' ? filteredUpdates.annual_income :
                (typeof filteredUpdates.annual_income === 'string' && /^\d+(\.\d+)?$/.test(filteredUpdates.annual_income) ? Number(filteredUpdates.annual_income) : NaN);
            if (!Number.isFinite(income) || income < 0) {
                return res.status(400).json({
                    success: false,
                    message: 'Annual income must be a valid positive number'
                });
            }
            filteredUpdates.annual_income = income;
        }

        if (filteredUpdates.income === '' && filteredUpdates.annual_income === undefined) {
            filteredUpdates.annual_income = null;
            delete filteredUpdates.income;
        }

        if (filteredUpdates.income !== undefined && filteredUpdates.annual_income === undefined) {
            const income = typeof filteredUpdates.income === 'number' ? filteredUpdates.income :
                (typeof filteredUpdates.income === 'string' && /^\d+(\.\d+)?$/.test(filteredUpdates.income) ? Number(filteredUpdates.income) : NaN);
            if (!Number.isFinite(income) || income < 0) {
                return res.status(400).json({ success: false, message: 'Income must be a supported range or a non-negative number' });
            }
            filteredUpdates.annual_income = income;
            delete filteredUpdates.income;
        }

        if (filteredUpdates.land_acres !== undefined) {
            const land = typeof filteredUpdates.land_acres === 'number' ? filteredUpdates.land_acres :
                (typeof filteredUpdates.land_acres === 'string' && /^\d+(\.\d+)?$/.test(filteredUpdates.land_acres) ? Number(filteredUpdates.land_acres) : NaN);
            if (!Number.isFinite(land) || land < 0) {
                return res.status(400).json({
                    success: false,
                    message: 'Land acres must be a valid positive number'
                });
            }
            filteredUpdates.land_acres = land;
        }

        for (const field of ['is_disabled', 'is_minority', 'is_woman_entrepreneur', 'is_ex_serviceman']) {
            if (filteredUpdates[field] !== undefined) {
                const value = parseBoolean(filteredUpdates[field]);
                if (value === null) {
                    return res.status(400).json({ success: false, message: `${field} must be true or false` });
                }
                filteredUpdates[field] = value;
            }
        }

        if (filteredUpdates.disability_percentage !== undefined && filteredUpdates.disability_percentage !== null) {
            const percentage = typeof filteredUpdates.disability_percentage === 'number'
                ? filteredUpdates.disability_percentage
                : (typeof filteredUpdates.disability_percentage === 'string' && /^\d+$/.test(filteredUpdates.disability_percentage)
                    ? Number(filteredUpdates.disability_percentage)
                    : NaN);
            if (!Number.isInteger(percentage) || percentage < 0 || percentage > 100) {
                return res.status(400).json({ success: false, message: 'Disability percentage must be an integer from 0 to 100' });
            }
            filteredUpdates.disability_percentage = percentage;
        }

        const validCategories = ['General', 'OBC', 'SC', 'ST', 'EWS'];
        if (filteredUpdates.category && !validCategories.includes(filteredUpdates.category)) {
            return res.status(400).json({
                success: false,
                message: `Category must be one of: ${validCategories.join(', ')}`
            });
        }

        // Normalize and validate occupation
        if (filteredUpdates.occupation) {
            const occMap = {
                'student': 'student',
                'farmer': 'farmer',
                'farmer / agriculture': 'farmer',
                'agriculture': 'farmer',
                'self employed / msme': 'msme',
                'small enterprise (msme)': 'msme',
                'msme': 'msme',
                'salaried employee': 'salaried',
                'salaried': 'salaried',
                'self-employed': 'self-employed',
                'unemployed / job seeker': 'unemployed',
                'unemployed': 'unemployed',
                'other': 'other'
            };
            const lowerOcc = String(filteredUpdates.occupation).trim().toLowerCase();
            const normalizedOccupation = occMap[lowerOcc];
            if (!normalizedOccupation) {
                return res.status(400).json({ success: false, message: 'Occupation must be a supported value' });
            }
            filteredUpdates.occupation = normalizedOccupation;
        }

        const validOccupations = ['farmer', 'msme', 'student', 'salaried', 'self-employed', 'unemployed', 'other'];
        if (filteredUpdates.occupation && !validOccupations.includes(filteredUpdates.occupation)) {
            return res.status(400).json({ success: false, message: 'Occupation must be a supported value' });
        }

        // Normalize and validate gender
        if (filteredUpdates.gender) {
            const genderMap = {
                'male': 'male',
                'female': 'female',
                'transgender': 'other',
                'other': 'other',
                'prefer not to say': 'prefer_not_to_say',
                'prefer_not_to_say': 'prefer_not_to_say'
            };
            const lowerGen = String(filteredUpdates.gender).trim().toLowerCase();
            if (!genderMap[lowerGen]) {
                return res.status(400).json({ success: false, message: 'Gender must be a supported value' });
            }
            filteredUpdates.gender = genderMap[lowerGen];
        }

        // Validate dob (date of birth)
        if (filteredUpdates.dob !== undefined) {
            if (filteredUpdates.dob !== null && filteredUpdates.dob !== '') {
                if (!isValidDateOnly(filteredUpdates.dob)) {
                    return res.status(400).json({
                        success: false,
                        message: 'Date of birth must be a valid date (YYYY-MM-DD)'
                    });
                }
                const dobDate = new Date(`${filteredUpdates.dob}T00:00:00.000Z`);
                if (dobDate > new Date()) {
                    return res.status(400).json({
                        success: false,
                        message: 'Date of birth cannot be in the future'
                    });
                }
            }
        }

        const profile = await profileService.updateProfile(userId, filteredUpdates);

        return res.status(200).json({
            success: true,
            message: 'Profile updated successfully',
            data: profile
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    getProfile,
    updateProfile
};
