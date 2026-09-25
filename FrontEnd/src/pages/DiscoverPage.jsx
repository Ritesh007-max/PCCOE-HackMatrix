import React, { useState, useMemo, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  SlidersHorizontal,
  ArrowRight,
  Bookmark,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ChevronDown,
  X,
  ShieldCheck,
  RotateCcw
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import { CATEGORIES, SCHEMES, SCHEME_TYPES } from '../data/schemesData';
import SchemeLogo from '../components/schemes/SchemeLogo';

import indiaGateHero from '../assets/india_gate_hero.jpg';
import tricolorFlagPerfect from '../assets/tricolor_flag_perfect.png';

export default function DiscoverPage() {
  // --------------------------------------------------------------------------
  // Filter States
  // --------------------------------------------------------------------------
  const [activeCategoryPill, setActiveCategoryPill] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedAgeGroup, setSelectedAgeGroup] = useState('');
  const [selectedIncomeRange, setSelectedIncomeRange] = useState('');
  const [selectedCasteCategory, setSelectedCasteCategory] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [selectedSchemeTypes, setSelectedSchemeTypes] = useState([]);
  const [sortBy, setSortBy] = useState('relevant');

  // Sidebar Toggles
  const [showAllCategories, setShowAllCategories] = useState(false);
  const [showAllSchemeTypes, setShowAllSchemeTypes] = useState(false);

  // Bookmarks
  const [bookmarkedIds, setBookmarkedIds] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_bookmarked_schemes');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  });

  // Modal State for Eligibility Quick Check
  const [modalScheme, setModalScheme] = useState(null);

  // Save Bookmarks to localStorage
  const toggleBookmark = (schemeId) => {
    setBookmarkedIds((prev) => {
      const updated = prev.includes(schemeId)
        ? prev.filter((id) => id !== schemeId)
        : [...prev, schemeId];
      try {
        localStorage.setItem('fin_bookmarked_schemes', JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });
  };

  const isBookmarked = (schemeId) => bookmarkedIds.includes(schemeId);

  // Synchronize category pill click with filter state
  const handlePillClick = (catId) => {
    setActiveCategoryPill(catId);
    if (catId === 'all') {
      setSelectedCategories([]);
    } else {
      setSelectedCategories([catId]);
    }
  };

  // Synchronize checkbox with pill selection
  const toggleCategoryCheckbox = (catId) => {
    setSelectedCategories((prev) => {
      let updated;
      if (prev.includes(catId)) {
        updated = prev.filter((id) => id !== catId);
      } else {
        updated = [...prev, catId];
      }

      // Update active pill indicator
      if (updated.length === 1) {
        setActiveCategoryPill(updated[0]);
      } else if (updated.length === 0) {
        setActiveCategoryPill('all');
      } else {
        setActiveCategoryPill('');
      }

      return updated;
    });
  };

  const toggleSchemeTypeCheckbox = (typeId) => {
    setSelectedSchemeTypes((prev) =>
      prev.includes(typeId)
        ? prev.filter((id) => id !== typeId)
        : [...prev, typeId]
    );
  };

  const handleClearAll = () => {
    setActiveCategoryPill('all');
    setSearchQuery('');
    setSelectedCategories([]);
    setSelectedAgeGroup('');
    setSelectedIncomeRange('');
    setSelectedCasteCategory('');
    setSelectedState('');
    setSelectedSchemeTypes([]);
    setSortBy('relevant');
  };

  const handleCheckEligibility = (scheme) => {
    setModalScheme(scheme);
  };

  // --------------------------------------------------------------------------
  // Filter & Sort Logic
  // --------------------------------------------------------------------------
  const filteredSchemes = useMemo(() => {
    return SCHEMES.filter((scheme) => {
      // 1. Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesTitle = scheme.title.toLowerCase().includes(q);
        const matchesSubtitle = scheme.subtitle.toLowerCase().includes(q);
        const matchesDesc = scheme.description.toLowerCase().includes(q);
        const matchesTags = scheme.tags.some((t) => t.toLowerCase().includes(q));
        if (!matchesTitle && !matchesSubtitle && !matchesDesc && !matchesTags) {
          return false;
        }
      }

      // 2. Category Checkboxes or Active Pill
      if (selectedCategories.length > 0) {
        const matchesCat = scheme.categories.some((c) => selectedCategories.includes(c));
        if (!matchesCat) return false;
      } else if (activeCategoryPill && activeCategoryPill !== 'all') {
        if (!scheme.categories.includes(activeCategoryPill)) return false;
      }

      // 3. Age Group Filter
      if (selectedAgeGroup) {
        if (scheme.ageGroup !== 'All Ages' && scheme.ageGroup !== selectedAgeGroup) {
          // Broad check
          if (selectedAgeGroup === '60+' && scheme.ageGroup !== '60+' && scheme.ageGroup !== '18-60') {
            return false;
          }
        }
      }

      // 4. Income Range Filter
      if (selectedIncomeRange) {
        if (scheme.incomeRange !== 'all' && scheme.incomeRange !== selectedIncomeRange) {
          return false;
        }
      }

      // 5. Caste / Social Category Filter
      if (selectedCasteCategory) {
        if (
          scheme.casteCategories &&
          !scheme.casteCategories.includes(selectedCasteCategory) &&
          !scheme.casteCategories.includes('General')
        ) {
          return false;
        }
      }

      // 6. State Filter
      if (selectedState && selectedState !== 'All India') {
        if (scheme.state !== 'All India' && !scheme.state.includes(selectedState)) {
          return false;
        }
      }

      // 7. Scheme Type Filter
      if (selectedSchemeTypes.length > 0) {
        const matchesType = scheme.schemeTypes.some((t) => selectedSchemeTypes.includes(t));
        if (!matchesType) return false;
      }

      return true;
    }).sort((a, b) => {
      if (sortBy === 'match_score') {
        return b.matchScore - a.matchScore;
      }
      if (sortBy === 'highest_benefit') {
        return (b.benefitValue || 0) - (a.benefitValue || 0);
      }
      if (sortBy === 'name_asc') {
        return a.title.localeCompare(b.title);
      }
      // 'relevant' (default maintains reference ordering)
      return 0;
    });
  }, [
    searchQuery,
    selectedCategories,
    activeCategoryPill,
    selectedAgeGroup,
    selectedIncomeRange,
    selectedCasteCategory,
    selectedState,
    selectedSchemeTypes,
    sortBy,
  ]);

  // Visible lists for right sidebar
  const visibleCategories = showAllCategories ? CATEGORIES.filter(c => c.id !== 'all') : CATEGORIES.filter(c => c.id !== 'all').slice(0, 5);
  const visibleSchemeTypes = showAllSchemeTypes ? SCHEME_TYPES : SCHEME_TYPES.slice(0, 5);

  return (
    <PageContainer>
      <div className="discover-page-wrapper">
        {/* ------------------------------------------------------------------
            1. Top Hero Banner (India Gate Fade + Editorial Quote + Tricolor)
            ------------------------------------------------------------------ */}
        <section className="discover-hero-banner" aria-label="Discover Government Schemes Header">
          <div className="discover-banner-left">
            <h1 className="discover-banner-title">Discover Government Schemes</h1>
            <p className="discover-banner-subtitle">
              Explore schemes across different categories and find what's right for you.
            </p>
          </div>

          <div className="discover-banner-right" aria-hidden="true">
            <div className="discover-banner-visual-wrapper">
              <img
                src={indiaGateHero}
                alt="India Gate Monument"
                className="discover-india-gate-img"
              />
              <div className="discover-banner-fade-overlay" />
            </div>

            <div className="discover-banner-editorial">
              <p className="discover-banner-quote">
                Opportunities<br />
                today for a<br />
                brighter tomorrow.
              </p>
              <img
                src={tricolorFlagPerfect}
                alt=""
                className="discover-banner-tricolor"
              />
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            2. Horizontal Category Filter Pills Row
            ------------------------------------------------------------------ */}
        <nav className="discover-categories-scroll" aria-label="Scheme Categories">
          {CATEGORIES.map((cat) => {
            const isActive = activeCategoryPill === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => handlePillClick(cat.id)}
                className={`category-pill-btn ${isActive ? 'active' : ''}`}
                aria-pressed={isActive}
              >
                <span>{cat.label}</span>
                <span className="category-pill-count">({cat.count})</span>
              </button>
            );
          })}
        </nav>

        {/* ------------------------------------------------------------------
            3. Main Grid: Schemes List (Left) + Sticky Filters Box (Right)
            ------------------------------------------------------------------ */}
        <div className="discover-main-grid">
          {/* LEFT: Schemes Column */}
          <div className="discover-schemes-column">
            {/* Header: Results count + Sort by dropdown */}
            <div className="discover-results-header">
              <span className="discover-count-text">
                {filteredSchemes.length} {filteredSchemes.length === 1 ? 'scheme' : 'schemes'} found
              </span>

              <div className="discover-sort-container">
                <span className="discover-sort-label">Sort by</span>
                <div className="discover-sort-btn-wrapper">
                  <SlidersHorizontal size={14} className="discover-sort-icon-left" aria-hidden="true" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="discover-sort-select"
                    aria-label="Sort schemes by"
                  >
                    <option value="relevant">Most Relevant</option>
                    <option value="highest_benefit">Highest Benefit</option>
                    <option value="match_score">Match Score</option>
                    <option value="name_asc">Scheme Name (A - Z)</option>
                  </select>
                  <ChevronDown size={14} className="discover-sort-chevron-right" aria-hidden="true" />
                </div>
              </div>
            </div>

            {/* Scheme Cards */}
            {filteredSchemes.length > 0 ? (
              <div className="schemes-list-container">
                {filteredSchemes.map((scheme) => (
                  <article key={scheme.id} className="scheme-card-item">
                    {/* 1. Logo Box */}
                    <div className="scheme-card-logo-box">
                      <SchemeLogo scheme={scheme} />
                    </div>

                    {/* 2. Text Info */}
                    <div className="scheme-card-info-col">
                      <h2 className="scheme-card-title">{scheme.title}</h2>
                      <h3 className="scheme-card-subtitle">{scheme.subtitle}</h3>
                      <p className="scheme-card-description">{scheme.description}</p>

                      <div className="scheme-card-tags-row">
                        {scheme.tags.map((tag) => (
                          <span key={tag} className="scheme-card-tag-pill">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* 3. Metrics Column */}
                    <div className="scheme-card-metrics-col">
                      <div className={`scheme-match-badge match-${scheme.matchType || 'green'}`}>
                        {scheme.matchScore}% Match
                      </div>

                      <div className="scheme-benefit-box">
                        <div className="scheme-benefit-amount-row">
                          <Calendar size={15} className="scheme-benefit-icon" aria-hidden="true" />
                          <span className="scheme-benefit-val">{scheme.benefitAmount}</span>
                        </div>
                        <span className="scheme-benefit-lbl">{scheme.benefitSubtitle || 'Estimated Benefit'}</span>
                      </div>

                      <div className="scheme-condition-status">
                        {scheme.conditionType === 'success' && (
                          <>
                            <CheckCircle2 size={16} className="condition-icon success" aria-hidden="true" />
                            <span className="condition-text success">{scheme.conditionText}</span>
                          </>
                        )}
                        {scheme.conditionType === 'warning' && (
                          <>
                            <AlertTriangle size={16} className="condition-icon warning" aria-hidden="true" />
                            <span className="condition-text warning">{scheme.conditionText}</span>
                          </>
                        )}
                        {scheme.conditionType === 'lock' && (
                          <>
                            <Lock size={15} className="condition-icon amber" aria-hidden="true" />
                            <span className="condition-text amber">{scheme.conditionText}</span>
                          </>
                        )}
                        {scheme.conditionType === 'lock-link' && (
                          <button
                            type="button"
                            onClick={() => handleCheckEligibility(scheme)}
                            className="condition-interactive-btn"
                            title="Check Eligibility Requirements"
                          >
                            <Lock size={15} className="condition-icon amber" aria-hidden="true" />
                            <span className="condition-text amber">{scheme.conditionText}</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* 4. Action Buttons */}
                    <div className="scheme-card-actions-col">
                      <Link
                        to={`/schemes/${scheme.id}`}
                        className={`btn-scheme-view ${scheme.primaryAction ? 'primary' : 'outline'}`}
                      >
                        <span>View Details</span>
                        <ArrowRight size={15} aria-hidden="true" />
                      </Link>

                      <button
                        type="button"
                        onClick={() => toggleBookmark(scheme.id)}
                        className={`btn-scheme-bookmark ${isBookmarked(scheme.id) ? 'bookmarked' : ''}`}
                        aria-label={isBookmarked(scheme.id) ? `Remove ${scheme.title} from bookmarks` : `Bookmark ${scheme.title}`}
                        title={isBookmarked(scheme.id) ? 'Bookmarked' : 'Bookmark scheme'}
                      >
                        <Bookmark
                          size={17}
                          fill={isBookmarked(scheme.id) ? '#073B30' : 'none'}
                          color={isBookmarked(scheme.id) ? '#073B30' : '#667085'}
                        />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="discover-empty-state">
                <div className="discover-empty-icon">
                  <Search size={24} />
                </div>
                <h3 className="discover-empty-title">No matching schemes found</h3>
                <p className="discover-empty-desc">
                  Try adjusting your search criteria, clearing category filters, or broadening your eligibility selections.
                </p>
                <button
                  type="button"
                  onClick={handleClearAll}
                  className="btn-apply-filters"
                  style={{ width: 'auto', padding: '9px 20px', marginTop: '8px' }}
                >
                  <RotateCcw size={14} style={{ marginRight: '6px' }} />
                  <span>Reset All Filters</span>
                </button>
              </div>
            )}
          </div>

          {/* RIGHT: Sticky Filters Sidebar */}
          <aside className="discover-filters-sidebar" aria-label="Scheme Filter Controls">
            {/* Header: Title + Clear All */}
            <div className="filters-header-row">
              <div className="filters-header-title-wrap">
                <SlidersHorizontal size={17} className="filters-header-icon" aria-hidden="true" />
                <h2 className="filters-header-title">Filters</h2>
              </div>
              <button
                type="button"
                onClick={handleClearAll}
                className="filters-clear-btn"
              >
                Clear All
              </button>
            </div>

            {/* 1. Search Box */}
            <div className="filter-group-block">
              <label htmlFor="filter-search-input" className="filter-group-title">
                Search
              </label>
              <div className="filter-search-box">
                <Search size={15} className="filter-search-icon" aria-hidden="true" />
                <input
                  id="filter-search-input"
                  type="search"
                  placeholder="Search schemes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="filter-search-input"
                  aria-label="Search schemes"
                />
              </div>
            </div>

            {/* 2. Category Checkboxes */}
            <div className="filter-group-block">
              <h3 className="filter-group-title">Category</h3>
              <div className="filter-checkbox-list">
                {visibleCategories.map((cat) => (
                  <label key={cat.id} className="filter-checkbox-item">
                    <div className="filter-checkbox-left">
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(cat.id)}
                        onChange={() => toggleCategoryCheckbox(cat.id)}
                        className="filter-checkbox-input"
                      />
                      <span className="filter-checkbox-name">{cat.label}</span>
                    </div>
                    <span className="filter-checkbox-count">({cat.count})</span>
                  </label>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setShowAllCategories((prev) => !prev)}
                className="filter-show-more-btn"
              >
                <span>{showAllCategories ? 'Show less ⌃' : 'Show more ⌄'}</span>
              </button>
            </div>

            {/* 3. Eligibility Dropdowns */}
            <div className="filter-group-block">
              <h3 className="filter-group-title">Eligibility</h3>
              <div className="filter-select-stack">
                <div className="filter-select-wrap">
                  <select
                    value={selectedAgeGroup}
                    onChange={(e) => setSelectedAgeGroup(e.target.value)}
                    className={`filter-select ${selectedAgeGroup ? 'has-value' : ''}`}
                    aria-label="Select Age Group"
                  >
                    <option value="">Select Age Group</option>
                    <option value="18-25">18 - 25 years</option>
                    <option value="18-40">18 - 40 years</option>
                    <option value="18-60">18 - 60 years</option>
                    <option value="60+">60+ Senior Citizens</option>
                  </select>
                  <ChevronDown size={14} className="filter-select-chevron" aria-hidden="true" />
                </div>

                <div className="filter-select-wrap">
                  <select
                    value={selectedIncomeRange}
                    onChange={(e) => setSelectedIncomeRange(e.target.value)}
                    className={`filter-select ${selectedIncomeRange ? 'has-value' : ''}`}
                    aria-label="Select Income Range"
                  >
                    <option value="">Select Income Range</option>
                    <option value="below-1.5l">Below ₹1.5 Lakh</option>
                    <option value="1.5l-3l">₹1.5L - ₹3 Lakh</option>
                    <option value="3l-8l">₹3L - ₹8 Lakh</option>
                    <option value="above-8l">Above ₹8 Lakh</option>
                  </select>
                  <ChevronDown size={14} className="filter-select-chevron" aria-hidden="true" />
                </div>

                <div className="filter-select-wrap">
                  <select
                    value={selectedCasteCategory}
                    onChange={(e) => setSelectedCasteCategory(e.target.value)}
                    className={`filter-select ${selectedCasteCategory ? 'has-value' : ''}`}
                    aria-label="Select Social Category"
                  >
                    <option value="">Select Category</option>
                    <option value="General">General</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                    <option value="Minority">Minority</option>
                  </select>
                  <ChevronDown size={14} className="filter-select-chevron" aria-hidden="true" />
                </div>

                <div className="filter-select-wrap">
                  <select
                    value={selectedState}
                    onChange={(e) => setSelectedState(e.target.value)}
                    className={`filter-select ${selectedState ? 'has-value' : ''}`}
                    aria-label="Select State"
                  >
                    <option value="">Select State</option>
                    <option value="All India">All India</option>
                    <option value="Maharashtra">Maharashtra</option>
                    <option value="Gujarat">Gujarat</option>
                    <option value="Karnataka">Karnataka</option>
                    <option value="Delhi">Delhi</option>
                    <option value="Uttar Pradesh">Uttar Pradesh</option>
                    <option value="Tamil Nadu">Tamil Nadu</option>
                    <option value="Rajasthan">Rajasthan</option>
                  </select>
                  <ChevronDown size={14} className="filter-select-chevron" aria-hidden="true" />
                </div>
              </div>
            </div>

            {/* 4. Scheme Type Checkboxes */}
            <div className="filter-group-block">
              <h3 className="filter-group-title">Scheme Type</h3>
              <div className="filter-checkbox-list">
                {visibleSchemeTypes.map((type) => (
                  <label key={type.id} className="filter-checkbox-item">
                    <div className="filter-checkbox-left">
                      <input
                        type="checkbox"
                        checked={selectedSchemeTypes.includes(type.id)}
                        onChange={() => toggleSchemeTypeCheckbox(type.id)}
                        className="filter-checkbox-input"
                      />
                      <span className="filter-checkbox-name">{type.label}</span>
                    </div>
                  </label>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setShowAllSchemeTypes((prev) => !prev)}
                className="filter-show-more-btn"
              >
                <span>{showAllSchemeTypes ? 'Show less ⌃' : 'Show more ⌄'}</span>
              </button>
            </div>

            {/* 5. Apply Filters Button */}
            <button
              type="button"
              onClick={() => {
                window.scrollTo({ top: 120, behavior: 'smooth' });
              }}
              className="btn-apply-filters"
            >
              Apply Filters
            </button>
          </aside>
        </div>
      </div>

      {/* ------------------------------------------------------------------
          Eligibility Check Modal
          ------------------------------------------------------------------ */}
      {modalScheme && (
        <div className="eligibility-modal-backdrop" onClick={() => setModalScheme(null)}>
          <div
            className="eligibility-modal-card"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="eligibility-title"
          >
            <div className="eligibility-modal-header">
              <div>
                <h3 id="eligibility-title" className="eligibility-modal-title">
                  Eligibility Criteria: {modalScheme.title}
                </h3>
                <p className="eligibility-modal-sub">{modalScheme.subtitle}</p>
              </div>
              <button
                type="button"
                onClick={() => setModalScheme(null)}
                className="eligibility-modal-close-btn"
                aria-label="Close eligibility modal"
              >
                <X size={20} />
              </button>
            </div>

            <div className="eligibility-modal-body">
              <p className="font-body" style={{ color: '#475467' }}>
                Review the qualifying conditions below. If your profile matches these requirements, you can proceed directly to apply.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {(modalScheme.eligibilityCriteria || [
                  'Indian citizen with valid Aadhaar & KYC documentation',
                  'Meets the age and income eligibility guidelines for this scheme',
                  'Possesses active bank account linked to Aadhaar for Direct Benefit Transfer',
                  'Clean banking credit track record with no unresolved defaults'
                ]).map((rule, idx) => (
                  <div key={idx} className="eligibility-checklist-item">
                    <ShieldCheck size={18} color="#073B30" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span className="eligibility-checklist-text">{rule}</span>
                  </div>
                ))}
              </div>

              {modalScheme.documentsRequired && (
                <div style={{ marginTop: '10px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#10243A', marginBottom: '8px' }}>
                    Required Documents:
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {modalScheme.documentsRequired.map((doc, idx) => (
                      <span key={idx} className="scheme-card-tag-pill">
                        {doc}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="eligibility-modal-footer">
              <button
                type="button"
                onClick={() => setModalScheme(null)}
                className="btn-scheme-view outline"
                style={{ padding: '8px 16px' }}
              >
                Close
              </button>
              <Link
                to={`/schemes/${modalScheme.id}`}
                className="btn-scheme-view primary"
                style={{ padding: '8px 18px' }}
              >
                <span>View Full Scheme Details</span>
                <ArrowRight size={15} />
              </Link>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
}
