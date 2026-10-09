import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Info,
  Search,
  ArrowRight,
  RefreshCw,
  ShieldCheck,
  X,
  ExternalLink,
  User,
  SlidersHorizontal,
  ChevronRight,
  BookOpen
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import { fetchRecommendedSchemes, fetchSchemes } from '../services/schemeService';
import { fetchUserProfile } from '../services/profileService';
import { getStoredUser } from '../services/authService';
import SchemeLogo from '../components/schemes/SchemeLogo';
import { interpretFinancialBenefit } from '../utils/financialBenefitEngine.js';
import { isInternalSentinel, formatProfileFieldLabel } from '../utils/schemeDetailsHelpers';
import { navigateToSchemeDocuments } from '../utils/schemeNavigation';
import { formatAnnualIncome, formatSocialCategory } from '../utils/profileHelpers';
import indiaGateHero from '../assets/india_gate_hero.jpg';
import '../styles/suggestedSchemes.css';

/**
 * Normalizes eligibility status strictly into one of the 4 statutory states:
 * PASS | REVIEW | UNKNOWN | FAIL
 * Invariant: UNKNOWN or REVIEW is never converted to PASS.
 */
function normalizeEligibility(status) {
  if (!status) return 'UNKNOWN';
  const upper = String(status).toUpperCase();
  if (upper === 'PASS' || upper === 'ELIGIBLE') return 'PASS';
  if (upper === 'REVIEW' || upper === 'NEEDS_REVIEW' || upper === 'IN_REVIEW') return 'REVIEW';
  if (upper === 'FAIL' || upper === 'INELIGIBLE') return 'FAIL';
  return 'UNKNOWN';
}

const SYSTEM_METADATA_FIELDS = new Set([
  'id', 'user_id', 'applicant_id',
  'created_at', 'updated_at', 'uploaded_at',
  'createdAt', 'updatedAt', 'uploadedAt',
  'status', 'verification_status', 'role'
]);

export default function SuggestedSchemesPage() {
  const navigate = useNavigate();

  // Data states
  const [recommendations, setRecommendations] = useState([]);
  const [activeFactsSummary, setActiveFactsSummary] = useState({});
  const [conflictsDetected, setConflictsDetected] = useState([]);
  const [conflictDetails, setConflictDetails] = useState({});
  const [userProfile, setUserProfile] = useState(() => getStoredUser() || {});
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isFallback, setIsFallback] = useState(false);

  // UI interaction states
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState('all'); // 'all' | 'pass' | 'review' | 'unknown' | 'fail'
  const [selectedSchemeForModal, setSelectedSchemeForModal] = useState(null);

  // Load applicant profile and real Intelligence recommendations with database fallback
  const loadRecommendations = async (showRefreshSpinner = false, overrideProfile = null) => {
    if (showRefreshSpinner) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);
    setIsFallback(false);

    let currentProfile = overrideProfile || userProfile || getStoredUser() || {};
    // 1. Fetch live user profile from Supabase
    try {
      const prof = await fetchUserProfile();
      if (prof) {
        currentProfile = { ...currentProfile, ...prof };
        setUserProfile(currentProfile);
      }
    } catch (profErr) {
      console.debug('Profile fetch notice:', profErr.message);
    }

    const userState = currentProfile?.state || currentProfile?.location?.state || undefined;
    const userCategory = currentProfile?.category || currentProfile?.social_category || undefined;

    let recsLoaded = false;

    // PRIMARY: fetchRecommendedSchemes()
    try {
      const result = await fetchRecommendedSchemes({
        query: 'schemes matching my profile and state',
        top_k: 16,
        state_override: userState,
        category_override: userCategory
      });

      if (result && Array.isArray(result.recommendations) && result.recommendations.length > 0) {
        // Deduplicate recommendations by canonical scheme_id or slug
        const seen = new Set();
        const deduped = [];
        for (const rec of result.recommendations) {
          const key = rec.scheme_id || rec.scheme_slug;
          if (key && !seen.has(key)) {
            seen.add(key);
            deduped.push(rec);
          }
        }
        setRecommendations(deduped);
        setActiveFactsSummary(result.active_facts_summary || {});
        const rawConflicts = result.conflicts_detected || [];
        const cleanConflicts = rawConflicts.filter(c => !SYSTEM_METADATA_FIELDS.has(c));
        setConflictsDetected(cleanConflicts);
        setConflictDetails(result.conflict_details || {});
        setLastUpdated(result.createdAt || new Date().toISOString());
        setIsFallback(false);
        recsLoaded = true;
      }
    } catch (recErr) {
      console.warn('Recommendation API unavailable or returned error, triggering database fallback:', recErr.message);
      if (showRefreshSpinner) {
        setError(`Re-evaluation notice: ${recErr.message || 'Evaluation service temporarily unavailable.'}`);
      }
    }

    // FALLBACK: If recommendations return empty array, fail, timeout, or otherwise cannot provide usable recommendations
    if (!recsLoaded) {
      try {
        // Look for education/scholarship schemes for students or state schemes
        const isStudent = (currentProfile?.occupation || '').toLowerCase().includes('student');
        let fallbackResult = await fetchSchemes({
          limit: 16,
          state: userState && userState !== 'Not provided' ? userState : undefined,
          category: isStudent ? 'education' : undefined
        });

        let fallbackList = Array.isArray(fallbackResult?.schemes) ? fallbackResult.schemes : [];
        if (fallbackList.length === 0) {
          const generalResult = await fetchSchemes({
            limit: 16,
            state: userState && userState !== 'Not provided' ? userState : undefined
          });
          fallbackList = Array.isArray(generalResult?.schemes) ? generalResult.schemes : [];
        }

        if (fallbackList.length > 0) {
          const seen = new Set();
          const adaptedFallback = [];
          for (const s of fallbackList) {
            const key = s.id || s.slug;
            if (key && !seen.has(key)) {
              seen.add(key);
              const reasons = [];
              if (userState && s.state && s.state.toLowerCase() === userState.toLowerCase()) {
                reasons.push(`State: Matches (${s.state})`);
              } else if (!s.state || s.state.toLowerCase() === 'all india' || s.state.toLowerCase() === 'central') {
                reasons.push('State: Open nationally (Central scheme)');
              }
              if (s.tags && Array.isArray(s.tags) && s.tags.some(t => String(t).toLowerCase().includes('student') || String(t).toLowerCase().includes('education'))) {
                reasons.push('Beneficiary: Education & learning domain matching profile');
              } else {
                reasons.push('Beneficiary: Open catalog scheme (evaluation pending)');
              }

              adaptedFallback.push({
                scheme_id: s.id,
                scheme_slug: s.slug,
                scheme_name: s.scheme_name || s.title || 'Government Scheme',
                ministry: s.ministry || s.department || 'Government of India',
                benefit_summary: s.brief_description || s.benefit_summary || s.description || 'Government welfare initiative',
                description: s.detailed_description || s.description || '',
                eligibility_status: 'UNKNOWN',
                overall_match_score: null, // Zero fake scores
                recommendation_reasons: reasons,
                source_metadata: { ministry: s.ministry, state: s.state },
                max_benefit: s.max_benefit,
                is_fallback: true
              });
            }
          }

          setRecommendations(adaptedFallback);
          setIsFallback(true);
          setActiveFactsSummary({ state: userState || 'All India' });
          setConflictsDetected([]);
          setLastUpdated(new Date().toISOString());
        } else {
          setRecommendations([]);
        }
      } catch (fbErr) {
        console.error('Error loading fallback schemes:', fbErr);
        setError(fbErr.message || 'Unable to load suggested schemes. Please verify service connectivity.');
        setRecommendations([]);
      }
    }


    setIsLoading(false);
    setIsRefreshing(false);
  };

  useEffect(() => {
    loadRecommendations();

    const handleProfileUpdate = (e) => {
      const newProf = e?.detail || getStoredUser() || {};
      setUserProfile(newProf);
      loadRecommendations(false, newProf);
    };

    window.addEventListener('fin_user_updated', handleProfileUpdate);
    window.addEventListener('storage', handleProfileUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleProfileUpdate);
      window.removeEventListener('storage', handleProfileUpdate);
    };
  }, []);

  // Filter and search computation
  const filteredSchemes = useMemo(() => {
    return recommendations.filter((item) => {
      const status = normalizeEligibility(item.eligibility_status);

      // Status filter tab
      let matchesTab = true;
      if (filterTab === 'pass') matchesTab = status === 'PASS';
      else if (filterTab === 'review') matchesTab = status === 'REVIEW';
      else if (filterTab === 'unknown') matchesTab = status === 'UNKNOWN';
      else if (filterTab === 'fail') matchesTab = status === 'FAIL';

      if (!matchesTab) return false;

      // Text search
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const name = (item.scheme_name || '').toLowerCase();
      const ministry = (item.ministry || item.source_metadata?.ministry || '').toLowerCase();
      const benefit = (item.benefit_summary || '').toLowerCase();
      const desc = (item.description || item.eligibility_summary || '').toLowerCase();
      const reasons = Array.isArray(item.recommendation_reasons)
        ? item.recommendation_reasons.join(' ').toLowerCase()
        : '';

      return name.includes(q) || ministry.includes(q) || benefit.includes(q) || desc.includes(q) || reasons.includes(q);
    });
  }, [recommendations, filterTab, searchQuery]);

  // Status counts for filter pills
  const counts = useMemo(() => {
    const res = { all: recommendations.length, pass: 0, review: 0, unknown: 0, fail: 0 };
    recommendations.forEach((item) => {
      const st = normalizeEligibility(item.eligibility_status);
      if (st === 'PASS') res.pass += 1;
      else if (st === 'REVIEW') res.review += 1;
      else if (st === 'FAIL') res.fail += 1;
      else res.unknown += 1;
    });
    return res;
  }, [recommendations]);

  // Eligibility badge renderer preserving 4-state statutory classification
  const renderStatutoryBadge = (rawStatus) => {
    const status = normalizeEligibility(rawStatus);
    switch (status) {
      case 'PASS':
        return (
          <span className="statutory-badge pass" title="Applicant satisfies all known statutory criteria">
            <CheckCircle2 size={12} strokeWidth={2.5} />
            <span>Eligible / Meets Criteria</span>
          </span>
        );
      case 'REVIEW':
        return (
          <span className="statutory-badge review" title="Conflicting facts or conditions require human officer review">
            <AlertTriangle size={12} strokeWidth={2.5} />
            <span>Requires Review</span>
          </span>
        );
      case 'FAIL':
        return (
          <span className="statutory-badge fail" title="Applicant does not meet mandatory threshold">
            <XCircle size={12} strokeWidth={2.5} />
            <span>Not Eligible</span>
          </span>
        );
      case 'UNKNOWN':
      default:
        return (
          <span className="statutory-badge unknown" title="Statutory eligibility cannot currently be determined">
            <Clock size={12} strokeWidth={2.5} />
            <span>Evaluation Pending</span>
          </span>
        );
    }
  };

  // Resolved applicant profile facts
  const displayState = userProfile.state || activeFactsSummary.state || 'Not provided';
  const rawCategory = userProfile.category || userProfile.social_category || userProfile.caste_category || activeFactsSummary.caste_category;
  const displayCategory = rawCategory ? formatSocialCategory(rawCategory) : 'Not provided';
  const displayDistrict = userProfile.district || userProfile.city || activeFactsSummary.city || 'Not provided';
  const displayOccupation = userProfile.occupation || 'Not provided';
  const rawPersonalIncome = userProfile.annual_income ?? userProfile.income ?? null;
  const displayPersonalIncome = (rawPersonalIncome !== null && rawPersonalIncome !== undefined && rawPersonalIncome !== '' && rawPersonalIncome !== 'Not added')
    ? formatAnnualIncome(rawPersonalIncome)
    : 'Not provided';
  const displayFamilyIncome = activeFactsSummary.annual_family_income != null
    ? formatAnnualIncome(activeFactsSummary.annual_family_income)
    : null;

  return (
    <PageContainer>
      <div className="suggested-page-wrapper">
        {/* ------------------------------------------------------------------
            1. HEADER SECTION
            ------------------------------------------------------------------ */}
        <section className="suggested-header-card" aria-label="Suggested Schemes Overview">
          {/* Background panoramic India Gate visual */}
          <div
            className="suggested-bg-visual"
            style={{ backgroundImage: `url(${indiaGateHero})` }}
            aria-hidden="true"
          />

          <div className="suggested-header-left">
            <div className="suggested-title-row">
              <h1 className="suggested-main-title">Suggested Schemes</h1>
              <span className="suggested-badge-ai">
                {isFallback ? <SlidersHorizontal size={12} /> : <Sparkles size={12} />}
                <span>{isFallback ? 'State & Category Matches' : 'FIN Intelligence'}</span>
              </span>
            </div>
            <p className="suggested-header-sub">
              {isFallback
                ? 'Government schemes filtered by your state and demographic profile from the national scheme database.'
                : 'Personalized government schemes based on your profile, eligibility information, documents, and available policy data.'}
            </p>
            <span className="suggested-meta-sub">
              <ShieldCheck size={13} color="#005B50" />
              <span>{isFallback ? 'State & Category Matches' : 'Based on your verified applicant profile'}</span>
              {isFallback && (
                <span
                  style={{
                    backgroundColor: '#F0F9FF',
                    border: '1px solid #B9E6FE',
                    color: '#026AA2',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600
                  }}
                >
                  State & Category Matches
                </span>
              )}
              {lastUpdated && (
                <span>
                  • Updated {new Date(lastUpdated).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                </span>
              )}
            </span>
          </div>

          <button
            type="button"
            className="suggested-refresh-btn"
            onClick={() => loadRecommendations(true)}
            disabled={isLoading || isRefreshing}
            aria-label="Refresh suggested schemes"
            title="Re-run recommendation engine with latest facts"
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'Evaluating...' : 'Re-Evaluate'}</span>
          </button>
        </section>

        {/* ------------------------------------------------------------------
            2. APPLICANT RECOMMENDATION PROFILE CONTEXT
            ------------------------------------------------------------------ */}
        <section className="suggested-context-card" aria-label="Recommendation Profile Parameters">
          <div className="suggested-context-header">
            <div className="suggested-context-title-group">
              <User size={15} color="#005B50" />
              <h3 className="suggested-context-title">Your Recommendation Profile</h3>
            </div>
            <button
              type="button"
              className="suggested-context-link"
              onClick={() => navigate('/profile')}
              aria-label="Edit Profile"
            >
              <span>Update Profile</span>
              <ChevronRight size={13} />
            </button>
          </div>

          <div className="suggested-context-grid">
            <div className="suggested-context-pill">
              <span className="suggested-context-key">State</span>
              <span className={`suggested-context-val ${displayState === 'Not provided' ? 'missing' : ''}`}>
                {displayState}
              </span>
            </div>

            <div className="suggested-context-pill">
              <span className="suggested-context-key">District / City</span>
              <span className={`suggested-context-val ${displayDistrict === 'Not provided' ? 'missing' : ''}`}>
                {displayDistrict}
              </span>
            </div>

            <div className="suggested-context-pill">
              <span className="suggested-context-key">Social Category</span>
              <span className={`suggested-context-val ${displayCategory === 'NOT PROVIDED' ? 'missing' : ''}`}>
                {displayCategory}
              </span>
            </div>

            <div className="suggested-context-pill">
              <span className="suggested-context-key">Occupation</span>
              <span className={`suggested-context-val ${displayOccupation === 'Not provided' ? 'missing' : ''}`}>
                {displayOccupation}
              </span>
            </div>

            <div className="suggested-context-pill">
              <span className="suggested-context-key">Personal Income</span>
              <span className={`suggested-context-val ${displayPersonalIncome === 'Not provided' ? 'missing' : ''}`}>
                {displayPersonalIncome}
              </span>
            </div>

            {displayFamilyIncome && (
              <div className="suggested-context-pill">
                <span className="suggested-context-key">Family Income (Doc)</span>
                <span className="suggested-context-val" title="Verified from submitted Income Certificate">
                  {displayFamilyIncome}
                </span>
              </div>
            )}
          </div>
        </section>

        {/* ------------------------------------------------------------------
            3. CONFLICTS / UNCERTAINTY BANNER (Evidence-first principle)
            ------------------------------------------------------------------ */}
        {(() => {
          const visibleConflicts = (conflictsDetected || []).filter((fKey) => {
            if (SYSTEM_METADATA_FIELDS.has(fKey)) return false;
            const facts = conflictDetails?.[fKey] || [];
            if (facts.length < 2) {
              const docFact = facts.find(f => f.source_type === 'DOCUMENT');
              return Boolean(docFact && docFact.value);
            }
            return true;
          });

          if (visibleConflicts.length === 0) return null;

          return (
            <div className="suggested-conflict-banner" role="alert">
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ width: '100%' }}>
                <div>
                  <strong>Information Needs Review: </strong>
                  Conflicting applicant facts ({visibleConflicts.join(', ')}) were detected across your
                  documents or profile. Statutory eligibility cannot be finalized until the conflict is resolved.
                  {' '}
                  <button type="button" onClick={() => navigate('/documents')}>
                    Review Document Evidence
                  </button>
                </div>

                {conflictDetails && Object.keys(conflictDetails).length > 0 && (
                  <div className="suggested-conflict-details" style={{ marginTop: '10px', fontSize: '12px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '6px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #fde68a', textAlign: 'left', color: '#78350f' }}>
                          <th style={{ padding: '4px 8px' }}>Fact Field</th>
                          <th style={{ padding: '4px 8px' }}>Profile Value</th>
                          <th style={{ padding: '4px 8px' }}>Document / Secondary Value</th>
                          <th style={{ padding: '4px 8px' }}>Source / Evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visibleConflicts.map((fKey) => {
                          const facts = conflictDetails[fKey] || [];
                          const profFact = facts.find(f => f.source_type === 'PROFILE');
                          const nonProfFacts = facts.filter(f => f.source_type !== 'PROFILE');
                          const secondaryFact = nonProfFacts[0] || facts[1];
                          const profVal = profFact?.value || userProfile[fKey] || '—';
                          const secVal = secondaryFact?.value || '—';
                          const srcName = secondaryFact?.source_document || (secondaryFact?.source_type === 'DOCUMENT' ? 'Uploaded Document' : secondaryFact?.source_type || 'Evidence');
                          const pageInfo = secondaryFact?.page_number ? ` (Page ${secondaryFact.page_number})` : '';

                          return (
                            <tr key={fKey} style={{ borderBottom: '1px solid #fef3c7' }}>
                              <td style={{ padding: '4px 8px', fontWeight: 600 }}>{formatProfileFieldLabel(fKey)}</td>
                              <td style={{ padding: '4px 8px' }}>{String(profVal)}</td>
                              <td style={{ padding: '4px 8px', color: '#b45309', fontWeight: 600 }}>{String(secVal)}</td>
                              <td style={{ padding: '4px 8px', color: '#92400e' }}>{srcName}{pageInfo}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          );
        })()}

        {/* ------------------------------------------------------------------
            4. TOOLBAR: SEARCH & FILTER TABS
            ------------------------------------------------------------------ */}
        <section className="suggested-toolbar-row" aria-label="Scheme Filters">
          <div className="suggested-search-wrapper">
            <Search size={16} className="suggested-search-icon" aria-hidden="true" />
            <input
              type="text"
              className="suggested-search-input"
              placeholder="Search recommended schemes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search recommended schemes"
            />
          </div>

          <div className="suggested-filter-tabs">
            <button
              type="button"
              className={`suggested-tab-btn ${filterTab === 'all' ? 'active' : ''}`}
              onClick={() => setFilterTab('all')}
            >
              <span>All</span>
              <span className="suggested-tab-count">{counts.all}</span>
            </button>

            <button
              type="button"
              className={`suggested-tab-btn ${filterTab === 'pass' ? 'active' : ''}`}
              onClick={() => setFilterTab('pass')}
            >
              <span>Eligible</span>
              <span className="suggested-tab-count">{counts.pass}</span>
            </button>

            <button
              type="button"
              className={`suggested-tab-btn ${filterTab === 'review' ? 'active' : ''}`}
              onClick={() => setFilterTab('review')}
            >
              <span>Review Required</span>
              <span className="suggested-tab-count">{counts.review}</span>
            </button>

            <button
              type="button"
              className={`suggested-tab-btn ${filterTab === 'unknown' ? 'active' : ''}`}
              onClick={() => setFilterTab('unknown')}
            >
              <span>Evaluation Pending</span>
              <span className="suggested-tab-count">{counts.unknown}</span>
            </button>

            {counts.fail > 0 && (
              <button
                type="button"
                className={`suggested-tab-btn ${filterTab === 'fail' ? 'active' : ''}`}
                onClick={() => setFilterTab('fail')}
              >
                <span>Not Eligible</span>
                <span className="suggested-tab-count">{counts.fail}</span>
              </button>
            )}
          </div>
        </section>

        {/* ------------------------------------------------------------------
            5. MAIN CONTENT AREA: SKELETON / ERROR / EMPTY / SCHEMES GRID
            ------------------------------------------------------------------ */}
        {isLoading ? (
          <div className="suggested-skeleton-grid" aria-label="Loading recommendations">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="suggested-skeleton-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <div className="skeleton-box" style={{ width: '46px', height: '46px' }} />
                  <div className="skeleton-box" style={{ width: '120px', height: '24px' }} />
                </div>
                <div className="skeleton-box" style={{ width: '60%', height: '14px' }} />
                <div className="skeleton-box" style={{ width: '90%', height: '22px' }} />
                <div className="skeleton-box" style={{ width: '100%', height: '40px' }} />
                <div className="skeleton-box" style={{ width: '100%', height: '60px' }} />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="suggested-error-state" role="alert">
            <div className="suggested-state-icon red">
              <AlertTriangle size={24} />
            </div>
            <h3 className="suggested-state-title">Unable to Load Suggested Schemes</h3>
            <p className="suggested-state-desc">
              We couldn't retrieve your recommendations right now. Please verify your internet connection or try again.
            </p>
            <button
              type="button"
              className="suggested-state-btn"
              onClick={() => loadRecommendations(false)}
            >
              <RefreshCw size={15} />
              <span>Retry</span>
            </button>
          </div>
        ) : filteredSchemes.length === 0 ? (
          <div className="suggested-empty-state">
            <div className="suggested-state-icon teal">
              <BookOpen size={24} />
            </div>
            <h3 className="suggested-state-title">
              {searchQuery || filterTab !== 'all' ? 'No Matching Schemes Found' : 'No Recommended Schemes Yet'}
            </h3>
            <p className="suggested-state-desc">
              {searchQuery || filterTab !== 'all'
                ? 'Try clearing your search query or switching to another filter tab.'
                : 'We need a little more information about your profile or documents to find relevant government schemes.'}
            </p>
            {searchQuery || filterTab !== 'all' ? (
              <button
                type="button"
                className="suggested-state-btn"
                onClick={() => {
                  setSearchQuery('');
                  setFilterTab('all');
                }}
              >
                <span>Reset Filters</span>
              </button>
            ) : (
              <button
                type="button"
                className="suggested-state-btn"
                onClick={() => navigate('/profile')}
              >
                <span>Complete Profile</span>
                <ArrowRight size={15} />
              </button>
            )}
          </div>
        ) : (
          <div className="suggested-schemes-grid">
            {filteredSchemes.map((scheme) => {
              const matchScore = Math.round(
                (scheme.overall_match_score || scheme.compatibility_score || scheme.relevance_score || 0.85) * 100
              );
              const reasons = Array.isArray(scheme.recommendation_reasons)
                ? scheme.recommendation_reasons.slice(0, 3)
                : [];
              const rawMissing = Array.isArray(scheme.missing_fields)
                ? scheme.missing_fields
                : [];
              const missingFields = rawMissing
                .map(m => (typeof m === 'object' && m !== null ? (m.field || m.name || '') : String(m)))
                .filter(f => !isInternalSentinel(f))
                .map(formatProfileFieldLabel);

              return (
                <div key={scheme.scheme_id || scheme.scheme_slug} className="suggested-scheme-card">
                  <div>
                    {/* Top row: Logo + Score & Statutory Status badges */}
                    <div className="suggested-card-top">
                      <div className="suggested-card-logo-box">
                        <SchemeLogo scheme={{ id: scheme.scheme_id, logoType: scheme.scheme_slug }} size={38} />
                      </div>
                      <div className="suggested-card-badges-row">
                        {isFallback || scheme.is_fallback ? (
                          <span
                            className="suggested-score-pill"
                            style={{ backgroundColor: '#F0F9FF', borderColor: '#B9E6FE', color: '#026AA2' }}
                            title="State & Category Matches from database"
                          >
                            <SlidersHorizontal size={11} />
                            <span>State & Category Matches</span>
                          </span>
                        ) : (
                          <span className="suggested-score-pill" title="Candidate profile compatibility score">
                            <Sparkles size={11} />
                            <span>{matchScore}% Match</span>
                          </span>
                        )}
                        {renderStatutoryBadge(scheme.eligibility_status)}
                      </div>
                    </div>

                    {/* Card Body */}
                    <div className="suggested-card-body" style={{ marginTop: '14px' }}>
                      <span className="suggested-card-authority">
                        {scheme.ministry || scheme.source_metadata?.ministry || 'Government of India'}
                      </span>
                      <h3 className="suggested-card-title">{scheme.scheme_name}</h3>
                      <p className="suggested-card-desc">
                        {scheme.benefit_summary || scheme.description || scheme.eligibility_summary || 'Official Government welfare initiative'}
                      </p>

                      {/* Benefit Banner */}
                      {(() => {
                        const interp = interpretFinancialBenefit(scheme);
                        return (
                          <div className="suggested-benefit-strip">
                            <span className="suggested-benefit-text">
                              {scheme.benefit_summary || interp.amountDisplay}
                            </span>
                          </div>
                        );
                      })()}

                      {/* Recommendation Reasons */}
                      {reasons.length > 0 && (
                        <div className="suggested-reasons-box">
                          <span className="suggested-reasons-title">Why this was recommended:</span>
                          <ul className="suggested-reasons-list">
                            {reasons.map((r, idx) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Missing fields alert */}
                      {missingFields.length > 0 && (
                        <div className="suggested-missing-alert">
                          <Info size={12} style={{ flexShrink: 0 }} />
                          <span>
                            Evaluation pending: missing {missingFields.slice(0, 2).join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Footer Actions */}
                  <div className="suggested-card-footer">
                    <button
                      type="button"
                      className="btn-suggested-details"
                      onClick={() => {
                        const targetId = scheme.scheme_slug || scheme.slug || scheme.scheme_id || scheme.id;
                        navigate(`/schemes/${targetId}`);
                      }}
                      aria-label={`View details for ${scheme.scheme_name}`}
                    >
                      <span>View Details</span>
                    </button>
                    <button
                      type="button"
                      className="btn-suggested-apply"
                      onClick={() => {
                        const targetId = scheme.scheme_slug || scheme.slug || scheme.scheme_id || scheme.id;
                        navigate(targetId ? `/schemes/${targetId}` : '/documents');
                      }}
                      aria-label={`Apply for ${scheme.scheme_name}`}
                    >
                      <span>Apply Now</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ------------------------------------------------------------------
            6. SCHEME DETAILS MODAL
            ------------------------------------------------------------------ */}
        {selectedSchemeForModal && (
          <div
            className="suggested-modal-backdrop"
            onClick={() => setSelectedSchemeForModal(null)}
          >
            <div
              className="suggested-modal-card"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-labelledby="modal-scheme-title"
            >
              <div className="suggested-modal-header">
                <div className="suggested-modal-header-meta">
                  <span className="suggested-modal-dept">
                    {selectedSchemeForModal.ministry || selectedSchemeForModal.source_metadata?.ministry || 'Government of India'}
                  </span>
                  <h2 id="modal-scheme-title" className="suggested-modal-title">
                    {selectedSchemeForModal.scheme_name}
                  </h2>
                </div>
                <button
                  type="button"
                  className="suggested-modal-close-btn"
                  onClick={() => setSelectedSchemeForModal(null)}
                  aria-label="Close scheme details"
                >
                  <X size={17} />
                </button>
              </div>

              <div className="suggested-modal-body">
                {/* Statutory Status & Compatibility */}
                <div className="suggested-modal-section">
                  <span className="suggested-modal-section-title">Statutory Eligibility Verdict</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
                    {renderStatutoryBadge(selectedSchemeForModal.eligibility_status)}
                    <span className="suggested-score-pill">
                      <Sparkles size={12} />
                      <span>
                        {Math.round(
                          (selectedSchemeForModal.overall_match_score ||
                            selectedSchemeForModal.compatibility_score ||
                            0.85) * 100
                        )}
                        % Match
                      </span>
                    </span>
                  </div>
                </div>

                {/* Benefits */}
                <div className="suggested-modal-section">
                  <span className="suggested-modal-section-title">Entitled Benefits & Financial Support</span>
                  <p className="suggested-modal-section-text">
                    {selectedSchemeForModal.benefit_summary ||
                      selectedSchemeForModal.description ||
                      'Direct statutory assistance, subsidies, or institutional credit access under official guidelines.'}
                  </p>
                </div>

                {/* Eligibility Summary */}
                {selectedSchemeForModal.eligibility_summary && (
                  <div className="suggested-modal-section">
                    <span className="suggested-modal-section-title">Eligibility Criteria</span>
                    <p className="suggested-modal-section-text">
                      {selectedSchemeForModal.eligibility_summary}
                    </p>
                  </div>
                )}

                {/* Why recommended */}
                {selectedSchemeForModal.recommendation_reasons &&
                  selectedSchemeForModal.recommendation_reasons.length > 0 && (
                    <div className="suggested-modal-section">
                      <span className="suggested-modal-section-title">Why this was recommended for you</span>
                      <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#334155', lineHeight: '1.6' }}>
                        {selectedSchemeForModal.recommendation_reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                {/* Required Documents */}
                {selectedSchemeForModal.documents_required &&
                  selectedSchemeForModal.documents_required.length > 0 && (
                    <div className="suggested-modal-section">
                      <span className="suggested-modal-section-title">Required Documents</span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                        {selectedSchemeForModal.documents_required.map((doc, i) => (
                          <span
                            key={i}
                            style={{
                              background: '#f1f5f9',
                              border: '1px solid #cbd5e1',
                              padding: '3px 8px',
                              borderRadius: '6px',
                              fontSize: '11.5px',
                              color: '#334155'
                            }}
                          >
                            {typeof doc === 'string' ? doc : doc.name || doc.id}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Missing information */}
                {selectedSchemeForModal.missing_fields &&
                  selectedSchemeForModal.missing_fields.length > 0 && (
                    <div className="suggested-modal-section">
                      <span className="suggested-modal-section-title">Information Needed for Final Approval</span>
                      <div className="suggested-conflict-banner" style={{ background: '#eff8ff', borderColor: '#b2ddff', color: '#175cd3' }}>
                        <Info size={16} style={{ flexShrink: 0 }} />
                        <div>
                          The recommendation engine requires the following facts to confirm statutory criteria:
                          <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                            {selectedSchemeForModal.missing_fields.map((mf, i) => (
                              <li key={i}>{typeof mf === 'string' ? mf : mf.reason || mf.field}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                {/* Evidence & Policy Provenance */}
                <div className="suggested-modal-section">
                  <span className="suggested-modal-section-title">Official Policy Provenance</span>
                  <div style={{ fontSize: '12px', color: '#64748b', lineHeight: '1.5' }}>
                    <div>
                      <strong>Source Authority:</strong>{' '}
                      {selectedSchemeForModal.source_metadata?.ministry || selectedSchemeForModal.ministry || 'Government of India'}
                    </div>
                    {selectedSchemeForModal.source_url && (
                      <div style={{ marginTop: '4px' }}>
                        <a
                          href={selectedSchemeForModal.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#005b50', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                          <span>Official Portal Reference</span>
                          <ExternalLink size={12} />
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="suggested-modal-footer">
                <button
                  type="button"
                  className="btn-suggested-details"
                  onClick={() => setSelectedSchemeForModal(null)}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="btn-suggested-details"
                  style={{ backgroundColor: '#F8FAFC', border: '1px solid #D0D5DD' }}
                  onClick={() => {
                    const targetId = selectedSchemeForModal.scheme_slug || selectedSchemeForModal.slug || selectedSchemeForModal.scheme_id || selectedSchemeForModal.id;
                    setSelectedSchemeForModal(null);
                    navigate(`/schemes/${targetId}`);
                  }}
                >
                  <span>Full Scheme Policy</span>
                  <ExternalLink size={13} style={{ marginLeft: '4px' }} />
                </button>
                <button
                  type="button"
                  className="btn-suggested-apply"
                  onClick={() => {
                    const targetId = selectedSchemeForModal.scheme_slug || selectedSchemeForModal.slug || selectedSchemeForModal.scheme_id || selectedSchemeForModal.id;
                    setSelectedSchemeForModal(null);
                    navigateToSchemeDocuments(navigate, targetId);
                  }}
                >
                  <span>Check Documents & Apply</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
