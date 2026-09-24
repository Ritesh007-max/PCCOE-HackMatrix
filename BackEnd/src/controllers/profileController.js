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

const getProfile = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const userMetadata = req.user.user_metadata || {};

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

        const allowedFields = [
            'full_name', 'phone', 'age', 'gender', 'category',
            'state', 'district', 'area_type', 'occupation',
            'annual_income', 'land_acres', 'is_disabled',
            'dob', 'applicant_type', 'income'
        ];

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

        if (filteredUpdates.age !== undefined) {
            const age = parseInt(filteredUpdates.age, 10);
            if (isNaN(age) || age < 1 || age > 120) {
                return res.status(400).json({
                    success: false,
                    message: 'Age must be a valid number between 1 and 120'
                });
            }
            filteredUpdates.age = age;
        }

        if (filteredUpdates.annual_income !== undefined) {
            const income = parseFloat(filteredUpdates.annual_income);
            if (isNaN(income) || income < 0) {
                return res.status(400).json({
                    success: false,
                    message: 'Annual income must be a valid positive number'
                });
            }
            filteredUpdates.annual_income = income;
        }

        if (filteredUpdates.income !== undefined && filteredUpdates.annual_income === undefined) {
            const income = parseFloat(filteredUpdates.income);
            if (!isNaN(income) && income >= 0) {
                filteredUpdates.annual_income = income;
            }
            delete filteredUpdates.income;
        }

        if (filteredUpdates.land_acres !== undefined) {
            const land = parseFloat(filteredUpdates.land_acres);
            if (isNaN(land) || land < 0) {
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

        const validOccupations = ['farmer', 'msme', 'student', 'salaried', 'self-employed', 'unemployed', 'Farmer / Agriculture', 'Self Employed / MSME', 'Salaried Employee', 'Unemployed / Job Seeker', 'Other', 'Student'];
        if (filteredUpdates.occupation && !validOccupations.includes(filteredUpdates.occupation)) {
            return res.status(400).json({
                success: false,
                message: `Occupation must be one of: ${validOccupations.join(', ')}`
            });
        }
        // Normalize occupation to lowercase backend format
        if (filteredUpdates.occupation) {
            const occupationMap = {
                'Farmer / Agriculture': 'farmer',
                'Self Employed / MSME': 'self-employed',
                'Salaried Employee': 'salaried',
                'Unemployed / Job Seeker': 'unemployed',
                'Other': 'unemployed',
                'Student': 'student',
                'farmer': 'farmer',
                'msme': 'msme',
                'student': 'student',
                'salaried': 'salaried',
                'self-employed': 'self-employed',
                'unemployed': 'unemployed'
            };
            filteredUpdates.occupation = occupationMap[filteredUpdates.occupation] || filteredUpdates.occupation.toLowerCase();
        }

        const validGenders = ['male', 'female', 'other', 'prefer_not_to_say', 'Male', 'Female', 'Transgender', 'Prefer not to say'];
        if (filteredUpdates.gender && !validGenders.includes(filteredUpdates.gender)) {
            return res.status(400).json({
                success: false,
                message: `Gender must be one of: ${validGenders.join(', ')}`
            });
        }
        if (filteredUpdates.gender) {
            const genderMap = {
                'Male': 'male',
                'Female': 'female',
                'Transgender': 'other',
                'Prefer not to say': 'prefer_not_to_say',
                'male': 'male',
                'female': 'female',
                'other': 'other',
                'prefer_not_to_say': 'prefer_not_to_say'
            };
            filteredUpdates.gender = genderMap[filteredUpdates.gender] || filteredUpdates.gender.toLowerCase();
        }

        // Validate dob (date of birth)
        if (filteredUpdates.dob !== undefined) {
            if (filteredUpdates.dob !== null && filteredUpdates.dob !== '') {
                const dobDate = new Date(filteredUpdates.dob);
                if (isNaN(dobDate.getTime())) {
                    return res.status(400).json({
                        success: false,
                        message: 'Date of birth must be a valid date (YYYY-MM-DD)'
                    });
                }
                // Optional: ensure not future date
                if (dobDate > new Date()) {
                    return res.status(400).json({
                        success: false,
                        message: 'Date of birth cannot be in the future'
                    });
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
