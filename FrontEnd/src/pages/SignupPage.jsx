import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  User,
  Mail,
  Phone,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ChevronDown,
  X,
  CheckCircle2,
  ShieldAlert,
  ShieldCheck,
  FileText,
} from 'lucide-react';
import '../styles/signup.css';
import {
  registerUser,
  loginUser,
  storeAuthSession,
  getRegisteredUserByEmail,
  saveRegisteredUser,
} from '../services/authService';

const DEV_AUTH_BYPASS_ENABLED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEV_AUTH_BYPASS === 'true';

// Assets
import indiaGateHero from '../assets/india_gate_hero.jpg';
import tricolorRibbon from '../assets/tricolor_ribbon_original.png';
import cardMonumentSketch from '../assets/card_monument_sketch.png';

const COUNTRY_OPTIONS = [
  { code: '+91', country: 'India', flag: '🇮🇳' },
  { code: '+1', country: 'United States', flag: '🇺🇸' },
  { code: '+44', country: 'United Kingdom', flag: '🇬🇧' },
  { code: '+971', country: 'United Arab Emirates', flag: '🇦🇪' },
  { code: '+1', country: 'Canada', flag: '🇨🇦' },
  { code: '+61', country: 'Australia', flag: '🇦🇺' },
  { code: '+65', country: 'Singapore', flag: '🇸🇬' },
  { code: '+49', country: 'Germany', flag: '🇩🇪' },
  { code: '+33', country: 'France', flag: '🇫🇷' },
  { code: '+81', country: 'Japan', flag: '🇯🇵' },
  { code: '+966', country: 'Saudi Arabia', flag: '🇸🇦' },
  { code: '+974', country: 'Qatar', flag: '🇶🇦' },
];

export default function SignupPage({ initialMode = 'signup' }) {
  const navigate = useNavigate();
  const location = useLocation();
  const inactivityReason = new URLSearchParams(location.search).get('reason');
  const isInactivityRedirect = inactivityReason === 'timeout' || inactivityReason === 'inactivity';
  const [isSignIn, setIsSignIn] = useState(initialMode === 'signin' || isInactivityRedirect);
  const [inactivityNotice] = useState(
    isInactivityRedirect
      ? 'For your security, your session was automatically ended due to inactivity. Please sign in again to continue.'
      : null
  );
  const [showPassword, setShowPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState(COUNTRY_OPTIONS[0]);
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Modals: null | 'terms' | 'privacy' | 'forgot'
  const [activeModal, setActiveModal] = useState(null);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitted, setForgotSubmitted] = useState(false);

  // Form Fields
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    mobile: '',
    password: '',
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const dropdownRef = useRef(null);

  // Close country dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setCountryDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errorMsg) setErrorMsg('');
  };

  const handleCountrySelect = (country) => {
    setSelectedCountry(country);
    setCountryDropdownOpen(false);
    setCountrySearch('');
  };

  const filteredCountries = COUNTRY_OPTIONS.filter(
    (c) =>
      c.country.toLowerCase().includes(countrySearch.toLowerCase()) ||
      c.code.includes(countrySearch)
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!isSignIn && !formData.fullName.trim()) {
      setErrorMsg('Please enter your full name.');
      return;
    }

    if (!formData.email.trim() || !formData.email.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    if (!isSignIn && !formData.mobile.trim()) {
      setErrorMsg('Please enter your mobile number.');
      return;
    }

    if (!formData.password || formData.password.length < 6) {
      setErrorMsg('Password must be at least 6 characters.');
      return;
    }

    if (!isSignIn && !agreedToTerms) {
      setErrorMsg('Please agree to the Terms of Service and Privacy Policy.');
      return;
    }

    setIsSubmitting(true);

    try {
      let authResult;

      if (isSignIn) {
        // Call BackEnd /api/users/login
        authResult = await loginUser({
          email: formData.email,
          password: formData.password,
        });
      } else {
        // Call BackEnd /api/users/register
        authResult = await registerUser({
          email: formData.email,
          password: formData.password,
          fullName: formData.fullName,
          phone: `${selectedCountry.code}${formData.mobile}`,
        });

      }

      // Check for backend errors (validation, invalid credentials, existing user, etc.)
      if (!authResult.success) {
        if (!authResult.isNetworkError) {
          setErrorMsg(authResult.message);
          setIsSubmitting(false);
          return;
        }

        if (!DEV_AUTH_BYPASS_ENABLED) {
          setErrorMsg(authResult.message);
          setIsSubmitting(false);
          return;
        }

        console.warn('Backend server offline, continuing with local development session:', authResult.message);
      }

      // Resolve proper registered citizen name (so login preserves the registration username)
      const targetEmail = formData.email.trim();
      const registeredProfile = getRegisteredUserByEmail(targetEmail);

      let citizenFullName = '';
      if (!isSignIn) {
        citizenFullName = formData.fullName.trim();
        saveRegisteredUser({
          email: targetEmail,
          fullName: citizenFullName,
          phone: `${selectedCountry.code}${formData.mobile}`.trim(),
        });
      } else {
        citizenFullName =
          authResult.data?.user?.user_metadata?.full_name ||
          authResult.data?.user?.user_metadata?.fullName ||
          authResult.data?.user?.fullName ||
          registeredProfile?.fullName ||
          '';
      }

      // Store authenticated session
      storeAuthSession({
        user: {
          ...(authResult.data?.user || {}),
          email: targetEmail,
          ...(citizenFullName ? { fullName: citizenFullName } : {}),
          state: registeredProfile?.state,
          district: registeredProfile?.district,
          occupation: registeredProfile?.occupation,
          income: registeredProfile?.income,
          applicantType: registeredProfile?.applicantType,
          dob: registeredProfile?.dob,
          gender: registeredProfile?.gender,
        },
        accessToken: authResult.data?.access_token,
        refreshToken: authResult.data?.refresh_token,
        fallbackName: citizenFullName || (isSignIn ? (registeredProfile?.fullName || '') : formData.fullName.trim()),
      });

      setSuccessMsg(isSignIn ? 'Welcome back! Redirecting...' : 'Account created successfully! Redirecting...');
      setTimeout(() => {
        navigate('/dashboard');
      }, 700);
    } catch (err) {
      setErrorMsg(err.message || 'An unexpected error occurred. Please try again.');
      setIsSubmitting(false);
    }
  };

  const handleGoogleAuth = () => {
    setSuccessMsg('Connecting with Google Account...');
    setTimeout(() => {
      storeAuthSession({
        user: { id: 'google-oauth-demo', email: 'citizen@gov.in' },
        accessToken: 'google-oauth-demo-token',
        fallbackName: 'Google User',
      });
      navigate('/dashboard');
    }, 700);
  };

  const handleDevAuthBypass = () => {
    const email = formData.email.trim() || 'developer@localhost.test';
    const name = !isSignIn && formData.fullName.trim()
      ? formData.fullName.trim()
      : getRegisteredUserByEmail(email)?.fullName || 'Developer';
    storeAuthSession({
      user: { id: `dev-${email}`, email, fullName: name, user_metadata: { full_name: name } },
      accessToken: 'development-only-bypass-token',
      refreshToken: 'development-only-bypass-refresh-token',
      fallbackName: name,
    });
    navigate('/dashboard');
  };

  const handleForgotSubmit = (e) => {
    e.preventDefault();
    if (!forgotEmail || !forgotEmail.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }
    setForgotSubmitted(true);
  };

  return (
    <div className="signup-viewport">
      {/* Background Atmosphere Layers */}
      <div className="signup-bg-gradient" aria-hidden="true" />

      {/* Scenic India Gate visual at bottom-left */}
      <div className="signup-scenery-wrap" aria-hidden="true">
        <img
          src={indiaGateHero}
          alt="India Gate Sunrise"
          className="signup-scenery-img"
        />
        <div className="signup-scenery-haze" />
      </div>

      {/* Birds in the sky SVG */}
      <svg
        className="signup-birds-svg"
        viewBox="0 0 160 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M20 30 C25 24, 30 26, 35 32 C40 26, 45 24, 50 30"
          stroke="#3B2A1E"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <path
          d="M65 18 C69 13, 73 14, 77 19 C81 14, 85 13, 89 18"
          stroke="#3B2A1E"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
        <path
          d="M105 28 C108 24, 111 25, 114 29 C117 25, 120 24, 123 28"
          stroke="#3B2A1E"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
        <path
          d="M80 44 C83 40, 86 41, 89 45 C92 41, 95 40, 98 44"
          stroke="#3B2A1E"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
        <path
          d="M130 38 C133 35, 136 36, 139 39 C142 36, 145 35, 148 38"
          stroke="#3B2A1E"
          strokeWidth="1.1"
          strokeLinecap="round"
        />
      </svg>

      {/* Flowing Tricolor Ribbon Wave along the bottom */}
      <svg
        className="signup-tricolor-wave"
        viewBox="0 0 1100 160"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="waveSaffron" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#EA580C" stopOpacity="0.85" />
            <stop offset="35%" stopColor="#F97316" stopOpacity="0.95" />
            <stop offset="70%" stopColor="#FB923C" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#EA580C" stopOpacity="0.75" />
          </linearGradient>
          <linearGradient id="waveWhite" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.4" />
            <stop offset="40%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="70%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.4" />
          </linearGradient>
          <linearGradient id="waveGreen" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#047857" stopOpacity="0.85" />
            <stop offset="35%" stopColor="#059669" stopOpacity="0.95" />
            <stop offset="70%" stopColor="#10B981" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#047857" stopOpacity="0.75" />
          </linearGradient>
        </defs>

        {/* Saffron Stream */}
        <path
          d="M-20 65 C 220 50, 480 135, 780 115 C 930 105, 1020 135, 1120 145"
          stroke="url(#waveSaffron)"
          strokeWidth="6"
          strokeLinecap="round"
        />

        {/* White Stream */}
        <path
          d="M-20 75 C 220 60, 480 145, 780 125 C 930 115, 1020 145, 1120 155"
          stroke="url(#waveWhite)"
          strokeWidth="5"
          strokeLinecap="round"
        />

        {/* Emerald Green Stream */}
        <path
          d="M-20 85 C 220 70, 480 155, 780 135 C 930 125, 1020 155, 1120 165"
          stroke="url(#waveGreen)"
          strokeWidth="6"
          strokeLinecap="round"
        />
      </svg>

      {/* Top Navigation Bar */}
      <header className="signup-navbar">
        <Link to="/dashboard" className="signup-nav-logo" title="FIN — Home">
          <div className="signup-logo-row">
            <span className="signup-logo-text">FIN</span>
            <img
              src={tricolorRibbon}
              alt="Tricolor Flag"
              className="signup-logo-flag"
            />
          </div>
          <span className="signup-logo-sub">Financial Policy Intelligence</span>
        </Link>

        <div className="signup-nav-right">
          <span>
            {isSignIn ? "Don't have an account?" : 'Already have an account?'}
          </span>
          <button
            type="button"
            className="signup-nav-signin-btn"
            id="authModeToggleBtn"
            onClick={() => {
              setIsSignIn(!isSignIn);
              setErrorMsg('');
              setSuccessMsg('');
            }}
          >
            <span>{isSignIn ? 'Sign Up' : 'Sign In'}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="signup-main-content">
        {/* Left Hero Column */}
        <section className="signup-hero-col">
          <div className="signup-hero-badge">
            <span className="signup-hero-line" />
            <span className="signup-hero-tag">
              Government Schemes, Your Rights
            </span>
          </div>

          <h1 className="signup-hero-title">
            A Stronger India
            <br />
            Through Informed
            <br />
            Citizens.
          </h1>

          <p className="signup-hero-desc">
            Discover government schemes, check your eligibility
            <br />
            and apply — all in one place.
          </p>

          <div className="signup-quote-box">
            <blockquote className="signup-quote-hindi">
              &ldquo;Sarkar ki yojana,
              <br />
              aapke sapno ka saathi.&rdquo;
            </blockquote>
            <div className="signup-quote-author">
              <img
                src={tricolorRibbon}
                alt="Tricolor"
                className="signup-quote-flag"
              />
              <span>&mdash; Government of India</span>
            </div>
          </div>
        </section>

        {/* Right Sign-Up / Sign-In Card */}
        <section className="signup-card-col">
          <div className="signup-card">
            {/* Card Overline Header */}
            <div className="signup-card-badge">
              <span className="signup-card-tag">
                {isSignIn ? 'SIGN IN' : 'CREATE ACCOUNT'}
              </span>
              <span className="signup-card-line" />
            </div>

            <h2 className="signup-card-title">
              {isSignIn ? 'Welcome Back' : 'Join FIN'}
            </h2>

            <p className="signup-card-subtitle">
              {isSignIn
                ? 'Sign in to access your saved schemes and track applications.'
                : 'Create your account to access government schemes and personalized recommendations.'}
            </p>

            {/* Session Inactivity Warning Banner */}
            {inactivityNotice && (
              <div className="signup-alert signup-alert-warning" role="alert">
                <ShieldAlert size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>{inactivityNotice}</span>
              </div>
            )}

            {/* Error or Success Alert */}
            {errorMsg && (
              <div className="signup-alert signup-alert-error" role="alert">
                {errorMsg}
              </div>
            )}
            {successMsg && (
              <div className="signup-alert signup-alert-success" role="status">
                {successMsg}
              </div>
            )}

            {/* Form */}
            <form className="signup-form" onSubmit={handleSubmit} noValidate>
              {/* Full Name (Sign Up only) */}
              {!isSignIn && (
                <div className="signup-field">
                  <label htmlFor="fullName" className="signup-label">
                    Full Name
                  </label>
                  <div className="signup-input-wrap">
                    <User size={16} className="signup-input-icon" />
                    <input
                      id="fullName"
                      name="fullName"
                      type="text"
                      placeholder="Enter your full name"
                      value={formData.fullName}
                      onChange={handleChange}
                      className="signup-input"
                      autoComplete="name"
                      required
                    />
                  </div>
                </div>
              )}

              {/* Email Address */}
              <div className="signup-field">
                <label htmlFor="email" className="signup-label">
                  Email Address
                </label>
                <div className="signup-input-wrap">
                  <Mail size={16} className="signup-input-icon" />
                  <input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="Enter your email address"
                    value={formData.email}
                    onChange={handleChange}
                    className="signup-input"
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              {/* Mobile Number (Sign Up only) */}
              {!isSignIn && (
                <div className="signup-field" ref={dropdownRef}>
                  <label htmlFor="mobile" className="signup-label">
                    Mobile Number
                  </label>
                  <div className="signup-input-wrap">
                    <Phone size={15} className="signup-input-icon" />

                    {/* Country Selector Button */}
                    <button
                      type="button"
                      className="signup-country-btn"
                      id="countrySelectorBtn"
                      onClick={() =>
                        setCountryDropdownOpen(!countryDropdownOpen)
                      }
                      aria-label="Select Country Code"
                      aria-expanded={countryDropdownOpen}
                    >
                      {/* India Flag SVG for +91 or dynamic flag */}
                      {selectedCountry.code === '+91' ? (
                        <svg
                          width="16"
                          height="11"
                          viewBox="0 0 24 16"
                          style={{ borderRadius: '2px', display: 'inline-block' }}
                        >
                          <rect width="24" height="5.33" fill="#FF9933" />
                          <rect y="5.33" width="24" height="5.33" fill="#FFFFFF" />
                          <rect y="10.67" width="24" height="5.33" fill="#138808" />
                          <circle
                            cx="12"
                            cy="8"
                            r="2.2"
                            fill="none"
                            stroke="#000080"
                            strokeWidth="0.6"
                          />
                        </svg>
                      ) : (
                        <span style={{ fontSize: '13px' }}>
                          {selectedCountry.flag}
                        </span>
                      )}
                      <span>{selectedCountry.code}</span>
                      <ChevronDown size={12} />
                    </button>

                    <div className="signup-mobile-divider" />

                    <input
                      id="mobile"
                      name="mobile"
                      type="tel"
                      placeholder="Enter your mobile number"
                      value={formData.mobile}
                      onChange={handleChange}
                      className="signup-input"
                      autoComplete="tel"
                      required
                    />
                  </div>

                  {/* Country Dropdown Popover */}
                  {countryDropdownOpen && (
                    <div className="signup-country-dropdown" role="listbox">
                      <div className="signup-country-search-wrap">
                        <input
                          type="text"
                          placeholder="Search country or code..."
                          value={countrySearch}
                          onChange={(e) => setCountrySearch(e.target.value)}
                          className="signup-country-search-input"
                          autoFocus
                        />
                      </div>
                      {filteredCountries.map((c) => (
                        <button
                          key={`${c.code}-${c.country}`}
                          type="button"
                          className="signup-country-item"
                          onClick={() => handleCountrySelect(c)}
                        >
                          <div className="signup-country-item-left">
                            <span className="signup-country-item-flag">
                              {c.code === '+91' ? (
                                <svg
                                  width="18"
                                  height="12"
                                  viewBox="0 0 24 16"
                                  style={{ borderRadius: '2px', display: 'inline-block' }}
                                >
                                  <rect width="24" height="5.33" fill="#FF9933" />
                                  <rect y="5.33" width="24" height="5.33" fill="#FFFFFF" />
                                  <rect y="10.67" width="24" height="5.33" fill="#138808" />
                                  <circle
                                    cx="12"
                                    cy="8"
                                    r="2.2"
                                    fill="none"
                                    stroke="#000080"
                                    strokeWidth="0.6"
                                  />
                                </svg>
                              ) : (
                                c.flag
                              )}
                            </span>
                            <span>{c.country}</span>
                          </div>
                          <span className="signup-country-item-code">
                            {c.code}
                          </span>
                        </button>
                      ))}
                      {filteredCountries.length === 0 && (
                        <div
                          style={{
                            padding: '8px 12px',
                            fontSize: '12px',
                            color: '#64748B',
                          }}
                        >
                          No countries match
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Password */}
              <div className="signup-field">
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <label htmlFor="password" className="signup-label">
                    Password
                  </label>
                  {isSignIn && (
                    <button
                      type="button"
                      className="signup-link-btn"
                      onClick={() => {
                        setActiveModal('forgot');
                        setForgotSubmitted(false);
                        setForgotEmail(formData.email || '');
                      }}
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="signup-input-wrap">
                  <Lock size={16} className="signup-input-icon" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder={
                      isSignIn ? 'Enter your password' : 'Create a strong password'
                    }
                    value={formData.password}
                    onChange={handleChange}
                    className="signup-input"
                    autoComplete={isSignIn ? 'current-password' : 'new-password'}
                    required
                  />
                  <button
                    type="button"
                    className="signup-eye-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Terms Checkbox (Sign Up only) */}
              {!isSignIn && (
                <div className="signup-terms-row">
                  <input
                    type="checkbox"
                    id="termsAgreementCheckbox"
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                    className="signup-checkbox"
                  />
                  <label
                    htmlFor="termsAgreementCheckbox"
                    className="signup-terms-text"
                  >
                    I agree to the{' '}
                    <button
                      type="button"
                      className="signup-link-btn"
                      onClick={(e) => {
                        e.preventDefault();
                        setActiveModal('terms');
                      }}
                    >
                      Terms of Service
                    </button>{' '}
                    and{' '}
                    <button
                      type="button"
                      className="signup-link-btn"
                      onClick={(e) => {
                        e.preventDefault();
                        setActiveModal('privacy');
                      }}
                    >
                      Privacy Policy
                    </button>
                  </label>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                id="submitAuthBtn"
                className="signup-submit-btn"
                disabled={isSubmitting}
              >
                <span>
                  {isSubmitting
                    ? 'Processing...'
                    : isSignIn
                    ? 'Sign In'
                    : 'Create Account'}
                </span>
                <ArrowRight size={15} />
              </button>

              {/* OR Divider */}
              <div className="signup-divider">
                <span className="signup-divider-line" />
                <span className="signup-divider-text">OR</span>
                <span className="signup-divider-line" />
              </div>

              {/* Continue with Google */}
              <button
                type="button"
                id="googleAuthBtn"
                className="signup-google-btn"
                onClick={handleGoogleAuth}
              >
                <svg width="17" height="17" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.35 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 10.03 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>

              {DEV_AUTH_BYPASS_ENABLED && (
                <button
                  type="button"
                  className="signup-dev-bypass-btn"
                  onClick={handleDevAuthBypass}
                >
                  Skip authentication (development only)
                </button>
              )}
            </form>

            {/* Card Footer Heritage Line Sketch & Quote */}
            <div className="signup-card-footer">
              <img
                src={cardMonumentSketch}
                alt="Indian Architecture Skyline"
                className="signup-card-monument"
              />
              <img
                src={tricolorRibbon}
                alt="Tricolor"
                className="signup-card-flag"
              />
              <p className="signup-card-footer-quote">
                Empowered citizens build a stronger India.
              </p>
              <p className="signup-card-footer-sub">&mdash; Government of India</p>
            </div>
          </div>
        </section>
      </main>

      {/* Modals Dialog (Terms of Service, Privacy Policy, Forgot Password) */}
      {activeModal && (
        <div
          className="signup-modal-backdrop"
          onClick={() => setActiveModal(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="signup-modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="signup-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {activeModal === 'terms' && <FileText size={20} color="#06542A" />}
                {activeModal === 'privacy' && <ShieldCheck size={20} color="#06542A" />}
                {activeModal === 'forgot' && <Lock size={20} color="#06542A" />}
                <h3 className="signup-modal-title">
                  {activeModal === 'terms' && 'Terms of Service'}
                  {activeModal === 'privacy' && 'Privacy Policy'}
                  {activeModal === 'forgot' && 'Reset Password'}
                </h3>
              </div>
              <button
                type="button"
                className="signup-modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="signup-modal-body">
              {activeModal === 'terms' && (
                <>
                  <h4>1. Acceptance of Terms</h4>
                  <p>
                    By creating an account on the FIN Financial Policy Discovery
                    Platform, you acknowledge that this portal assists Indian
                    citizens in identifying, checking eligibility for, and
                    applying for Central and State Government welfare schemes.
                  </p>
                  <h4>2. Citizen Information Accuracy</h4>
                  <p>
                    You agree that all personal, demographic, and financial details
                    provided are genuine and match your official Indian identity
                    documents (Aadhaar, PAN, Ration Card, etc.).
                  </p>
                  <h4>3. Scheme Eligibility & Disbursement</h4>
                  <p>
                    FIN acts as an informational assistant and application
                    facilitator. Final eligibility verification and direct benefit
                    transfers (DBT) remain solely under the jurisdiction of the
                    respective government ministries.
                  </p>
                </>
              )}

              {activeModal === 'privacy' && (
                <>
                  <h4>1. Protection of Citizen Data</h4>
                  <p>
                    FIN adheres to the Digital Personal Data Protection Act (DPDPA)
                    guidelines. Your data is encrypted in transit and at rest using
                    banking-grade protocols.
                  </p>
                  <h4>2. Information Collected</h4>
                  <p>
                    We collect basic contact information (Name, Email, Mobile
                    Number) and optional scheme eligibility metrics only to provide
                    tailored policy recommendations.
                  </p>
                  <h4>3. No Commercial Data Sharing</h4>
                  <p>
                    Your personal information is never sold, leased, or shared with
                    unauthorized third-party advertisers or private entities.
                  </p>
                </>
              )}

              {activeModal === 'forgot' && (
                <>
                  {forgotSubmitted ? (
                    <div style={{ textAlign: 'center', padding: '16px 0' }}>
                      <CheckCircle2
                        size={40}
                        color="#059669"
                        style={{ margin: '0 auto 12px auto' }}
                      />
                      <h4 style={{ color: '#10243A', marginBottom: '8px' }}>
                        Reset Link Dispatched
                      </h4>
                      <p style={{ color: '#4B5563', fontSize: '13px' }}>
                        If an account exists for <strong>{forgotEmail}</strong>,
                        you will receive an email shortly with instructions to reset
                        your credentials.
                      </p>
                    </div>
                  ) : (
                    <form onSubmit={handleForgotSubmit}>
                      <p style={{ color: '#4B5563', fontSize: '13px' }}>
                        Enter the email associated with your FIN account and we'll
                        send you instructions to securely reset your password.
                      </p>
                      <div className="signup-field" style={{ marginTop: '12px' }}>
                        <label htmlFor="forgotEmail" className="signup-label">
                          Registered Email
                        </label>
                        <div className="signup-input-wrap">
                          <Mail size={16} className="signup-input-icon" />
                          <input
                            id="forgotEmail"
                            type="email"
                            placeholder="Enter your registered email"
                            value={forgotEmail}
                            onChange={(e) => setForgotEmail(e.target.value)}
                            className="signup-input"
                            required
                          />
                        </div>
                      </div>
                      <button
                        type="submit"
                        className="signup-submit-btn"
                        style={{ marginTop: '16px' }}
                      >
                        Send Reset Instructions
                      </button>
                    </form>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="signup-modal-footer">
              {activeModal === 'terms' && (
                <>
                  <button
                    type="button"
                    className="signup-modal-btn-secondary"
                    onClick={() => setActiveModal(null)}
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    className="signup-modal-btn-primary"
                    onClick={() => {
                      setAgreedToTerms(true);
                      setActiveModal(null);
                    }}
                  >
                    I Accept Terms
                  </button>
                </>
              )}
              {activeModal === 'privacy' && (
                <>
                  <button
                    type="button"
                    className="signup-modal-btn-secondary"
                    onClick={() => setActiveModal(null)}
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    className="signup-modal-btn-primary"
                    onClick={() => {
                      setAgreedToTerms(true);
                      setActiveModal(null);
                    }}
                  >
                    I Understand
                  </button>
                </>
              )}
              {activeModal === 'forgot' && forgotSubmitted && (
                <button
                  type="button"
                  className="signup-modal-btn-primary"
                  onClick={() => setActiveModal(null)}
                >
                  Done
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
