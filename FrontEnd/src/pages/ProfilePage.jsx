import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mail,
  Phone,
  MapPin,
  User,
  Shield,
  CheckCircle2,
  Settings,
  LogOut,
  Info,
  Target,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Search,
  Check,
  Lock,
  Edit3,
  Sprout,
  X,
  Camera,
  Trash2,
  ArrowLeft,
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import tricolorRibbon from '../assets/tricolor_ribbon_original.png';
import {
  getStoredUser,
  logoutUser,
  resolveDisplayName,
  saveRegisteredUser,
  getRegisteredUserByEmail,
  updateBackendProfile,
  fetchBackendProfile,
  changeAccountPassword,
} from '../services/authService';
import {
  sanitizeIndianPhone,
  formatAnnualIncome,
  formatGender,
  mapIncomeToRange,
  formatLastLogin,
  calculateProfileCompletion,
  calculateCompletion,
  getProfileInitials,
  CANONICAL_INCOME_RANGES,
  getCanonicalAmountForRange,
  isLocationAndIncomeComplete,
  isValidNumericIncome,
  normalizeSocialCategory,
  formatSocialCategory
} from '../utils/profileHelpers';
import {
  CANONICAL_STATES,
  getDistrictsForState,
  isValidStateDistrict,
  normalizeDistrictName
} from '../data/geoData';
import '../styles/profile.css';

export {
  sanitizeIndianPhone,
  formatAnnualIncome,
  mapIncomeToRange,
  formatLastLogin,
  calculateProfileCompletion,
  calculateCompletion,
  getProfileInitials,
  CANONICAL_INCOME_RANGES,
  getCanonicalAmountForRange,
  isLocationAndIncomeComplete,
  isValidNumericIncome
};

export default function ProfilePage() {
  const navigate = useNavigate();

  // Load and initialize profile data dynamically
  const [profileData, setProfileData] = useState(() => {
    try {
      const stored = getStoredUser();
      const email = stored?.email || '';
      const reg = email ? getRegisteredUserByEmail(email) : null;
      const name = resolveDisplayName(stored, email) || reg?.fullName || '';

      return {
        fullName: name,
        email: email,
        phone: (stored?.phone || reg?.phone) ? sanitizeIndianPhone(stored?.phone || reg?.phone) : '',
        state: stored?.state || reg?.state || '',
        district: stored?.district || reg?.district || '',
        occupation: stored?.occupation || reg?.occupation || '',
        income: stored?.annual_income ?? stored?.income ?? reg?.annual_income ?? reg?.income ?? '',
        annual_income: stored?.annual_income ?? reg?.annual_income ?? (typeof stored?.income === 'number' ? stored.income : null),
        applicantType: stored?.applicantType || reg?.applicantType || 'Individual',
        dob: stored?.dob || reg?.dob || '',
        gender: stored?.gender || reg?.gender || '',
        category: stored?.category || stored?.social_category || reg?.category || reg?.social_category || '',
        social_category: stored?.social_category || stored?.category || reg?.social_category || reg?.category || '',
        avatarUrl: stored?.avatarUrl || stored?.avatar_url || reg?.avatarUrl || '',
        lastSignInAt: stored?.lastSignInAt || stored?.last_sign_in_at || null,
        emailConfirmedAt: stored?.emailConfirmedAt || stored?.email_confirmed_at || null,
        loginMethod: stored?.loginMethod || stored?.login_method || 'Email & Password',
      };
    } catch (e) {
      return {
        fullName: '',
        email: '',
        phone: '',
        state: '',
        district: '',
        occupation: '',
        income: '',
        annual_income: null,
        applicantType: 'Individual',
        dob: '',
        gender: '',
        category: '',
        social_category: '',
        avatarUrl: '',
        lastSignInAt: null,
        emailConfirmedAt: null,
        loginMethod: 'Email & Password',
      };
    }
  });

  const [completionPercentage, setCompletionPercentage] = useState(() =>
    calculateProfileCompletion(profileData)
  );

  // Modal State
  const [activeModal, setActiveModal] = useState(null); // null | 'edit' | 'security'
  const [editFormData, setEditFormData] = useState({ ...profileData });
  const [passwordFormData, setPasswordFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordError, setPasswordError] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // District Combobox state & refs
  const [isDistrictDropdownOpen, setIsDistrictDropdownOpen] = useState(false);
  const [districtSearchQuery, setDistrictSearchQuery] = useState('');
  const districtDropdownRef = React.useRef(null);
  const districtSearchInputRef = React.useRef(null);

  const availableDistricts = React.useMemo(() => {
    return getDistrictsForState(editFormData.state);
  }, [editFormData.state]);

  const filteredDistricts = React.useMemo(() => {
    if (!districtSearchQuery.trim()) return availableDistricts;
    const q = districtSearchQuery.toLowerCase().trim();
    return availableDistricts.filter((d) => d.toLowerCase().includes(q));
  }, [availableDistricts, districtSearchQuery]);

  useEffect(() => {
    if (!isDistrictDropdownOpen) return;
    const handleOutsideClick = (e) => {
      if (districtDropdownRef.current && !districtDropdownRef.current.contains(e.target)) {
        setIsDistrictDropdownOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsDistrictDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isDistrictDropdownOpen]);

  useEffect(() => {
    if (isDistrictDropdownOpen && districtSearchInputRef.current) {
      districtSearchInputRef.current.focus();
    }
  }, [isDistrictDropdownOpen]);

  // Sync on mount with registered user registry and backend if available
  useEffect(() => {
    try {
      const stored = getStoredUser();
      const email = stored?.email || profileData.email;
      const reg = email ? getRegisteredUserByEmail(email) : null;
      if (reg) {
        setProfileData((prev) => {
          const merged = {
            ...prev,
            fullName: stored?.fullName || reg.fullName || prev.fullName,
            phone: stored?.phone || reg.phone || prev.phone,
            state: stored?.state || reg.state || prev.state,
            district: stored?.district || reg.district || prev.district,
            occupation: stored?.occupation || reg.occupation || prev.occupation,
            income: stored?.annual_income ?? stored?.income ?? reg.annual_income ?? reg.income ?? prev.income,
            annual_income: stored?.annual_income ?? reg.annual_income ?? (typeof stored?.income === 'number' ? stored.income : prev.annual_income) ?? null,
            applicantType: stored?.applicantType || stored?.applicant_type || reg.applicantType || reg.applicant_type || prev.applicantType,
            dob: stored?.dob || reg.dob || prev.dob,
            gender: stored?.gender || reg.gender || prev.gender,
            category: normalizeSocialCategory(stored?.category || stored?.social_category || reg.category || reg.social_category || prev.category),
            social_category: normalizeSocialCategory(stored?.social_category || stored?.category || reg.social_category || reg.category || prev.social_category),
            avatarUrl: stored?.avatarUrl || stored?.avatar_url || reg?.avatarUrl || prev.avatarUrl,
          };
          // Ensure stored user in localStorage is also populated with all registry fields
          if (stored) {
            localStorage.setItem('fin_user', JSON.stringify({ ...stored, ...merged }));
          }
          return merged;
        });
      }

      // If backend profile is available, hydrate from it
      fetchBackendProfile().then((res) => {
        if (res.success && res.data) {
          const b = res.data;
          setProfileData((prev) => {
            const updatedFromBackend = {
              ...prev,
              fullName: b.full_name || prev.fullName,
              phone: sanitizeIndianPhone(b.phone || prev.phone),
              state: b.state || prev.state,
              district: b.district || b.city || prev.district,
              occupation: b.occupation || prev.occupation,
              income: b.annual_income ?? b.income ?? prev.income,
              annual_income: b.annual_income ?? (typeof b.income === 'number' ? b.income : prev.annual_income) ?? null,
              applicantType: b.applicant_type || b.applicantType || prev.applicantType,
              dob: b.dob || b.date_of_birth || prev.dob,
              gender: b.gender || prev.gender,
              category: normalizeSocialCategory(b.category || b.social_category || b.caste_category || prev.category),
              social_category: normalizeSocialCategory(b.social_category || b.category || b.caste_category || prev.social_category),
              avatarUrl: b.avatar_url || b.avatarUrl || prev.avatarUrl,
              lastSignInAt: b.last_sign_in_at || prev.lastSignInAt,
              emailConfirmedAt: b.email_confirmed_at || prev.emailConfirmedAt,
              loginMethod: b.login_method || prev.loginMethod,
            };
            const currentStored = getStoredUser() || {};
            const fullObj = { ...currentStored, ...updatedFromBackend };
            localStorage.setItem('fin_user', JSON.stringify(fullObj));
            saveRegisteredUser(fullObj);
            return updatedFromBackend;
          });
        }
      }).catch(() => {});
    } catch (err) {}
  }, []);

  // Sync with global storage events
  useEffect(() => {
    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || getStoredUser();
        if (user) {
          const email = user.email || profileData.email;
          const reg = email ? getRegisteredUserByEmail(email) : null;
          const name = resolveDisplayName(user, email);
          setProfileData((prev) => ({
            ...prev,
            fullName: name || reg?.fullName || prev.fullName,
            email: email || prev.email,
            phone: sanitizeIndianPhone(user.phone || reg?.phone || prev.phone),
            state: user.state || reg?.state || prev.state,
            district: user.district || user.city || reg?.district || prev.district,
            occupation: user.occupation || reg?.occupation || prev.occupation,
            income: user.annual_income ?? user.income ?? reg?.annual_income ?? reg?.income ?? prev.income,
            annual_income: user.annual_income ?? (typeof user.income === 'number' ? user.income : reg?.annual_income) ?? prev.annual_income ?? null,
            applicantType: user.applicantType || user.applicant_type || reg?.applicantType || reg?.applicant_type || prev.applicantType,
            dob: user.dob || user.date_of_birth || reg?.dob || prev.dob,
            gender: user.gender || reg?.gender || prev.gender,
            category: user.category || user.social_category || user.caste_category || reg?.category || prev.category,
            social_category: user.social_category || user.category || user.caste_category || reg?.social_category || prev.social_category,
            avatarUrl: user.avatarUrl || user.avatar_url || prev.avatarUrl,
          }));
        }
      } catch (err) {}
    };

    window.addEventListener('fin_user_updated', handleUserUpdate);
    window.addEventListener('storage', handleUserUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleUserUpdate);
      window.removeEventListener('storage', handleUserUpdate);
    };
  }, []);

  // Update completion percentage when profileData changes
  useEffect(() => {
    setCompletionPercentage(calculateProfileCompletion(profileData));
  }, [profileData]);

  // Avatar upload and remove handlers
  const avatarInputRef = React.useRef(null);

  const handleAvatarUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setToastMessage('Image size must be less than 5MB');
      setTimeout(() => setToastMessage(''), 3000);
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64Url = event.target.result;
      const updated = {
        ...profileData,
        avatarUrl: base64Url,
      };
      setProfileData(updated);

      try {
        const stored = getStoredUser() || {};
        const fullUser = {
          ...stored,
          ...updated,
          avatarUrl: base64Url,
          avatar_url: base64Url,
        };
        localStorage.setItem('fin_user', JSON.stringify(fullUser));
        saveRegisteredUser(fullUser);
        window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: fullUser }));
        updateBackendProfile({ avatar_url: base64Url }).catch(() => {});
      } catch (err) {}

      setToastMessage('Profile picture updated successfully!');
      setTimeout(() => setToastMessage(''), 3000);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveAvatar = (e) => {
    e.stopPropagation();
    const updated = {
      ...profileData,
      avatarUrl: '',
    };
    setProfileData(updated);

    try {
      const stored = getStoredUser() || {};
      const fullUser = {
        ...stored,
        ...updated,
        avatarUrl: '',
        avatar_url: '',
      };
      localStorage.setItem('fin_user', JSON.stringify(fullUser));
      saveRegisteredUser(fullUser);
      window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: fullUser }));
      updateBackendProfile({ avatar_url: '' }).catch(() => {});
    } catch (err) {}

    if (avatarInputRef.current) {
      avatarInputRef.current.value = '';
    }
    setToastMessage('Profile picture removed.');
    setTimeout(() => setToastMessage(''), 3000);
  };

  // Derive initials dynamically from applicant full name
  const getInitials = (name) => {
    if (!name) return 'CI';
    const clean = name.trim();
    if (!clean) return 'CI';
    const parts = clean.split(/\s+/).filter(Boolean);
    if (parts.length > 1) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return clean.slice(0, 2).toUpperCase();
  };

  // Open modal with current state
  const handleOpenEditModal = () => {
    const currentState = profileData.state || 'Gujarat';
    const currentDistrict = profileData.district || '';
    // Requirement 4 & 6:
    // If persisted District belongs to that State, automatically select it.
    // If invalid combination (e.g. State=Gujarat, District=Jaipur), require correction.
    const isDistrictValid = isValidStateDistrict(currentState, currentDistrict);

    setEditFormData({
      ...profileData,
      state: currentState,
      district: isDistrictValid ? currentDistrict : '',
      phone: sanitizeIndianPhone(profileData.phone),
      income: profileData.income ?? '',
      gender: profileData.gender ? profileData.gender.toLowerCase() : '',
      category: normalizeSocialCategory(profileData.category || profileData.social_category || ''),
      social_category: normalizeSocialCategory(profileData.social_category || profileData.category || ''),
      applicantType: profileData.applicantType || profileData.applicant_type || 'Individual',
    });
    setDistrictSearchQuery('');
    setIsDistrictDropdownOpen(false);
    setActiveModal('edit');
  };

  const handleStateChange = (e) => {
    const newState = e.target.value;
    setEditFormData((prev) => ({
      ...prev,
      state: newState,
      district: '', // Requirement 5: clear selected district on state change
    }));
    setDistrictSearchQuery('');
    setIsDistrictDropdownOpen(false);
  };

  const handleSelectDistrict = (district) => {
    setEditFormData((prev) => ({
      ...prev,
      district,
    }));
    setIsDistrictDropdownOpen(false);
    setDistrictSearchQuery('');
  };

  const handleOpenSecurityModal = () => {
    setPasswordFormData({
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    });
    setActiveModal('security');
  };

  const handleCloseModal = () => {
    setActiveModal(null);
    setIsDistrictDropdownOpen(false);
  };

  // Handle annual income range bracket selection
  const handleIncomeRangeChange = (e) => {
    const selectedRange = e.target.value;
    if (!selectedRange) {
      setEditFormData((prev) => ({ ...prev, income: '' }));
      return;
    }
    // If the selected range matches current numeric income classification, preserve exact numeric income!
    const currentRange = mapIncomeToRange(editFormData.income);
    if (selectedRange === currentRange && (typeof editFormData.income === 'number' || /^\d+$/.test(String(editFormData.income).trim()))) {
      return;
    }
    // Otherwise, assign the canonical representative amount for the new range
    const canonicalAmount = getCanonicalAmountForRange(selectedRange);
    setEditFormData((prev) => ({
      ...prev,
      income: canonicalAmount !== null ? canonicalAmount : selectedRange,
    }));
  };

  // Handle edit form field change
  const handleEditChange = (e) => {
    const { name, value } = e.target;
    if (name === 'income') {
      handleIncomeRangeChange(e);
      return;
    }
    setEditFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Handle save changes
  const handleSaveProfile = async (e) => {
    e.preventDefault();

    const trimmedName = (editFormData.fullName || '').trim();
    if (!trimmedName || trimmedName.length < 2) {
      showToast('Please enter a valid full name (at least 2 characters).');
      return;
    }
    if (trimmedName.length > 120) {
      showToast('Full name must be at most 120 characters.');
      return;
    }

    if (!editFormData.state) {
      showToast('Please select a valid State.');
      return;
    }

    if (!editFormData.district) {
      showToast(`Please select a district for ${editFormData.state}.`);
      return;
    }

    if (!isValidStateDistrict(editFormData.state, editFormData.district)) {
      showToast(`Please select a valid district for ${editFormData.state}.`);
      return;
    }

    if (editFormData.dob) {
      const dobDate = new Date(editFormData.dob);
      if (dobDate > new Date()) {
        showToast('Date of birth cannot be in the future.');
        return;
      }
    }

    let backendProfileResult = { success: false };
    const cleanedPhone = sanitizeIndianPhone(editFormData.phone);

    // Canonical personal income resolution:
    // If exact numeric income is provided (or unchanged), preserve it!
    // If a range string is explicitly selected, map to representative canonical amount.
    let canonicalPersonalIncome = editFormData.income;
    if (typeof canonicalPersonalIncome === 'string' && CANONICAL_INCOME_RANGES.includes(canonicalPersonalIncome)) {
      canonicalPersonalIncome = getCanonicalAmountForRange(canonicalPersonalIncome);
    } else if (canonicalPersonalIncome !== '' && canonicalPersonalIncome !== null && canonicalPersonalIncome !== undefined && canonicalPersonalIncome !== 'Not added') {
      const numOnly = Number(String(canonicalPersonalIncome).replace(/[^0-9.]/g, ''));
      if (!isNaN(numOnly)) {
        canonicalPersonalIncome = numOnly;
      }
    } else if (canonicalPersonalIncome === '' || canonicalPersonalIncome === 'Not added' || canonicalPersonalIncome === null || canonicalPersonalIncome === undefined) {
      canonicalPersonalIncome = null;
    }

    const normalizedGender = editFormData.gender ? editFormData.gender.toLowerCase() : '';
    const categoryVal = normalizeSocialCategory(editFormData.category || editFormData.social_category || '');
    const applicantTypeVal = editFormData.applicantType || editFormData.applicant_type || 'Individual';

    const updated = {
      ...profileData,
      ...editFormData,
      fullName: trimmedName,
      name: trimmedName,
      phone: cleanedPhone,
      mobile_number: cleanedPhone,
      income: canonicalPersonalIncome !== null ? canonicalPersonalIncome : '',
      annual_income: canonicalPersonalIncome,
      gender: normalizedGender,
      category: categoryVal,
      social_category: categoryVal,
      applicantType: applicantTypeVal,
      applicant_type: applicantTypeVal,
    };

    setProfileData(updated);

    // Persist in localStorage and persistent registry (survives logout!)
    try {
      const stored = getStoredUser() || {};
      let fullUserObject = {
        ...stored,
        ...updated,
        fullName: trimmedName,
        name: trimmedName,
        email: updated.email,
        phone: cleanedPhone,
        mobile_number: cleanedPhone,
        state: updated.state,
        district: updated.district,
        occupation: updated.occupation,
        income: canonicalPersonalIncome !== null ? canonicalPersonalIncome : '',
        annual_income: canonicalPersonalIncome,
        applicantType: applicantTypeVal,
        applicant_type: applicantTypeVal,
        dob: updated.dob,
        date_of_birth: updated.dob,
        gender: normalizedGender,
        category: categoryVal,
        social_category: categoryVal,
      };

      localStorage.setItem('fin_user', JSON.stringify(fullUserObject));

      // Persist in persistent registry
      saveRegisteredUser(fullUserObject);

      // Also persist to backend API if active
      backendProfileResult = await updateBackendProfile({
        full_name: trimmedName,
        phone: cleanedPhone,
        mobile_number: cleanedPhone,
        state: updated.state,
        district: updated.district,
        occupation: updated.occupation,
        annual_income: canonicalPersonalIncome,
        income: canonicalPersonalIncome,
        dob: updated.dob,
        date_of_birth: updated.dob,
        gender: normalizedGender,
        category: categoryVal,
        social_category: categoryVal,
        applicant_type: applicantTypeVal,
        applicantType: applicantTypeVal,
      });

      if (backendProfileResult?.success && backendProfileResult?.data) {
        const bd = backendProfileResult.data.data || backendProfileResult.data;
        fullUserObject = {
          ...fullUserObject,
          id: bd.id || fullUserObject.id,
          fullName: bd.full_name || fullUserObject.fullName,
          phone: sanitizeIndianPhone(bd.phone || fullUserObject.phone),
          state: bd.state || fullUserObject.state,
          district: bd.district || bd.city || fullUserObject.district,
          occupation: bd.occupation || fullUserObject.occupation,
          income: bd.annual_income ?? bd.income ?? fullUserObject.income,
          annual_income: bd.annual_income ?? fullUserObject.annual_income,
          applicantType: bd.applicant_type || bd.applicantType || fullUserObject.applicantType,
          dob: bd.dob || bd.date_of_birth || fullUserObject.dob,
          gender: bd.gender || fullUserObject.gender,
          category: normalizeSocialCategory(bd.category || bd.social_category || bd.caste_category || categoryVal),
          social_category: normalizeSocialCategory(bd.social_category || bd.category || bd.caste_category || categoryVal),
        };
        localStorage.setItem('fin_user', JSON.stringify(fullUserObject));
        saveRegisteredUser(fullUserObject);
        setProfileData(fullUserObject);
      }

      // Dispatch reactive events for Header, HeroBanner, SuggestedSchemes, etc.
      window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: fullUserObject }));
      window.dispatchEvent(new Event('storage'));
    } catch (err) {
      console.error('Failed to save profile:', err);
    }

    setActiveModal(null);
    showToast(backendProfileResult?.success
      ? 'Profile details saved successfully.'
      : 'Profile saved on this device; backend persistence failed.');
  };

  // Handle password change submit
  const handleSavePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');

    if (!passwordFormData.currentPassword || !passwordFormData.currentPassword.trim()) {
      setPasswordError('Current password is required.');
      return;
    }
    if (!passwordFormData.newPassword || passwordFormData.newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters.');
      return;
    }
    if (passwordFormData.newPassword !== passwordFormData.confirmPassword) {
      setPasswordError('New password and confirm password do not match.');
      return;
    }
    if (passwordFormData.currentPassword === passwordFormData.newPassword) {
      setPasswordError('New password must be different from current password.');
      return;
    }

    try {
      setIsChangingPassword(true);
      const res = await changeAccountPassword({
        currentPassword: passwordFormData.currentPassword,
        newPassword: passwordFormData.newPassword,
      });

      if (res.success) {
        setActiveModal(null);
        setPasswordFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
        showToast('Password changed successfully!');
      } else {
        setPasswordError(res.message || 'Failed to change password.');
      }
    } catch (err) {
      setPasswordError(err.message || 'An error occurred while changing password.');
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Show temporary toast message
  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage('');
    }, 3200);
  };

  // Handle Log Out
  const handleLogoutClick = async () => {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    try {
      await logoutUser();
      navigate('/login');
    } catch (err) {
      navigate('/login');
    }
  };

  return (
    <PageContainer>
      <div className="profile-page-wrapper">
        {/* Toast Notification */}
        {toastMessage && (
          <div className="profile-toast-message" role="status">
            <CheckCircle2 size={18} />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Back to Dashboard navigation bar */}
        <div className="profile-back-bar">
          <button
            type="button"
            className="profile-back-btn"
            onClick={() => navigate('/dashboard')}
            aria-label="Back to Dashboard"
          >
            <ArrowLeft size={16} />
            <span>Back to Dashboard</span>
          </button>
        </div>

        {/* Top Hero Profile Row */}
        <section className="profile-hero-row" aria-label="Applicant Overview">
          {/* Main Profile Info Card */}
          <div className="profile-hero-card">
            <div className="profile-identity-section">
              <div className="profile-avatar-wrapper">
                <div className="profile-avatar-circle" aria-hidden="true">
                  {profileData.avatarUrl ? (
                    <img
                      src={profileData.avatarUrl}
                      alt={profileData.fullName}
                      className="profile-avatar-img"
                    />
                  ) : (
                    getInitials(profileData.fullName)
                  )}
                </div>
                <label
                  className="profile-avatar-camera-btn"
                  title="Upload profile picture"
                  aria-label="Upload profile picture"
                >
                  <Camera size={15} />
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarUpload}
                    style={{ display: 'none' }}
                  />
                </label>
                {profileData.avatarUrl && (
                  <button
                    type="button"
                    className="profile-avatar-remove-btn"
                    title="Remove profile picture"
                    aria-label="Remove profile picture"
                    onClick={handleRemoveAvatar}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
              <div className="profile-identity-details">
                <h2 className="profile-applicant-name">{profileData.fullName}</h2>
                <span className="profile-applicant-role">{profileData.applicantType} Applicant</span>

                <div className="profile-contact-meta">
                  <span className="profile-meta-item">
                    <Mail size={14} aria-hidden="true" />
                    <span>{profileData.email}</span>
                  </span>
                  <span className="profile-meta-item">
                    <Phone size={14} aria-hidden="true" />
                    <span>{sanitizeIndianPhone(profileData.phone)}</span>
                  </span>
                  <span className="profile-meta-item">
                    <MapPin size={14} aria-hidden="true" />
                    <span>{profileData.state ? `${profileData.state}, India` : 'India'}</span>
                  </span>
                </div>

                <div className="profile-pill-tags">
                  {profileData.occupation && (
                    <span className="profile-pill">{profileData.occupation}</span>
                  )}
                  <span className="profile-pill">{profileData.applicantType || 'Individual'}</span>
                  <span className="profile-pill">Profile {completionPercentage}% Complete</span>
                </div>
              </div>
            </div>

            <div className="profile-completion-divider" aria-hidden="true" />

            {/* Profile Completion Meter */}
            <div className="profile-completion-section">
              <div className="profile-completion-header">
                <span className="profile-completion-title">Profile Completion</span>
                <span className="profile-completion-percent">{completionPercentage}%</span>
              </div>

              <div
                className="profile-progress-bar-wrap"
                role="progressbar"
                aria-valuenow={completionPercentage}
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <div
                  className="profile-progress-bar-fill"
                  style={{ width: `${completionPercentage}%` }}
                />
              </div>

              <p className="profile-completion-desc">
                Complete your profile to get personalized scheme recommendations.
              </p>

              <button
                type="button"
                className="btn-edit-profile-green"
                onClick={handleOpenEditModal}
                id="editProfileHeroBtn"
              >
                <Edit3 size={15} />
                <span>Edit Profile</span>
              </button>
            </div>
          </div>

          {/* Inspirational Sprout Card */}
          <div className="profile-sprout-card">
            <div className="profile-sprout-icon-wrap" aria-hidden="true">
              <Sprout size={26} strokeWidth={2.2} />
            </div>
            <p className="profile-sprout-message">
              Small steps today, bigger opportunities tomorrow.
            </p>
            <img src={tricolorRibbon} alt="" className="profile-sprout-ribbon" aria-hidden="true" />
          </div>
        </section>

        {/* 3. Middle 2-Column Grid: Personal Info vs Location & Profile */}
        <section className="profile-grid-two-cols" aria-label="Personal and Location Details">
          {/* Card A: Personal Information */}
          <div className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-header-left">
                <div className="profile-card-icon-title">
                  <User size={18} className="profile-section-icon" aria-hidden="true" />
                  <h3 className="profile-card-title">Personal Information</h3>
                </div>
                <p className="profile-card-subtitle">Your basic details as per official documents.</p>
              </div>
              <button
                type="button"
                className="btn-card-action"
                onClick={handleOpenEditModal}
                id="editPersonalInfoBtn"
              >
                <Edit3 size={13} />
                <span>Edit Information</span>
              </button>
            </div>

            <div className="profile-details-table">
              <div className="profile-detail-row">
                <span className="profile-detail-label">Full Name</span>
                <span className="profile-detail-value">{profileData.fullName}</span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Email Address</span>
                <span className="profile-detail-value">{profileData.email}</span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Mobile Number</span>
                <span className="profile-detail-value">{sanitizeIndianPhone(profileData.phone)}</span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Date of Birth</span>
                <span
                  className={`profile-detail-value ${!profileData.dob || profileData.dob === 'Not added' ? 'text-not-added' : ''}`}
                >
                  {profileData.dob || 'Not added'}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Gender</span>
                <span
                  className={`profile-detail-value ${!profileData.gender || profileData.gender === 'Not added' ? 'text-not-added' : ''}`}
                >
                  {profileData.gender ? formatGender(profileData.gender) : 'Not added'}
                </span>
              </div>
            </div>
          </div>

          {/* Card B: Location & Profile */}
          <div className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-header-left">
                <div className="profile-card-icon-title">
                  <MapPin size={18} className="profile-section-icon" aria-hidden="true" />
                  <h3 className="profile-card-title">Location & Profile</h3>
                </div>
                <p className="profile-card-subtitle">Help us understand your background better.</p>
              </div>
              <button
                type="button"
                className="btn-card-action"
                onClick={handleOpenEditModal}
                id="completeProfileBtn"
              >
                <Edit3 size={13} />
                <span>Complete Profile</span>
              </button>
            </div>

            <div className="profile-details-table">
              <div className="profile-detail-row">
                <span className="profile-detail-label">State</span>
                <span
                  className={`profile-detail-value ${!profileData.state || profileData.state === 'Not added' ? 'text-not-added' : ''}`}
                >
                  {profileData.state || 'Not added'}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">District</span>
                <span
                  className={`profile-detail-value ${!profileData.district || profileData.district === 'Not added' ? 'text-not-added' : ''}`}
                >
                  {profileData.district || 'Not added'}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Occupation</span>
                <span
                  className={`profile-detail-value ${!profileData.occupation || profileData.occupation === 'Not added' ? 'text-not-added' : ''}`}
                >
                  {profileData.occupation || 'Not added'}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Annual Income</span>
                <span
                  className={`profile-detail-value ${
                    (profileData.annual_income === null || profileData.annual_income === undefined || profileData.annual_income === '') &&
                    (!profileData.income || profileData.income === 'Not added')
                      ? 'text-not-added'
                      : ''
                  }`}
                >
                  {formatAnnualIncome(profileData.annual_income ?? profileData.income)}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Social Category</span>
                <span
                  className={`profile-detail-value ${!profileData.category && !profileData.social_category ? 'text-not-added' : ''}`}
                >
                  {formatSocialCategory(profileData.category || profileData.social_category)}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Applicant Type</span>
                <span className="profile-detail-value">{profileData.applicantType || 'Individual'}</span>
              </div>
            </div>

            {/* Recommendation Callout Banner - shown ONLY when location or income is incomplete */}
            {!isLocationAndIncomeComplete(profileData) && (
              <div
                className="profile-recommendation-callout"
                onClick={handleOpenEditModal}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && handleOpenEditModal()}
                aria-label="Complete location and income details"
                id="locationIncomeCallout"
              >
                <div className="callout-left">
                  <Target size={17} className="callout-target-icon" aria-hidden="true" />
                  <span className="callout-text">
                    Complete your location and income details to receive more relevant scheme recommendations.
                  </span>
                </div>
                <ChevronRight size={16} className="callout-arrow" aria-hidden="true" />
              </div>
            )}
          </div>
        </section>

        {/* 4. Bottom 2-Column Grid: Account & Security vs Account Actions */}
        <section className="profile-grid-two-cols" aria-label="Account Settings and Actions">
          {/* Card C: Account & Security */}
          <div className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-header-left">
                <div className="profile-card-icon-title">
                  <Shield size={18} className="profile-section-icon" aria-hidden="true" />
                  <h3 className="profile-card-title">Account & Security</h3>
                </div>
                <p className="profile-card-subtitle">Keep your account secure.</p>
              </div>
              <button
                type="button"
                className="btn-card-action"
                onClick={handleOpenSecurityModal}
                id="manageSecurityBtn"
              >
                <Lock size={13} />
                <span>Manage Security</span>
              </button>
            </div>

            <div className="profile-details-table">
              <div className="profile-detail-row">
                <span className="profile-detail-label">Email verification</span>
                <span className="profile-verified-badge">
                  <CheckCircle2 size={16} className="verified-icon" aria-hidden="true" />
                  <span>{profileData.emailConfirmedAt || profileData.email ? 'Verified' : 'Pending'}</span>
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Password</span>
                <div className="profile-password-value-wrap">
                  <span className="profile-password-dots" aria-label="Hidden password">
                    ••••••••
                  </span>
                  <button
                    type="button"
                    className="btn-change-password"
                    onClick={handleOpenSecurityModal}
                    id="changePasswordBtn"
                  >
                    Change
                  </button>
                </div>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Login method</span>
                <span className="profile-detail-value">{profileData.loginMethod || 'Email & Password'}</span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Last login</span>
                <span className="profile-detail-value">{formatLastLogin(profileData.lastSignInAt)}</span>
              </div>
            </div>
          </div>

          {/* Card D: Account Actions */}
          <div className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-header-left">
                <div className="profile-card-icon-title">
                  <Settings size={18} className="profile-section-icon" aria-hidden="true" />
                  <h3 className="profile-card-title">Account Actions</h3>
                </div>
                <p className="profile-card-subtitle">Manage your account settings.</p>
              </div>
            </div>

            <div className="profile-actions-container">
              {/* Log Out Button Row */}
              <div
                className="profile-logout-card"
                onClick={handleLogoutClick}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && handleLogoutClick()}
                id="profileLogoutBtn"
                aria-label="Log Out from your account"
              >
                <div className="profile-logout-left">
                  <LogOut size={20} className="profile-logout-icon" aria-hidden="true" />
                  <div className="profile-logout-texts">
                    <span className="profile-logout-title">Log Out</span>
                    <span className="profile-logout-subtitle">
                      Sign out from your account. You can log in again anytime.
                    </span>
                  </div>
                </div>
                <ChevronRight size={18} className="profile-logout-arrow" aria-hidden="true" />
              </div>

              {/* Info Banner */}
              <div className="profile-info-banner">
                <Info size={18} className="profile-info-icon" aria-hidden="true" />
                <span className="profile-info-text">
                  Your data, documents, and applications will remain safe and will not be deleted.
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* 5. Edit Profile Interactive Modal */}
        {activeModal === 'edit' && (
          <div
            className="profile-modal-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="editProfileModalTitle"
            onClick={handleCloseModal}
          >
            <div className="profile-modal-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="profile-modal-header">
                <h3 className="profile-modal-title" id="editProfileModalTitle">
                  Edit Applicant Profile
                </h3>
                <button
                  type="button"
                  className="profile-modal-close-btn"
                  onClick={handleCloseModal}
                  aria-label="Close dialog"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleSaveProfile}>
                <div className="profile-modal-body">
                  <div className="modal-form-grid">
                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputFullName">
                        Full Name
                      </label>
                      <input
                        id="inputFullName"
                        type="text"
                        name="fullName"
                        className="modal-form-input"
                        value={editFormData.fullName}
                        onChange={handleEditChange}
                        required
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputEmail">
                        Email Address (Read-only)
                      </label>
                      <input
                        id="inputEmail"
                        type="email"
                        name="email"
                        className="modal-form-input"
                        value={editFormData.email}
                        disabled
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputPhone">
                        Mobile Number
                      </label>
                      <input
                        id="inputPhone"
                        type="tel"
                        name="phone"
                        className="modal-form-input"
                        value={editFormData.phone}
                        onChange={handleEditChange}
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="selectOccupation">
                        Occupation
                      </label>
                      <select
                        id="selectOccupation"
                        name="occupation"
                        className="modal-form-select"
                        value={editFormData.occupation}
                        onChange={handleEditChange}
                      >
                        <option value="Student">Student</option>
                        <option value="Farmer / Agriculture">Farmer / Agriculture</option>
                        <option value="Self Employed / MSME">Self Employed / MSME</option>
                        <option value="Salaried Employee">Salaried Employee</option>
                        <option value="Unemployed / Job Seeker">Unemployed / Job Seeker</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputState">
                        State
                      </label>
                      <select
                        id="inputState"
                        name="state"
                        className="modal-form-select"
                        value={editFormData.state}
                        onChange={handleStateChange}
                      >
                        <option value="">-- Select State --</option>
                        {CANONICAL_STATES.map((st) => (
                          <option key={st} value={st}>
                            {st}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="districtTrigger">
                        District
                      </label>
                      <div className="district-combobox-wrapper" ref={districtDropdownRef}>
                        <button
                          type="button"
                          id="districtTrigger"
                          className={`district-combobox-trigger ${isDistrictDropdownOpen ? 'open' : ''}`}
                          onClick={() => {
                            if (editFormData.state) {
                              setIsDistrictDropdownOpen((prev) => !prev);
                            }
                          }}
                          aria-haspopup="listbox"
                          aria-expanded={isDistrictDropdownOpen}
                          disabled={!editFormData.state}
                        >
                          <span className={editFormData.district ? 'district-selected-text' : 'district-placeholder-text'}>
                            {editFormData.district || (editFormData.state ? `Select a district for ${editFormData.state}` : 'Select a State first')}
                          </span>
                          {isDistrictDropdownOpen ? (
                            <ChevronUp size={16} className="district-chevron-icon" />
                          ) : (
                            <ChevronDown size={16} className="district-chevron-icon" />
                          )}
                        </button>

                        {isDistrictDropdownOpen && (
                          <div className="district-combobox-dropdown" role="listbox">
                            <div className="district-search-bar">
                              <Search size={14} className="district-search-icon" />
                              <input
                                ref={districtSearchInputRef}
                                type="text"
                                placeholder={`Search in ${availableDistricts.length} districts...`}
                                value={districtSearchQuery}
                                onChange={(e) => setDistrictSearchQuery(e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                              />
                              {districtSearchQuery && (
                                <button
                                  type="button"
                                  className="district-search-clear-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setDistrictSearchQuery('');
                                    districtSearchInputRef.current?.focus();
                                  }}
                                  aria-label="Clear search"
                                >
                                  <X size={13} />
                                </button>
                              )}
                            </div>

                            <div className="district-options-list">
                              {filteredDistricts.length > 0 ? (
                                filteredDistricts.map((d) => {
                                  const isSelected = editFormData.district === d;
                                  return (
                                    <button
                                      key={d}
                                      type="button"
                                      className={`district-option-item ${isSelected ? 'selected' : ''}`}
                                      onClick={() => handleSelectDistrict(d)}
                                      role="option"
                                      aria-selected={isSelected}
                                    >
                                      <span>{d}</span>
                                      {isSelected && <Check size={14} className="district-check-icon" />}
                                    </button>
                                  );
                                })
                              ) : (
                                <div className="district-empty-message">
                                  No districts found matching "{districtSearchQuery}"
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="selectIncome">
                        Annual Income
                      </label>
                      <select
                        id="selectIncome"
                        name="income"
                        className="modal-form-select"
                        value={mapIncomeToRange(editFormData.income)}
                        onChange={handleIncomeRangeChange}
                      >
                        <option value="">Select income range</option>
                        {CANONICAL_INCOME_RANGES.map((rng) => (
                          <option key={rng} value={rng}>{rng}</option>
                        ))}
                      </select>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="selectApplicantType">
                        Applicant Type
                      </label>
                      <select
                        id="selectApplicantType"
                        name="applicantType"
                        className="modal-form-select"
                        value={editFormData.applicantType}
                        onChange={handleEditChange}
                      >
                        <option value="Individual">Individual</option>
                        <option value="Family / Household">Family / Household</option>
                        <option value="Small Enterprise (MSME)">Small Enterprise (MSME)</option>
                        <option value="Self Help Group (SHG)">Self Help Group (SHG)</option>
                      </select>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputDob">
                        Date of Birth
                      </label>
                      <input
                        id="inputDob"
                        type="date"
                        name="dob"
                        className="modal-form-input"
                        value={editFormData.dob}
                        onChange={handleEditChange}
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="selectGender">
                        Gender
                      </label>
                      <select
                        id="selectGender"
                        name="gender"
                        className="modal-form-select"
                        value={editFormData.gender ? editFormData.gender.toLowerCase() : ''}
                        onChange={handleEditChange}
                      >
                        <option value="">Select gender</option>
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                        <option value="prefer_not_to_say">Prefer not to say</option>
                      </select>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="selectSocialCategory">
                        Social Category
                      </label>
                      <select
                        id="selectSocialCategory"
                        name="category"
                        className="modal-form-select"
                        value={normalizeSocialCategory(editFormData.category || editFormData.social_category || '')}
                        onChange={(e) => {
                          const val = e.target.value;
                          setEditFormData((prev) => ({
                            ...prev,
                            category: val,
                            social_category: val,
                          }));
                        }}
                      >
                        <option value="">Select social category</option>
                        <option value="general">General</option>
                        <option value="obc">OBC</option>
                        <option value="sc">SC</option>
                        <option value="st">ST</option>
                        <option value="ews">EWS</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="profile-modal-footer">
                  <button type="button" className="btn-modal-cancel" onClick={handleCloseModal}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-modal-save">
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 6. Security & Password Change Modal */}
        {activeModal === 'security' && (
          <div
            className="profile-modal-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="securityModalTitle"
            onClick={handleCloseModal}
          >
            <div className="profile-modal-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="profile-modal-header">
                <h3 className="profile-modal-title" id="securityModalTitle">
                  Change Account Password
                </h3>
                <button
                  type="button"
                  className="profile-modal-close-btn"
                  onClick={handleCloseModal}
                  aria-label="Close dialog"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleSavePassword}>
                <div className="profile-modal-body">
                  {passwordError && (
                    <div
                      className="profile-password-error-banner"
                      role="alert"
                      style={{
                        color: '#D92D20',
                        backgroundColor: '#FEF3F2',
                        border: '1px solid #FECDCA',
                        padding: '10px 14px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: 500,
                        marginBottom: '14px',
                      }}
                    >
                      {passwordError}
                    </div>
                  )}
                  <div className="modal-form-grid single-col">
                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputCurrentPassword">
                        Current Password
                      </label>
                      <input
                        id="inputCurrentPassword"
                        type="password"
                        placeholder="Enter current password"
                        className="modal-form-input"
                        value={passwordFormData.currentPassword}
                        onChange={(e) =>
                          setPasswordFormData((prev) => ({
                            ...prev,
                            currentPassword: e.target.value,
                          }))
                        }
                        required
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputNewPassword">
                        New Password
                      </label>
                      <input
                        id="inputNewPassword"
                        type="password"
                        placeholder="At least 6 characters"
                        className="modal-form-input"
                        value={passwordFormData.newPassword}
                        onChange={(e) =>
                          setPasswordFormData((prev) => ({
                            ...prev,
                            newPassword: e.target.value,
                          }))
                        }
                        required
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputConfirmPassword">
                        Confirm New Password
                      </label>
                      <input
                        id="inputConfirmPassword"
                        type="password"
                        placeholder="Confirm new password"
                        className="modal-form-input"
                        value={passwordFormData.confirmPassword}
                        onChange={(e) =>
                          setPasswordFormData((prev) => ({
                            ...prev,
                            confirmPassword: e.target.value,
                          }))
                        }
                        required
                      />
                    </div>
                  </div>
                </div>

                <div className="profile-modal-footer">
                  <button type="button" className="btn-modal-cancel" onClick={handleCloseModal}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-modal-save" disabled={isChangingPassword}>
                    {isChangingPassword ? 'Updating...' : 'Update Password'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
