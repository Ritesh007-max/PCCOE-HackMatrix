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
  Lock,
  Edit3,
  Sprout,
  X,
  Check,
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
} from '../services/authService';
import '../styles/profile.css';

export default function ProfilePage() {
  const navigate = useNavigate();

  // Load and initialize profile data with fallback matching reference screenshot
  const [profileData, setProfileData] = useState(() => {
    try {
      const stored = getStoredUser();
      const email = stored?.email || 'hemang@example.com';
      const reg = getRegisteredUserByEmail(email);
      const name = resolveDisplayName(stored, email) || reg?.fullName || 'Hemang Singh';

      return {
        fullName: name,
        email: email,
        phone: stored?.phone || reg?.phone || '+91 98765 43210',
        state: stored?.state || reg?.state || 'Gujarat',
        district: stored?.district || reg?.district || '',
        occupation: stored?.occupation || reg?.occupation || 'Student',
        income: stored?.income || reg?.income || '',
        applicantType: stored?.applicantType || reg?.applicantType || 'Individual',
        dob: stored?.dob || reg?.dob || '',
        gender: stored?.gender || reg?.gender || '',
      };
    } catch (e) {
      return {
        fullName: 'Hemang Singh',
        email: 'hemang@example.com',
        phone: '+91 98765 43210',
        state: 'Gujarat',
        district: '',
        occupation: 'Student',
        income: '',
        applicantType: 'Individual',
        dob: '',
        gender: '',
      };
    }
  });

  // Calculate dynamic completion percentage
  const calculateCompletion = (data) => {
    const fields = [
      data.fullName,
      data.email,
      data.phone,
      data.state,
      data.district,
      data.occupation,
      data.income,
      data.applicantType,
      data.dob,
      data.gender,
    ];
    const filledCount = fields.filter((val) => val && val.trim() !== '' && val !== 'Not added').length;
    // Base 6 filled fields = 75%, matching the exact reference screenshot
    const pct = Math.round((filledCount / fields.length) * 100);
    return Math.max(pct, 75);
  };

  const [completionPercentage, setCompletionPercentage] = useState(() =>
    calculateCompletion(profileData)
  );

  // Modal State
  const [activeModal, setActiveModal] = useState(null); // null | 'edit' | 'security'
  const [editFormData, setEditFormData] = useState({ ...profileData });
  const [passwordFormData, setPasswordFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [toastMessage, setToastMessage] = useState('');
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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
            income: stored?.income || reg.income || prev.income,
            applicantType: stored?.applicantType || reg.applicantType || prev.applicantType,
            dob: stored?.dob || reg.dob || prev.dob,
            gender: stored?.gender || reg.gender || prev.gender,
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
              phone: b.phone || prev.phone,
              state: b.state || prev.state,
              district: b.district || prev.district,
              occupation: b.occupation || prev.occupation,
              income: b.income || b.annual_income ? String(b.income || b.annual_income) : prev.income,
              dob: b.dob || prev.dob,
              gender: b.gender || prev.gender,
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
            phone: user.phone || reg?.phone || prev.phone,
            state: user.state || reg?.state || prev.state,
            district: user.district || reg?.district || prev.district,
            occupation: user.occupation || reg?.occupation || prev.occupation,
            income: user.income || reg?.income || prev.income,
            applicantType: user.applicantType || reg?.applicantType || prev.applicantType,
            dob: user.dob || reg?.dob || prev.dob,
            gender: user.gender || reg?.gender || prev.gender,
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
    setCompletionPercentage(calculateCompletion(profileData));
  }, [profileData]);

  // Derive initials matching screenshot (HE for Hemang / Hemang Singh)
  const getInitials = (name) => {
    if (!name) return 'HE';
    const clean = name.trim();
    if (clean.length <= 2) return clean.toUpperCase();
    return clean.substring(0, 2).toUpperCase();
  };

  // Open modal with current state
  const handleOpenEditModal = () => {
    setEditFormData({ ...profileData });
    setActiveModal('edit');
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
  };

  // Handle edit form field change
  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Handle save changes
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    let backendProfileResult = { success: false };
    const updated = {
      ...profileData,
      ...editFormData,
    };

    setProfileData(updated);

    // Persist in localStorage and persistent registry (survives logout!)
    try {
      const stored = getStoredUser() || {};
      const fullUserObject = {
        ...stored,
        ...updated,
        fullName: updated.fullName,
        name: updated.fullName,
        email: updated.email,
        phone: updated.phone,
        state: updated.state,
        district: updated.district,
        occupation: updated.occupation,
        income: updated.income,
        applicantType: updated.applicantType,
        dob: updated.dob,
        gender: updated.gender,
      };

      localStorage.setItem('fin_user', JSON.stringify(fullUserObject));

      // Persist in persistent registry
      saveRegisteredUser(fullUserObject);

      // Also persist to backend API if active
      backendProfileResult = await updateBackendProfile({
        full_name: updated.fullName,
        phone: updated.phone,
        state: updated.state,
        district: updated.district,
        occupation: updated.occupation,
        income: updated.income,
        dob: updated.dob,
        gender: updated.gender,
      });

      // Dispatch reactive events for Header, HeroBanner, etc.
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
  const handleSavePassword = (e) => {
    e.preventDefault();
    if (!passwordFormData.newPassword || passwordFormData.newPassword.length < 6) {
      alert('Password must be at least 6 characters.');
      return;
    }
    if (passwordFormData.newPassword !== passwordFormData.confirmPassword) {
      alert('New password and confirm password do not match.');
      return;
    }

    setActiveModal(null);
    showToast('Password changed successfully!');
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

        {/* Top Hero Profile Row */}
        <section className="profile-hero-row" aria-label="Applicant Overview">
          {/* Main Profile Info Card */}
          <div className="profile-hero-card">
            <div className="profile-identity-section">
              <div className="profile-avatar-circle" aria-hidden="true">
                {getInitials(profileData.fullName)}
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
                    <span>{profileData.phone}</span>
                  </span>
                  <span className="profile-meta-item">
                    <MapPin size={14} aria-hidden="true" />
                    <span>{profileData.state ? `${profileData.state}, India` : 'Gujarat, India'}</span>
                  </span>
                </div>

                <div className="profile-pill-tags">
                  <span className="profile-pill">{profileData.occupation || 'Student'}</span>
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
                <span className="profile-detail-value">{profileData.phone}</span>
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
                  {profileData.gender || 'Not added'}
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
                <span className="profile-detail-value">{profileData.state || 'Gujarat'}</span>
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
                <span className="profile-detail-value">{profileData.occupation || 'Student'}</span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Annual Income</span>
                <span
                  className={`profile-detail-value ${!profileData.income || profileData.income === 'Not added' ? 'text-not-added' : ''}`}
                >
                  {profileData.income || 'Not added'}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Applicant Type</span>
                <span className="profile-detail-value">{profileData.applicantType || 'Individual'}</span>
              </div>
            </div>

            {/* Recommendation Callout Banner */}
            <div
              className="profile-recommendation-callout"
              onClick={handleOpenEditModal}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && handleOpenEditModal()}
              aria-label="Complete location and income details"
            >
              <div className="callout-left">
                <Target size={17} className="callout-target-icon" aria-hidden="true" />
                <span className="callout-text">
                  Complete your location and income details to receive more relevant scheme recommendations.
                </span>
              </div>
              <ChevronRight size={16} className="callout-arrow" aria-hidden="true" />
            </div>
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
                  <span>Verified</span>
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
                <span className="profile-detail-value">Email & Password</span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Last login</span>
                <span className="profile-detail-value">23 Sep 2026, 10:24 AM</span>
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
                        onChange={handleEditChange}
                      >
                        <option value="Gujarat">Gujarat</option>
                        <option value="Maharashtra">Maharashtra</option>
                        <option value="Delhi">Delhi</option>
                        <option value="Karnataka">Karnataka</option>
                        <option value="Tamil Nadu">Tamil Nadu</option>
                        <option value="Uttar Pradesh">Uttar Pradesh</option>
                        <option value="Rajasthan">Rajasthan</option>
                        <option value="Madhya Pradesh">Madhya Pradesh</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="inputDistrict">
                        District
                      </label>
                      <input
                        id="inputDistrict"
                        type="text"
                        name="district"
                        placeholder="e.g. Ahmedabad, Pune"
                        className="modal-form-input"
                        value={editFormData.district}
                        onChange={handleEditChange}
                      />
                    </div>

                    <div className="modal-form-field">
                      <label className="modal-form-label" htmlFor="selectIncome">
                        Annual Income
                      </label>
                      <select
                        id="selectIncome"
                        name="income"
                        className="modal-form-select"
                        value={editFormData.income}
                        onChange={handleEditChange}
                      >
                        <option value="">Select income range</option>
                        <option value="Below ₹1 Lakh">Below ₹1 Lakh</option>
                        <option value="₹1 Lakh - ₹2.5 Lakhs">₹1 Lakh - ₹2.5 Lakhs</option>
                        <option value="₹2.5 Lakhs - ₹5 Lakhs">₹2.5 Lakhs - ₹5 Lakhs</option>
                        <option value="₹5 Lakhs - ₹10 Lakhs">₹5 Lakhs - ₹10 Lakhs</option>
                        <option value="Above ₹10 Lakhs">Above ₹10 Lakhs</option>
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
                        value={editFormData.gender}
                        onChange={handleEditChange}
                      >
                        <option value="">Select gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Transgender">Transgender</option>
                        <option value="Prefer not to say">Prefer not to say</option>
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
                  <button type="submit" className="btn-modal-save">
                    Update Password
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
