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
            'annual_income', 'income', 'land_acres', 'is_disabled',
            'dob', 'applicant_type'
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

        // Handle dob and derive age if age is not explicitly passed
        if (filteredUpdates.dob && filteredUpdates.age === undefined) {
            const birthDate = new Date(filteredUpdates.dob);
            if (!isNaN(birthDate.getTime())) {
                const diffMs = Date.now() - birthDate.getTime();
                const ageDt = new Date(diffMs);
                const calcAge = Math.abs(ageDt.getUTCFullYear() - 1970);
                if (calcAge >= 1 && calcAge <= 120) {
                    filteredUpdates.age = calcAge;
                }
            }
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
            filteredUpdates.occupation = occMap[lowerOcc] || occMap[filteredUpdates.occupation] || 'other';
        }

        const validOccupations = ['farmer', 'msme', 'student', 'salaried', 'self-employed', 'unemployed', 'other'];
        if (filteredUpdates.occupation && !validOccupations.includes(filteredUpdates.occupation)) {
            filteredUpdates.occupation = 'other';
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
            filteredUpdates.gender = genderMap[lowerGen] || 'prefer_not_to_say';
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
