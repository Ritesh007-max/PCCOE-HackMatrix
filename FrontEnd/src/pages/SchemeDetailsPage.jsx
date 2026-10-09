import React, { useState, useMemo, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  Building2,
  Landmark,
  Sliders,
  User,
  ShieldCheck,
  Globe,
  FileText,
  FileCheck,
  Download,
  Headphones,
  CheckCircle2,
  Clock,
  MapPin,
  Store,
  Banknote,
  Coins,
  Briefcase,
  Users,
  Info,
  ExternalLink,
  Calculator,
  Share2,
  Printer,
  Calendar,
  PhoneCall,
  Loader2,
  AlertTriangle,
  HelpCircle,
  AlertCircle
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import { fetchSchemeById, checkSchemeEligibility, fetchSchemeFaqs } from '../services/schemeService';
import { getStoredUser } from '../services/authService';
import { fetchUserDocuments } from '../services/documentService';
import SchemeLogo from '../components/schemes/SchemeLogo';
import { submitApplication } from '../services/applicationService';
import { navigateToSchemeDocuments } from '../utils/schemeNavigation';

// Assets
import ashokStambhVector from '../assets/ashok_stambh_vector.svg';
import ashokStambhGold from '../assets/ashok_stambh_gold.png';
import govtOfIndiaImg from '../assets/govt_of_india_hero.png';

// Canonical Scheme Details Sanitization & Helper Functions
export {
  formatCurrency,
  getSchemePortalDetails,
  parseRequiredDocuments,
  matchDocumentStatus,
  parseApplicationProcess,
  parseEligibilityCriteria,
  parseSchemeBenefits,
  isLoanSchemeWithCalculator,
  adaptSchemeDetails,
  getSchemeApplicationCycle,
  resolveBenefitClassification,
  getSchemeBenefitDisplay,
  validateOfficialUrl
} from '../utils/schemeDetailsHelpers.js';

import {
  formatCurrency,
  getSchemePortalDetails,
  parseRequiredDocuments,
  matchDocumentStatus,
  parseApplicationProcess,
  parseEligibilityCriteria,
  parseSchemeBenefits,
  isLoanSchemeWithCalculator,
  adaptSchemeDetails,
  getSchemeApplicationCycle,
  getEligibilityStateDetails,
  resolveBenefitClassification,
  getSchemeBenefitDisplay,
  BenefitCategories,
  validateOfficialUrl
} from '../utils/schemeDetailsHelpers.js';


export default function SchemeDetailsPage({ defaultTab, schemeIdProp }) {
  const { schemeId: routeSchemeId } = useParams();
  const schemeId = schemeIdProp || routeSchemeId;

  const [activeTab, setActiveTab] = useState(
    defaultTab || (window.location.pathname.includes('/benefits') ? 'benefits' : 'overview')
  );

  const [scheme, setScheme] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);

  // Dynamic eligibility state
  const [eligibilityResult, setEligibilityResult] = useState(null);
  const eligibilityState = useMemo(() => getEligibilityStateDetails(eligibilityResult), [eligibilityResult]);
  const [userDocs, setUserDocs] = useState([]);

  const storedUser = useMemo(() => getStoredUser(), []);

  useEffect(() => {
    fetchUserDocuments()
      .then((docs) => setUserDocs(Array.isArray(docs) ? docs : []))
      .catch(() => setUserDocs([]));
  }, []);
  const [isCheckingEligibility, setIsCheckingEligibility] = useState(false);
  const [eligibilityError, setEligibilityError] = useState(null);

  // Fetch scheme details on mount / ID change
  useEffect(() => {
    let isMounted = true;
    if (!schemeId) {
      setNotFound(true);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    setNotFound(false);

    fetchSchemeById(schemeId)
      .then((data) => {
        if (!isMounted) return;
        if (!data) {
          setNotFound(true);
        } else {
          setScheme(adaptSchemeDetails(data));
        }
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        if (err.status === 404 || err.message?.includes('not found')) {
          setNotFound(true);
        } else {
          setError(err.message || 'Failed to load scheme details');
        }
        setIsLoading(false);
      });

    return () => { isMounted = false; };
  }, [schemeId]);

  // Run eligibility check against backend
  const runEligibilityCheck = React.useCallback(async () => {
    setIsCheckingEligibility(true);
    setEligibilityError(null);
    try {
      const stored = getStoredUser();
      const profile = stored || {};
      const res = await checkSchemeEligibility(schemeId, profile);
      setEligibilityResult(res?.data || res);
    } catch (err) {
      setEligibilityError(err.message || 'Eligibility check failed');
    } finally {
      setIsCheckingEligibility(false);
    }
  }, [schemeId]);

  useEffect(() => {
    if (activeTab === 'eligibility' && !eligibilityResult && !isCheckingEligibility && scheme) {
      runEligibilityCheck();
    }
  }, [activeTab, scheme, eligibilityResult, isCheckingEligibility, runEligibilityCheck]);

  // FAQ state
  const [faqs, setFaqs] = useState([]);
  const [isFaqsLoading, setIsFaqsLoading] = useState(false);
  const [faqsError, setFaqsError] = useState(null);
  const [faqsLoaded, setFaqsLoaded] = useState(false);
  const [expandedFaqIndex, setExpandedFaqIndex] = useState(null);

  // Reset all scheme-scoped state when scheme changes to eliminate cross-scheme state leakage
  useEffect(() => {
    setEligibilityResult(null);
    setEligibilityError(null);
    setFaqs([]);
    setIsFaqsLoading(false);
    setFaqsError(null);
    setFaqsLoaded(false);
    setExpandedFaqIndex(null);
    setShowApplyModal(false);
  }, [schemeId]);

  // Fetch FAQs when scheme slug is available
  useEffect(() => {
    if (!scheme) return;
    const isUuid = scheme.id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(scheme.id);
    const validSlug = scheme.slug || (!isUuid ? scheme.id : null);

    const shouldFetch = (activeTab === 'faqs' || (scheme.faq_count && scheme.faq_count > 0));
    if (shouldFetch && validSlug && !faqsLoaded && !isFaqsLoading) {
      setIsFaqsLoading(true);
      setFaqsError(null);
      fetchSchemeFaqs(validSlug)
        .then((data) => {
          setFaqs(Array.isArray(data) ? data : []);
          setFaqsLoaded(true);
          setIsFaqsLoading(false);
        })
        .catch((err) => {
          console.warn('FAQ fetch notice:', err.message);
          setFaqsError('FAQs are currently unavailable.');
          setFaqsLoaded(true);
          setIsFaqsLoading(false);
        });
    } else if (activeTab === 'faqs' && !validSlug && !faqsLoaded) {
      setFaqsError('FAQs are currently unavailable.');
      setFaqsLoaded(true);
    }
  }, [scheme, activeTab, faqsLoaded, isFaqsLoading]);

  const [isSaved, setIsSaved] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('fin_bookmarks') || '[]');
      return saved.includes(schemeId);
    } catch (e) {
      return false;
    }
  });

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('fin_bookmarks') || '[]');
      const targetId = scheme?.id || schemeId;
      setIsSaved(saved.includes(targetId));
    } catch {
      setIsSaved(false);
    }
  }, [schemeId, scheme?.id]);

  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [downloadNotice, setDownloadNotice] = useState(null);
  const [copyToast, setCopyToast] = useState(false);
  const [expandedStep, setExpandedStep] = useState(null);

  const matchScore = scheme?.matchScore != null ? scheme.matchScore : null;
  const relevanceScore = scheme?.relevanceScore != null ? scheme.relevanceScore : null;
  const eligibilityStatus = scheme?.eligibilityStatus || 'UNKNOWN';
  const isEvaluated = matchScore != null && eligibilityStatus !== 'UNKNOWN';
  const displayScore = isEvaluated ? matchScore : (relevanceScore != null ? relevanceScore : 0);

  // Dynamic official government portal, ministry, scheme type, and helpline details
  const portalDetails = useMemo(() => getSchemePortalDetails(scheme), [scheme]);
  const guidelineDocumentUrl = useMemo(() => {
    if (!scheme) return null;
    // 1. Pre-verified guidelinesUrl or officialRulesPageUrl from portal details
    if (portalDetails?.guidelinesUrl) return portalDetails.guidelinesUrl;
    if (portalDetails?.officialRulesPageUrl) return portalDetails.officialRulesPageUrl;

    // 2. Direct explicit document/guideline/pdf URLs on scheme record (strictly verified)
    const explicitCandidates = [
      scheme.guidelines_url,
      scheme.guidelinesUrl,
      scheme.official_guidelines_url,
      scheme.document_url,
      scheme.pdf_url
    ].filter(Boolean);
    for (const c of explicitCandidates) {
      const val = validateOfficialUrl(c);
      if (val && !val.toLowerCase().includes('myscheme.gov.in')) {
        return val;
      }
    }

    // 3. References pointing explicitly to a verified PDF or guideline document
    const refs = Array.isArray(scheme.references) ? scheme.references : [];
    for (const ref of refs) {
      const u = typeof ref === 'string' ? ref : ref?.url;
      if (!u || typeof u !== 'string') continue;
      const lower = u.toLowerCase();
      if (lower.includes('myscheme.gov.in')) continue;
      if (lower.endsWith('.pdf') || lower.includes('/pdf/') || lower.includes('guideline') || lower.includes('guidance')) {
        const val = validateOfficialUrl(u);
        if (val) {
          return val;
        }
      }
    }

    // Return null when no genuine document exists (never fabricate or use portal homepages)
    return null;
  }, [scheme, portalDetails]);
  const requiredDocs = useMemo(() => parseRequiredDocuments(scheme), [scheme]);
  const applicationSteps = useMemo(() => parseApplicationProcess(scheme?.application_process), [scheme]);
  const eligibilityCriteriaList = useMemo(() => parseEligibilityCriteria(scheme), [scheme]);
  const canonicalBenefitsList = useMemo(() => parseSchemeBenefits(scheme), [scheme]);
  const hasLoanCalculator = useMemo(() => isLoanSchemeWithCalculator(scheme), [scheme]);
  const cycle = useMemo(() => getSchemeApplicationCycle(scheme), [scheme]);
  const benefitDisplay = useMemo(() => getSchemeBenefitDisplay(scheme), [scheme]);

  // =========================================================================
  // INTERACTIVE SUBSIDY CALCULATOR STATE (Strictly gated to verified loan schemes)
  // =========================================================================
  const calcParams = benefitDisplay?.calculatorParameters || null;
  const hasValidCalculator = hasLoanCalculator && Boolean(calcParams && (calcParams.subsidyGrid || calcParams.flatSubsidyPercent != null));

  const defaultCost = calcParams?.defaultProjectCost || (hasValidCalculator ? 1000000 : 500000);
  const [projectCost, setProjectCost] = useState(defaultCost);
  const [locationType, setLocationType] = useState('rural'); // 'rural' | 'urban'
  const [categoryType, setCategoryType] = useState('special'); // 'special' | 'general'

  // Reset project cost dynamically when scheme changes and provides scheme-specific default
  useEffect(() => {
    if (calcParams?.defaultProjectCost) {
      setProjectCost(calcParams.defaultProjectCost);
    } else if (hasValidCalculator) {
      setProjectCost(1000000);
    }
  }, [scheme?.id, hasValidCalculator, calcParams?.defaultProjectCost]);

  // Dynamic calculations:
  // Evaluates subsidy from explicit grid or flat rate, never hardcoded broad assumptions
  const subsidyPercent = useMemo(() => {
    if (!hasValidCalculator || !calcParams) return 0;
    if (calcParams.flatSubsidyPercent != null) {
      return calcParams.flatSubsidyPercent;
    }
    if (calcParams.subsidyGrid) {
      const grid = calcParams.subsidyGrid;
      const cat = grid[categoryType] || grid.general || {};
      return (locationType === 'rural' ? cat.rural : cat.urban) ?? 0;
    }
    return 0;
  }, [hasValidCalculator, calcParams, locationType, categoryType]);

  const ownPercent = useMemo(() => {
    if (!hasValidCalculator || !calcParams) return 0;
    if (calcParams.ownContributionGrid) {
      return (categoryType === 'special' ? calcParams.ownContributionGrid.special : calcParams.ownContributionGrid.general) ?? 10;
    }
    if (calcParams.subsidyGrid) {
      const grid = calcParams.subsidyGrid;
      const cat = grid[categoryType] || grid.general || {};
      if (cat.own != null) return cat.own;
    }
    if (calcParams.ownPercent != null) return calcParams.ownPercent;
    return categoryType === 'special' ? 5 : 10;
  }, [hasValidCalculator, calcParams, categoryType]);

  const loanPercent = useMemo(() => {
    if (!hasValidCalculator) return 0;
    return Math.max(0, 100 - subsidyPercent - ownPercent);
  }, [hasValidCalculator, subsidyPercent, ownPercent]);

  const subsidyAmount = hasValidCalculator ? Math.round((projectCost * subsidyPercent) / 100) : 0;
  const ownAmount = hasValidCalculator ? Math.round((projectCost * ownPercent) / 100) : 0;
  const loanAmount = hasValidCalculator ? Math.round((projectCost * loanPercent) / 100) : 0;

  // Monthly EMI estimation: from verified parameters or neutral default tenure
  const estimatedEmi = useMemo(() => {
    if (!hasValidCalculator) return 0;
    const principal = loanAmount;
    if (principal <= 0) return 0;
    const rate = calcParams?.interestRate || 0.09;
    const monthlyRate = rate / 12;
    const months = calcParams?.tenureMonths || 84;
    const emi = (principal * monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1);
    return Math.round(emi);
  }, [hasValidCalculator, calcParams, loanAmount]);

  // Compact circular gauge calculations (radius 11 for 26px gauge)
  const gaugeRadius = 11;
  const gaugeCircumference = 2 * Math.PI * gaugeRadius;
  const gaugeOffset = gaugeCircumference - (gaugeCircumference * displayScore) / 100;

  const navigate = useNavigate();

  const handleApplyClick = () => {
    setShowApplyModal(true);
  };

  const handleCheckDocumentsClick = () => {
    const canonicalId = scheme?.slug || scheme?.id || schemeId;
    navigateToSchemeDocuments(navigate, canonicalId);
  };

  const handleInitiateSubmit = async () => {
    if (!scheme) return;
    try {
      const payload = {
        schemeId: scheme.id,
        scheme_name: scheme.title
      };
      if (hasValidCalculator) {
        payload.projectCost = projectCost;
        payload.subsidyAmount = subsidyAmount;
        payload.subsidyPercent = subsidyPercent;
        payload.loanAmount = loanAmount;
        payload.ownContribution = ownAmount;
        payload.estimatedEmi = estimatedEmi;
      }
      await submitApplication(payload).catch((e) => console.warn('Application submit notice:', e));
    } catch (_) {}
  };

  const handleSaveToggle = () => {
    if (!scheme) return;
    setIsSaved((prev) => {
      const nextState = !prev;
      try {
        const saved = JSON.parse(localStorage.getItem('fin_bookmarks') || '[]');
        const updated = nextState
          ? [...new Set([...saved, scheme.id])]
          : saved.filter((id) => id !== scheme.id);
        localStorage.setItem('fin_bookmarks', JSON.stringify(updated));
      } catch (e) {}
      return nextState;
    });
  };

  const handleDownloadGuidelines = () => {
    // 1. Strictly re-validate the URL before attempting any action
    const verifiedUrl = validateOfficialUrl(guidelineDocumentUrl);
    if (!verifiedUrl) {
      setDownloadSuccess(false);
      setDownloadNotice('Official guidelines link is not available in the current policy record.');
      setTimeout(() => setDownloadNotice(null), 4000);
      return;
    }

    // 2. Perform safe opening in a new tab without fabricating downloads
    try {
      if (typeof window !== 'undefined' && typeof window.open === 'function') {
        const win = window.open(verifiedUrl, '_blank', 'noopener,noreferrer');
        // Handle pop-up blocker returning null in real browser environments
        if (win === null && typeof window.document !== 'undefined') {
          setDownloadSuccess(false);
          setDownloadNotice('Pop-up was blocked by browser. Please allow pop-ups to open the official guidelines.');
          setTimeout(() => setDownloadNotice(null), 4000);
          return;
        }
      }
      setDownloadNotice(null);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 3500);
    } catch (err) {
      setDownloadSuccess(false);
      setDownloadNotice('Unable to open official document link.');
      setTimeout(() => setDownloadNotice(null), 4000);
    }
  };

  const handleShareClick = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopyToast(true);
      setTimeout(() => setCopyToast(false), 3000);
    }
  };

  const handlePrintClick = () => {
    window.print();
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  if (isLoading) {
    return (
      <PageContainer>
        <div style={{ padding: '80px 20px', textAlign: 'center' }}>
          <Loader2 size={36} className="spin" style={{ color: '#073B30', margin: '0 auto 16px' }} />
          <h2 style={{ fontSize: '18px', color: '#101828' }}>Loading Scheme Details</h2>
          <p style={{ color: '#667085', fontSize: '14px' }}>Retrieving authoritative policy data from Government registry...</p>
        </div>
      </PageContainer>
    );
  }

  if (notFound || !scheme) {
    return (
      <PageContainer>
        <div style={{ padding: '80px 20px', textAlign: 'center' }}>
          <AlertTriangle size={36} style={{ color: '#D92D20', margin: '0 auto 16px' }} />
          <h2 style={{ fontSize: '20px', color: '#B42318' }}>Scheme Not Found</h2>
          <p style={{ color: '#475467', margin: '8px 0 20px' }}>The requested scheme '{schemeId}' could not be found in the official registry.</p>
          <Link to="/discover" className="btn btn-primary" style={{ display: 'inline-flex', padding: '10px 20px' }}>
            Explore Available Schemes
          </Link>
        </div>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <div style={{ padding: '80px 20px', textAlign: 'center' }}>
          <AlertTriangle size={36} style={{ color: '#D92D20', margin: '0 auto 16px' }} />
          <h2 style={{ fontSize: '20px', color: '#B42318' }}>Unable to Load Scheme Details</h2>
          <p style={{ color: '#475467', margin: '8px 0 20px' }}>{error}</p>
          <button type="button" onClick={() => window.location.reload()} className="btn btn-primary" style={{ padding: '10px 20px' }}>
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="scheme-details-container">
        {/* 1. Sleek Compact Back Link */}
        <div>
          <Link to="/discover" className="scheme-back-link">
            <ArrowLeft size={14} />
            <span>Back to Schemes</span>
          </Link>
        </div>

        {/* 2. Top Scheme Header Area - Fully Balanced (No Empty Space on Right) */}
        <div className="scheme-main-header">
          <div className="scheme-header-identity">
            {/* National Emblem or Scheme Logo */}
            <div className="scheme-emblem-container">
              <SchemeLogo scheme={scheme} size={44} />
            </div>

            {/* Title, Subtitle, Category Tags */}
            <div className="scheme-header-text">
              <h1 className="scheme-title-main">{scheme.title}</h1>
              <h2 className="scheme-subtitle-main">{scheme.subtitle}</h2>
              <div className="scheme-tags-list">
                {scheme.tags && scheme.tags.length > 0 ? (
                  scheme.tags.map((tag) => (
                    <span key={tag} className="scheme-tag-item">
                      {tag}
                    </span>
                  ))
                ) : (
                  <>
                    <span className="scheme-tag-item">{scheme.state || 'All India'}</span>
                    <span className="scheme-tag-item">{scheme.level ? `${scheme.level} Scheme` : (scheme.state && scheme.state !== 'All India' ? 'State Scheme' : 'Central Scheme')}</span>
                    {scheme.type && <span className="scheme-tag-item">{scheme.type}</span>}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Header Cluster: Status, DBT, Match Score, Share & Print */}
          <div className="scheme-header-right-cluster">
            {/* Dynamic Application Cycle Status Pill */}
            <div
              className={`scheme-status-pill ${cycle.badgeClass}`}
              title={cycle.cycleDescription}
            >
              {cycle.isLive && <span className="status-live-dot" />}
              {cycle.status === 'CLOSED' && <span className="status-closed-dot" />}
              {cycle.status === 'UPCOMING' && <span className="status-upcoming-dot" />}
              {cycle.status === 'NOT_SPECIFIED' && <span className="status-unspecified-dot" />}
              <span>{cycle.badgeText}</span>
            </div>

            {/* DBT Direct Benefit Transfer Badge - Only render if canonical dbt_scheme is explicitly true */}
            {scheme.dbt_scheme === true && (
              <div className="scheme-dbt-pill" title="Subsidy / Benefit released directly to Aadhaar-linked Bank Account">
                <ShieldCheck size={14} />
                <span>Direct Benefit Transfer</span>
              </div>
            )}

            {/* Compact Match Score Gauge Card */}
            <div
              className="scheme-match-gauge-box"
              title={
                isEvaluated
                  ? `Your profile has an evaluated ${matchScore}% match for this scheme`
                  : (relevanceScore != null && relevanceScore > 0
                    ? `Search relevance: ${relevanceScore}% | Eligibility: Unverified`
                    : 'Search ranking not computed for direct access | Statutory eligibility: UNKNOWN')
              }
            >
              <div className="scheme-gauge-svg-wrap">
                <svg className="scheme-gauge-svg" viewBox="0 0 26 26">
                  <circle cx="13" cy="13" r={gaugeRadius} fill="none" stroke="#E5E7EB" strokeWidth="2.8" />
                  <circle
                    cx="13"
                    cy="13"
                    r={gaugeRadius}
                    fill="none"
                    stroke={isEvaluated ? '#12B76A' : (relevanceScore != null && relevanceScore > 0 ? '#175CD3' : '#94A3B8')}
                    strokeWidth="2.8"
                    strokeDasharray={gaugeCircumference}
                    strokeDashoffset={isEvaluated || (relevanceScore != null && relevanceScore > 0) ? gaugeOffset : gaugeCircumference}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="scheme-gauge-center">
                  <span style={{ fontSize: isEvaluated || (relevanceScore != null && relevanceScore > 0) ? '8.5px' : '7.5px' }}>
                    {isEvaluated ? `${matchScore}%` : (relevanceScore != null && relevanceScore > 0 ? `${relevanceScore}%` : '—')}
                  </span>
                </div>
              </div>
              <div className="scheme-gauge-meta">
                <span className="scheme-gauge-match-text">
                  {isEvaluated ? 'Eligibility' : 'Relevance'}
                </span>
                <span className="scheme-gauge-subtext">
                  {isEvaluated
                    ? (matchScore >= 80 ? 'Highly eligible' : 'Partial match')
                    : (relevanceScore != null && relevanceScore > 0 ? 'Search ranking' : 'Not ranked / Direct access')}
                </span>
              </div>
            </div>

            {/* Quick Action Buttons */}
            <button
              type="button"
              onClick={handleShareClick}
              className="scheme-header-action-btn"
              title="Share Scheme Link"
              aria-label="Share Scheme Link"
            >
              <Share2 size={14} />
            </button>

            <button
              type="button"
              onClick={handlePrintClick}
              className="scheme-header-action-btn"
              title="Print Scheme Summary"
              aria-label="Print Scheme Summary"
            >
              <Printer size={14} />
            </button>
          </div>
        </div>

        {/* Share Feedback Toast */}
        {copyToast && (
          <div
            style={{
              padding: '6px 14px',
              backgroundColor: '#ECFDF3',
              border: '1px solid #A6F4C5',
              borderRadius: '8px',
              color: '#087443',
              fontSize: '12px',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              width: 'fit-content'
            }}
          >
            <CheckCircle2 size={14} />
            <span>Scheme link copied to clipboard!</span>
          </div>
        )}

        {/* 3. Horizontal Navigation Tabs */}
        <div className="scheme-tabs-nav" role="tablist">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'eligibility', label: 'Eligibility' },
            { id: 'benefits', label: 'Benefits' },
            { id: 'documents', label: 'Documents' },
            { id: 'how-to-apply', label: 'How to Apply' },
            { id: 'source-rules', label: 'Source & Rules' },
            { id: 'faqs', label: faqs.length > 0 ? `FAQs (${faqs.length})` : 'FAQs' }
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`scheme-tab-button ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 4. Two-Column Main Content Layout */}
        <div className="scheme-content-grid">
          {/* ============================================================== */}
          {/* LEFT COLUMN: Tab-dependent Content */}
          {/* ============================================================== */}
          <div className="scheme-left-column">
            {/* TAB: OVERVIEW */}
            {activeTab === 'overview' && (
              <>
                {/* Hero Banner Card with Dynamic Scheme Title & Authority */}
                <div className="scheme-hero-card">
                  <div className="scheme-hero-content">
                    <div>
                      <div className="scheme-hero-eyebrow">
                        {portalDetails.ministry}
                      </div>
                      <h3 className="scheme-hero-headline" style={{ fontSize: '24px', lineHeight: 1.3 }}>
                        {scheme.title}
                      </h3>
                      <p className="scheme-hero-desc">
                        {scheme.brief_description || scheme.description || 'Official Government welfare initiative.'}
                      </p>
                    </div>

                    {scheme.slogan && (
                      <div className="scheme-hero-quote-box">
                        <span className="scheme-hero-quote-mark">“</span>
                        <div className="scheme-hero-quote-text-wrap">
                          <span className="scheme-hero-quote-phrase">
                            "{scheme.slogan}"
                          </span>
                          <span className="scheme-hero-quote-author">
                            — {portalDetails.ministry}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Official Insignia Graphic */}
                  <div className="scheme-hero-media">
                    <img
                      src={govtOfIndiaImg}
                      alt="Government Welfare Programme"
                      className="scheme-hero-gov-img"
                    />
                    <div className="scheme-hero-stamp-badge">
                      <ShieldCheck size={12} />
                      <span>{scheme.state ? `${scheme.state} State Initiative` : 'National Welfare Programme'}</span>
                    </div>
                  </div>
                </div>

                {/* Canonical Scheme Overview Details */}
                <div className="scheme-section-block">
                  <h3 className="scheme-section-heading">Scheme Summary & Scope</h3>
                  <p style={{ fontSize: '13.5px', color: '#344054', lineHeight: 1.65, margin: '8px 0 16px 0' }}>
                    {scheme.detailed_description || scheme.description || scheme.brief_description}
                  </p>

                  <div className="scheme-highlights-grid">
                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round blue">
                        <MapPin size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value">{scheme.state || 'All India'}</span>
                        <span className="highlight-label">Jurisdiction ({scheme.level || 'State/Central'})</span>
                      </div>
                    </div>

                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round teal">
                        <Users size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value" style={{ fontSize: '13.5px' }}>{scheme.beneficiary_type || 'Individuals'}</span>
                        <span className="highlight-label">Target Beneficiary</span>
                      </div>
                    </div>

                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round purple">
                        <Building2 size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value" style={{ fontSize: '13.5px' }}>{scheme.category || scheme.categories?.[0] || 'Welfare'}</span>
                        <span className="highlight-label">Primary Sector</span>
                      </div>
                    </div>

                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round amber">
                        <Coins size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value" style={{ fontSize: '13.5px' }}>{benefitDisplay.classification}</span>
                        <span className="highlight-label">Benefit Nature</span>
                      </div>
                    </div>

                    <div className="scheme-highlight-box">
                      <div className={`highlight-icon-round ${cycle.status === 'CLOSED' ? 'red' : cycle.status === 'UPCOMING' ? 'blue' : cycle.isLive ? 'teal' : 'gray'}`}>
                        <Calendar size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value" style={{ fontSize: '13px' }}>{cycle.detailedStatus}</span>
                        <span className="highlight-label">Application Status</span>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* TAB: ELIGIBILITY */}
            {activeTab === 'eligibility' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Statutory Eligibility: {scheme.title}</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    {eligibilityState ? eligibilityState.tabSubtitle : 'Authoritative eligibility evaluation determined via Government policy rules engine.'}
                  </p>
                </div>

                {/* Live Interactive Eligibility Status */}
                {isCheckingEligibility ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px', gap: '10px', background: '#F8F9FA', borderRadius: '10px' }}>
                    <Loader2 size={24} className="spin" style={{ color: '#073B30' }} />
                    <span style={{ fontSize: '14px', color: '#475467' }}>Evaluating statutory criteria against your profile...</span>
                  </div>
                ) : eligibilityError ? (
                  <div style={{ background: '#FEF3F2', border: '1px solid #FECDCA', borderRadius: '8px', padding: '16px', color: '#B42318' }}>
                    <div style={{ fontWeight: 600, marginBottom: '6px' }}>Eligibility Check Notice:</div>
                    <div style={{ fontSize: '13px' }}>{eligibilityError}</div>
                    <button
                      type="button"
                      onClick={runEligibilityCheck}
                      className="btn-apply-filters"
                      style={{ width: 'auto', padding: '6px 16px', marginTop: '10px' }}
                    >
                      Retry Evaluation
                    </button>
                  </div>
                ) : eligibilityResult && eligibilityState ? (
                  <div>
                    {/* Verdict Banner */}
                    <div
                      style={{
                        padding: '16px 20px',
                        borderRadius: '10px',
                        border: '1px solid',
                        marginBottom: '16px',
                        borderColor:
                          eligibilityState.badgeClass === 'green'
                            ? '#A6F4C5'
                            : eligibilityState.badgeClass === 'red'
                            ? '#FECDCA'
                            : '#FEDF89',
                        backgroundColor:
                          eligibilityState.badgeClass === 'green'
                            ? '#ECFDF3'
                            : eligibilityState.badgeClass === 'red'
                            ? '#FEF3F2'
                            : '#FEF0C7',
                        color:
                          eligibilityState.badgeClass === 'green'
                            ? '#087443'
                            : eligibilityState.badgeClass === 'red'
                            ? '#B42318'
                            : '#B54708'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <span style={{ fontSize: '15px', fontWeight: 800 }}>
                          VERDICT: {eligibilityState.verdict}
                        </span>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            letterSpacing: '0.4px',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: 'rgba(0,0,0,0.06)'
                          }}
                        >
                          Source: {eligibilityResult.source === 'intelligence' ? 'Intelligence Gateway' : (eligibilityResult.source === 'local_fallback' ? (eligibilityResult.degraded ? 'Offline Fallback Engine' : 'Local Rules Engine') : (eligibilityResult.source || 'Intelligence Gateway'))}
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5 }}>
                        {eligibilityState.bannerReason}
                      </p>
                    </div>

                    {/* Notice when no machine-evaluable rules were executed */}
                    {!eligibilityState.hasExecutedRules && eligibilityState.notice && (
                      <div style={{ padding: '14px 18px', background: '#F8F9FA', border: '1px solid #EAECF0', borderRadius: '10px', marginBottom: '16px' }}>
                        <p style={{ margin: 0, fontSize: '13px', color: '#475467', lineHeight: 1.5 }}>
                          {eligibilityState.notice}
                        </p>
                      </div>
                    )}

                    {/* Evaluated Rules Breakdown */}
                    {eligibilityState.hasExecutedRules && Array.isArray(eligibilityResult.rules) && eligibilityResult.rules.length > 0 && (
                      <div style={{ marginBottom: '20px' }}>
                        <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#1D2939', marginBottom: '10px' }}>
                          Evaluated Statutory Rules ({eligibilityResult.rules.length})
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {eligibilityResult.rules.map((rule, idx) => {
                            const isPass = rule.status === 'pass' || rule.rawStatus === 'PASS';
                            const isFail = rule.status === 'fail' || rule.rawStatus === 'FAIL';
                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: '12px 16px',
                                  borderRadius: '8px',
                                  background: '#F8F9FA',
                                  border: '1px solid #EAECF0',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'flex-start'
                                }}
                              >
                                <div style={{ flex: 1, paddingRight: '12px' }}>
                                  <span style={{ fontWeight: 700, fontSize: '13px', color: '#101828' }}>
                                    {rule.id || `Rule ${idx + 1}`}:{' '}
                                  </span>
                                  <span style={{ fontSize: '13px', color: '#475467' }}>
                                    {rule.reason || rule.description}
                                  </span>
                                </div>
                                <span
                                  style={{
                                    padding: '3px 9px',
                                    borderRadius: '5px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    textTransform: 'uppercase',
                                    flexShrink: 0,
                                    backgroundColor: isPass ? '#ECFDF3' : isFail ? '#FEF3F2' : '#FEF0C7',
                                    color: isPass ? '#087443' : isFail ? '#B42318' : '#B54708'
                                  }}
                                >
                                  {rule.rawStatus || (isPass ? 'PASS' : isFail ? 'FAIL' : 'REVIEW')}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Missing Profile Information Requirement */}
                    {eligibilityState.showMissingProfileBox && eligibilityState.missingFieldLabels.length > 0 && (
                      <div style={{ padding: '14px 18px', background: '#FFF4ED', border: '1px solid #FFD6AE', borderRadius: '10px', marginBottom: '16px' }}>
                        <strong style={{ color: '#B93815', fontSize: '13.5px' }}>Missing Profile Information:</strong>
                        <div style={{ fontSize: '12.5px', color: '#7E2A0C', marginTop: '4px', lineHeight: 1.5 }}>
                          The statutory evaluator requires the following applicant data to resolve uncertainty: <strong>{eligibilityState.missingFieldLabels.join(', ')}</strong>.
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ padding: '24px', textAlign: 'center', background: '#F8F9FA', borderRadius: '10px' }}>
                    <p style={{ color: '#475467', marginBottom: '14px', fontSize: '14px' }}>
                      Evaluate your profile against this scheme's statutory eligibility criteria.
                    </p>
                    <button
                      type="button"
                      onClick={runEligibilityCheck}
                      className="btn-apply-filters"
                      style={{ width: 'auto', padding: '9px 24px', margin: '0 auto' }}
                    >
                      Check Eligibility Now
                    </button>
                  </div>
                )}

                {/* Descriptive Policy Eligibility Requirements from Scheme Database */}
                {(eligibilityCriteriaList.length > 0 || scheme.eligibilitySummary) && (
                  <div style={{ marginTop: '16px', padding: '16px 20px', backgroundColor: '#F0F9FF', borderRadius: '10px', border: '1px solid #B9E6FE' }}>
                    <h4 style={{ color: '#026AA2', fontSize: '13.5px', fontWeight: 700, margin: '0 0 10px 0' }}>
                      Descriptive Policy Eligibility Requirements
                    </h4>
                    {eligibilityCriteriaList.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {eligibilityCriteriaList.map((crit, idx) => (
                          <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12.5px', color: '#344054', lineHeight: 1.5 }}>
                            <span style={{ color: '#026AA2', fontWeight: 700 }}>•</span>
                            <span>{crit}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '12.5px', color: '#344054', margin: 0, lineHeight: 1.5 }}>
                        {scheme.eligibilitySummary}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB: BENEFITS */}
            {activeTab === 'benefits' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Financial Benefits: {scheme.title}</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    {scheme.benefitSummary || 'Detailed overview of financial benefits and subsidies provided under this scheme.'}
                  </p>
                </div>

                {/* Gated Financial Calculator */}
                {hasValidCalculator ? (
                  <div className="scheme-calculator-card">
                    <div className="calc-header-row">
                      <div className="calc-title-lockup">
                        <div className="calc-title-icon">
                          <Calculator size={15} />
                        </div>
                        <h4 className="calc-title-text">
                          Credit-Linked Subsidy & Loan Estimator
                        </h4>
                      </div>
                      <span className="calc-badge-live">Live Reactive Calculator</span>
                    </div>

                    <div style={{ padding: '8px 12px', background: '#F8F9FA', borderRadius: '6px', fontSize: '12px', color: '#475467', marginBottom: '14px', border: '1px solid #EAECF0' }}>
                      <strong>Note:</strong> Selected investment amount is a user-selected hypothetical assumption, not an official scheme entitlement.
                    </div>

                    {/* Calculator Controls */}
                    <div className="calc-controls-grid">
                      <div className="calc-control-group">
                        <div className="calc-control-label">
                          <span>Proposed Project Investment (Hypothetical Assumption):</span>
                          <span className="calc-cost-display">{formatCurrency(projectCost)}</span>
                        </div>

                        <input
                          type="range"
                          min={calcParams?.minProjectCost || 50000}
                          max={calcParams?.maxProjectCost || 5000000}
                          step="25000"
                          value={projectCost}
                          onChange={(e) => setProjectCost(Number(e.target.value))}
                          className="calc-range-slider"
                        />

                        <div className="calc-presets-chips">
                          {(calcParams?.presets || [200000, 500000, 1000000, 2500000, 5000000]).map((amt) => (
                            <button
                              key={amt}
                              type="button"
                              onClick={() => setProjectCost(amt)}
                              className={`calc-chip-btn ${projectCost === amt ? 'active' : ''}`}
                            >
                              ₹{(amt / 100000).toFixed(amt % 100000 === 0 ? 0 : 1)} Lakh
                            </button>
                          ))}
                        </div>
                      </div>

                      {calcParams?.isGridModel !== false ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <div className="calc-control-group">
                            <label className="calc-control-label">Enterprise Location:</label>
                            <div className="calc-segmented-toggles">
                              <button
                                type="button"
                                onClick={() => setLocationType('rural')}
                                className={`calc-toggle-btn ${locationType === 'rural' ? 'active' : ''}`}
                              >
                                Rural
                              </button>
                              <button
                                type="button"
                                onClick={() => setLocationType('urban')}
                                className={`calc-toggle-btn ${locationType === 'urban' ? 'active' : ''}`}
                              >
                                Urban
                              </button>
                            </div>
                          </div>

                          <div className="calc-control-group">
                            <label className="calc-control-label">Applicant Category:</label>
                            <div className="calc-segmented-toggles">
                              <button
                                type="button"
                                onClick={() => setCategoryType('special')}
                                className={`calc-toggle-btn ${categoryType === 'special' ? 'active' : ''}`}
                              >
                                Special (SC/ST/OBC/Women)
                              </button>
                              <button
                                type="button"
                                onClick={() => setCategoryType('general')}
                                className={`calc-toggle-btn ${categoryType === 'general' ? 'active' : ''}`}
                              >
                                General
                              </button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <div className="calc-control-group">
                            <label className="calc-control-label">Subsidy Model:</label>
                            <div style={{ padding: '10px 14px', background: '#ECFDF3', borderRadius: '6px', fontSize: '13px', color: '#027A48', fontWeight: 600, border: '1px solid #A6F4C5' }}>
                              Verified Policy Subsidy: {subsidyPercent}%
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Progress Bar & Calculated Cards */}
                    <div className="calc-segment-bar-wrap">
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: '#667085' }}>
                        <span style={{ color: '#087443', fontWeight: 600 }}>● Govt Subsidy ({subsidyPercent}%)</span>
                        <span style={{ color: '#175CD3', fontWeight: 600 }}>● Bank Term Loan ({loanPercent}%)</span>
                        <span style={{ color: '#D97706', fontWeight: 600 }}>● Own Capital ({ownPercent}%)</span>
                      </div>

                      <div className="calc-multi-bar">
                        <div className="bar-segment-subsidy" style={{ width: `${subsidyPercent}%` }} />
                        <div className="bar-segment-loan" style={{ width: `${loanPercent}%` }} />
                        <div className="bar-segment-own" style={{ width: `${ownPercent}%` }} />
                      </div>
                    </div>

                    <div className="calc-metrics-row">
                      <div className="calc-metric-card highlight">
                        <span className="calc-metric-label">
                          <Coins size={12} color="#12B76A" />
                          <span>Govt Subsidy ({subsidyPercent}%)</span>
                        </span>
                        <span className="calc-metric-value">{formatCurrency(subsidyAmount)}</span>
                        <span className="calc-metric-sub">Capital subsidy</span>
                      </div>

                      <div className="calc-metric-card">
                        <span className="calc-metric-label">
                          <Landmark size={12} color="#175CD3" />
                          <span>Bank Loan ({loanPercent}%)</span>
                        </span>
                        <span className="calc-metric-value">{formatCurrency(loanAmount)}</span>
                        <span className="calc-metric-sub">Commercial loan</span>
                      </div>

                      <div className="calc-metric-card">
                        <span className="calc-metric-label">
                          <User size={12} color="#D97706" />
                          <span>Your Funds ({ownPercent}%)</span>
                        </span>
                        <span className="calc-metric-value">{formatCurrency(ownAmount)}</span>
                        <span className="calc-metric-sub">Promoter contribution</span>
                      </div>

                      <div className="calc-metric-card">
                        <span className="calc-metric-label">
                          <Clock size={12} color="#667085" />
                          <span>Est. Monthly EMI</span>
                        </span>
                        <span className="calc-metric-value">{formatCurrency(estimatedEmi)}</span>
                        <span className="calc-metric-sub">
                          {calcParams?.interestRate ? `at ${(calcParams.interestRate * 100).toFixed(0)}% for ${(calcParams.tenureMonths || 84) / 12} years` : 'at 9% for 7 years'}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '24px 20px', backgroundColor: '#F8F9FA', borderRadius: '10px', border: '1px solid #EAECF0', textAlign: 'center', marginBottom: '20px' }}>
                    <Calculator size={26} style={{ color: '#98A2B3', margin: '0 auto 10px' }} />
                    <h4 style={{ fontSize: '14.5px', fontWeight: 600, color: '#344054', margin: '0 0 6px 0' }}>
                      Calculator not applicable
                    </h4>
                    <p style={{ fontSize: '13px', color: '#667085', maxWidth: '560px', margin: '0 auto', lineHeight: 1.5 }}>
                      {benefitDisplay?.category === BenefitCategories.CREDIT_LINKED_SUBSIDY
                        ? 'Verified calculation parameters are not specified for this credit-linked scheme. Official subsidy and loan terms are determined under departmental guidelines.'
                        : 'A credit-linked project investment calculator is not applicable to this scheme. Benefits are granted as direct support, concessions, or waivers as specified in the official policy clauses below.'}
                    </p>
                  </div>
                )}

                {/* Canonical Benefits Entitlement Details */}
                <div className="scheme-section-block">
                  <h3 className="scheme-section-heading">Policy Benefit Terms & Conditions</h3>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' }}>
                    <div style={{ padding: '16px 20px', backgroundColor: '#F0FDF4', borderRadius: '10px', border: '1px solid #BBF7D0' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#15803D', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                        Entitlement Value
                      </span>
                      <div style={{ fontSize: '16px', fontWeight: 750, color: '#073B30', marginTop: '6px', lineHeight: 1.5 }}>
                        {benefitDisplay.entitlementText}
                      </div>
                    </div>

                    {/* Multi-Component Authoritative Breakdown */}
                    {benefitDisplay.benefitComponents && benefitDisplay.benefitComponents.length > 0 ? (
                      <div style={{ padding: '18px 20px', backgroundColor: '#FFFFFF', borderRadius: '10px', border: '1px solid #E4E7EC' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                          <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', margin: 0 }}>
                            Authoritative Benefit Components
                          </h4>
                          <span style={{ fontSize: '12px', color: '#667085', fontWeight: 500 }}>
                            {benefitDisplay.benefitComponents.length} component{benefitDisplay.benefitComponents.length > 1 ? 's' : ''}
                          </span>
                        </div>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          {benefitDisplay.benefitComponents.map((comp, idx) => (
                            <div
                              key={idx}
                              style={{
                                padding: '12px 14px',
                                backgroundColor: '#F9FAFB',
                                borderRadius: '8px',
                                border: '1px solid #EAECF0',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '6px'
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.3px',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    backgroundColor: comp.isCeiling ? '#FEF3F2' : '#EFF8FF',
                                    color: comp.isCeiling ? '#B42318' : '#175CD3',
                                    border: `1px solid ${comp.isCeiling ? '#FECDCA' : '#B2DDFF'}`
                                  }}>
                                    {comp.benefitType}
                                  </span>
                                  {comp.isCeiling && (
                                    <span style={{
                                      fontSize: '11px',
                                      fontWeight: 600,
                                      padding: '2px 6px',
                                      borderRadius: '4px',
                                      backgroundColor: '#FFF4ED',
                                      color: '#B93815',
                                      border: '1px solid #FECDCA'
                                    }}>
                                      Max Ceiling
                                    </span>
                                  )}
                                </div>
                                
                                {comp.frequency && (
                                  <span style={{ fontSize: '12px', color: '#475467', fontWeight: 500 }}>
                                    Frequency: <strong style={{ color: '#101828' }}>{comp.frequency}</strong>
                                  </span>
                                )}
                              </div>

                              <div style={{ fontSize: '15px', fontWeight: 700, color: '#101828' }}>
                                {comp.amountDisplay}
                              </div>

                              {comp.applicableBeneficiary && (
                                <div style={{ fontSize: '12px', color: '#475467' }}>
                                  <strong>Beneficiary:</strong> {comp.applicableBeneficiary}
                                </div>
                              )}

                              {comp.duration && (
                                <div style={{ fontSize: '12px', color: '#475467' }}>
                                  <strong>Duration:</strong> {comp.duration}
                                </div>
                              )}

                              {comp.description && comp.description !== comp.amountDisplay && (
                                <div style={{ fontSize: '12px', color: '#667085', lineHeight: 1.4 }}>
                                  {comp.description}
                                </div>
                              )}

                              {comp.conditions && comp.conditions.length > 0 && (
                                <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                  {comp.conditions.map((c, cIdx) => (
                                    <div key={cIdx} style={{ fontSize: '12px', color: '#7A2E0E', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <span style={{ color: '#D92D20', fontWeight: 700 }}>•</span>
                                      <span>{c}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      canonicalBenefitsList.length > 0 && (
                        <div style={{ padding: '18px 20px', backgroundColor: '#FFFFFF', borderRadius: '10px', border: '1px solid #E4E7EC' }}>
                          <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', marginBottom: '10px' }}>
                            Authoritative Benefit Breakdown
                          </h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {canonicalBenefitsList.map((clause, idx) => (
                              <div
                                key={idx}
                                style={{
                                  display: 'flex',
                                  alignItems: 'flex-start',
                                  gap: '8px',
                                  fontSize: '13px',
                                  color: '#344054',
                                  padding: '2px 0'
                                }}
                              >
                                <span style={{ color: '#087443', fontWeight: 700 }}>•</span>
                                <span style={{ flex: 1, lineHeight: 1.5 }}>{clause}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    )}

                    {/* Dedicated Policy Conditions & Compliance Requirements Section */}
                    {benefitDisplay.conditions && benefitDisplay.conditions.length > 0 && (
                      <div style={{ padding: '18px 20px', backgroundColor: '#FFFAEB', borderRadius: '10px', border: '1px solid #FEDF89' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                          <span style={{ fontSize: '14px', fontWeight: 700, color: '#B54708' }}>
                            Policy Conditions & Compliance Requirements
                          </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {benefitDisplay.conditions.map((cond, idx) => (
                            <div
                              key={idx}
                              style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '8px',
                                fontSize: '13px',
                                color: '#7A2E0E',
                                lineHeight: 1.5
                              }}
                            >
                              <span style={{ color: '#D92D20', fontWeight: 700 }}>•</span>
                              <span style={{ flex: 1 }}>{cond}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* TAB: DOCUMENTS */}
            {activeTab === 'documents' && (
              <div className="scheme-tab-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <h3 className="tab-panel-title">Required Documents Checklist</h3>
                    <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                      Authoritative document prerequisites specified in official Government policy.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleCheckDocumentsClick}
                    className="btn-check-docs-secondary"
                    style={{
                      padding: '8px 14px',
                      backgroundColor: '#E6F4F1',
                      color: '#005B50',
                      border: '1px solid #B2DDDA',
                      borderRadius: '8px',
                      fontSize: '12.5px',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    title="Evaluate your uploaded documents against this scheme in My Documents"
                  >
                    <FileCheck size={14} />
                    <span>Check Readiness in My Documents</span>
                    <ArrowRight size={13} />
                  </button>
                </div>

                {requiredDocs.length === 0 ? (
                  <div style={{ padding: '32px 20px', textAlign: 'center', background: '#F8F9FA', borderRadius: '10px' }}>
                    <FileText size={32} style={{ color: '#98A2B3', margin: '0 auto 12px' }} />
                    <h4 style={{ fontSize: '15px', color: '#344054', margin: '0 0 6px 0' }}>
                      Document Requirements Not Specified
                    </h4>
                    <p style={{ fontSize: '13px', color: '#667085', margin: 0 }}>
                      Specific document requirements are not detailed in the official scheme record. Please consult the implementing department guidelines.
                    </p>
                  </div>
                ) : (
                  <div className="criteria-checklist">
                    {requiredDocs.map((docName, idx) => {
                      const docStatus = matchDocumentStatus(docName, userDocs, storedUser?.id);
                      const isVerified = docStatus === 'Verified';
                      const isUploaded = docStatus === 'Uploaded';
                      const isReview = docStatus === 'Review Required';

                      return (
                        <div
                          key={idx}
                          className="criteria-item"
                          style={{ justifyContent: 'space-between', alignItems: 'center' }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <FileText size={16} color="#005B50" />
                            <div>
                              <span style={{ fontSize: '13px', fontWeight: 600, color: '#10243A' }}>
                                {docName}
                              </span>
                            </div>
                          </div>

                          <span
                            style={{
                              fontSize: '11.5px',
                              fontWeight: 600,
                              padding: '3px 10px',
                              borderRadius: '6px',
                              backgroundColor: isVerified
                                ? '#ECFDF3'
                                : isUploaded
                                ? '#EFF8FF'
                                : isReview
                                ? '#FEF0C7'
                                : '#F2F4F7',
                              color: isVerified
                                ? '#087443'
                                : isUploaded
                                ? '#175CD3'
                                : isReview
                                ? '#B54708'
                                : '#667085',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {docStatus}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* TAB: HOW TO APPLY */}
            {activeTab === 'how-to-apply' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Official Application Process</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    Step-by-step submission roadmap from canonical Government guidelines.
                  </p>
                </div>

                {/* Application Cycle Status Advisory Banner */}
                {cycle.status === 'CLOSED' ? (
                  <div
                    style={{
                      padding: '12px 16px',
                      backgroundColor: '#FEF3F2',
                      border: '1px solid #FECDCA',
                      borderRadius: '8px',
                      color: '#B42318',
                      marginTop: '14px',
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px'
                    }}
                  >
                    <AlertCircle size={18} color="#D92D20" style={{ flexShrink: 0 }} />
                    <div style={{ fontSize: '13px' }}>
                      <strong>Application Cycle Closed:</strong> Applications for this cycle closed on{' '}
                      <strong>{cycle.formattedCloseDate || cycle.closeDate}</strong>. New submissions may not be accepted until the next official notification.
                    </div>
                  </div>
                ) : cycle.status === 'UPCOMING' ? (
                  <div
                    style={{
                      padding: '12px 16px',
                      backgroundColor: '#EFF8FF',
                      border: '1px solid #B2DDFF',
                      borderRadius: '8px',
                      color: '#175CD3',
                      marginTop: '14px',
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px'
                    }}
                  >
                    <Calendar size={18} color="#175CD3" style={{ flexShrink: 0 }} />
                    <div style={{ fontSize: '13px' }}>
                      <strong>Upcoming Application Cycle:</strong> Applications are scheduled to open on{' '}
                      <strong>{cycle.formattedOpenDate || cycle.openDate}</strong>.
                    </div>
                  </div>
                ) : cycle.status === 'OPEN' && cycle.formattedCloseDate ? (
                  <div
                    style={{
                      padding: '12px 16px',
                      backgroundColor: '#ECFDF3',
                      border: '1px solid #A6F4C5',
                      borderRadius: '8px',
                      color: '#087443',
                      marginTop: '14px',
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px'
                    }}
                  >
                    <CheckCircle2 size={18} color="#087443" style={{ flexShrink: 0 }} />
                    <div style={{ fontSize: '13px' }}>
                      <strong>Applications Open:</strong> Submission window is currently active until{' '}
                      <strong>{cycle.formattedCloseDate}</strong>.
                    </div>
                  </div>
                ) : cycle.status === 'NOT_SPECIFIED' ? (
                  <div
                    style={{
                      padding: '12px 16px',
                      backgroundColor: '#F8F9FA',
                      border: '1px solid #EAECF0',
                      borderRadius: '8px',
                      color: '#475467',
                      marginTop: '14px',
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px'
                    }}
                  >
                    <Info size={18} color="#667085" style={{ flexShrink: 0 }} />
                    <div style={{ fontSize: '13px' }}>
                      <strong>Application Cycle:</strong> Official cycle dates and deadlines are not specified in the scheme record. Consult the implementing authority for current availability.
                    </div>
                  </div>
                ) : null}

                {applicationSteps.length === 0 ? (
                  <div style={{ padding: '32px 20px', textAlign: 'center', background: '#F8F9FA', borderRadius: '10px' }}>
                    <h4 style={{ fontSize: '15px', color: '#344054', margin: '0 0 6px 0' }}>
                      Official Roadmap Not Available
                    </h4>
                    <p style={{ fontSize: '13px', color: '#667085', margin: 0 }}>
                      Official step-by-step application roadmap is not detailed in the current scheme record. Please consult official scheme guidelines or nodal department.
                    </p>
                  </div>
                ) : (
                  <div className="application-roadmap">
                    {applicationSteps.map((s, idx) => (
                      <div
                        key={s.step || idx}
                        onClick={() => setExpandedStep(expandedStep === s.step ? null : s.step)}
                        className={`roadmap-step-item ${expandedStep === s.step ? 'expanded' : ''}`}
                      >
                        <div className="step-num-circle">{s.step}</div>
                        <div className="step-content">
                          <div className="step-name">
                            <span>{s.title}</span>
                          </div>
                          <p className="step-detail">{s.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {(portalDetails.applicationUrl || portalDetails.officialWebsite) && (
                  <div style={{ marginTop: '20px', padding: '16px 20px', backgroundColor: '#F0FDF4', borderRadius: '10px', border: '1px solid #DCFCE7', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                    <div>
                      <h5 style={{ margin: 0, fontSize: '14px', color: '#073B30', fontWeight: 700 }}>
                        Apply via Official Portal
                      </h5>
                      <span style={{ fontSize: '12.5px', color: '#15803D' }}>
                        Submit your application or register on the verified government portal.
                      </span>
                    </div>
                    <a
                      href={portalDetails.applicationUrl || portalDetails.officialWebsite}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: '9px 18px',
                        backgroundColor: '#073B30',
                        color: '#FFFFFF',
                        borderRadius: '7px',
                        fontSize: '13px',
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        textDecoration: 'none'
                      }}
                    >
                      <span>Proceed to Official Application</span>
                      <ExternalLink size={13} />
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* TAB: SOURCE & RULES */}
            {activeTab === 'source-rules' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Official Sources & Operating Rules</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    Statutory notifications, nodal executing bodies, and official gazette guidelines.
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
                  <div style={{ padding: '16px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Building2 size={16} color="#005B50" />
                      <h4 style={{ margin: 0, fontSize: '13.5px', color: '#10243A' }}>Implementing Agencies</h4>
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12.5px', color: '#475467', lineHeight: 1.6 }}>
                      {portalDetails.department && <li>{portalDetails.department}</li>}
                      {portalDetails.ministry && portalDetails.ministry !== portalDetails.department && portalDetails.ministry !== 'Implementing Authority Not Specified' && (
                        <li>{portalDetails.ministry}</li>
                      )}
                      {scheme.nodal_agency && <li>{scheme.nodal_agency}</li>}
                      {!portalDetails.department && (!portalDetails.ministry || portalDetails.ministry === 'Implementing Authority Not Specified') && !scheme.nodal_agency && (
                        <li>Not specified in available official information.</li>
                      )}
                    </ul>
                  </div>

                  <div style={{ padding: '16px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Landmark size={16} color="#005B50" />
                      <h4 style={{ margin: 0, fontSize: '13.5px', color: '#10243A' }}>
                        {hasLoanCalculator || scheme.is_loan_scheme ? 'Financing & Lending Institutions' : 'Disbursement & Settlement Mechanism'}
                      </h4>
                    </div>
                    {hasLoanCalculator || scheme.is_loan_scheme ? (
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12.5px', color: '#475467', lineHeight: 1.6 }}>
                        {Array.isArray(scheme.participating_banks) && scheme.participating_banks.length > 0 ? (
                          scheme.participating_banks.map((b, i) => <li key={i}>{b}</li>)
                        ) : (
                          <li>Participating commercial banks and lending institutions under official scheme guidelines.</li>
                        )}
                      </ul>
                    ) : (
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12.5px', color: '#475467', lineHeight: 1.6 }}>
                        {scheme.dbt_scheme ? (
                          <li>Direct Benefit Transfer (DBT) to beneficiary Aadhaar-linked bank account</li>
                        ) : scheme.disbursement_mechanism ? (
                          <li>{scheme.disbursement_mechanism}</li>
                        ) : (
                          <li>Not specified in available official information.</li>
                        )}
                      </ul>
                    )}
                  </div>
                </div>

                {/* Distinguished Official Sources Grid */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '14px' }}>
                  {/* Source 1: Official Scheme Portal & Authoritative Source */}
                  {portalDetails.officialWebsite ? (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F0FDF4', borderRadius: '10px', border: '1px solid #DCFCE7' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <h5 style={{ margin: 0, fontSize: '13.5px', color: '#073B30', fontWeight: 700 }}>
                            Official Scheme Portal & Authoritative Source
                          </h5>
                          <span style={{ fontSize: '12px', color: '#15803D' }}>
                            {portalDetails.department || portalDetails.ministry || 'Implementing Authority'}: {portalDetails.officialWebsite}
                          </span>
                        </div>
                        <a
                          href={portalDetails.officialWebsite}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '7px 14px',
                            backgroundColor: '#073B30',
                            color: '#FFFFFF',
                            borderRadius: '6px',
                            fontSize: '12.5px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            textDecoration: 'none'
                          }}
                        >
                          <span>Visit Official Portal</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                      <h5 style={{ margin: 0, fontSize: '13.5px', color: '#10243A', fontWeight: 700 }}>
                        Official Scheme Portal
                      </h5>
                      <span style={{ fontSize: '12px', color: '#667085', fontStyle: 'italic' }}>
                        Official link not verified
                      </span>
                    </div>
                  )}

                  {/* Source 2: Implementing Authority Departmental Portal (if distinct) */}
                  {portalDetails.authorityPortalUrl && portalDetails.authorityPortalUrl !== portalDetails.officialWebsite && (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <h5 style={{ margin: 0, fontSize: '13.5px', color: '#10243A', fontWeight: 700 }}>
                            Implementing Authority Departmental Portal
                          </h5>
                          <span style={{ fontSize: '12px', color: '#475467' }}>
                            {portalDetails.department || portalDetails.ministry || 'Department Portal'}: {portalDetails.authorityPortalUrl}
                          </span>
                        </div>
                        <a
                          href={portalDetails.authorityPortalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '7px 14px',
                            backgroundColor: '#FFFFFF',
                            color: '#344054',
                            border: '1px solid #D0D5DD',
                            borderRadius: '6px',
                            fontSize: '12.5px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            textDecoration: 'none'
                          }}
                        >
                          <span>Visit Authority Portal</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Source 3: Scheme Information Source (if distinct) */}
                  {portalDetails.informationSourceUrl && portalDetails.informationSourceUrl !== portalDetails.officialWebsite && (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <h5 style={{ margin: 0, fontSize: '13.5px', color: '#10243A', fontWeight: 700 }}>
                            Scheme Information Source
                          </h5>
                          <span style={{ fontSize: '12px', color: '#475467' }}>
                            {portalDetails.informationSourceName}: {portalDetails.informationSourceUrl}
                          </span>
                        </div>
                        <a
                          href={portalDetails.informationSourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '7px 14px',
                            backgroundColor: '#FFFFFF',
                            color: '#344054',
                            border: '1px solid #D0D5DD',
                            borderRadius: '6px',
                            fontSize: '12.5px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            textDecoration: 'none'
                          }}
                        >
                          <span>View Information Source</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Source 4: Official Guidelines Document */}
                  {portalDetails.isPdf ? (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <h5 style={{ margin: 0, fontSize: '13.5px', color: '#10243A', fontWeight: 700 }}>
                            Official Policy Guidelines (PDF)
                          </h5>
                          <span style={{ fontSize: '12px', color: '#475467' }}>
                            {portalDetails.guidelinesTitle}: {guidelineDocumentUrl}
                          </span>
                        </div>
                        <a
                          href={guidelineDocumentUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '7px 14px',
                            backgroundColor: '#FFFFFF',
                            color: '#344054',
                            border: '1px solid #D0D5DD',
                            borderRadius: '6px',
                            fontSize: '12.5px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            textDecoration: 'none'
                          }}
                        >
                          <span>Open Guidelines (PDF)</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </div>
                  ) : portalDetails.officialRulesPageUrl ? (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <h5 style={{ margin: 0, fontSize: '13.5px', color: '#10243A', fontWeight: 700 }}>
                            Official Guidelines & Rules
                          </h5>
                          <span style={{ fontSize: '12px', color: '#475467' }}>
                            {portalDetails.guidelinesTitle}: {portalDetails.officialRulesPageUrl}
                          </span>
                        </div>
                        <a
                          href={portalDetails.officialRulesPageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '7px 14px',
                            backgroundColor: '#FFFFFF',
                            color: '#344054',
                            border: '1px solid #D0D5DD',
                            borderRadius: '6px',
                            fontSize: '12.5px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            textDecoration: 'none'
                          }}
                        >
                          <span>Open Guidelines & Rules</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '14px 18px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <h5 style={{ margin: 0, fontSize: '13.5px', color: '#10243A', fontWeight: 700 }}>
                            Official Policy Guidelines & Documents
                          </h5>
                          <span style={{ fontSize: '12px', color: '#667085', fontStyle: 'italic' }}>
                            Official guideline PDF is not indexed or available in the current policy record.
                          </span>
                        </div>
                        <span style={{ fontSize: '12px', color: '#98A2B3', padding: '6px 12px', backgroundColor: '#F2F4F7', borderRadius: '6px' }}>
                          Document Unavailable
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB: FAQS */}
            {activeTab === 'faqs' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Frequently Asked Questions</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    Authoritative answers to common questions regarding eligibility, documentation, and disbursement rules for {scheme.title}.
                  </p>
                </div>

                {isFaqsLoading && (
                  <div style={{ padding: '48px 20px', textAlign: 'center' }}>
                    <Loader2 size={30} className="spin" style={{ color: '#005B50', margin: '0 auto 12px' }} />
                    <p style={{ color: '#475467', fontSize: '14px', margin: 0 }}>Loading official scheme FAQs...</p>
                  </div>
                )}

                {faqsError && !isFaqsLoading && (
                  <div style={{ padding: '24px 20px', textAlign: 'center', backgroundColor: '#FEF3F2', borderRadius: '10px', border: '1px solid #FECDCA', marginTop: '16px' }}>
                    <AlertTriangle size={24} style={{ color: '#D92D20', margin: '0 auto 8px' }} />
                    <p style={{ color: '#B42318', fontSize: '14px', fontWeight: 500, margin: 0 }}>
                      {faqsError}
                    </p>
                  </div>
                )}

                {!isFaqsLoading && !faqsError && faqs.length === 0 && faqsLoaded && (
                  <div style={{ padding: '36px 20px', textAlign: 'center', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0', marginTop: '16px' }}>
                    <Info size={24} style={{ color: '#667085', margin: '0 auto 8px' }} />
                    <p style={{ color: '#475467', fontSize: '14px', margin: 0 }}>
                      No official FAQs available for this scheme.
                    </p>
                  </div>
                )}

                {!isFaqsLoading && faqs.length > 0 && (
                  <div className="faq-accordion" style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '16px' }}>
                    {faqs.map((faq, idx) => {
                      const isExpanded = expandedFaqIndex === idx;
                      const faqId = `faq-desc-${faq.faq_number || idx}`;
                      const btnId = `faq-btn-${faq.faq_number || idx}`;
                      return (
                        <div
                          key={faq.id || faq.faq_number || idx}
                          style={{
                            border: '1px solid',
                            borderColor: isExpanded ? '#005B50' : '#EAECF0',
                            borderRadius: '10px',
                            overflow: 'hidden',
                            backgroundColor: isExpanded ? '#F8FCFB' : '#FFFFFF',
                            transition: 'all 0.2s ease'
                          }}
                        >
                          <button
                            type="button"
                            id={btnId}
                            aria-expanded={isExpanded}
                            aria-controls={faqId}
                            onClick={() => setExpandedFaqIndex(isExpanded ? null : idx)}
                            style={{
                              width: '100%',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '16px 18px',
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              textAlign: 'left',
                              color: '#10243A',
                              fontSize: '14px',
                              fontWeight: 600,
                              gap: '12px'
                            }}
                          >
                            <span style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                              <span
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  minWidth: '24px',
                                  height: '24px',
                                  borderRadius: '50%',
                                  backgroundColor: isExpanded ? '#005B50' : '#E6F4F1',
                                  color: isExpanded ? '#FFFFFF' : '#005B50',
                                  fontSize: '11.5px',
                                  fontWeight: 700,
                                  flexShrink: 0,
                                  marginTop: '1px'
                                }}
                              >
                                {faq.faq_number != null ? faq.faq_number : idx + 1}
                              </span>
                              <span style={{ lineHeight: 1.45 }}>{faq.question}</span>
                            </span>
                            <span
                              style={{
                                fontSize: '16px',
                                color: isExpanded ? '#005B50' : '#667085',
                                transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                transition: 'transform 0.2s ease',
                                display: 'inline-flex',
                                alignItems: 'center',
                                flexShrink: 0
                              }}
                              aria-hidden="true"
                            >
                              ▾
                            </span>
                          </button>
                          {isExpanded && (
                            <div
                              id={faqId}
                              role="region"
                              aria-labelledby={btnId}
                              style={{
                                padding: '0 20px 18px 52px',
                                color: '#344054',
                                fontSize: '13.5px',
                                lineHeight: 1.65,
                                whiteSpace: 'pre-line'
                              }}
                            >
                              {faq.answer}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ============================================================== */}
          {/* RIGHT COLUMN: Sticky Full-Height Sidebar (Zero Blank Bottom) */}
          {/* ============================================================== */}
          <div className="scheme-right-sidebar">
            {/* Card 1: Estimated Financial Support */}
            <div className="scheme-support-card">
              <div className="support-badge-row">
                <div className="support-badge-icon">
                  <Coins size={14} />
                </div>
                <span className="support-badge-label">Estimated Financial Support</span>
              </div>

              <div className="support-amount-text">
                {benefitDisplay.amountDisplay}
              </div>

              <div className="support-amount-sub" title="Official financial benefit structure">
                <span>
                  {benefitDisplay.subtitle}
                </span>
                <Info size={13} style={{ cursor: 'pointer', color: '#98A2B3' }} />
              </div>

              <button
                type="button"
                onClick={handleApplyClick}
                className="btn-apply-main"
                style={cycle.status === 'CLOSED' ? { backgroundColor: '#475467' } : undefined}
                title={cycle.status === 'CLOSED' ? `Applications closed on ${cycle.formattedCloseDate || cycle.closeDate}` : 'Apply for Scheme'}
              >
                <span>{cycle.status === 'CLOSED' ? 'Cycle Closed' : 'Apply Now'}</span>
                <ArrowRight size={15} />
              </button>

              <button
                type="button"
                onClick={handleCheckDocumentsClick}
                className="btn-check-docs-main"
                title="Check your document readiness for this scheme in My Documents"
                aria-label="Check Required Documents in My Documents"
              >
                <FileCheck size={14} />
                <span>Check Required Documents</span>
              </button>

              <button
                type="button"
                onClick={handleSaveToggle}
                className={`btn-save-main ${isSaved ? 'saved' : ''}`}
              >
                {isSaved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
                <span>{isSaved ? 'Saved to Bookmarks' : 'Save for Later'}</span>
              </button>
            </div>

            {/* Card 2: Metadata Details */}
            <div className="scheme-metadata-card">
              {/* Row 1: Implementing Ministry */}
              <div className="meta-item-row">
                <Building2 size={16} className="meta-item-icon" />
                <div className="meta-item-body">
                  <span className="meta-item-title">Implementing Ministry</span>
                  <span className="meta-item-value">
                    {portalDetails.ministry}
                  </span>
                </div>
              </div>

              {/* Row 2: Scheme Type */}
              <div className="meta-item-row">
                <Sliders size={16} className="meta-item-icon" />
                <div className="meta-item-body">
                  <span className="meta-item-title">Scheme Type</span>
                  <span className="meta-item-value">{portalDetails.schemeType}</span>
                </div>
              </div>

              {/* Row 3: Target Beneficiaries */}
              <div className="meta-item-row">
                <User size={16} className="meta-item-icon" />
                <div className="meta-item-body">
                  <span className="meta-item-title">Target Beneficiaries</span>
                  <span className="meta-item-value">
                    {portalDetails.targetBeneficiaries}
                  </span>
                </div>
              </div>

              {/* Row 4: Coverage */}
              <div className="meta-item-row">
                <ShieldCheck size={16} className="meta-item-icon" />
                <div className="meta-item-body">
                  <span className="meta-item-title">Coverage</span>
                  <span className="meta-item-value">{portalDetails.coverage}</span>
                </div>
              </div>

              {/* Row 5: Official Website */}
              <div className="meta-item-row">
                <Globe size={16} className="meta-item-icon" />
                <div className="meta-item-body">
                  <span className="meta-item-title">Official Website</span>
                  {portalDetails.officialWebsite ? (
                    <a
                      href={portalDetails.officialWebsite}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="meta-item-value meta-website-link"
                    >
                      {portalDetails.officialWebsite}
                    </a>
                  ) : (
                    <span className="meta-item-value" style={{ color: '#667085', fontStyle: 'italic' }}>
                      Official link not verified
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Card 3: Application Timelines & Milestones */}
            <div className="scheme-timeline-card">
              <div className="sidebar-card-header">
                <Calendar size={15} color="#005B50" />
                <span>Application Cycle & Timelines</span>
              </div>

              <div className="timeline-list">
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Application Status:</span>
                  <span
                    className="timeline-item-val"
                    style={{
                      color:
                        cycle.status === 'CLOSED'
                          ? '#B42318'
                          : cycle.status === 'UPCOMING'
                          ? '#175CD3'
                          : cycle.isLive
                          ? '#087443'
                          : '#475467',
                      fontWeight: 600
                    }}
                  >
                    {cycle.label}
                  </span>
                </div>
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Start Date:</span>
                  <span className="timeline-item-val">
                    {cycle.formattedOpenDate || (cycle.openDate ? cycle.openDate : 'Not Specified')}
                  </span>
                </div>
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Closing Date:</span>
                  <span
                    className="timeline-item-val"
                    style={{
                      color: cycle.closeDate ? (cycle.status === 'CLOSED' ? '#B42318' : '#087443') : '#475467',
                      fontWeight: cycle.closeDate ? 600 : 400
                    }}
                  >
                    {cycle.formattedCloseDate || (cycle.closeDate ? cycle.closeDate : 'Not Specified')}
                  </span>
                </div>
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Processing SLA:</span>
                  <span className="timeline-item-val" style={{ color: '#475467', fontStyle: 'italic' }}>
                    Authority Discretion
                  </span>
                </div>
              </div>
            </div>

            {/* Card 4: Download Official Guidelines */}
            <div className="scheme-guidelines-box">
              <div className="guidelines-left">
                <div className="guidelines-icon-sq">
                  {portalDetails.isPdf ? (
                    <FileText size={16} />
                  ) : portalDetails.officialRulesPageUrl ? (
                    <ExternalLink size={16} />
                  ) : (
                    <FileText size={16} style={{ opacity: 0.5 }} />
                  )}
                </div>
                <div className="guidelines-text">
                  <h4 className="guidelines-title">
                    {portalDetails.isPdf
                      ? 'Download Official Guidelines (PDF)'
                      : portalDetails.officialRulesPageUrl
                      ? 'Official Guidelines & Rules'
                      : 'Official Guidelines'}
                  </h4>
                  <p className="guidelines-sub">
                    {guidelineDocumentUrl ? portalDetails.guidelinesTitle : 'Official document link not available in record'}
                  </p>
                </div>
              </div>

              {guidelineDocumentUrl || portalDetails.officialRulesPageUrl ? (
                <button
                  type="button"
                  onClick={handleDownloadGuidelines}
                  className="guidelines-download-btn"
                  title={
                    portalDetails.isPdf
                      ? `Download / Open ${portalDetails.guidelinesTitle}`
                      : `Open ${portalDetails.guidelinesTitle}`
                  }
                  aria-label={
                    portalDetails.isPdf
                      ? 'Download Official Guidelines (PDF)'
                      : 'Open Official Guidelines Webpage'
                  }
                >
                  {portalDetails.isPdf ? <Download size={15} /> : <ExternalLink size={15} />}
                </button>
              ) : (
                <button
                  type="button"
                  className="guidelines-download-btn"
                  title="Official guidelines document link not available in record"
                  aria-label="Guidelines Unavailable"
                  style={{ opacity: 0.6, cursor: 'not-allowed' }}
                  disabled
                  aria-disabled="true"
                >
                  <Download size={15} />
                </button>
              )}
            </div>

            {/* Download feedback toast */}
            {downloadSuccess && (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#ECFDF3',
                  border: '1px solid #A6F4C5',
                  borderRadius: '8px',
                  color: '#087443',
                  fontSize: '12px',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <CheckCircle2 size={14} />
                <span>Opening official policy guidelines...</span>
              </div>
            )}

            {/* Unavailable notice toast */}
            {downloadNotice && (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#FEF3F2',
                  border: '1px solid #FECDCA',
                  borderRadius: '8px',
                  color: '#B42318',
                  fontSize: '12px',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <AlertCircle size={14} />
                <span>{downloadNotice}</span>
              </div>
            )}

            {/* Card 5: Official Helplines & Support Desk (Fills Bottom Right) */}
            <div className="scheme-helpdesk-card">
              <div className="helpdesk-header">
                <PhoneCall size={14} color="#005B50" />
                <span>{portalDetails.helplineName || 'Official Scheme Helpline'}</span>
              </div>
              <div className="helpdesk-number" style={portalDetails.helplineNumber === 'Not Specified' ? { fontSize: '15px', color: '#475467' } : undefined}>
                {portalDetails.helplineNumber || 'Not Specified'}
              </div>
              <div className="helpdesk-hours">
                {portalDetails.helplineHours || 'Refer to official department portal for support channels'}
              </div>
            </div>

            {/* Card 6: Need Help Guidance Link Box */}
            <div className="scheme-help-box">
              <div className="help-icon-circle">
                <Headphones size={15} />
              </div>
              <div className="help-body">
                <h4 className="help-title">Need Help?</h4>
                <p className="help-sub">Read our guide or contact support.</p>
                <button
                  type="button"
                  onClick={() => setShowHelpModal(true)}
                  className="help-guidance-link"
                >
                  <span>Get Guidance</span>
                  <ArrowRight size={12} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Modal: Application Initiation */}
        {showApplyModal && (
          <div className="application-modal-overlay" onClick={() => setShowApplyModal(false)}>
            <div className="application-modal-card" onClick={(e) => e.stopPropagation()}>
              <div
                style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '50%',
                  backgroundColor: '#ECFDF3',
                  color: '#087443',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '14px'
                }}
              >
                <CheckCircle2 size={24} />
              </div>

              <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#10243A', margin: '0 0 6px 0' }}>
                Initiate {scheme.title} Application
              </h3>

              {cycle.status === 'CLOSED' && (
                <div
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#FEF3F2',
                    border: '1px solid #FECDCA',
                    borderRadius: '6px',
                    color: '#B42318',
                    fontSize: '12px',
                    marginBottom: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <AlertTriangle size={15} style={{ flexShrink: 0 }} />
                  <span>Notice: Application cycle closed on {cycle.formattedCloseDate || cycle.closeDate}.</span>
                </div>
              )}

              {hasValidCalculator ? (
                <>
                  <p style={{ fontSize: '13px', color: '#475467', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                    {isEvaluated ? (
                      <>Your FIN profile has an evaluated <strong>{matchScore}% match</strong>. Calculated estimated subsidy:{' '}</>
                    ) : (
                      <>Statutory eligibility is currently <strong>Unverified (UNKNOWN)</strong>. Calculated estimated subsidy:{' '}</>
                    )}
                    <strong style={{ color: '#005B50' }}>{formatCurrency(subsidyAmount)}</strong>.
                  </p>

                  <div
                    style={{
                      width: '100%',
                      padding: '12px',
                      backgroundColor: '#F8FAFC',
                      borderRadius: '8px',
                      border: '1px solid #EAECF0',
                      textAlign: 'left',
                      fontSize: '12px',
                      color: '#344054',
                      marginBottom: '16px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span>Proposed Project Cost:</span>
                      <strong>{formatCurrency(projectCost)}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span>Eligible Subsidy:</span>
                      <strong style={{ color: '#005B50' }}>{formatCurrency(subsidyAmount)} ({subsidyPercent}%)</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Bank Term Loan:</span>
                      <strong>{formatCurrency(loanAmount)} ({loanPercent}%)</strong>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <p style={{ fontSize: '13px', color: '#475467', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                    {isEvaluated ? (
                      <>Your FIN profile has an evaluated <strong>{matchScore}% match</strong> for this initiative.</>
                    ) : (
                      <>Statutory eligibility is currently <strong>Unverified (UNKNOWN)</strong>. Application requirements will be reviewed against scheme policy.</>
                    )}
                  </p>

                  <div
                    style={{
                      width: '100%',
                      padding: '12px',
                      backgroundColor: '#F8FAFC',
                      borderRadius: '8px',
                      border: '1px solid #EAECF0',
                      textAlign: 'left',
                      fontSize: '12px',
                      color: '#344054',
                      marginBottom: '16px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span>Scheme Authority:</span>
                      <strong>{portalDetails.department || portalDetails.ministry || 'Government Authority'}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span>Application Mode:</span>
                      <strong style={{ color: '#005B50' }}>
                        {portalDetails.authorityPortalUrl || portalDetails.applicationUrl
                          ? 'Official Government Portal'
                          : (portalDetails.officialWebsite?.includes('myscheme.gov.in') ? 'National Information Portal (myScheme)' : 'Departmental Guidelines')}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Required Documents:</span>
                      <strong>{requiredDocs.length > 0 ? `${requiredDocs.length} mandatory documents` : 'Refer to policy requirements'}</strong>
                    </div>
                  </div>
                </>
              )}

              <div style={{ display: 'flex', gap: '8px', width: '100%' }}>
                <button
                  type="button"
                  onClick={() => setShowApplyModal(false)}
                  style={{
                    flex: 1,
                    padding: '9px',
                    borderRadius: '8px',
                    border: '1px solid #D0D5DD',
                    backgroundColor: '#FFFFFF',
                    color: '#344054',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
                {portalDetails.authorityPortalUrl || portalDetails.applicationUrl ? (
                  <a
                    href={portalDetails.authorityPortalUrl || portalDetails.applicationUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={handleInitiateSubmit}
                    style={{
                      flex: 1.4,
                      padding: '9px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: '#073B30',
                      color: '#FFFFFF',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      textDecoration: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>Proceed to Official Portal</span>
                    <ExternalLink size={14} />
                  </a>
                ) : portalDetails.officialWebsite ? (
                  <a
                    href={portalDetails.officialWebsite}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={handleInitiateSubmit}
                    style={{
                      flex: 1.4,
                      padding: '9px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: '#073B30',
                      color: '#FFFFFF',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      textDecoration: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>{portalDetails.officialWebsite.includes('myscheme.gov.in') ? 'View on myScheme Portal' : 'Proceed to Official Portal'}</span>
                    <ExternalLink size={14} />
                  </a>
                ) : (
                  <button
                    type="button"
                    disabled
                    style={{
                      flex: 1.4,
                      padding: '9px',
                      borderRadius: '8px',
                      border: '1px solid #E4E7EC',
                      backgroundColor: '#F2F4F7',
                      color: '#98A2B3',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'not-allowed',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>Official Portal Not Verified</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Modal: Guidance & Support */}
        {showHelpModal && (
          <div className="application-modal-overlay" onClick={() => setShowHelpModal(false)}>
            <div className="application-modal-card" onClick={(e) => e.stopPropagation()}>
              <div
                style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '50%',
                  backgroundColor: '#EFF8FF',
                  color: '#175CD3',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '14px'
                }}
              >
                <Headphones size={22} />
              </div>

              <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#10243A', margin: '0 0 6px 0' }}>
                {scheme.title} Guidance Desk
              </h3>

              <p style={{ fontSize: '13px', color: '#475467', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                Need assistance with your eligibility, documentation appraisal, or subsidy claim? Official government support channels and automated guidance are available.
              </p>

              <div
                style={{
                  width: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  textAlign: 'left',
                  fontSize: '12.5px',
                  marginBottom: '16px'
                }}
              >
                <div style={{ padding: '10px 12px', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid #EAECF0' }}>
                  <strong style={{ color: '#10243A', display: 'block' }}>{portalDetails.helplineName}:</strong>
                  <span style={{ color: '#005B50', fontWeight: 600 }}>{portalDetails.helplineNumber} ({portalDetails.helplineHours})</span>
                </div>
                <div style={{ padding: '10px 12px', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid #EAECF0' }}>
                  <strong style={{ color: '#10243A', display: 'block' }}>Official Government Portal:</strong>
                  <a
                    href={portalDetails.officialWebsite}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#175CD3', textDecoration: 'none', wordBreak: 'break-all' }}
                  >
                    {portalDetails.officialWebsite}
                  </a>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowHelpModal(false)}
                style={{
                  width: '100%',
                  padding: '9px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: '#073B30',
                  color: '#FFFFFF',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer'
                }}
              >
                Got It
              </button>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
