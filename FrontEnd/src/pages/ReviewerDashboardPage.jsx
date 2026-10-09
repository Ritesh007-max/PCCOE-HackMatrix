import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import PageContainer from '../components/layout/PageContainer';
import {
  fetchReviewerDashboardStats,
  fetchReviewerApplicationsQueue
} from '../services/reviewerService';
import {
  ShieldCheck,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  ArrowRight,
  FileText,
  User,
  Calendar,
  Layers,
  Sparkles
} from 'lucide-react';
import '../styles/reviewerDashboard.css';

export default function ReviewerDashboardPage() {
  const [stats, setStats] = useState({
    pending_reviews: 0,
    reviewed_today: 0,
    approved: 0,
    rejected: 0,
    action_required: 0,
    total_applications: 0
  });
  const [recentApps, setRecentApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsData, queueData] = await Promise.all([
        fetchReviewerDashboardStats(),
        fetchReviewerApplicationsQueue('all')
      ]);
      setStats(statsData);
      setRecentApps(queueData.slice(0, 6));
    } catch (err) {
      console.error('Failed to load reviewer dashboard data:', err);
      setError(err.message || 'Failed to load reviewer dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <PageContainer>
      <div className="reviewer-dashboard-container">
        {/* Header Hero Banner */}
        <div className="reviewer-header-banner">
          <div className="reviewer-header-badge">
            <ShieldCheck size={14} />
            <span>Government Application Review Workflow</span>
          </div>
          <h1 className="reviewer-header-title">Reviewer Control Desk</h1>
          <p className="reviewer-header-subtitle">
            Authoritative portal for statutory verification, document validation,
            and final ministerial approval decisions on citizen applications.
          </p>

          <div className="reviewer-header-actions">
            <Link to="/reviewer/applications" className="reviewer-btn-primary">
              <span>Open Review Queue</span>
              <ArrowRight size={15} />
            </Link>
            <button
              type="button"
              onClick={loadData}
              className="reviewer-btn-secondary"
              disabled={loading}
              title="Refresh Queue Metrics"
            >
              <RotateCw size={14} className={loading ? 'animate-spin' : ''} />
              <span>{loading ? 'Updating...' : 'Refresh Metrics'}</span>
            </button>
          </div>
        </div>

        {error && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: '#FEE2E2',
              color: '#B91C1C',
              borderRadius: '8px',
              marginBottom: '20px',
              fontSize: '13px'
            }}
          >
            {error}
          </div>
        )}

        {/* 5 Dynamic Metric Cards Grid */}
        <div className="reviewer-metrics-grid">
          {/* Card 1: Pending Reviews */}
          <Link
            to="/reviewer/applications?status=under_review"
            className="reviewer-metric-card"
          >
            <div className="reviewer-metric-header">
              <span className="reviewer-metric-label">Pending Reviews</span>
              <div className="reviewer-metric-icon-wrap amber">
                <Clock size={20} />
              </div>
            </div>
            <div className="reviewer-metric-val">{stats.pending_reviews}</div>
            <div className="reviewer-metric-sub">Awaiting officer action</div>
          </Link>

          {/* Card 2: Reviewed Today */}
          <div className="reviewer-metric-card">
            <div className="reviewer-metric-header">
              <span className="reviewer-metric-label">Reviewed Today</span>
              <div className="reviewer-metric-icon-wrap blue">
                <Calendar size={20} />
              </div>
            </div>
            <div className="reviewer-metric-val">{stats.reviewed_today}</div>
            <div className="reviewer-metric-sub">Processed in current shift</div>
          </div>

          {/* Card 3: Approved */}
          <Link
            to="/reviewer/applications?status=approved"
            className="reviewer-metric-card"
          >
            <div className="reviewer-metric-header">
              <span className="reviewer-metric-label">Approved</span>
              <div className="reviewer-metric-icon-wrap green">
                <CheckCircle2 size={20} />
              </div>
            </div>
            <div className="reviewer-metric-val">{stats.approved}</div>
            <div className="reviewer-metric-sub">Sanctioned & verified</div>
          </Link>

          {/* Card 4: Action Required */}
          <Link
            to="/reviewer/applications?status=action_required"
            className="reviewer-metric-card"
          >
            <div className="reviewer-metric-header">
              <span className="reviewer-metric-label">Action Required</span>
              <div className="reviewer-metric-icon-wrap purple">
                <AlertTriangle size={20} />
              </div>
            </div>
            <div className="reviewer-metric-val">{stats.action_required}</div>
            <div className="reviewer-metric-sub">Changes requested to citizen</div>
          </Link>

          {/* Card 5: Rejected */}
          <Link
            to="/reviewer/applications?status=rejected"
            className="reviewer-metric-card"
          >
            <div className="reviewer-metric-header">
              <span className="reviewer-metric-label">Rejected</span>
              <div className="reviewer-metric-icon-wrap red">
                <XCircle size={20} />
              </div>
            </div>
            <div className="reviewer-metric-val">{stats.rejected}</div>
            <div className="reviewer-metric-sub">Ineligible / incomplete</div>
          </Link>
        </div>

        {/* Priority Review Queue Preview */}
        <div className="reviewer-section">
          <div className="reviewer-section-header">
            <div>
              <h2 className="reviewer-section-title">Active Review Queue</h2>
              <p className="reviewer-section-sub">
                Applications submitted by citizens requiring administrative review
              </p>
            </div>
            <Link to="/reviewer/applications" className="reviewer-action-btn">
              <span>View Full Queue ({stats.total_applications})</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '30px', color: '#64748B' }}>
              Loading review applications...
            </div>
          ) : recentApps.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px', color: '#64748B' }}>
              No applications in the queue at this time.
            </div>
          ) : (
            <div className="reviewer-table-wrap">
              <table className="reviewer-table">
                <thead>
                  <tr>
                    <th>Application ID</th>
                    <th>Applicant</th>
                    <th>Scheme</th>
                    <th>Submission Date</th>
                    <th>Current Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentApps.map((app) => {
                    const statusClass = (app.status || 'under_review').toLowerCase();
                    const appId = app.id ? `FIN-${String(app.id).slice(0, 8).toUpperCase()}` : 'FIN-APP';
                    const dateStr = app.submitted_at || app.created_at
                      ? new Date(app.submitted_at || app.created_at).toLocaleDateString('en-GB')
                      : 'Recent';

                    return (
                      <tr key={app.id}>
                        <td>
                          <strong>{appId}</strong>
                        </td>
                        <td>{app.applicant_name || 'Citizen Applicant'}</td>
                        <td>
                          <strong>{app.scheme_name || 'Scheme Catalog Record'}</strong>
                        </td>
                        <td>{dateStr}</td>
                        <td>
                          <span className={`reviewer-badge ${statusClass}`}>
                            {statusClass.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td>
                          <Link
                            to={`/reviewer/applications?open=${app.id}`}
                            className="reviewer-action-btn"
                          >
                            <span>Inspect & Review</span>
                            <ArrowRight size={12} />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Statutory Invariant Banner */}
        <div className="reviewer-evidence-banner">
          <ShieldCheck size={24} />
          <div>
            <h4 className="reviewer-evidence-title">
              Evidence-First Governance Principle
            </h4>
            <p className="reviewer-evidence-desc">
              FIN AI provides assisted fact-extraction and policy eligibility analysis.
              In accordance with administrative regulations, AI will never mutate application
              status or finalize decisions automatically. Human review officers remain the final
              statutory decision authority.
            </p>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
