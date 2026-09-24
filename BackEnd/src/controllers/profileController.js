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
        const userMetadata = { email: req.user.email, ...(req.user.user_metadata || {}) };

        const profile = await profileService.getOrCreateProfile(userId, userMetadata);

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
        if (!updates || typeof updates !== 'object' || Array.isArray(updates)) {
            return res.status(400).json({ success: false, message: 'Profile updates must be a JSON object' });
        }

        const allowedFields = profileService.PERSISTED_FIELDS;
        const unsupportedFields = Object.keys(updates).filter((field) => !allowedFields.includes(field));
        if (unsupportedFields.length > 0) {
            return res.status(400).json({
                success: false,
                message: `The users table only persists full_name and phone. Unsupported fields: ${unsupportedFields.join(', ')}`
            });
        }

        const filteredUpdates = {};
        for (const field of allowedFields) {
            if (updates[field] !== undefined) {
                filteredUpdates[field] = updates[field];
            }
        }

        if (Object.keys(filteredUpdates).length === 0) {
            return res.status(400).json({
                success: false,
                message: 'No valid fields provided for update'
            });
        }

        const validateText = (field, maxLength) => {
            const value = filteredUpdates[field];
            if (value === undefined) return null;
            if (typeof value !== 'string' || value.trim().length === 0 || value.trim().length > maxLength) {
                return `${field} must be a non-empty string of at most ${maxLength} characters`;
            }
            filteredUpdates[field] = value.trim();
            return null;
        };
        for (const [field, max] of [['full_name', 120], ['state', 100], ['district', 100]]) {
            const validationMessage = validateText(field, max);
            if (validationMessage) return res.status(400).json({ success: false, message: validationMessage });
        }
        if (filteredUpdates.phone !== undefined &&
            (typeof filteredUpdates.phone !== 'string' || !/^\+?[0-9][0-9\s()-]{6,19}$/.test(filteredUpdates.phone.trim()))) {
            return res.status(400).json({ success: false, message: 'Phone must be a valid phone number' });
        }
        if (filteredUpdates.phone !== undefined) filteredUpdates.phone = filteredUpdates.phone.trim();

        // Handle dob and derive age if age is not explicitly passed
        if (filteredUpdates.dob && !isValidDateOnly(filteredUpdates.dob)) {
            return res.status(400).json({ success: false, message: 'Date of birth must be a valid date (YYYY-MM-DD)' });
        }
        if (filteredUpdates.dob && new Date(`${filteredUpdates.dob}T00:00:00.000Z`) > new Date()) {
            return res.status(400).json({ success: false, message: 'Date of birth cannot be in the future' });
        }
        if (filteredUpdates.dob && filteredUpdates.age === undefined) {
            const birthDate = new Date(`${filteredUpdates.dob}T00:00:00.000Z`);
            const today = new Date();
            let calculatedAge = today.getUTCFullYear() - birthDate.getUTCFullYear();
            const beforeBirthday = today.getUTCMonth() < birthDate.getUTCMonth() ||
                (today.getUTCMonth() === birthDate.getUTCMonth() && today.getUTCDate() < birthDate.getUTCDate());
            if (beforeBirthday) calculatedAge--;
            if (calculatedAge < 1 || calculatedAge > 120) {
                return res.status(400).json({ success: false, message: 'Date of birth must result in an age between 1 and 120' });
            }
            filteredUpdates.age = calculatedAge;
        }

        if (filteredUpdates.age !== undefined) {
            const age = typeof filteredUpdates.age === 'number' ? filteredUpdates.age :
                (typeof filteredUpdates.age === 'string' && /^\d+$/.test(filteredUpdates.age) ? Number(filteredUpdates.age) : NaN);
            if (!Number.isInteger(age) || age < 1 || age > 120) {
                return res.status(400).json({
                    success: false,
                    message: 'Age must be a valid number between 1 and 120'
                });
            }
            filteredUpdates.age = age;
        }

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

        if (filteredUpdates.annual_income !== undefined) {
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

        if (filteredUpdates.is_disabled !== undefined) {
            const isDisabled = parseBoolean(filteredUpdates.is_disabled);
            if (isDisabled === null) {
                return res.status(400).json({
                    success: false,
                    message: 'Is disabled must be true or false'
                });
            }
            filteredUpdates.is_disabled = isDisabled;
        }

        const validCategories = ['General', 'OBC', 'SC', 'ST', 'EWS'];
        if (filteredUpdates.category && !validCategories.includes(filteredUpdates.category)) {
            return res.status(400).json({
                success: false,
                message: `Category must be one of: ${validCategories.join(', ')}`
            });
        }

        const validAreaTypes = ['rural', 'urban'];
        if (filteredUpdates.area_type && !validAreaTypes.includes(filteredUpdates.area_type)) {
            return res.status(400).json({
                success: false,
                message: `Area type must be one of: ${validAreaTypes.join(', ')}`
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
                if (filteredUpdates.age !== undefined) {
                    const birthDate = new Date(`${filteredUpdates.dob}T00:00:00.000Z`);
                    const today = new Date();
                    let actualAge = today.getUTCFullYear() - birthDate.getUTCFullYear();
                    if (today.getUTCMonth() < birthDate.getUTCMonth() ||
                        (today.getUTCMonth() === birthDate.getUTCMonth() && today.getUTCDate() < birthDate.getUTCDate())) actualAge--;
                    if (actualAge !== filteredUpdates.age) {
                        return res.status(400).json({ success: false, message: 'Age does not match date of birth' });
                    }
                }
            }
        }

        // Validate applicant_type
        const validApplicantTypes = ['Individual', 'Family / Household', 'Small Enterprise (MSME)', 'Self Help Group (SHG)'];
        if (filteredUpdates.applicant_type !== undefined) {
            if (filteredUpdates.applicant_type !== null && filteredUpdates.applicant_type !== '' && !validApplicantTypes.includes(filteredUpdates.applicant_type)) {
                return res.status(400).json({
                    success: false,
                    message: `Applicant type must be one of: ${validApplicantTypes.join(', ')}`
                });
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
