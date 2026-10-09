import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Info,
  Shield,
  Users,
  Mail,
  X as CloseIcon,
  HelpCircle,
  FileText,
  ExternalLink,
  PhoneCall,
  MapPin,
  CheckCircle2
} from 'lucide-react';
import tricolorFlagClean from '../../assets/tricolor_flag_clean.png';
import ashokStambhSvg from '../../assets/ashok_stambh_vector.svg';

const MODAL_CONTENT = {
  about: {
    badge: 'Institutional Mission',
    title: 'About FIN — Financial Policy Intelligence',
    subtitle: 'National Welfare Architecture & Citizen Policy Delivery',
    content: (
      <>
        <p>
          <strong>FIN (Financial Policy Intelligence)</strong> is a state-of-the-art sovereign welfare discovery platform designed to connect every citizen of India with their entitled government welfare schemes, direct financial subsidies, and developmental opportunities.
        </p>
        <h4>Core Mandates</h4>
        <ul>
          <li><strong>Algorithmic Policy Matching:</strong> Real-time deterministic evaluation of Central and State scheme eligibility across age, caste, gender, income, and occupation criteria.</li>
          <li><strong>Zero Citizen Exclusion:</strong> Reducing administrative friction and eliminating documentation barriers through assisted intelligence and document verification.</li>
          <li><strong>Fiscal Transparency:</strong> Providing accurate benefit estimations, statutory DBT disbursements, and transparent application tracking.</li>
        </ul>
        <p>
          Governed under Digital Public Infrastructure (DPI) guidelines, FIN functions as an institutional bridge between policy makers and 1.4 billion citizens across all States and Union Territories.
        </p>
      </>
    )
  },
  howItWorks: {
    badge: 'Operational Flow',
    title: 'How FIN Works',
    subtitle: 'From Citizen Profile to Verified Scheme Entitlements',
    content: (
      <>
        <p>FIN operates a 4-stage transparent intelligence pipeline:</p>
        <h4>1. Profile Calibration</h4>
        <p>Citizens input verified demographic data including state of domicile, annual household income, social category, and occupation.</p>
        <h4>2. Deterministic Rule Engine</h4>
        <p>Our rule engine evaluates eligibility rules across thousands of Central and State gazetted policies without human bias or delay.</p>
        <h4>3. Document Readiness Audit</h4>
        <p>Uploaded documents (Aadhaar, Income Certificates, Ration Cards, Caste Certificates) are analyzed for statutory readiness, ensuring applications never get rejected for missing paperwork.</p>
        <h4>4. Direct Application Tracking</h4>
        <p>Applicants receive step-by-step guidance, application cycle checkpoints, and official department portal links for seamless final submission.</p>
      </>
    )
  },
  guidelines: {
    badge: 'Statutory Guidelines',
    title: 'Scheme Guidelines & Framework',
    subtitle: 'Official Standards for Central and State Welfare Programs',
    content: (
      <>
        <p>
          All welfare schemes cataloged on FIN adhere to gazetted notifications issued by respective Central Ministries and State Government Departments.
        </p>
        <h4>Verification Benchmarks</h4>
        <ul>
          <li><strong>Income Categorization:</strong> Benchmarked against state-specific non-creamy layer, BPL, and EWS guidelines.</li>
          <li><strong>Direct Benefit Transfer (DBT):</strong> Verified Aadhaar-seeded bank account requirements for direct electronic disbursal.</li>
          <li><strong>Reservation & Affirmative Action:</strong> Alignment with statutory certificates issued by competent revenue authorities.</li>
        </ul>
        <p>
          For specific scheme guidelines, please consult the detailed criteria available on the respective scheme profile page or contact the nodal department desk.
        </p>
      </>
    )
  },
  contact: {
    badge: 'Helpdesk & Support',
    title: 'Contact FIN Institutional Desk',
    subtitle: 'National Helpdesk, Ministry Coordination & Grievance Cell',
    content: (
      <>
        <p>
          Our dedicated citizen support team is available to assist with eligibility verification, portal navigation, and technical queries.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', margin: '12px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <PhoneCall size={20} color="#005B50" />
            <div>
              <strong>Toll-Free Helpline:</strong>{' '}
              <a href="tel:1800113464" style={{ color: '#005B50', fontWeight: 600, textDecoration: 'none' }}>
                1800-11-FIN-GOV (1800-11-3464)
              </a>
              <div style={{ fontSize: '12px', color: '#667085' }}>Operating Hours: Mon–Sat, 9:00 AM to 6:00 PM IST</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Mail size={20} color="#005B50" />
            <div>
              <strong>Official Email:</strong>{' '}
              <a href="mailto:support@fin.gov.in" style={{ color: '#005B50', fontWeight: 600, textDecoration: 'none' }}>
                support@fin.gov.in / helpdesk@fin.gov.in
              </a>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <MapPin size={20} color="#005B50" style={{ marginTop: '2px' }} />
            <div>
              <strong>Secretariat Address:</strong>
              <div style={{ fontSize: '13px', color: '#475467' }}>
                Financial Policy Intelligence Directorate<br />
                Central Secretariat, Rajpath Area, New Delhi - 110001
              </div>
            </div>
          </div>
        </div>
      </>
    )
  },
  faq: {
    badge: 'Help & FAQs',
    title: 'Frequently Asked Questions (FAQs)',
    subtitle: 'Official Guidance on Scheme Eligibility, Documents & Subsidies',
    content: (
      <>
        <h4>1. How does FIN determine my scheme eligibility?</h4>
        <p>
          FIN evaluates your demographic profile—including state of domicile, annual household income, social category, and occupation—against canonical gazetted scheme rules using a deterministic, rule-based matching engine.
        </p>
        <h4>2. Is FIN an official welfare intelligence service?</h4>
        <p>
          Yes. Governed under Digital Public Infrastructure (DPI) guidelines, FIN functions as an institutional bridge aggregating verified Central and State government welfare notifications.
        </p>
        <h4>3. How do I verify my documents for a scheme?</h4>
        <p>
          Navigate to the <Link to="/documents" style={{ color: '#005B50', fontWeight: 600 }}>My Documents</Link> vault to upload statutory certificates (Aadhaar, Income Certificate, Caste Certificate, Ration Card). The platform audits document readiness to prevent application rejection.
        </p>
        <h4>4. Are financial benefits disbursed directly?</h4>
        <p>
          All eligible cash subsidies and financial grants are transferred electronically into your Aadhaar-seeded bank account through the Direct Benefit Transfer (DBT) framework.
        </p>
        <h4>5. What should I do if an application requires attention?</h4>
        <p>
          Visit the <Link to="/applications" style={{ color: '#005B50', fontWeight: 600 }}>Applications Tracker</Link> for real-time progress updates. If a nodal department flags missing documents, upload them in My Documents and follow the direct portal link.
        </p>
      </>
    )
  },
  terms: {
    badge: 'Legal Terms',
    title: 'Terms of Use',
    subtitle: 'Terms Governing Citizen Access and Platform Services',
    content: (
      <>
        <p>
          By accessing and using FIN (Financial Policy Intelligence), you agree to comply with the terms, statutory conditions, and data handling protocols outlined herein.
        </p>
        <h4>Key Terms</h4>
        <ul>
          <li><strong>Accuracy of Information:</strong> Users are responsible for providing authentic and lawful demographic data when computing scheme eligibility.</li>
          <li><strong>Informational Nature:</strong> Scheme recommendations and eligibility indicators computed by FIN represent deterministic algorithmic matching based on public rules. Final approval is subject to verification by implementing government authorities.</li>
          <li><strong>Authorized Use:</strong> The platform may not be scraped, probed, or utilized for unlawful commercial exploitation.</li>
        </ul>
      </>
    )
  },
  privacy: {
    badge: 'Data Protection',
    title: 'Privacy Policy',
    subtitle: 'Citizen Data Safeguards & Digital Personal Data Protection Compliance',
    content: (
      <>
        <p>
          FIN strictly complies with the <em>Digital Personal Data Protection Act (DPDP)</em> and Indian sovereign cybersecurity standards.
        </p>
        <h4>Data Governance Standards</h4>
        <ul>
          <li><strong>Zero Commercial Monetization:</strong> Citizen profile information is never sold, leased, or shared with commercial entities.</li>
          <li><strong>Encrypted In-Transit & At-Rest:</strong> All document uploads and verification pipelines use AES-256 encryption.</li>
          <li><strong>Consent-Driven Processing:</strong> Data is analyzed solely for the purpose of identifying eligible welfare benefits requested by the citizen.</li>
        </ul>
      </>
    )
  },
  disclaimer: {
    badge: 'Statutory Notice',
    title: 'Legal Disclaimer',
    subtitle: 'Statutory Notice Regarding Scheme Rules and Government Disbursals',
    content: (
      <>
        <p>
          The information contained on the FIN platform is aggregated from gazetted Central and State Government scheme documents and public notifications.
        </p>
        <p>
          While every care is taken to ensure accuracy and real-time synchronization, scheme terms, funding allocations, and operational guidelines are determined solely by the respective administrative Ministries and State Departments.
        </p>
        <p>
          FIN shall not be held liable for discrepancies arising from recent policy amendments not yet notified in official ministerial gazettes.
        </p>
      </>
    )
  },
  accessibility: {
    badge: 'Inclusion & Standards',
    title: 'Accessibility Statement',
    subtitle: 'Commitment to Universal Web Accessibility for All Citizens',
    content: (
      <>
        <p>
          FIN is engineered to ensure seamless accessibility for all citizens, including individuals with visual, auditory, cognitive, and motor impairments.
        </p>
        <h4>Conformity & Features</h4>
        <ul>
          <li><strong>WCAG 2.1 Level AA Conformity:</strong> Strict contrast ratios, semantic HTML5 elements, and keyboard navigability across all views.</li>
          <li><strong>Screen Reader Compatibility:</strong> Standard ARIA landmark labels, accessible headings, and image alt text.</li>
          <li><strong>Responsive Scaling:</strong> Adaptive layouts maintaining 100% clarity from mobile devices to ultra-wide desktop monitors.</li>
        </ul>
      </>
    )
  },
  cookies: {
    badge: 'Session Security',
    title: 'Cookie & Session Policy',
    subtitle: 'Transparent Session Tokens & Security Cookies',
    content: (
      <>
        <p>
          FIN uses strictly necessary session cookies and encrypted local storage tokens to preserve user authentication, state security, and language preferences.
        </p>
        <h4>Types of Cookies Used</h4>
        <ul>
          <li><strong>Authentication Tokens:</strong> Secure JWT credentials maintaining authenticated access across routes.</li>
          <li><strong>Session State:</strong> Temporary tokens used to prevent session timeout during document uploads.</li>
          <li><strong>Zero Tracking:</strong> No third-party behavioral advertising or cross-site tracking cookies are deployed on this platform.</li>
        </ul>
      </>
    )
  },
  sitemap: {
    badge: 'Directory Index',
    title: 'Portal Sitemap',
    subtitle: 'Comprehensive Index of FIN Public and Authenticated Routes',
    content: (
      <>
        <p>Quick access to all principal portals and modules within FIN:</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '10px' }}>
          <div>
            <strong>Core Services:</strong>
            <ul>
              <li><Link to="/dashboard" style={{ color: '#005B50' }}>Citizen Dashboard</Link></li>
              <li><Link to="/discover" style={{ color: '#005B50' }}>Discover All Schemes</Link></li>
              <li><Link to="/suggested-schemes" style={{ color: '#005B50' }}>Suggested Opportunities</Link></li>
              <li><Link to="/documents" style={{ color: '#005B50' }}>My Documents Vault</Link></li>
              <li><Link to="/applications" style={{ color: '#005B50' }}>Application Tracker</Link></li>
            </ul>
          </div>
          <div>
            <strong>Citizen Account:</strong>
            <ul>
              <li><Link to="/profile" style={{ color: '#005B50' }}>Citizen Profile & Demographics</Link></li>
              <li><Link to="/signup" style={{ color: '#005B50' }}>Account Registration</Link></li>
              <li><Link to="/login" style={{ color: '#005B50' }}>Secure Portal Login</Link></li>
            </ul>
          </div>
        </div>
      </>
    )
  }
};

export default function Footer({ isAtEnd = false }) {
  const [activeModalKey, setActiveModalKey] = useState(null);
  const [isSynced, setIsSynced] = useState(false);
  const footerRef = React.useRef(null);
  const isSyncedRef = React.useRef(false);

  useEffect(() => {
    let ticking = false;

    const checkSync = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollBottom = window.innerHeight + window.scrollY;
          const docHeight = document.documentElement.scrollHeight;
          // Document bottom detection
          const atDocBottom = scrollBottom >= docHeight - 35;

          // Footer element alignment detection
          let footerAtBottom = false;
          if (footerRef.current) {
            const rect = footerRef.current.getBoundingClientRect();
            // The footer bottom meets or is within bottom edge of viewport
            footerAtBottom = rect.bottom <= window.innerHeight + 15 && rect.top < window.innerHeight;
          }

          const currentlyAtBottom = Boolean(atDocBottom || footerAtBottom || isAtEnd);

          if (currentlyAtBottom && !isSyncedRef.current) {
            isSyncedRef.current = true;
            setIsSynced(true);
          } else if (!currentlyAtBottom && isSyncedRef.current) {
            // Hysteresis of 60px before resetting so micro-scroll doesn't jitter
            let distanceAbove = 0;
            if (footerRef.current) {
              const rect = footerRef.current.getBoundingClientRect();
              distanceAbove = rect.bottom - window.innerHeight;
            } else {
              distanceAbove = docHeight - scrollBottom;
            }
            if (distanceAbove > 60) {
              isSyncedRef.current = false;
              setIsSynced(false);
            }
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', checkSync, { passive: true });
    window.addEventListener('resize', checkSync, { passive: true });
    checkSync();

    return () => {
      window.removeEventListener('scroll', checkSync);
      window.removeEventListener('resize', checkSync);
    };
  }, [isAtEnd]);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveModalKey(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const openModal = (key) => {
    setActiveModalKey(key);
  };

  const closeModal = () => {
    setActiveModalKey(null);
  };

  const handleOpenAssistant = () => {
    window.dispatchEvent(new CustomEvent('open_fin_chat'));
  };

  const activeModal = activeModalKey ? MODAL_CONTENT[activeModalKey] : null;

  return (
    <footer
      ref={footerRef}
      className={`site-footer ${isSynced ? 'is-synced' : ''}`}
      role="contentinfo"
      aria-label="FIN Institutional Footer"
    >
      {/* 1. Top subtle horizontal divider with centered Indian tricolor accent */}
      <div className="footer-top-divider">
        <div className="footer-top-divider-line" aria-hidden="true" />
        <div className="footer-top-flag-badge" aria-label="National Tricolor">
          <img
            src={tricolorFlagClean}
            alt="National Tricolor Badge"
            className="footer-top-flag-img"
          />
        </div>
        <div className="footer-sync-top-line" aria-hidden="true" />
      </div>

      {/* 2. Main 5-column content with integrated panoramic building background */}
      <div className="footer-body-wrapper">
        <div className="footer-building-backdrop" aria-hidden="true">
          <div className="footer-sync-sweep-light" aria-hidden="true" />
        </div>

        <div className="footer-content-container">
          <div className="footer-grid-5cols">
            {/* COLUMN 1: FIN Brand Lockup & Government Quote */}
            <div className="footer-col footer-col-brand">
              <Link to="/dashboard" className="footer-brand-link" title="FIN — Financial Policy Intelligence (Return to Dashboard)">
                <div className="footer-brand-lockup">
                  <div className="footer-brand-title-row">
                    <span className="footer-brand-title">FIN</span>
                    <svg
                      width="34"
                      height="23"
                      viewBox="0 0 44 30"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      className="footer-brand-tricolor-wave"
                      aria-hidden="true"
                    >
                      <defs>
                        <linearGradient id="finFootSaffron" x1="0%" y1="100%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#E65100" />
                          <stop offset="50%" stopColor="#F97316" />
                          <stop offset="100%" stopColor="#FB923C" />
                        </linearGradient>
                        <linearGradient id="finFootWhite" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#F1F5F9" />
                          <stop offset="50%" stopColor="#FFFFFF" />
                          <stop offset="100%" stopColor="#E2E8F0" />
                        </linearGradient>
                        <linearGradient id="finFootGreen" x1="0%" y1="100%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#047857" />
                          <stop offset="50%" stopColor="#059669" />
                          <stop offset="100%" stopColor="#10B981" />
                        </linearGradient>
                      </defs>
                      <path
                        d="M2 13.5 C 9 16.5, 18 10, 28 6.5 C 34 4.5, 39 3, 42 2 C 39.5 5.5, 31 10, 23 13 C 15 16, 7 19.5, 2 17.5 Z"
                        fill="url(#finFootSaffron)"
                      />
                      <path
                        d="M2 18 C 9 20.8, 18 14.5, 28 11.2 C 34 9.2, 39 7.8, 42 6.8 C 39.5 10, 31 14.2, 23 17.2 C 15 20.2, 7 23.5, 2 21.5 Z"
                        fill="url(#finFootWhite)"
                      />
                      <circle cx="21.5" cy="14" r="2.8" stroke="#003366" strokeWidth="0.75" fill="#FFFFFF" />
                      <circle cx="21.5" cy="14" r="0.8" fill="#003366" />
                      <path d="M21.5 11.6 V16.4 M19.1 14 H23.9" stroke="#003366" strokeWidth="0.4" />
                      <path
                        d="M2 22.5 C 9 25.2, 18 19, 28 15.8 C 34 13.8, 39 12.4, 42 11.5 C 39.5 14.8, 31 18.8, 23 21.8 C 15 24.8, 7 28, 2 26 Z"
                        fill="url(#finFootGreen)"
                      />
                    </svg>
                  </div>
                  <span className="footer-brand-subtitle">Financial Policy Intelligence</span>
                  <div className="footer-brand-tricolor-accent" aria-hidden="true" />
                </div>
              </Link>
            </div>

            {/* COLUMN 2: Explore */}
            <div className="footer-col">
              <h3 className="footer-col-header">
                <BookOpen size={18} className="footer-col-icon" aria-hidden="true" />
                <span>Explore</span>
              </h3>
              <ul className="footer-nav-list">
                <li><Link to="/dashboard" className="footer-link">Dashboard</Link></li>
                <li><Link to="/discover" className="footer-link">Discover Schemes</Link></li>
                <li><Link to="/suggested-schemes" className="footer-link">Suggested Schemes</Link></li>
                <li><Link to="/documents" className="footer-link">My Documents</Link></li>
                <li><Link to="/applications" className="footer-link">Applications</Link></li>
              </ul>
            </div>

            {/* COLUMN 3: Information */}
            <div className="footer-col">
              <h3 className="footer-col-header">
                <Info size={18} className="footer-col-icon" aria-hidden="true" />
                <span>Information</span>
              </h3>
              <ul className="footer-nav-list">
                <li>
                  <button type="button" onClick={() => openModal('about')} className="footer-link-btn">
                    About FIN
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('howItWorks')} className="footer-link-btn">
                    How It Works
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('guidelines')} className="footer-link-btn">
                    Scheme Guidelines
                  </button>
                </li>
                <li>
                  <button type="button" onClick={handleOpenAssistant} className="footer-link-btn">
                    Help & Support
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('faq')} className="footer-link-btn">
                    FAQs
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('contact')} className="footer-link-btn">
                    Contact Us
                  </button>
                </li>
              </ul>
            </div>

            {/* COLUMN 4: Legal */}
            <div className="footer-col">
              <h3 className="footer-col-header">
                <Shield size={18} className="footer-col-icon" aria-hidden="true" />
                <span>Legal</span>
              </h3>
              <ul className="footer-nav-list">
                <li>
                  <button type="button" onClick={() => openModal('terms')} className="footer-link-btn">
                    Terms of Use
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('privacy')} className="footer-link-btn">
                    Privacy Policy
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('disclaimer')} className="footer-link-btn">
                    Disclaimer
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('accessibility')} className="footer-link-btn">
                    Accessibility
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('cookies')} className="footer-link-btn">
                    Cookie Policy
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => openModal('sitemap')} className="footer-link-btn">
                    Sitemap
                  </button>
                </li>
              </ul>
            </div>

            {/* COLUMN 5: Stay Connected */}
            <div className="footer-col footer-col-connected">
              <h3 className="footer-col-header">
                <Users size={18} className="footer-col-icon" aria-hidden="true" />
                <span>Stay Connected</span>
              </h3>
              <p className="footer-connected-desc">
                Get the latest updates on government schemes and policy intelligence.
              </p>
              <div className="footer-social-row">
                {/* X (formerly Twitter) */}
                <a
                  href="https://x.com/mygovindia"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-social-btn social-x"
                  aria-label="Follow FIN on X (formerly Twitter)"
                  title="FIN on X (@mygovindia)"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </a>
                {/* LinkedIn */}
                <a
                  href="https://www.linkedin.com/company/digital-india"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-social-btn social-linkedin"
                  aria-label="Connect with FIN on LinkedIn"
                  title="FIN on LinkedIn (Digital India)"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                  </svg>
                </a>
                {/* YouTube */}
                <a
                  href="https://www.youtube.com/@MyGovIndia"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-social-btn social-youtube"
                  aria-label="Subscribe to FIN on YouTube"
                  title="FIN on YouTube (@MyGovIndia)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                </a>
                {/* Email */}
                <a
                  href="mailto:support@fin.gov.in"
                  className="footer-social-btn social-email"
                  aria-label="Email FIN Institutional Support"
                  title="support@fin.gov.in"
                >
                  <Mail size={16} />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Dark deep-green sovereign bottom bar */}
      <div className="footer-bottom-bar">
        <div className="footer-bottom-sync-sweep" aria-hidden="true" />
        <div className="footer-bottom-bar-inner">
          <div className="footer-bottom-left">
            <span>© 2026 FIN – Financial Policy Intelligence. All rights reserved.</span>
          </div>

          <div className="footer-bottom-divider" aria-hidden="true" />

          <div className="footer-bottom-center">
            <img
              src={ashokStambhSvg}
              alt="State Emblem of India"
              className="footer-bottom-emblem"
            />
            <span className="footer-bottom-initiative">
              An initiative towards a more inclusive and informed India.
            </span>
          </div>

          <div className="footer-bottom-divider" aria-hidden="true" />

          <div className="footer-bottom-right">
            <div className="footer-bharat-tricolor-line" aria-hidden="true" />
            <span className="footer-bharat-tagline">
              <strong className="footer-bharat-bold">Bharat</strong> for a brighter tomorrow.
            </span>
          </div>
        </div>
      </div>

      {/* 4. Institutional Information / Legal Modal */}
      {activeModal && (typeof document !== 'undefined' ? (
        createPortal(
          <div
            className="footer-modal-backdrop"
            onClick={closeModal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="footer-modal-title"
          >
            <div
              className="footer-modal-card"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="footer-modal-header">
                <div className="footer-modal-header-text">
                  <span className="footer-modal-badge">
                    <CheckCircle2 size={13} />
                    <span>{activeModal.badge}</span>
                  </span>
                  <h3 id="footer-modal-title" className="footer-modal-title">
                    {activeModal.title}
                  </h3>
                  <span className="footer-modal-subtitle">{activeModal.subtitle}</span>
                </div>
                <button
                  type="button"
                  onClick={closeModal}
                  className="footer-modal-close-btn"
                  aria-label="Close modal dialog"
                >
                  <CloseIcon size={20} />
                </button>
              </div>

              <div
                className="footer-modal-body"
                onClick={(e) => {
                  if (e.target.closest('a')) closeModal();
                }}
              >
                {activeModal.content}
              </div>

              <div className="footer-modal-footer">
                <button
                  type="button"
                  onClick={closeModal}
                  className="footer-modal-btn-primary"
                >
                  Close
                </button>
              </div>
            </div>
          </div>,
          document.body
        )
      ) : null)}
    </footer>
  );
}
