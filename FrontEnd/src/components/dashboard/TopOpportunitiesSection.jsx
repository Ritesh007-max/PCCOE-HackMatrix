import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Headphones
} from 'lucide-react';
import { TricolorRibbon } from '../common/BrandAssets';
import ashokStambhSvg from '../../assets/ashok_stambh_vector.svg';
import msmeSvg from '../../assets/msme_logo_vector.svg';
import kisanSvg from '../../assets/kisan_logo_vector.svg';

export default function TopOpportunitiesSection({ opportunities = [] }) {
  const navigate = useNavigate();

  const renderEmblem = (type) => {
    if (type === 'ashoka') {
      return (
        <img
          src={ashokStambhSvg}
          alt="State Emblem of India (Ashok Stambh)"
          className="scheme-emblem-img ashoka"
        />
      );
    }
    if (type === 'msme') {
      return (
        <img
          src={msmeSvg}
          alt="MSME Government of India"
          className="scheme-emblem-img msme"
        />
      );
    }
    if (type === 'kisan') {
      return (
        <img
          src={kisanSvg}
          alt="PM Kisan Agriculture"
          className="scheme-emblem-img kisan"
        />
      );
    }
    return (
      <img
        src={ashokStambhSvg}
        alt="State Emblem of India"
        className="scheme-emblem-img ashoka"
      />
    );
  };

  const renderStatusIcon = (type) => {
    if (type === 'warning') return <AlertTriangle size={16} color="#C56A00" />;
    return <CheckCircle2 size={16} color="#087443" />;
  };

  return (
    <section className="dashboard-opportunities-section" aria-label="Top Opportunities">
      <div className="section-header-row">
        <div>
          <h2 className="section-title-large">Top Opportunities for You</h2>
          <p className="section-subtitle-text">
            Personalized schemes based on your profile, sorted by relevance.
          </p>
        </div>
        <Link to="/discover" className="section-view-all-link">
          <span>View All Schemes</span>
          <ArrowRight size={16} />
        </Link>
      </div>

      <div className="opportunities-main-grid">
        {opportunities.length === 0 && (
          <div className="scheme-card-box" style={{ padding: '36px 20px', textAlign: 'center', gridColumn: 'span 2' }}>
            <p style={{ color: '#475467', marginBottom: '12px', fontSize: '14px' }}>
              No personalized scheme recommendations computed yet.
            </p>
            <Link to="/discover" className="btn btn-outline" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span>Browse All Schemes</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        )}
        {/* Scheme Cards */}
        {opportunities.map((scheme) => (
          <article
            key={scheme.id}
            className="scheme-card-box clickable-scheme-card"
            onClick={() => navigate(`/schemes/${scheme.id}`)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                navigate(`/schemes/${scheme.id}`);
              }
            }}
            title={`View ${scheme.name} Details`}
            style={{ cursor: 'pointer' }}
          >
            <div className="scheme-card-body">
              <div className="scheme-card-top">
                <div className="scheme-logo-container">
                  {renderEmblem(scheme.emblemType)}
                </div>
                <span className={`badge ${scheme.matchBadgeClass}`}>
                  {scheme.matchRate}
                </span>
              </div>

              <h3 className="scheme-card-name" title={scheme.name}>
                <Link
                  to={`/schemes/${scheme.id}`}
                  onClick={(e) => e.stopPropagation()}
                  style={{ color: 'inherit', textDecoration: 'none' }}
                >
                  {scheme.name}
                </Link>
              </h3>
              <p className="scheme-card-full-name" title={scheme.fullName}>{scheme.fullName}</p>

              <div className="scheme-tags-row">
                {scheme.tags.map((tag) => (
                  <span key={tag} className="scheme-tag-pill">
                    {tag}
                  </span>
                ))}
              </div>

              <div className="scheme-metric-box">
                <Clock size={16} className="scheme-metric-icon" />
                <div>
                  <div className="scheme-metric-val">{scheme.estimatedBenefit}</div>
                  <div className="scheme-metric-lbl">Estimated Benefit</div>
                </div>
              </div>
            </div>

            <div className="scheme-card-bottom">
              <div className="condition-match-status">
                {renderStatusIcon(scheme.conditionType)}
                <span>{scheme.conditionText}</span>
              </div>

              <Link
                to={`/schemes/${scheme.id}`}
                className="btn-circular-arrow"
                aria-label={`View details for ${scheme.name}`}
                title="View Scheme Details"
                onClick={(e) => e.stopPropagation()}
              >
                <ArrowRight size={16} />
              </Link>
            </div>
          </article>
        ))}
      </div>

      {/* Quote card and Need Help card placed below the opportunities card */}
      <div className="opportunities-bottom-widgets">
        {/* Top Quote Card */}
        <div className="side-quote-card">
          <TrendingUp size={24} className="side-quote-icon" />
          <p className="side-quote-text">
            “A more inclusive India grows with informed citizens.”
          </p>
          <TricolorRibbon width={44} height={4} />
        </div>

        {/* Need Help? Card */}
        <div className="side-help-card">
          <div>
            <div className="side-help-icon-wrap" aria-hidden="true">
              <Headphones size={20} />
            </div>
            <h4 className="side-help-title">Need Help?</h4>
            <p className="side-help-desc">Read our guide or contact support.</p>
          </div>
          <Link to="/documents" className="btn-guidance">
            <span>Get Guidance</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </section>
  );
}
