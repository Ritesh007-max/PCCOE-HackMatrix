import React, { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
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
  ChevronRight,
  ChevronDown,
  X,
  ExternalLink,
  Calculator,
  Percent,
  Check,
  Share2,
  Printer,
  Calendar,
  PhoneCall
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import { SCHEMES } from '../data/schemesData';
import SchemeLogo from '../components/schemes/SchemeLogo';

// Assets
import ashokStambhVector from '../assets/ashok_stambh_vector.svg';
import ashokStambhGold from '../assets/ashok_stambh_gold.png';
import govtOfIndiaImg from '../assets/govt_of_india_hero.png';

// Helper function to resolve dynamic official government portal, ministry, and helpline according to scheme
export function getSchemePortalDetails(scheme) {
  if (!scheme) {
    return {
      ministry: 'Government of India',
      schemeType: 'Central Welfare Programme',
      targetBeneficiaries: 'Eligible Indian Citizens',
      coverage: 'All India (Rural & Urban)',
      officialWebsite: 'https://india.gov.in',
      helplineName: 'National Citizen Service Helpdesk',
      helplineNumber: '1800 11 0001',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'Official Guidelines 2026 (PDF)'
    };
  }

  const id = scheme.id?.toLowerCase() || '';
  const title = scheme.title?.toLowerCase() || '';
  const cats = scheme.categories || [];

  // 1. Farmer / Agriculture Schemes (e.g. PM Kisan, PM Fasal Bima, KCC, etc.)
  if (
    id.includes('kisan') ||
    id.includes('farmer') ||
    id.includes('fasal') ||
    id.includes('krishi') ||
    title.includes('kisan') ||
    title.includes('farmer') ||
    cats.includes('agriculture')
  ) {
    if (id.includes('pm-kisan') || id === 'pmkisan' || title.includes('samman nidhi')) {
      return {
        ministry: scheme.ministry || 'Ministry of Agriculture & Farmers Welfare',
        schemeType: 'Direct Benefit Transfer (DBT) Income Support',
        targetBeneficiaries: 'Landholding Small & Marginal Farmer Families',
        coverage: 'All States & Union Territories (Pan-India)',
        officialWebsite: 'https://pmkisan.gov.in',
        helplineName: 'PM-Kisan National Farmer Helpline',
        helplineNumber: '155261 / 1800 11 5526',
        helplineHours: 'Toll-Free • 24×7 Kisan Suvidha Support',
        guidelinesTitle: 'PM-Kisan Operational Guidelines 2026 (PDF)'
      };
    }
    if (id.includes('fasal') || title.includes('fasal') || title.includes('crop')) {
      return {
        ministry: scheme.ministry || 'Ministry of Agriculture & Farmers Welfare',
        schemeType: 'Comprehensive Crop Insurance & Weather Shield',
        targetBeneficiaries: 'All Farmers including Sharecroppers & Tenant Farmers',
        coverage: 'All Agricultural Districts Across India',
        officialWebsite: 'https://pmfby.gov.in',
        helplineName: 'PMFBY Farmer Grievance Cell',
        helplineNumber: '14447 / 1800 200 5142',
        helplineHours: 'Toll-Free • 24×7 Farmer Support',
        guidelinesTitle: 'PM Fasal Bima Yojana Guidelines (PDF)'
      };
    }
    if (id.includes('kcc') || id.includes('credit-card') || title.includes('credit card')) {
      return {
        ministry: scheme.ministry || 'Ministry of Agriculture & Farmers Welfare',
        schemeType: 'Subsidized Revolving Agricultural Credit',
        targetBeneficiaries: 'Farmers, Dairy & Animal Husbandry Cultivators',
        coverage: 'All Commercial & Rural Banks Nationwide',
        officialWebsite: 'https://pmkisan.gov.in',
        helplineName: 'KCC Farmer Support Desk',
        helplineNumber: '155261 / 1800 180 1551',
        helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
        guidelinesTitle: 'Kisan Credit Card Scheme Guidelines (PDF)'
      };
    }
    return {
      ministry: scheme.ministry || 'Ministry of Agriculture & Farmers Welfare',
      schemeType: 'Agricultural Modernization & Farmer Grant',
      targetBeneficiaries: 'Smallholder Farmers & Producer Organizations',
      coverage: 'Rural & Agricultural Belts Across India',
      officialWebsite: 'https://agricoop.nic.in',
      helplineName: 'Kisan Call Centre (KCC)',
      helplineNumber: '1800 180 1551',
      helplineHours: 'Toll-Free • 24×7 (All Indian Languages)',
      guidelinesTitle: `${scheme.title} Operational Guidelines (PDF)`
    };
  }

  // 2. PMEGP (Prime Minister's Employment Generation Programme)
  if (id === 'pmegp') {
    return {
      ministry: scheme.ministry || 'Ministry of Micro, Small and Medium Enterprises',
      schemeType: 'Credit Linked Subsidy Programme',
      targetBeneficiaries: 'New Entrepreneurs / Unemployed Youth / SHGs',
      coverage: 'Rural & Urban Areas (All India)',
      officialWebsite: 'https://kviconline.gov.in/pmegpeportal/',
      helplineName: 'National MSME & KVIC Helpdesk',
      helplineNumber: '1800 180 6763',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'PMEGP Guidelines 2026 (PDF)'
    };
  }

  // 3. MSME & Small Business Schemes
  if (id.includes('msme') || id.includes('udyam') || title.includes('msme')) {
    return {
      ministry: scheme.ministry || 'Ministry of Micro, Small and Medium Enterprises',
      schemeType: 'Credit & Financial Assistance Package',
      targetBeneficiaries: 'Micro, Small & Medium Enterprises (Udyam Registered)',
      coverage: 'Manufacturing & Service Units Pan-India',
      officialWebsite: 'https://msme.gov.in',
      helplineName: 'National MSME Champions Helpdesk',
      helplineNumber: '1800 180 6763 / 011-23063288',
      helplineHours: 'Toll-Free • Mon–Fri (9:00 AM – 5:30 PM)',
      guidelinesTitle: `${scheme.title} Policy & Support Manual (PDF)`
    };
  }

  // 4. Mudra Yojana
  if (id.includes('mudra') || title.includes('mudra')) {
    return {
      ministry: scheme.ministry || 'Department of Financial Services, Ministry of Finance',
      schemeType: 'Institutional Refinance & Collateral-Free Micro Loan',
      targetBeneficiaries: 'Small Business Owners, Artisans & Shopkeepers',
      coverage: 'All Scheduled Commercial Banks & NBFCs Nationwide',
      officialWebsite: 'https://www.mudra.org.in',
      helplineName: 'National MUDRA Toll-Free Helpline',
      helplineNumber: '1800 180 1111 / 1800 11 0001',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'Pradhan Mantri MUDRA Yojana Guidelines (PDF)'
    };
  }

  // 5. Stand Up India
  if (id.includes('standup') || id.includes('stand-up') || title.includes('stand up')) {
    return {
      ministry: scheme.ministry || 'Department of Financial Services, Ministry of Finance',
      schemeType: 'Composite Bank Loan (Term Loan + Working Capital)',
      targetBeneficiaries: 'SC, ST and Women Entrepreneurs (First-time founders)',
      coverage: 'All Public Sector & Commercial Bank Branches Pan-India',
      officialWebsite: 'https://www.standupmitra.in',
      helplineName: 'Stand-Up Mitra National Support Desk',
      helplineNumber: '1800 180 1111',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'Stand-Up India Scheme Guidelines (PDF)'
    };
  }

  // 6. PM SVANidhi
  if (id.includes('svanidhi') || title.includes('svanidhi') || title.includes('street vendor')) {
    return {
      ministry: scheme.ministry || 'Ministry of Housing and Urban Affairs (MoHUA)',
      schemeType: 'Micro-Credit Working Capital Loan & Cash-back Incentives',
      targetBeneficiaries: 'Urban & Peri-Urban Street Vendors and Hawkers',
      coverage: 'All Statutory Urban Local Bodies (ULBs)',
      officialWebsite: 'https://pmsvanidhi.mohua.gov.in',
      helplineName: 'PM SVANidhi National Helpdesk',
      helplineNumber: '1800 11 1979',
      helplineHours: 'Toll-Free • 9:30 AM – 6:00 PM',
      guidelinesTitle: 'PM SVANidhi Operational Guidelines (PDF)'
    };
  }

  // 7. PM Vishwakarma
  if (id.includes('vishwakarma') || title.includes('vishwakarma')) {
    return {
      ministry: scheme.ministry || 'Ministry of MSME & Ministry of Skill Development',
      schemeType: 'End-to-End Artisan Skilling & Toolkit Financial Grant',
      targetBeneficiaries: 'Traditional Artisans & Craftspeople (18 Identified Trades)',
      coverage: 'All States and Union Territories Pan-India',
      officialWebsite: 'https://pmvishwakarma.gov.in',
      helplineName: 'PM Vishwakarma Champions Desk',
      helplineNumber: '1800 267 7777',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'PM Vishwakarma Guidelines 2026 (PDF)'
    };
  }

  // 8. Ayushman Bharat (PM-JAY)
  if (id.includes('ayushman') || id.includes('pmjay') || title.includes('ayushman') || cats.includes('health')) {
    return {
      ministry: scheme.ministry || 'National Health Authority, MoHFW',
      schemeType: 'Cashless Secondary & Tertiary Health Assurance Cover',
      targetBeneficiaries: 'Eligible Deprived Rural & Urban Occupational Families',
      coverage: 'Empanelled Public & Private Hospitals Nationwide',
      officialWebsite: 'https://pmjay.gov.in',
      helplineName: 'Ayushman Bharat National Call Centre',
      helplineNumber: '14555 / 1800 11 1565',
      helplineHours: '24×7 Toll-Free Multi-lingual Support',
      guidelinesTitle: 'AB PM-JAY Operational Guidelines 2026 (PDF)'
    };
  }

  // 9. PM Awas Yojana
  if (id.includes('awas') || id.includes('pmay') || title.includes('awas') || title.includes('housing')) {
    return {
      ministry: scheme.ministry || 'Ministry of Housing and Urban Affairs (MoHUA)',
      schemeType: 'Credit-Linked Subsidy & Affordable Pucca Housing',
      targetBeneficiaries: 'Economically Weaker Section (EWS) & Low Income Groups (LIG)',
      coverage: 'Urban & Rural India (PMAY Pan-India)',
      officialWebsite: 'https://pmaymis.gov.in',
      helplineName: 'PMAY Citizen Grievance Cell',
      helplineNumber: '1800 11 6163 / 1800 11 3377',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'PMAY Operational Guidelines & Subsidy Norms (PDF)'
    };
  }

  // 10. Sukanya Samriddhi / Women Welfare
  if (id.includes('sukanya') || title.includes('sukanya') || cats.includes('women')) {
    return {
      ministry: scheme.ministry || 'Ministry of Finance & Department of Posts',
      schemeType: 'Government Sovereign Small Savings Scheme (Beti Bachao Beti Padhao)',
      targetBeneficiaries: 'Parents / Guardians of Girl Children (under 10 years)',
      coverage: 'All Post Offices & Authorized Bank Branches Across India',
      officialWebsite: 'https://www.indiapost.gov.in',
      helplineName: 'National Savings & Postal Helpline',
      helplineNumber: '1800 266 6868',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'Sukanya Samriddhi Account Rules (PDF)'
    };
  }

  // 11. Education & National Scholarships
  if (id.includes('scholarship') || id.includes('nsp') || title.includes('scholarship') || cats.includes('education')) {
    return {
      ministry: scheme.ministry || 'Ministry of Education & MeitY',
      schemeType: 'Direct Benefit Transfer (DBT) Scholarship Grant',
      targetBeneficiaries: 'Pre-Matric, Post-Matric & Higher Education Students',
      coverage: 'All Recognized Schools, Colleges & Universities Pan-India',
      officialWebsite: 'https://scholarships.gov.in',
      helplineName: 'National Scholarship Portal (NSP) Helpdesk',
      helplineNumber: '0120-6619540',
      helplineHours: '24×7 Technical Assistance Support',
      guidelinesTitle: 'NSP Central Guidelines & Document Verifier Manual (PDF)'
    };
  }

  // 12. Startup India Seed Fund
  if (id.includes('startup') || id.includes('seed-fund') || title.includes('startup')) {
    return {
      ministry: scheme.ministry || 'DPIIT, Ministry of Commerce and Industry',
      schemeType: 'Proof of Concept & Prototype Seed Grant',
      targetBeneficiaries: 'DPIIT Recognized Startups & Early-stage Founders',
      coverage: 'Incubators & Tech Hubs Pan-India',
      officialWebsite: 'https://seedfund.startupindia.gov.in',
      helplineName: 'Startup India Toll-Free Hub',
      helplineNumber: '1800 115 565',
      helplineHours: 'Toll-Free • Mon–Fri (10:00 AM – 5:30 PM)',
      guidelinesTitle: 'Startup India Seed Fund Guidelines (PDF)'
    };
  }

  // 13. Skill India / PMKVY
  if (id.includes('skill') || id.includes('pmkvy') || id.includes('naps') || cats.includes('youth')) {
    return {
      ministry: scheme.ministry || 'Ministry of Skill Development and Entrepreneurship',
      schemeType: 'Industry 4.0 Skill Certification & Assessment Award',
      targetBeneficiaries: 'School / College Dropouts & Unemployed Youth',
      coverage: 'Pradhan Mantri Kaushal Kendras (PMKK) Pan-India',
      officialWebsite: 'https://www.pmkvyofficial.org',
      helplineName: 'National Skill Development Helpdesk',
      helplineNumber: '1800 123 9626',
      helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
      guidelinesTitle: 'PMKVY Guidelines & Trade List (PDF)'
    };
  }

  // Default Central Government Fallback
  return {
    ministry: scheme.ministry || 'Government of India',
    schemeType: scheme.schemeTypes?.join(', ') || 'Central Government Welfare Scheme',
    targetBeneficiaries: 'Eligible Beneficiaries & Citizens',
    coverage: scheme.state || 'All India (Rural & Urban)',
    officialWebsite: 'https://india.gov.in',
    helplineName: 'National Citizen Service Helpdesk',
    helplineNumber: '1800 11 0001',
    helplineHours: 'Toll-Free • Mon–Sat (9:00 AM – 6:00 PM)',
    guidelinesTitle: `${scheme.title} Scheme Guidelines 2026 (PDF)`
  };
}

export default function SchemeDetailsPage() {
  const { schemeId = 'pmegp' } = useParams();
  const [activeTab, setActiveTab] = useState('overview');
  const [isSaved, setIsSaved] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('fin_bookmarks') || '[]');
      return saved.includes(schemeId);
    } catch (e) {
      return false;
    }
  });

  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [copyToast, setCopyToast] = useState(false);
  const [expandedStep, setExpandedStep] = useState(null);

  // Retrieve scheme details with alias tolerance or fallback
  const scheme =
    SCHEMES.find(
      (s) =>
        s.id === schemeId ||
        (schemeId === 'msme' && s.id === 'msme-financial-support') ||
        ((schemeId === 'pmkisan' || schemeId === 'PM-KISAN-2024') && s.id === 'pm-kisan') ||
        s.id.toLowerCase() === schemeId?.toLowerCase()
    ) || SCHEMES[0];
  const isPmegp = scheme.id === 'pmegp';
  const matchScore = scheme.matchScore || 96;

  // Dynamic official government portal, ministry, scheme type, and helpline details
  const portalDetails = useMemo(() => getSchemePortalDetails(scheme), [scheme]);

  // =========================================================================
  // INTERACTIVE SUBSIDY CALCULATOR STATE
  // =========================================================================
  const defaultCost = isPmegp ? 1000000 : (scheme.benefitValue ? Math.max(scheme.benefitValue * 3, 500000) : 500000);
  const [projectCost, setProjectCost] = useState(defaultCost);
  const [locationType, setLocationType] = useState('rural'); // 'rural' | 'urban'
  const [categoryType, setCategoryType] = useState('special'); // 'special' | 'general'

  // Dynamic calculations:
  // General: 15% Urban, 25% Rural (Own contribution 10%)
  // Special: 25% Urban, 35% Rural (Own contribution 5%)
  const subsidyPercent = useMemo(() => {
    if (categoryType === 'special') {
      return locationType === 'rural' ? 35 : 25;
    }
    return locationType === 'rural' ? 25 : 15;
  }, [locationType, categoryType]);

  const ownPercent = useMemo(() => {
    return categoryType === 'special' ? 5 : 10;
  }, [categoryType]);

  const loanPercent = useMemo(() => {
    return 100 - subsidyPercent - ownPercent;
  }, [subsidyPercent, ownPercent]);

  const subsidyAmount = Math.round((projectCost * subsidyPercent) / 100);
  const ownAmount = Math.round((projectCost * ownPercent) / 100);
  const loanAmount = Math.round((projectCost * loanPercent) / 100);

  // Monthly EMI estimation: 9% interest for 7 years (84 months)
  const estimatedEmi = useMemo(() => {
    const principal = loanAmount;
    if (principal <= 0) return 0;
    const monthlyRate = 0.09 / 12;
    const months = 84;
    const emi = (principal * monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1);
    return Math.round(emi);
  }, [loanAmount]);

  // =========================================================================
  // INTERACTIVE ELIGIBILITY CHECKLIST STATE
  // =========================================================================
  const [eligibilityChecks, setEligibilityChecks] = useState({
    age: true,
    education: true,
    greenfield: true,
    identity: true
  });

  const allEligible = Object.values(eligibilityChecks).every(Boolean);

  const toggleEligibility = (key) => {
    setEligibilityChecks((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Compact circular gauge calculations (radius 11 for 26px gauge)
  const gaugeRadius = 11;
  const gaugeCircumference = 2 * Math.PI * gaugeRadius;
  const gaugeOffset = gaugeCircumference - (gaugeCircumference * matchScore) / 100;

  const handleApplyClick = () => {
    setShowApplyModal(true);
  };

  const handleSaveToggle = () => {
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
    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 3500);
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
              {isPmegp ? (
                <img
                  src={ashokStambhVector}
                  alt="State Emblem of India"
                  className="scheme-emblem-img"
                  onError={(e) => {
                    e.currentTarget.src = ashokStambhGold;
                  }}
                />
              ) : (
                <SchemeLogo scheme={scheme} size={44} />
              )}
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
                    <span className="scheme-tag-item">Business Support</span>
                    <span className="scheme-tag-item">Self Employment</span>
                    <span className="scheme-tag-item">Central Government</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Header Cluster: Status, DBT, Match Score, Share & Print */}
          <div className="scheme-header-right-cluster">
            {/* Live Applications Open Status */}
            <div className="scheme-status-pill" title="Applications are actively accepted for FY 2025-26">
              <span className="status-live-dot" />
              <span>Applications Open (FY 2025–26)</span>
            </div>

            {/* DBT Direct Benefit Transfer Badge */}
            <div className="scheme-dbt-pill" title="Subsidy / Benefit released directly to Aadhaar-linked Bank Account">
              <ShieldCheck size={14} />
              <span>Direct Benefit Transfer</span>
            </div>

            {/* Compact Match Score Gauge Card */}
            <div className="scheme-match-gauge-box" title={`Your profile has a ${matchScore}% match for this scheme`}>
              <div className="scheme-gauge-svg-wrap">
                <svg className="scheme-gauge-svg" viewBox="0 0 26 26">
                  <circle
                    cx="13"
                    cy="13"
                    r={gaugeRadius}
                    fill="none"
                    stroke="#E5E7EB"
                    strokeWidth="2.8"
                  />
                  <circle
                    cx="13"
                    cy="13"
                    r={gaugeRadius}
                    fill="none"
                    stroke="#12B76A"
                    strokeWidth="2.8"
                    strokeDasharray={gaugeCircumference}
                    strokeDashoffset={gaugeOffset}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="scheme-gauge-center">
                  <span>{matchScore}%</span>
                </div>
              </div>
              <div className="scheme-gauge-meta">
                <span className="scheme-gauge-match-text">Match</span>
                <span className="scheme-gauge-subtext">Highly relevant</span>
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
            { id: 'source-rules', label: 'Source & Rules' }
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
                {/* Hero Banner Card with Official Government of India Graphic across ALL schemes */}
                <div className="scheme-hero-card">
                  <div className="scheme-hero-content">
                    <div>
                      <div className="scheme-hero-eyebrow">
                        {portalDetails.ministry}
                      </div>
                      <h3 className="scheme-hero-headline">
                        Turn Your
                        <br />
                        Entrepreneurial Dreams
                        <br />
                        into <span className="hero-highlight-green">Reality.</span>
                      </h3>
                      <p className="scheme-hero-desc">
                        {scheme.overview || scheme.description}
                      </p>
                    </div>

                    <div className="scheme-hero-quote-box">
                      <span className="scheme-hero-quote-mark">“</span>
                      <div className="scheme-hero-quote-text-wrap">
                        <span className="scheme-hero-quote-phrase">
                          "Empowering citizens, Strengthening Bharat."
                        </span>
                        <span className="scheme-hero-quote-author">
                          — {portalDetails.ministry}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Official Government of India Emblem & Insignia Graphic */}
                  <div className="scheme-hero-media">
                    <img
                      src={govtOfIndiaImg}
                      alt="भारत सरकार | Government of India"
                      className="scheme-hero-gov-img"
                    />
                    <div className="scheme-hero-stamp-badge">
                      <ShieldCheck size={12} />
                      <span>Official National Welfare Programme</span>
                    </div>
                  </div>
                </div>

                {/* INTERACTIVE SUBSIDY & REPAYMENT ESTIMATOR */}
                <div className="scheme-calculator-card">
                  <div className="calc-header-row">
                    <div className="calc-title-lockup">
                      <div className="calc-title-icon">
                        <Calculator size={15} />
                      </div>
                      <h4 className="calc-title-text">
                        Interactive Subsidy & Repayment Estimator
                      </h4>
                    </div>
                    <span className="calc-badge-live">Live Reactive Calculator</span>
                  </div>

                  {/* Calculator Controls */}
                  <div className="calc-controls-grid">
                    {/* Left Controls: Cost Slider & Presets */}
                    <div className="calc-control-group">
                      <div className="calc-control-label">
                        <span>Proposed Project Investment:</span>
                        <span className="calc-cost-display">{formatCurrency(projectCost)}</span>
                      </div>

                      <input
                        type="range"
                        min="50000"
                        max="5000000"
                        step="25000"
                        value={projectCost}
                        onChange={(e) => setProjectCost(Number(e.target.value))}
                        className="calc-range-slider"
                      />

                      <div className="calc-presets-chips">
                        {[200000, 500000, 1000000, 2500000, 5000000].map((amt) => (
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

                    {/* Right Controls: Location & Category Toggles */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div className="calc-control-group">
                        <label className="calc-control-label">Enterprise Location:</label>
                        <div className="calc-segmented-toggles">
                          <button
                            type="button"
                            onClick={() => setLocationType('rural')}
                            className={`calc-toggle-btn ${locationType === 'rural' ? 'active' : ''}`}
                          >
                            Rural (Higher Subsidy)
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
                  </div>

                  {/* Visual Segmented Progress Bar */}
                  <div className="calc-segment-bar-wrap">
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: '#667085' }}>
                      <span style={{ color: '#087443', fontWeight: 600 }}>● Govt Subsidy ({subsidyPercent}%)</span>
                      <span style={{ color: '#175CD3', fontWeight: 600 }}>● Bank Term Loan ({loanPercent}%)</span>
                      <span style={{ color: '#D97706', fontWeight: 600 }}>● Own Capital ({ownPercent}%)</span>
                    </div>

                    <div className="calc-multi-bar">
                      <div
                        className="bar-segment-subsidy"
                        style={{ width: `${subsidyPercent}%` }}
                        title={`Govt Subsidy: ${subsidyPercent}%`}
                      />
                      <div
                        className="bar-segment-loan"
                        style={{ width: `${loanPercent}%` }}
                        title={`Bank Loan: ${loanPercent}%`}
                      />
                      <div
                        className="bar-segment-own"
                        style={{ width: `${ownPercent}%` }}
                        title={`Own Investment: ${ownPercent}%`}
                      />
                    </div>
                  </div>

                  {/* Calculated Metric Cards */}
                  <div className="calc-metrics-row">
                    <div className="calc-metric-card highlight">
                      <span className="calc-metric-label">
                        <Coins size={12} color="#12B76A" />
                        <span>Govt Subsidy ({subsidyPercent}%)</span>
                      </span>
                      <span className="calc-metric-value">{formatCurrency(subsidyAmount)}</span>
                      <span className="calc-metric-sub">Non-repayable grant</span>
                    </div>

                    <div className="calc-metric-card">
                      <span className="calc-metric-label">
                        <Landmark size={12} color="#175CD3" />
                        <span>Bank Loan ({loanPercent}%)</span>
                      </span>
                      <span className="calc-metric-value">{formatCurrency(loanAmount)}</span>
                      <span className="calc-metric-sub">Low interest finance</span>
                    </div>

                    <div className="calc-metric-card">
                      <span className="calc-metric-label">
                        <User size={12} color="#D97706" />
                        <span>Your Funds ({ownPercent}%)</span>
                      </span>
                      <span className="calc-metric-value">{formatCurrency(ownAmount)}</span>
                      <span className="calc-metric-sub">Promoter margin money</span>
                    </div>

                    <div className="calc-metric-card">
                      <span className="calc-metric-label">
                        <Clock size={12} color="#667085" />
                        <span>Est. Monthly EMI</span>
                      </span>
                      <span className="calc-metric-value">{formatCurrency(estimatedEmi)}</span>
                      <span className="calc-metric-sub">at 9% for 7 years</span>
                    </div>
                  </div>
                </div>

                {/* Section: Key Benefits */}
                <div className="scheme-section-block">
                  <h3 className="scheme-section-heading">Key Benefits</h3>
                  <p className="scheme-section-subheading">
                    Financial support, subsidies and other benefits under {scheme.title}.
                  </p>

                  <div className="scheme-benefits-grid">
                    {/* Card 1: Margin Money Subsidy */}
                    <div className="scheme-benefit-card">
                      <div className="benefit-icon-badge green">
                        <Coins size={18} />
                      </div>
                      <h4 className="benefit-title">Margin Money Subsidy</h4>
                      <div className="benefit-highlight-val">{scheme.benefitAmount || 'Up to ₹1,25,000'}</div>
                      <p className="benefit-desc-note">Based on project cost and category</p>
                    </div>

                    {/* Card 2: Bank Loan Support */}
                    <div className="scheme-benefit-card">
                      <div className="benefit-icon-badge blue">
                        <Landmark size={18} />
                      </div>
                      <h4 className="benefit-title">Bank Loan Support</h4>
                      <div className="benefit-highlight-val">Up to 90% of project cost</div>
                      <p className="benefit-desc-note">Through eligible banks</p>
                    </div>

                    {/* Card 3: Self Employment */}
                    <div className="scheme-benefit-card">
                      <div className="benefit-icon-badge amber">
                        <Briefcase size={18} />
                      </div>
                      <h4 className="benefit-title">Self Employment</h4>
                      <div className="benefit-highlight-val">
                        Promotes self-reliance and jobs
                      </div>
                      <p className="benefit-desc-note">In rural and urban areas</p>
                    </div>

                    {/* Card 4: Employment Generation */}
                    <div className="scheme-benefit-card">
                      <div className="benefit-icon-badge purple">
                        <Users size={18} />
                      </div>
                      <h4 className="benefit-title">Employment Generation</h4>
                      <div className="benefit-highlight-val">
                        Sustainable livelihoods
                      </div>
                      <p className="benefit-desc-note">Supports Atmanirbhar Bharat</p>
                    </div>
                  </div>
                </div>

                {/* Section: Quick Highlights */}
                <div className="scheme-section-block">
                  <h3 className="scheme-section-heading">Quick Highlights</h3>

                  <div className="scheme-highlights-grid">
                    {/* Highlight 1: ₹10 Lakh */}
                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round blue">
                        <Banknote size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value">₹10 Lakh</span>
                        <span className="highlight-label">
                          Max project cost (Mfg)
                        </span>
                      </div>
                    </div>

                    {/* Highlight 2: ₹5 Lakh */}
                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round teal">
                        <Store size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value">₹5 Lakh</span>
                        <span className="highlight-label">
                          Max project cost (Service)
                        </span>
                      </div>
                    </div>

                    {/* Highlight 3: 25% – 35% */}
                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round purple">
                        <MapPin size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value">25% – 35%</span>
                        <span className="highlight-label">
                          Subsidy (varies by category)
                        </span>
                      </div>
                    </div>

                    {/* Highlight 4: 18+ Years */}
                    <div className="scheme-highlight-box">
                      <div className="highlight-icon-round amber">
                        <Clock size={15} />
                      </div>
                      <div className="highlight-text-wrap">
                        <span className="highlight-value">18+ Years</span>
                        <span className="highlight-label">Minimum age limit</span>
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
                  <h3 className="tab-panel-title">Who is Eligible for {scheme.title}?</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    Applicants must satisfy statutory eligibility norms. Test your eligibility live below:
                  </p>
                </div>

                {/* Live Interactive Eligibility Switcher */}
                <div className="interactive-test-banner">
                  <div>
                    <strong style={{ color: '#10243A', fontSize: '13.5px' }}>
                      Profile Match Verification:
                    </strong>
                    <div style={{ fontSize: '12px', color: '#475467', marginTop: '2px' }}>
                      Click on items to check your current eligibility status.
                    </div>
                  </div>

                  <span
                    style={{
                      padding: '4px 10px',
                      borderRadius: '8px',
                      fontSize: '12px',
                      fontWeight: 700,
                      backgroundColor: allEligible ? '#ECFDF3' : '#FEF3F2',
                      color: allEligible ? '#087443' : '#B42318',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {allEligible ? '✓ 100% Eligible to Apply' : '⚠ Action Needed for Eligibility'}
                  </span>
                </div>

                <div className="criteria-checklist">
                  {[
                    {
                      key: 'age',
                      title: 'Age Criteria (18+ Years)',
                      desc: 'Any Indian citizen above 18 years of age. There is no upper age limit for applying.'
                    },
                    {
                      key: 'education',
                      title: 'Educational Qualification (Standard VIII Pass)',
                      desc: 'At least 8th standard pass for projects costing above ₹10 Lakh in manufacturing and above ₹5 Lakh in business/service.'
                    },
                    {
                      key: 'greenfield',
                      title: 'Greenfield Venture (New Enterprise)',
                      desc: 'Assistance is available strictly for setting up new viable micro-enterprises. Existing units already receiving subsidy are ineligible.'
                    },
                    {
                      key: 'identity',
                      title: 'Valid Aadhaar & Seeded Bank Account',
                      desc: 'Valid Aadhaar credentials with active bank account details required for direct DBT subsidy disbursement.'
                    }
                  ].map((item) => (
                    <div
                      key={item.key}
                      onClick={() => toggleEligibility(item.key)}
                      className={`eligibility-toggle-row ${eligibilityChecks[item.key] ? 'checked' : ''}`}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <div
                          style={{
                            width: '20px',
                            height: '20px',
                            borderRadius: '5px',
                            backgroundColor: eligibilityChecks[item.key] ? '#005B50' : '#E5E7EB',
                            color: '#FFFFFF',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            marginTop: '2px',
                            flexShrink: 0
                          }}
                        >
                          {eligibilityChecks[item.key] && <Check size={14} />}
                        </div>
                        <div>
                          <strong style={{ color: '#10243A', fontSize: '13px' }}>
                            {item.title}:
                          </strong>{' '}
                          <span className="criteria-text">{item.desc}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ padding: '14px 18px', backgroundColor: '#FEF6EC', borderRadius: '10px', border: '1px solid #FADBB0' }}>
                  <h4 style={{ color: '#C56A00', fontSize: '13.5px', fontWeight: 700, margin: '0 0 4px 0' }}>
                    Special Category Priority Rate
                  </h4>
                  <p style={{ fontSize: '12.5px', color: '#475467', margin: 0, lineHeight: 1.5 }}>
                    SC, ST, OBC, Women, Minorities, Differently-Abled, Ex-servicemen, and Hill/Border area applicants qualify for <strong>higher subsidy rates (up to 35%)</strong> and lower promoter contribution (only 5%).
                  </p>
                </div>
              </div>
            )}

            {/* TAB: BENEFITS */}
            {activeTab === 'benefits' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Comprehensive Financial Benefits & Subsidies</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    PMEGP provides a structured combination of bank finance and government-funded Margin Money subsidy to minimize upfront capital risk.
                  </p>
                </div>

                <div className="subsidy-table-wrap">
                  <table className="subsidy-table">
                    <thead>
                      <tr>
                        <th>Beneficiary Category</th>
                        <th>Own Contribution</th>
                        <th>Rate of Subsidy (Urban)</th>
                        <th>Rate of Subsidy (Rural)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>
                          <strong>General Category</strong>
                        </td>
                        <td>10% of project cost</td>
                        <td>
                          <span style={{ color: '#005B50', fontWeight: 700 }}>15%</span>
                        </td>
                        <td>
                          <span style={{ color: '#005B50', fontWeight: 700 }}>25%</span>
                        </td>
                      </tr>
                      <tr>
                        <td>
                          <strong>Special Categories</strong>
                          <div style={{ fontSize: '11.5px', color: '#667085', marginTop: '2px' }}>
                            SC / ST / OBC / Minorities / Women / Ex-servicemen / Differently Abled
                          </div>
                        </td>
                        <td>
                          <span style={{ color: '#15803D', fontWeight: 700 }}>5% only</span>
                        </td>
                        <td>
                          <span style={{ color: '#005B50', fontWeight: 700 }}>25%</span>
                        </td>
                        <td>
                          <span style={{ color: '#005B50', fontWeight: 700 }}>35% (Maximum)</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
                  <div style={{ padding: '16px', backgroundColor: '#F0FDF4', borderRadius: '10px', border: '1px solid #BBF7D0' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#15803D' }}>Project Cost Ceilings</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#073B30', marginTop: '4px' }}>
                      ₹50 L / ₹20 L
                    </div>
                    <p style={{ fontSize: '12px', color: '#166534', margin: '4px 0 0 0' }}>
                      Up to ₹50 Lakh for manufacturing units and up to ₹20 Lakh for service enterprises.
                    </p>
                  </div>

                  <div style={{ padding: '16px', backgroundColor: '#EFF8FF', borderRadius: '10px', border: '1px solid #B2DDFF' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#175CD3' }}>Second Loan for Upgradation</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#10243A', marginTop: '4px' }}>
                      Up to ₹1 Crore
                    </div>
                    <p style={{ fontSize: '12px', color: '#1E40AF', margin: '4px 0 0 0' }}>
                      Existing high-performing units can apply for a secondary loan up to ₹1 Crore with 15–20% subsidy.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: DOCUMENTS */}
            {activeTab === 'documents' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Required Documents Checklist</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    FIN automatically verifies and synchronizes these documents from your digital repository.
                  </p>
                </div>

                <div className="criteria-checklist">
                  {[
                    {
                      name: 'Aadhaar Card (Identity & Residential Proof)',
                      status: 'Verified from FIN Profile',
                      mandatory: true
                    },
                    {
                      name: 'PAN Card (Permanent Account Number)',
                      status: 'Verified from FIN Profile',
                      mandatory: true
                    },
                    {
                      name: 'Detailed Project Report (DPR) / Business Feasibility Plan',
                      status: 'Ready in My Documents',
                      mandatory: true
                    },
                    {
                      name: 'Highest Educational Qualification Certificate (8th standard or higher)',
                      status: 'Ready',
                      mandatory: true
                    },
                    {
                      name: 'Caste / Community Certificate (for SC / ST / OBC category benefit)',
                      status: 'Optional if General Category',
                      mandatory: false
                    },
                    {
                      name: 'Rural Area Certificate from Tehsildar / Gram Panchayat',
                      status: 'Required for 25% – 35% rural subsidy claim',
                      mandatory: false
                    },
                    {
                      name: 'Bank Passbook & Cancelled Cheque with active IFSC code',
                      status: 'Ready',
                      mandatory: true
                    }
                  ].map((doc, idx) => (
                    <div
                      key={idx}
                      className="criteria-item"
                      style={{ justifyContent: 'space-between', alignItems: 'center' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <FileText size={16} color="#005B50" />
                        <div>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: '#10243A' }}>
                            {doc.name}
                          </span>
                          {doc.mandatory && (
                            <span style={{ marginLeft: '6px', fontSize: '11px', color: '#D92D20', fontWeight: 600 }}>
                              *Required
                            </span>
                          )}
                        </div>
                      </div>
                      <span
                        style={{
                          fontSize: '11.5px',
                          fontWeight: 500,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor: doc.status.includes('Verified') || doc.status.includes('Ready') ? '#ECFDF3' : '#F2F4F7',
                          color: doc.status.includes('Verified') || doc.status.includes('Ready') ? '#087443' : '#475467',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        {doc.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: HOW TO APPLY */}
            {activeTab === 'how-to-apply' && (
              <div className="scheme-tab-panel">
                <div>
                  <h3 className="tab-panel-title">Interactive Application Roadmap</h3>
                  <p className="tab-panel-desc" style={{ marginTop: '6px' }}>
                    Click on each phase below to inspect processing milestones and requirements:
                  </p>
                </div>

                <div className="application-roadmap">
                  {(isPmegp
                    ? [
                        {
                          step: '1',
                          title: 'Online Application on Official KVIC Portal',
                          time: '~1 Working Day',
                          desc: 'Register as an Individual or Non-Individual on kviconline.gov.in. Fill the e-form, enter proposed project costs, and select your preferred financing bank branch.'
                        },
                        {
                          step: '2',
                          title: 'District Task Force Committee (DTFC) Review',
                          time: '~7–10 Working Days',
                          desc: 'Your application is forwarded to the DTFC headed by the District Magistrate/Collector for preliminary technical scrutiny and suitability verification.'
                        },
                        {
                          step: '3',
                          title: 'Forwarding to Financing Bank Branch',
                          time: '~5 Working Days',
                          desc: 'Upon DTFC clearance, the application is transmitted electronically to your designated bank branch for credit and techno-economic appraisal.'
                        },
                        {
                          step: '4',
                          title: 'Sanction & First Loan Disbursement',
                          time: '~10 Working Days',
                          desc: 'Bank issues an in-principle sanction letter. You deposit the 5%–10% borrower contribution, and the bank releases the initial capital installment.'
                        },
                        {
                          step: '5',
                          title: 'Mandatory EDP Entrepreneurship Training',
                          time: '~5–10 Days Training',
                          desc: 'Complete the mandatory 5–10 day Entrepreneurship Development Programme (EDP) training conducted by certified MSME / KVIC institutes (available online).'
                        },
                        {
                          step: '6',
                          title: 'Margin Money Subsidy Credited',
                          time: 'Direct DBT',
                          desc: 'Financing bank uploads the subsidy claim on the online portal. KVIC transfers the Margin Money into a 3-year term deposit in your bank account, adjusted against loan principal on completion.'
                        }
                      ]
                    : [
                        {
                          step: '1',
                          title: `Online Registration on Official Portal`,
                          time: '~1 Working Day',
                          desc: `Visit the official national portal (${portalDetails.officialWebsite}). Complete your Aadhaar-based e-KYC and initiate the fresh scheme application form.`
                        },
                        {
                          step: '2',
                          title: 'Document Upload & Land / Identity Verification',
                          time: '~3–5 Working Days',
                          desc: 'Upload requisite proof of identification, income / caste certificate, and land records or enterprise registration for institutional scrutiny.'
                        },
                        {
                          step: '3',
                          title: 'District / State Level Administrative Review',
                          time: '~7–10 Working Days',
                          desc: `Designated nodal officers under ${portalDetails.ministry} conduct automated cross-verification of data through PFMS and departmental records.`
                        },
                        {
                          step: '4',
                          title: 'Field Level Inspection & Bank Validation',
                          time: '~5 Working Days',
                          desc: 'Verification of active beneficiary bank account seeded with Aadhaar and confirmation of compliance against eligibility norms.'
                        },
                        {
                          step: '5',
                          title: 'Final Approval & Beneficiary List Enrolment',
                          time: '~3 Working Days',
                          desc: 'Formal sanction order issued with a unique Government Beneficiary Tracking ID for tracking future disbursement cycles.'
                        },
                        {
                          step: '6',
                          title: 'Direct Benefit Transfer (DBT) Release',
                          time: 'Direct DBT',
                          desc: 'Financial support / subsidy is disbursed directly to your Aadhaar-linked bank account under DBT protocols with zero middleman deductions.'
                        }
                      ]
                  ).map((s) => (
                    <div
                      key={s.step}
                      onClick={() => setExpandedStep(expandedStep === s.step ? null : s.step)}
                      className={`roadmap-step-item ${expandedStep === s.step ? 'expanded' : ''}`}
                    >
                      <div className="step-num-circle">{s.step}</div>
                      <div className="step-content">
                        <div className="step-name">
                          <span>{s.title}</span>
                          <span style={{ fontSize: '11px', color: '#005B50', fontWeight: 600 }}>
                            {s.time}
                          </span>
                        </div>
                        <p className="step-detail">{s.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
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
                      {isPmegp ? (
                        <>
                          <li>Khadi and Village Industries Commission (KVIC)</li>
                          <li>State Khadi & Village Industries Boards (KVIB)</li>
                          <li>District Industries Centres (DICs) in respective states</li>
                          <li>Coir Board for coir-related units</li>
                        </>
                      ) : (
                        <>
                          <li>{portalDetails.ministry}</li>
                          <li>State & District Level Department Nodal Cells</li>
                          <li>National Informatics Centre (NIC) Portal Wing</li>
                          <li>Common Service Centres (CSCs) & Seva Kendras</li>
                        </>
                      )}
                    </ul>
                  </div>

                  <div style={{ padding: '16px', backgroundColor: '#F8FAFC', borderRadius: '10px', border: '1px solid #EAECF0' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Landmark size={16} color="#005B50" />
                      <h4 style={{ margin: 0, fontSize: '13.5px', color: '#10243A' }}>Financing Institutions</h4>
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12.5px', color: '#475467', lineHeight: 1.6 }}>
                      <li>All 12 Public Sector Commercial Banks (SBI, PNB, BoB, etc.)</li>
                      <li>Regional Rural Banks (RRBs)</li>
                      <li>Co-operative Banks approved by State Task Force</li>
                      <li>Scheduled Private Commercial Banks with RBI license</li>
                    </ul>
                  </div>
                </div>

                <div style={{ padding: '14px 18px', backgroundColor: '#F0FDF4', borderRadius: '10px', border: '1px solid #DCFCE7' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                    <div>
                      <h5 style={{ margin: 0, fontSize: '13.5px', color: '#073B30', fontWeight: 700 }}>
                        Official Ministry Portal & Guidelines Repository
                      </h5>
                      <span style={{ fontSize: '12px', color: '#15803D' }}>
                        {portalDetails.ministry}: {portalDetails.officialWebsite}
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
                      <span>Visit Portal</span>
                      <ExternalLink size={13} />
                    </a>
                  </div>
                </div>
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
                {scheme.benefitAmount || '₹1,25,000'}
              </div>

              <div className="support-amount-sub" title="Official financial benefit structure">
                <span>
                  {isPmegp
                    ? '(Margin Money Subsidy)'
                    : scheme.benefitSubtitle
                    ? `(${scheme.benefitSubtitle})`
                    : '(Direct Financial Benefit)'}
                </span>
                <Info size={13} style={{ cursor: 'pointer', color: '#98A2B3' }} />
              </div>

              <button
                type="button"
                onClick={handleApplyClick}
                className="btn-apply-main"
              >
                <span>Apply Now</span>
                <ArrowRight size={15} />
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
                  <a
                    href={portalDetails.officialWebsite}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="meta-item-value meta-website-link"
                  >
                    {portalDetails.officialWebsite}
                  </a>
                </div>
              </div>
            </div>

            {/* Card 3: Application Timelines & Milestones (Fills Bottom Right) */}
            <div className="scheme-timeline-card">
              <div className="sidebar-card-header">
                <Calendar size={15} color="#005B50" />
                <span>Application Cycle & Timelines</span>
              </div>

              <div className="timeline-list">
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Portal Registration:</span>
                  <span className="timeline-item-val" style={{ color: '#087443' }}>Open 24×7 (All Year)</span>
                </div>
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Bank Scrutiny:</span>
                  <span className="timeline-item-val">~7 to 10 Working Days</span>
                </div>
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Subsidy Release:</span>
                  <span className="timeline-item-val">100% DBT Deposit</span>
                </div>
                <div className="timeline-row-item">
                  <span className="timeline-item-label">Grievance SLA:</span>
                  <span className="timeline-item-val">Within 48 Hours</span>
                </div>
              </div>
            </div>

            {/* Card 4: Download Official Guidelines */}
            <div className="scheme-guidelines-box">
              <div className="guidelines-left">
                <div className="guidelines-icon-sq">
                  <FileText size={16} />
                </div>
                <div className="guidelines-text">
                  <h4 className="guidelines-title">Download Official Guidelines</h4>
                  <p className="guidelines-sub">{portalDetails.guidelinesTitle}</p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDownloadGuidelines}
                className="guidelines-download-btn"
                title={`Download ${portalDetails.guidelinesTitle}`}
                aria-label="Download Guidelines"
              >
                <Download size={15} />
              </button>
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
                <span>Downloading {portalDetails.guidelinesTitle}...</span>
              </div>
            )}

            {/* Card 5: Official Helplines & Support Desk (Fills Bottom Right) */}
            <div className="scheme-helpdesk-card">
              <div className="helpdesk-header">
                <PhoneCall size={14} color="#005B50" />
                <span>{portalDetails.helplineName}</span>
              </div>
              <div className="helpdesk-number">
                {portalDetails.helplineNumber}
              </div>
              <div className="helpdesk-hours">
                {portalDetails.helplineHours}
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

              <p style={{ fontSize: '13px', color: '#475467', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                Your FIN profile has a <strong>{matchScore}% match</strong>. Calculated estimated subsidy:{' '}
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
                <a
                  href={portalDetails.officialWebsite}
                  target="_blank"
                  rel="noopener noreferrer"
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
                  <span>Go to Official Portal</span>
                  <ExternalLink size={14} />
                </a>
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
