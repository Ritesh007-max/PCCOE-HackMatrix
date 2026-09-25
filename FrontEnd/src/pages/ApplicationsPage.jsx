import React, { useState, useMemo, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Search,
  ChevronDown,
  MoreVertical,
  Headphones,
  Info,
  ArrowRight,
  X,
  Download,
  Check,
  ShieldCheck,
  Eye,
  FileCheck,
  AlertCircle
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import { StandUpIndiaLogo, MudraLogo } from '../components/common/BrandAssets';
import { fetchUserApplications, submitApplication } from '../services/applicationService';

// Assets
import ashokStambhOriginal from '../assets/ashok_stambh_original.png';
import msmeOriginal from '../assets/msme_original.png';
import kisanOriginal from '../assets/kisan_original.png';
import indiaGateHero from '../assets/india_gate_hero.jpg';
import tricolorRibbon from '../assets/tricolor_flag_perfect.png';
import cardMonumentSketch from '../assets/card_monument_sketch.png';

// Dataset matching image copy 3.png
const INITIAL_APPLICATIONS = [
  {
    id: 'pmegp',
    schemeTitle: 'PMEGP',
    schemeSubtitle: "Prime Minister's Employment Generation Programme",
    applicationId: 'FIN202600123',
    appliedDate: '15 Sep 2026',
    rawDate: '2026-09-15',
    benefitAmount: '₹1,25,000',
    benefitSubtitle: 'Estimated Benefit',
    benefitNumeric: 125000,
    status: 'under_review',
    statusBadge: 'Under Review',
    statusMessage: 'Your application is under review.',
    actionLabel: 'View Application',
    actionType: 'view',
    logoType: 'ashoka',
    submittedDocs: [
      { name: 'Aadhaar Card (Biometric Verified)', verified: true },
      { name: 'PAN Card (NSDL Linked)', verified: true },
      { name: 'Detailed Project Report (DPR)', verified: true },
      { name: 'Special Category Caste Certificate', verified: true }
    ],
    steps: [
      { label: 'Submitted', date: '15 Sep 2026', status: 'completed' },
      { label: 'Verification', date: 'In Progress', status: 'current-green' },
      { label: 'Approval', date: '', status: 'upcoming' },
      { label: 'Disbursement', date: '', status: 'upcoming' }
    ]
  },
  {
    id: 'msme-financial-support',
    schemeTitle: 'MSME Financial Support',
    schemeSubtitle: 'Ministry of Micro, Small and Medium Enterprises',
    applicationId: 'FIN202600087',
    appliedDate: '02 Sep 2026',
    rawDate: '2026-09-02',
    benefitAmount: '₹80,000',
    benefitSubtitle: 'Estimated Benefit',
    benefitNumeric: 80000,
    status: 'action_required',
    statusBadge: 'Action Required',
    statusMessage: 'Please upload additional documents.',
    actionLabel: 'Continue Application',
    actionType: 'continue',
    logoType: 'msme',
    submittedDocs: [
      { name: 'Udyam Registration Certificate', verified: true },
      { name: 'Bank Statement (Last 6 Months)', verified: false, reason: 'Page 3 missing stamp' },
      { name: 'Electricity Bill for Business Premises', verified: false, reason: 'Expired bill' }
    ],
    steps: [
      { label: 'Submitted', date: '02 Sep 2026', status: 'completed' },
      { label: 'Verification', date: 'Pending Documents', status: 'error' },
      { label: 'Approval', date: '', status: 'upcoming' },
      { label: 'Disbursement', date: '', status: 'upcoming' }
    ]
  },
  {
    id: 'pm-kisan',
    schemeTitle: 'PM Kisan Samman Nidhi',
    schemeSubtitle: 'Income Support for Small & Marginal Farmers',
    applicationId: 'FIN202600045',
    appliedDate: '28 Aug 2026',
    rawDate: '2026-08-28',
    benefitAmount: '₹6,000 / year',
    benefitSubtitle: 'Estimated Benefit',
    benefitNumeric: 6000,
    status: 'approved',
    statusBadge: 'Approved',
    statusMessage: 'Your application has been approved.',
    actionLabel: 'View Application',
    actionType: 'view',
    logoType: 'kisan',
    submittedDocs: [
      { name: 'Land Record (7/12 & 8A Extract)', verified: true },
      { name: 'Aadhaar Seeded Bank Passbook', verified: true },
      { name: 'Self-declaration Affidavit', verified: true }
    ],
    steps: [
      { label: 'Submitted', date: '28 Aug 2026', status: 'completed' },
      { label: 'Verification', date: '05 Sep 2026', status: 'completed' },
      { label: 'Approved', date: '12 Sep 2026', status: 'completed' },
      { label: 'Disbursement', date: '', status: 'upcoming' }
    ]
  },
  {
    id: 'stand-up-india',
    schemeTitle: 'Stand Up India',
    schemeSubtitle: 'Credit Guarantee for SC/ST and Women Entrepreneurs',
    applicationId: 'FIN202600032',
    appliedDate: '10 Aug 2026',
    rawDate: '2026-08-10',
    benefitAmount: '₹50 Lakh',
    benefitSubtitle: 'Estimated Benefit',
    benefitNumeric: 5000000,
    status: 'draft',
    statusBadge: 'Draft',
    statusMessage: 'Application not yet submitted.',
    actionLabel: 'Continue Application',
    actionType: 'continue',
    logoType: 'standup',
    submittedDocs: [
      { name: 'Identity Proof (Aadhaar)', verified: true },
      { name: 'Business Plan Draft', verified: false, reason: 'Pending final review' }
    ],
    steps: [
      { label: 'Draft', date: '10 Aug 2026', status: 'current-green' },
      { label: 'Submitted', date: '', status: 'upcoming' },
      { label: 'Verification', date: '', status: 'upcoming' },
      { label: 'Approval', date: '', status: 'upcoming' }
    ]
  },
  {
    id: 'mudra-yojana',
    schemeTitle: 'Mudra Yojana',
    schemeSubtitle: 'Collateral-free Loans for Micro Enterprises',
    applicationId: 'FIN202600018',
    appliedDate: '25 Jul 2026',
    rawDate: '2026-07-25',
    benefitAmount: '₹10 Lakh',
    benefitSubtitle: 'Estimated Benefit',
    benefitNumeric: 1000000,
    status: 'not_started',
    statusBadge: 'Not Started',
    statusMessage: 'Start your application to avail benefits.',
    actionLabel: 'Start Application',
    actionType: 'start',
    logoType: 'mudra',
    submittedDocs: [],
    steps: [
      { label: 'Not Started', date: '', status: 'current-green' },
      { label: 'Submitted', date: '', status: 'upcoming' },
      { label: 'Verification', date: '', status: 'upcoming' },
      { label: 'Approval', date: '', status: 'upcoming' }
    ]
  }
];

export default function ApplicationsPage() {
  const navigate = useNavigate();

  // Search, filter, and sorting states
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('latest');
  const [applicationsList, setApplicationsList] = useState(INITIAL_APPLICATIONS);

  // Modal and menu states
  const [selectedApp, setSelectedApp] = useState(null);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showGuidelinesModal, setShowGuidelinesModal] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const menuRef = useRef(null);

  // Sync applications from backend API on mount
  useEffect(() => {
    const syncBackendApps = async () => {
      try {
        const backendApps = await fetchUserApplications();
        if (backendApps && backendApps.length > 0) {
          setApplicationsList((prevApps) => {
            const merged = [...prevApps];
            backendApps.forEach((bApp) => {
              const existingIdx = merged.findIndex(
                (a) => a.id === bApp.scheme_id || a.applicationId === bApp.id
              );
              const status = bApp.status || 'under_review';
              const statusBadge = status === 'under_review' ? 'Under Review' :
                status === 'approved' ? 'Approved' :
                status === 'action_required' ? 'Action Required' :
                status === 'draft' ? 'Draft' : 'Not Started';

              if (existingIdx >= 0) {
                merged[existingIdx] = {
                  ...merged[existingIdx],
                  status,
                  statusBadge,
                  appliedDate: bApp.submitted_at
                    ? new Date(bApp.submitted_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
                    : merged[existingIdx].appliedDate
                };
              } else {
                merged.unshift({
                  id: bApp.scheme_id || bApp.id,
                  schemeTitle: bApp.scheme_name || 'Government Scheme',
                  schemeSubtitle: 'Government of India Programme',
                  applicationId: `FIN${String(bApp.id).slice(0, 8).toUpperCase()}`,
                  appliedDate: bApp.submitted_at
                    ? new Date(bApp.submitted_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
                    : 'Today',
                  rawDate: bApp.submitted_at ? bApp.submitted_at.slice(0, 10) : new Date().toISOString().slice(0, 10),
                  benefitAmount: bApp.estimated_benefit ? `₹${Number(bApp.estimated_benefit).toLocaleString('en-IN')}` : '₹1,25,000',
                  benefitSubtitle: 'Estimated Benefit',
                  benefitNumeric: bApp.estimated_benefit || 125000,
                  status,
                  statusBadge,
                  statusMessage: `Your application is ${statusBadge.toLowerCase()}.`,
                  actionLabel: 'View Application',
                  actionType: 'view',
                  logoType: 'ashoka',
                  submittedDocs: [],
                  steps: [
                    { label: 'Submitted', date: 'Today', status: 'completed' },
                    { label: 'Verification', date: 'In Progress', status: 'current-green' },
                    { label: 'Approval', date: '', status: 'upcoming' },
                    { label: 'Disbursement', date: '', status: 'upcoming' }
                  ]
                });
              }
            });
            return merged;
          });
        }
      } catch (err) {
        console.warn('Backend applications sync notice:', err);
      }
    };
    syncBackendApps();
  }, []);

  // Close kebab dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setActiveMenuId(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // Filtered and sorted applications
  const filteredApplications = useMemo(() => {
    return applicationsList.filter((app) => {
      // 1. Status Filter
      if (statusFilter !== 'all') {
        if (statusFilter === 'under_review' && app.status !== 'under_review') return false;
        if (statusFilter === 'action_required' && app.status !== 'action_required') return false;
        if (statusFilter === 'approved' && app.status !== 'approved') return false;
        if (statusFilter === 'draft' && app.status !== 'draft') return false;
        if (statusFilter === 'not_started' && app.status !== 'not_started') return false;
      }

      // 2. Search Query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchesTitle = app.schemeTitle.toLowerCase().includes(query);
        const matchesId = app.applicationId.toLowerCase().includes(query);
        const matchesSubtitle = app.schemeSubtitle.toLowerCase().includes(query);
        if (!matchesTitle && !matchesId && !matchesSubtitle) {
          return false;
        }
      }

      return true;
    }).sort((a, b) => {
      if (sortBy === 'latest') {
        return new Date(b.rawDate) - new Date(a.rawDate);
      }
      if (sortBy === 'oldest') {
        return new Date(a.rawDate) - new Date(b.rawDate);
      }
      if (sortBy === 'benefit') {
        return b.benefitNumeric - a.benefitNumeric;
      }
      return 0;
    });
  }, [searchQuery, statusFilter, sortBy]);

  // Helper to render scheme logo
  const renderSchemeLogo = (logoType) => {
    switch (logoType) {
      case 'ashoka':
        return (
          <img
            src={ashokStambhOriginal}
            alt="State Emblem of India"
            className="app-card-logo-img"
            style={{ width: '38px', height: '48px', objectFit: 'contain' }}
          />
        );
      case 'msme':
        return (
          <img
            src={msmeOriginal}
            alt="MSME Government of India"
            className="app-card-logo-img"
            style={{ width: '48px', height: '34px', objectFit: 'contain' }}
          />
        );
      case 'kisan':
        return (
          <img
            src={kisanOriginal}
            alt="PM Kisan Samman Nidhi"
            className="app-card-logo-img"
            style={{ width: '42px', height: '42px', objectFit: 'contain' }}
          />
        );
      case 'standup':
        return <StandUpIndiaLogo width={58} height={24} />;
      case 'mudra':
        return <MudraLogo size={38} />;
      default:
        return (
          <img
            src={ashokStambhOriginal}
            alt="Emblem of India"
            className="app-card-logo-img"
            style={{ width: '38px', height: '48px', objectFit: 'contain' }}
          />
        );
    }
  };

  const handleActionClick = (app) => {
    if (app.actionType === 'start') {
      navigate(`/schemes/${app.id}`);
    } else {
      setSelectedApp(app);
    }
  };

  return (
    <PageContainer>
      <div className="applications-page-container">
        {/* ================================================================ */}
        {/* 1. TOP HEADER (Title + India Gate Inspirational Quote Banner)   */}
        {/* ================================================================ */}
        {/* ------------------------------------------------------------------
            1. Top Hero Banner (India Gate Fade + Government Editorial Slogan)
            ------------------------------------------------------------------ */}
        <section className="applications-hero-banner" aria-label="My Applications Header">
          <div className="applications-banner-left">
            <h1 className="applications-banner-title">My Applications</h1>
            <p className="applications-banner-subtitle">
              Track the status of your scheme applications and manage your submissions.
            </p>
          </div>

          <div className="applications-banner-right" aria-hidden="true">
            <div className="applications-banner-visual-wrapper">
              <img
                src={indiaGateHero}
                alt="India Gate Monument"
                className="applications-india-gate-img"
              />
              <div className="applications-banner-fade-overlay" />
            </div>

            <div className="applications-banner-editorial">
              <p className="applications-banner-quote">
                Opportunities<br />
                today for a<br />
                brighter tomorrow.
              </p>
              <img
                src={tricolorRibbon}
                alt=""
                className="applications-banner-tricolor"
              />
            </div>
          </div>
        </section>

        {/* ================================================================ */}
        {/* 2. SUMMARY KPI METRIC CARDS ROW (4 Cards)                       */}
        {/* ================================================================ */}
        <div className="applications-kpi-grid">
          {/* Card 1: Total Applications */}
          <div className="applications-kpi-card">
            <div className="kpi-icon-container green">
              <FileText size={22} />
            </div>
            <div className="kpi-content">
              <span className="kpi-number">5</span>
              <span className="kpi-title">Total Applications</span>
              <span className="kpi-subtext">Across all schemes</span>
            </div>
          </div>

          {/* Card 2: Under Review */}
          <div className="applications-kpi-card">
            <div className="kpi-icon-container blue">
              <Clock size={22} />
            </div>
            <div className="kpi-content">
              <span className="kpi-number">2</span>
              <span className="kpi-title">Under Review</span>
              <span className="kpi-subtext">Applications in process</span>
            </div>
          </div>

          {/* Card 3: Approved */}
          <div className="applications-kpi-card">
            <div className="kpi-icon-container approved">
              <CheckCircle2 size={22} />
            </div>
            <div className="kpi-content">
              <span className="kpi-number">1</span>
              <span className="kpi-title">Approved</span>
              <span className="kpi-subtext">Successfully approved</span>
            </div>
          </div>

          {/* Card 4: Action Required */}
          <div className="applications-kpi-card alert">
            <div className="kpi-icon-container amber">
              <AlertTriangle size={22} />
            </div>
            <div className="kpi-content">
              <span className="kpi-number">1</span>
              <span className="kpi-title">Action Required</span>
              <span className="kpi-subtext">Needs your attention</span>
            </div>
          </div>
        </div>

        {/* ================================================================ */}
        {/* 3. TWO-COLUMN MAIN CONTENT GRID                                  */}
        {/* ================================================================ */}
        <div className="applications-main-grid">
          {/* ============================================================== */}
          {/* LEFT COLUMN: Controls & Applications List                      */}
          {/* ============================================================== */}
          <div className="applications-left-column">
            {/* Filter and Search Controls Bar */}
            <div className="applications-filter-bar">
              {/* Search input */}
              <div className="app-search-input-wrap">
                <Search size={16} className="app-search-icon" />
                <input
                  type="text"
                  placeholder="Search applications by scheme name or application ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="app-search-input"
                />
              </div>

              {/* Status Select Filter */}
              <div className="app-filter-select-wrap">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="app-filter-select"
                  aria-label="Filter by application status"
                >
                  <option value="all">All Status</option>
                  <option value="under_review">Under Review</option>
                  <option value="action_required">Action Required</option>
                  <option value="approved">Approved</option>
                  <option value="draft">Draft</option>
                  <option value="not_started">Not Started</option>
                </select>
                <ChevronDown size={14} className="app-select-chevron" />
              </div>

              {/* Sort By Filter */}
              <div className="app-filter-select-wrap">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="app-filter-select"
                  aria-label="Sort applications"
                >
                  <option value="latest">Sort by Latest</option>
                  <option value="oldest">Sort by Oldest</option>
                  <option value="benefit">Sort by Benefit</option>
                </select>
                <ChevronDown size={14} className="app-select-chevron" />
              </div>
            </div>

            {/* Applications List */}
            <div className="applications-list-container">
              {filteredApplications.length === 0 ? (
                <div className="applications-empty-state">
                  <AlertCircle size={36} color="#98A2B3" />
                  <h3 className="empty-state-title">No applications found</h3>
                  <p className="empty-state-sub">
                    No submissions matched your search query "{searchQuery}" or status filter. Try clearing filters.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery('');
                      setStatusFilter('all');
                    }}
                    className="app-btn-view"
                    style={{ marginTop: '8px' }}
                  >
                    Reset Filters
                  </button>
                </div>
              ) : (
                filteredApplications.map((app) => {
                  const isActionRequired = app.status === 'action_required';
                  const isDraft = app.status === 'draft';
                  const isNotStarted = app.status === 'not_started';

                  return (
                    <div key={app.id} className="application-card-item">
                      {/* CARD TOP ROW */}
                      <div className="app-card-top-row">
                        {/* Section A: Scheme Identity */}
                        <div className="app-card-identity">
                          <div className="app-card-logo-box">
                            {renderSchemeLogo(app.logoType)}
                          </div>
                          <div className="app-card-titles">
                            <h3 className="app-scheme-name">{app.schemeTitle}</h3>
                            <div className="app-meta-line">
                              <span>Application ID: {app.applicationId}</span>
                              <span style={{ margin: '0 5px' }}>•</span>
                              <span>Applied on: {app.appliedDate}</span>
                            </div>
                          </div>
                        </div>

                        {/* Section B: Benefit Value */}
                        <div className="app-card-benefit">
                          <span className="app-benefit-val">{app.benefitAmount}</span>
                          <span className="app-benefit-label">{app.benefitSubtitle}</span>
                        </div>

                        {/* Section C: Status & Subtitle */}
                        <div className="app-card-status-block">
                          <span
                            className={`app-status-badge ${
                              app.status === 'under_review'
                                ? 'under-review'
                                : app.status === 'action_required'
                                ? 'action-required'
                                : app.status === 'approved'
                                ? 'approved'
                                : app.status === 'draft'
                                ? 'draft'
                                : 'not-started'
                            }`}
                          >
                            {app.statusBadge}
                          </span>
                          <span
                            className={`app-status-message ${
                              isActionRequired ? 'danger' : ''
                            }`}
                          >
                            {app.statusMessage}
                          </span>
                        </div>

                        {/* Section D: Action Button & Menu */}
                        <div className="app-card-actions">
                          {isActionRequired || isDraft ? (
                            <button
                              type="button"
                              onClick={() => handleActionClick(app)}
                              className="app-btn-continue"
                            >
                              {app.actionLabel}
                            </button>
                          ) : isNotStarted ? (
                            <button
                              type="button"
                              onClick={() => handleActionClick(app)}
                              className="app-btn-start"
                            >
                              {app.actionLabel}
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleActionClick(app)}
                              className="app-btn-view"
                            >
                              {app.actionLabel}
                            </button>
                          )}

                          {/* Kebab 3-dots Menu Button */}
                          <button
                            type="button"
                            onClick={() =>
                              setActiveMenuId(activeMenuId === app.id ? null : app.id)
                            }
                            className="app-menu-btn"
                            title="More options"
                            aria-label="More options"
                          >
                            <MoreVertical size={16} />
                          </button>

                          {/* Context Dropdown Menu */}
                          {activeMenuId === app.id && (
                            <div className="app-dropdown-menu" ref={menuRef}>
                              <button
                                type="button"
                                onClick={() => {
                                  setSelectedApp(app);
                                  setActiveMenuId(null);
                                }}
                                className="app-dropdown-item"
                              >
                                <Eye size={13} />
                                <span>View Details</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  showToast(`Downloaded receipt for ${app.applicationId}`);
                                  setActiveMenuId(null);
                                }}
                                className="app-dropdown-item"
                              >
                                <Download size={13} />
                                <span>Download Receipt</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  navigator.clipboard?.writeText(app.applicationId);
                                  showToast(`Copied Application ID: ${app.applicationId}`);
                                  setActiveMenuId(null);
                                }}
                                className="app-dropdown-item"
                              >
                                <FileCheck size={13} />
                                <span>Copy ID</span>
                              </button>
                              <Link
                                to={`/schemes/${app.id}`}
                                className="app-dropdown-item"
                                onClick={() => setActiveMenuId(null)}
                              >
                                <ArrowRight size={13} />
                                <span>Scheme Overview</span>
                              </Link>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* CARD BOTTOM ROW: 4-STAGE TRACKER STEPPER */}
                      <div className="app-card-stepper-track">
                        {app.steps.map((step, idx) => {
                          const isLast = idx === app.steps.length - 1;
                          const nextStep = app.steps[idx + 1];

                          // Determine connector line color
                          let connectorClass = '';
                          if (step.status === 'completed') {
                            if (nextStep && nextStep.status === 'error') {
                              connectorClass = 'red';
                            } else if (nextStep && (nextStep.status === 'completed' || nextStep.status === 'current-green')) {
                              connectorClass = 'green';
                            }
                          }

                          return (
                            <React.Fragment key={step.label}>
                              {/* Step Node */}
                              <div className="app-step-node-wrap">
                                <div
                                  className={`app-step-indicator ${
                                    step.status === 'completed'
                                      ? 'completed'
                                      : step.status === 'current-green'
                                      ? 'current-green'
                                      : step.status === 'error'
                                      ? 'error'
                                      : 'upcoming'
                                  }`}
                                >
                                  {step.status === 'completed' && <Check size={10} strokeWidth={3} />}
                                  {step.status === 'current-green' && (
                                    <div
                                      style={{
                                        width: '6px',
                                        height: '6px',
                                        borderRadius: '50%',
                                        backgroundColor: '#FFFFFF'
                                      }}
                                    />
                                  )}
                                  {step.status === 'error' && (
                                    <span style={{ fontSize: '9px', fontWeight: 'bold' }}>!</span>
                                  )}
                                  {step.status === 'upcoming' && (
                                    <div
                                      style={{
                                        width: '4px',
                                        height: '4px',
                                        borderRadius: '50%',
                                        backgroundColor: '#D0D5DD'
                                      }}
                                    />
                                  )}
                                </div>

                                <div className="app-step-text-group">
                                  <span
                                    className={`app-step-label ${
                                      step.status === 'error'
                                        ? 'error'
                                        : step.status === 'upcoming'
                                        ? 'muted'
                                        : ''
                                    }`}
                                  >
                                    {step.label}
                                  </span>
                                  {step.date && (
                                    <span
                                      className={`app-step-date ${
                                        step.status === 'error'
                                          ? 'error'
                                          : step.date === 'In Progress'
                                          ? 'highlight'
                                          : ''
                                      }`}
                                    >
                                      {step.date}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Connector line between steps */}
                              {!isLast && (
                                <div className={`app-step-connector-line ${connectorClass}`} />
                              )}
                            </React.Fragment>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* ============================================================== */}
          {/* RIGHT COLUMN: 3 Sidebar Cards                                  */}
          {/* ============================================================== */}
          <div className="applications-right-sidebar">
            {/* Card 1: Need Help? Card */}
            <div className="app-help-card">
              <div className="app-help-icon-wrap">
                <Headphones size={18} />
              </div>
              <h4 className="app-help-title">Need Help?</h4>
              <p className="app-help-desc">
                Have questions about your application status or required documents?
              </p>
              <button
                type="button"
                onClick={() => setShowHelpModal(true)}
                className="app-help-btn"
              >
                <span>Get Guidance</span>
                <ArrowRight size={13} />
              </button>
            </div>

            {/* Card 2: Important Information Card */}
            <div className="app-info-card">
              <div className="app-info-header">
                <Info size={16} color="#344054" />
                <h4 className="app-info-title">Important Information</h4>
              </div>

              <ul className="app-info-list">
                <li className="app-info-item">
                  <span className="info-dot amber" />
                  <span>Application processing time varies by scheme.</span>
                </li>
                <li className="app-info-item">
                  <span className="info-dot amber" />
                  <span>You will be notified at each stage of the process.</span>
                </li>
                <li className="app-info-item">
                  <span className="info-dot blue" />
                  <span>Keep your documents updated to avoid delays.</span>
                </li>
              </ul>

              <button
                type="button"
                onClick={() => setShowGuidelinesModal(true)}
                className="app-info-link"
                style={{ background: 'none', border: 'none', padding: 0 }}
              >
                <span>View Application Guidelines</span>
                <ArrowRight size={13} />
              </button>
            </div>

            {/* Card 3: Apply for More Schemes Card with Monument Watermark */}
            <div className="app-explore-card">
              <div className="app-explore-icon-wrap">
                <FileText size={18} />
              </div>
              <h4 className="app-explore-title">Apply for More Schemes</h4>
              <p className="app-explore-desc">
                Discover new opportunities based on your profile.
              </p>
              <Link to="/discover" className="app-explore-btn">
                <span>Explore Schemes</span>
                <ArrowRight size={14} />
              </Link>

              {/* Indian Monument Architectural Watermark */}
              <div className="app-explore-monument-watermark">
                <img
                  src={cardMonumentSketch}
                  alt="National Monument Sketch"
                />
              </div>
            </div>
          </div>
        </div>

        {/* ================================================================ */}
        {/* MODAL: APPLICATION DETAILS & STATUS TIMELINE                    */}
        {/* ================================================================ */}
        {selectedApp && (
          <div className="app-modal-overlay" onClick={() => setSelectedApp(null)}>
            <div className="app-modal-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="app-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {renderSchemeLogo(selectedApp.logoType)}
                  </div>
                  <div>
                    <h3 className="app-modal-title">{selectedApp.schemeTitle}</h3>
                    <p className="app-modal-subtitle">{selectedApp.schemeSubtitle}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedApp(null)}
                  className="app-modal-close-btn"
                  title="Close modal"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Meta Grid */}
              <div className="app-modal-meta-grid">
                <div className="app-modal-meta-item">
                  <span className="meta-field-label">Application Number</span>
                  <span className="meta-field-val">{selectedApp.applicationId}</span>
                </div>
                <div className="app-modal-meta-item">
                  <span className="meta-field-label">Current Status</span>
                  <span className="meta-field-val" style={{ color: selectedApp.status === 'approved' ? '#087443' : selectedApp.status === 'action_required' ? '#D92D20' : '#B54708' }}>
                    {selectedApp.statusBadge}
                  </span>
                </div>
                <div className="app-modal-meta-item">
                  <span className="meta-field-label">Submission Date</span>
                  <span className="meta-field-val">{selectedApp.appliedDate}</span>
                </div>
                <div className="app-modal-meta-item">
                  <span className="meta-field-label">Estimated Financial Grant</span>
                  <span className="meta-field-val">{selectedApp.benefitAmount}</span>
                </div>
              </div>

              {/* Status Note */}
              <div
                style={{
                  padding: '10px 14px',
                  backgroundColor: selectedApp.status === 'action_required' ? '#FEF3F2' : '#F0FDF4',
                  borderRadius: '8px',
                  border: `1px solid ${selectedApp.status === 'action_required' ? '#FECDCA' : '#BBF7D0'}`,
                  fontSize: '12.5px',
                  color: selectedApp.status === 'action_required' ? '#B42318' : '#087443',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                {selectedApp.status === 'action_required' ? (
                  <AlertTriangle size={16} />
                ) : (
                  <ShieldCheck size={16} />
                )}
                <span>{selectedApp.statusMessage}</span>
              </div>

              {/* Submitted Documents Checklist */}
              {selectedApp.submittedDocs && selectedApp.submittedDocs.length > 0 && (
                <div>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#10243A', marginBottom: '8px' }}>
                    Document Verification Checklist
                  </h4>
                  <div className="app-modal-docs-list">
                    {selectedApp.submittedDocs.map((doc, i) => (
                      <div key={i} className="app-modal-doc-row">
                        <div className="doc-name-group">
                          <FileText size={14} color="#667085" />
                          <span>{doc.name}</span>
                        </div>
                        <span className={`doc-status-pill ${doc.verified ? 'verified' : 'pending'}`}>
                          {doc.verified ? 'Verified ✓' : doc.reason || 'Pending Action'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Modal Footer */}
              <div className="app-modal-footer">
                <button
                  type="button"
                  onClick={() => {
                    showToast(`Official acknowledgement receipt downloaded for ${selectedApp.applicationId}`);
                  }}
                  className="modal-btn-cancel"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Download size={13} />
                  <span>Download Receipt (PDF)</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedApp(null);
                    navigate(`/schemes/${selectedApp.id}`);
                  }}
                  className="modal-btn-primary"
                >
                  View Scheme Guidelines
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* MODAL: GET GUIDANCE (Helpdesk)                                   */}
        {/* ================================================================ */}
        {showHelpModal && (
          <div className="app-modal-overlay" onClick={() => setShowHelpModal(false)}>
            <div className="app-modal-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="app-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: '#ECFDF3', color: '#12B76A', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Headphones size={18} />
                  </div>
                  <div>
                    <h3 className="app-modal-title">National Citizen Helpdesk</h3>
                    <p className="app-modal-subtitle">Direct Assistance for Scheme Submissions</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowHelpModal(false)}
                  className="app-modal-close-btn"
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px', color: '#475467' }}>
                <p>
                  Need assistance with document re-upload, verification status, or bank account Aadhaar seeding? Our grievance officers are available through official government channels:
                </p>

                <div style={{ backgroundColor: '#F8FAFC', padding: '12px 14px', borderRadius: '8px', border: '1px solid #EAECF0' }}>
                  <div style={{ fontWeight: 700, color: '#10243A' }}>National Toll-Free Helpline:</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#005B50', marginTop: '2px' }}>
                    1800 180 6763 / 1800 11 0001
                  </div>
                  <div style={{ fontSize: '11px', color: '#667085', marginTop: '2px' }}>
                    Operational: Mon–Sat, 9:00 AM – 6:00 PM IST (Excluding Gazetted Holidays)
                  </div>
                </div>

                <div style={{ backgroundColor: '#F8FAFC', padding: '12px 14px', borderRadius: '8px', border: '1px solid #EAECF0' }}>
                  <div style={{ fontWeight: 700, color: '#10243A' }}>Official Grievance Email:</div>
                  <div style={{ fontSize: '13.5px', fontWeight: 600, color: '#175CD3', marginTop: '2px' }}>
                    support-schemes@gov.in
                  </div>
                  <div style={{ fontSize: '11px', color: '#667085', marginTop: '2px' }}>
                    Guaranteed response within 48 business hours with ticket tracking.
                  </div>
                </div>
              </div>

              <div className="app-modal-footer">
                <button
                  type="button"
                  onClick={() => setShowHelpModal(false)}
                  className="modal-btn-primary"
                >
                  Close Guidance
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* MODAL: APPLICATION GUIDELINES                                    */}
        {/* ================================================================ */}
        {showGuidelinesModal && (
          <div className="app-modal-overlay" onClick={() => setShowGuidelinesModal(false)}>
            <div className="app-modal-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="app-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: '#EFF8FF', color: '#175CD3', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Info size={18} />
                  </div>
                  <div>
                    <h3 className="app-modal-title">Application Guidelines</h3>
                    <p className="app-modal-subtitle">Official Procedures & Verification Standards</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowGuidelinesModal(false)}
                  className="app-modal-close-btn"
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12.5px', color: '#475467', lineHeight: 1.5 }}>
                <div>
                  <strong style={{ color: '#10243A' }}>1. Document Verification Cycle:</strong>
                  <p style={{ margin: '2px 0 0 0' }}>
                    Applications are validated by the designated District Level Task Force Committee (DLTFC) and verified by participating nodal banks within 7 to 10 working days.
                  </p>
                </div>
                <div>
                  <strong style={{ color: '#10243A' }}>2. Action Required (Document Rectification):</strong>
                  <p style={{ margin: '2px 0 0 0' }}>
                    If a discrepancy is identified (e.g., blurred stamp or expired certificate), you have 15 calendar days to re-upload the corrected document before auto-cancellation.
                  </p>
                </div>
                <div>
                  <strong style={{ color: '#10243A' }}>3. Direct Benefit Transfer (DBT):</strong>
                  <p style={{ margin: '2px 0 0 0' }}>
                    Subsidies are credited directly into your Aadhaar-seeded NPCI mapper enabled bank account without any intermediaries.
                  </p>
                </div>
              </div>

              <div className="app-modal-footer">
                <button
                  type="button"
                  onClick={() => setShowGuidelinesModal(false)}
                  className="modal-btn-primary"
                >
                  Understood
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Global Toast Notification */}
        {toastMessage && (
          <div
            style={{
              position: 'fixed',
              bottom: '24px',
              right: '24px',
              backgroundColor: '#10243A',
              color: '#FFFFFF',
              padding: '10px 16px',
              borderRadius: '8px',
              fontSize: '12.5px',
              fontWeight: 500,
              boxShadow: '0 8px 24px rgba(16, 24, 40, 0.2)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              zIndex: 1000,
              animation: 'fadeInModal 0.2s ease-out'
            }}
          >
            <CheckCircle2 size={16} color="#12B76A" />
            <span>{toastMessage}</span>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
