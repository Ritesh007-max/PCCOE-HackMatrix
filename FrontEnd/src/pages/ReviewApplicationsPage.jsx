import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import PageContainer from '../components/layout/PageContainer';
import {
  fetchReviewerApplicationsQueue,
  fetchApplicationReviewDetails,
  submitReviewDecision
} from '../services/reviewerService';
import {
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  FileText,
  User,
  ExternalLink,
  X,
  Clock,
  Check,
  ArrowRight,
  Info,
  Calendar,
  Building,
  Award,
  Download
} from 'lucide-react';
import '../styles/reviewApplications.css';

export default function ReviewApplicationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get('status') || 'all';
  const openAppId = searchParams.get('open');

  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [searchQuery, setSearchQuery] = useState('');
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Detail Modal State
  const [selectedAppId, setSelectedAppId] = useState(openAppId || null);
  const [appDetails, setAppDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Decision Modal State
  const [decisionModal, setDecisionModal] = useState({
    isOpen: false,
    decisionType: null, // 'approve' | 'request_changes' | 'reject'
    remark: '',
    error: ''
  });
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [successToast, setSuccessToast] = useState(null);

  // Fetch queue
  const loadQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchReviewerApplicationsQueue(statusFilter);
      setApplications(data);
    } catch (err) {
      console.error('Error fetching reviewer queue:', err);
      setError(err.message || 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [statusFilter]);

  // Load details if selected
  useEffect(() => {
    if (!selectedAppId) {
      setAppDetails(null);
      return;
    }
    const loadDetails = async () => {
      try {
        setLoadingDetails(true);
        const data = await fetchApplicationReviewDetails(selectedAppId);
        setAppDetails(data);
      } catch (err) {
        console.error('Error loading application details:', err);
        setError(`Failed to load details: ${err.message}`);
      } finally {
        setLoadingDetails(false);
      }
    };
    loadDetails();
  }, [selectedAppId]);

  // Filtered applications
  const filteredApps = applications.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const id = String(app.id || '').toLowerCase();
    const name = String(app.applicant_name || '').toLowerCase();
    const scheme = String(app.scheme_name || '').toLowerCase();
    return id.includes(q) || name.includes(q) || scheme.includes(q);
  });

  const handleOpenDecision = (decisionType) => {
    setDecisionModal({
      isOpen: true,
      decisionType,
      remark: decisionType === 'approve' ? 'Approved after statutory document verification' : '',
      error: ''
    });
  };

  const handleConfirmDecision = async () => {
    const { decisionType, remark } = decisionModal;
    if ((decisionType === 'reject' || decisionType === 'request_changes') && !remark.trim()) {
      setDecisionModal(prev => ({
        ...prev,
        error: `A mandatory remark is required to ${decisionType === 'reject' ? 'reject' : 'request changes'}.`
      }));
      return;
    }

    try {
      setSubmittingDecision(true);
      await submitReviewDecision(selectedAppId, {
        decision: decisionType,
        remark: remark.trim()
      });

      setSuccessToast(`Application successfully marked as ${decisionType === 'approve' ? 'Approved' : decisionType === 'request_changes' ? 'Action Required' : 'Rejected'}.`);
      setTimeout(() => setSuccessToast(null), 4000);

      setDecisionModal({ isOpen: false, decisionType: null, remark: '', error: '' });
      setSelectedAppId(null);
      setSearchParams({});
      loadQueue();
    } catch (err) {
      setDecisionModal(prev => ({
        ...prev,
        error: err.message || 'Failed to submit decision'
      }));
    } finally {
      setSubmittingDecision(false);
    }
  };

  return (
    <PageContainer>
      <div className="review-apps-container">
        {/* Header */}
        <div className="review-apps-header">
          <div>
            <h1 className="review-apps-title">Application Review Queue</h1>
            <p className="review-apps-subtitle">
              Verify submitted documents, evaluate scheme conditions, and record auditable government decisions.
            </p>
          </div>

          <button
            type="button"
            onClick={loadQueue}
            className="reviewer-btn-secondary"
            style={{ color: '#0F172A', borderColor: '#CBD5E1', background: '#FFFFFF' }}
            disabled={loading}
          >
            <RotateCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh Queue</span>
          </button>
        </div>

        {/* Success Toast */}
        {successToast && (
          <div
            style={{
              padding: '12px 18px',
              backgroundColor: '#DCFCE7',
              border: '1px solid #86EFAC',
              color: '#15803D',
              borderRadius: '8px',
              marginBottom: '16px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <CheckCircle2 size={18} />
            <span>{successToast}</span>
          </div>
        )}

        {/* Filter Controls Row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            marginBottom: '20px',
            flexWrap: 'wrap'
          }}
        >
          {/* Status Tabs */}
          <div className="review-filter-tabs">
            {[
              { id: 'all', label: 'All Applications' },
              { id: 'under_review', label: 'Pending Review' },
              { id: 'action_required', label: 'Action Required' },
              { id: 'approved', label: 'Approved' },
              { id: 'rejected', label: 'Rejected' }
            ].map(tab => (
              <button
                key={tab.id}
                type="button"
                className={`review-tab-btn ${statusFilter === tab.id ? 'active' : ''}`}
                onClick={() => {
                  setStatusFilter(tab.id);
                  setSearchParams(tab.id === 'all' ? {} : { status: tab.id });
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative', width: '280px' }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#94A3B8'
              }}
            />
            <input
              type="text"
              placeholder="Search by ID, applicant, scheme..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px 8px 34px',
                border: '1px solid #CBD5E1',
                borderRadius: '8px',
                fontSize: '13px',
                boxSizing: 'border-box'
              }}
            />
          </div>
        </div>

        {/* Queue Table */}
        <div className="reviewer-section" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#64748B' }}>
              Loading review queue...
            </div>
          ) : filteredApps.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#64748B' }}>
              No applications matching the selected criteria.
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
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredApps.map((app) => {
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
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedAppId(app.id);
                              setSearchParams({ open: app.id });
                            }}
                            className="reviewer-action-btn"
                          >
                            <span>Inspect & Decide</span>
                            <ArrowRight size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Application Inspection Drawer/Modal */}
        {selectedAppId && (
          <div
            className="review-modal-backdrop"
            onClick={() => {
              setSelectedAppId(null);
              setSearchParams({});
            }}
          >
            <div
              className="review-modal-card"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="review-modal-header">
                <div>
                  <h3 className="review-modal-title">
                    Application Review: FIN-{String(selectedAppId).slice(0, 8).toUpperCase()}
                  </h3>
                  <p className="review-modal-sub">
                    {appDetails?.application?.scheme_name || 'Statutory Scheme Review'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedAppId(null);
                    setSearchParams({});
                  }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B' }}
                >
                  <X size={20} />
                </button>
              </div>

              {/* Modal Body */}
              <div className="review-modal-body">
                {loadingDetails ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#64748B' }}>
                    Loading full application dossier & documents...
                  </div>
                ) : !appDetails ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#DC2626' }}>
                    Failed to load application details.
                  </div>
                ) : (
                  <>
                    {/* Top 2 Columns: Scheme & Applicant Profile */}
                    <div className="review-grid-2col">
                      {/* Left Panel: Scheme Info & Benefits */}
                      <div className="review-card-panel">
                        <h4 className="review-panel-title">
                          <Building size={16} />
                          <span>Scheme Information</span>
                        </h4>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Scheme Title</span>
                          <span className="review-fact-val">{appDetails.application.scheme_name || 'N/A'}</span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Benefit Category</span>
                          <span className="review-fact-val">{appDetails.application.benefit_subtitle || 'Statutory Assistance'}</span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Financial Value</span>
                          <span className="review-fact-val" style={{ color: '#16A34A' }}>
                            {appDetails.application.benefit_display || 'Not specified'}
                          </span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Current Status</span>
                          <span className="review-fact-val">
                            <span className={`reviewer-badge ${appDetails.application.status}`}>
                              {String(appDetails.application.status).replace(/_/g, ' ')}
                            </span>
                          </span>
                        </div>
                        {appDetails.application.decision_notes && (
                          <div style={{ marginTop: '12px', padding: '10px', background: '#F1F5F9', borderRadius: '6px', fontSize: '12px' }}>
                            <strong>Existing Reviewer Note:</strong> {appDetails.application.decision_notes}
                          </div>
                        )}
                      </div>

                      {/* Right Panel: Applicant Profile Facts */}
                      <div className="review-card-panel">
                        <h4 className="review-panel-title">
                          <User size={16} />
                          <span>Applicant Profile Dossier</span>
                        </h4>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Full Name</span>
                          <span className="review-fact-val">{appDetails.applicant.fullName || 'Applicant'}</span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Email</span>
                          <span className="review-fact-val">{appDetails.applicant.email || 'N/A'}</span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Phone</span>
                          <span className="review-fact-val">{appDetails.applicant.phone || 'N/A'}</span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Occupation</span>
                          <span className="review-fact-val">{appDetails.applicant.profile?.occupation || 'Not specified'}</span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">State / District</span>
                          <span className="review-fact-val">
                            {[appDetails.applicant.profile?.district, appDetails.applicant.profile?.state].filter(Boolean).join(', ') || 'Not specified'}
                          </span>
                        </div>
                        <div className="review-fact-row">
                          <span className="review-fact-label">Annual Income</span>
                          <span className="review-fact-val">
                            {appDetails.applicant.profile?.annual_income ? `₹${Number(appDetails.applicant.profile.annual_income).toLocaleString('en-IN')}` : 'Not specified'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Associated Documents Section */}
                    <div style={{ marginBottom: '24px' }}>
                      <h4 className="review-panel-title">
                        <FileText size={16} />
                        <span>Associated Verification Documents ({appDetails.documents.length})</span>
                      </h4>

                      {appDetails.documents.length === 0 ? (
                        <div style={{ padding: '16px', background: '#F8FAFC', borderRadius: '8px', color: '#64748B', fontSize: '13px' }}>
                          No documents uploaded for this application.
                        </div>
                      ) : (
                        <div className="review-docs-list">
                          {appDetails.documents.map((doc) => (
                            <div key={doc.id} className="review-doc-card">
                              <div className="review-doc-info">
                                <div className="review-doc-icon">
                                  <FileText size={18} />
                                </div>
                                <div>
                                  <h5 className="review-doc-name">{doc.fileName || doc.documentType}</h5>
                                  <div className="review-doc-meta">
                                    <span>Type: {doc.documentType}</span>
                                    <span>Status: <strong>{doc.verificationStatus}</strong></span>
                                    {doc.ocr?.confidence && (
                                      <span className="ocr-chip">
                                        OCR Confidence: {Math.round(doc.ocr.confidence * 100)}%
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <div>
                                {doc.fileUrl ? (
                                  <a
                                    href={doc.fileUrl}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="reviewer-action-btn"
                                  >
                                    <span>View Document</span>
                                    <ExternalLink size={12} />
                                  </a>
                                ) : (
                                  <span style={{ fontSize: '12px', color: '#94A3B8' }}>Vault Encrypted</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Review History / Timeline */}
                    <div>
                      <h4 className="review-panel-title">
                        <Clock size={16} />
                        <span>Auditable Review Timeline</span>
                      </h4>

                      {appDetails.reviewHistory.length === 0 ? (
                        <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '8px', color: '#64748B', fontSize: '12.5px' }}>
                          No prior decisions recorded. Application is awaiting initial officer review.
                        </div>
                      ) : (
                        <div className="review-timeline">
                          {appDetails.reviewHistory.map((rev) => (
                            <div key={rev.id} className={`review-timeline-item ${rev.status || rev.decision}`}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                <strong>Decision: {String(rev.decision || rev.status).toUpperCase()}</strong>
                                <span style={{ color: '#64748B' }}>{new Date(rev.createdAt).toLocaleString('en-IN')}</span>
                              </div>
                              <div><strong>Reviewer:</strong> {rev.reviewerName}</div>
                              {rev.remark && (
                                <div style={{ marginTop: '4px', fontStyle: 'italic', color: '#334155' }}>
                                  "{rev.remark}"
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Modal Decision Actions Bar */}
              {appDetails && (
                <div className="review-actions-bar">
                  <div style={{ fontSize: '12.5px', color: '#64748B' }}>
                    Reviewer actions alter application state and generate persistent citizen notifications.
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      type="button"
                      onClick={() => handleOpenDecision('request_changes')}
                      className="btn-request-changes"
                    >
                      <AlertTriangle size={15} />
                      <span>Request Changes</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleOpenDecision('reject')}
                      className="btn-reject"
                    >
                      <XCircle size={15} />
                      <span>Reject</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleOpenDecision('approve')}
                      className="btn-approve"
                    >
                      <CheckCircle2 size={15} />
                      <span>Approve</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Decision Remark Dialog */}
        {decisionModal.isOpen && (
          <div className="decision-dialog-backdrop">
            <div className="decision-dialog-card">
              <h3 className="decision-dialog-title">
                {decisionModal.decisionType === 'approve' && 'Approve Government Application'}
                {decisionModal.decisionType === 'request_changes' && 'Request Application Modifications'}
                {decisionModal.decisionType === 'reject' && 'Reject Government Application'}
              </h3>

              <p className="decision-dialog-sub">
                {decisionModal.decisionType === 'approve' &&
                  'Application will transition to Approved status. Add an optional administrative approval remark for the citizen.'}
                {decisionModal.decisionType === 'request_changes' &&
                  'Application will transition to Action Required. You MUST provide a clear remark instructing the applicant on what documents or facts need rectification.'}
                {decisionModal.decisionType === 'reject' &&
                  'Application will transition to Rejected. You MUST provide an official administrative justification for rejection.'}
              </p>

              {decisionModal.error && (
                <div style={{ padding: '8px 12px', background: '#FEE2E2', color: '#B91C1C', borderRadius: '6px', marginBottom: '12px', fontSize: '13px' }}>
                  {decisionModal.error}
                </div>
              )}

              <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                Reviewer Remark {decisionModal.decisionType !== 'approve' && <span style={{ color: '#DC2626' }}>* (Mandatory)</span>}
              </label>

              <textarea
                className="decision-textarea"
                placeholder={
                  decisionModal.decisionType === 'approve'
                    ? 'Enter approval notes (optional)...'
                    : 'Enter detailed statutory reason or instructions for the citizen (required)...'
                }
                value={decisionModal.remark}
                onChange={(e) => setDecisionModal(prev => ({ ...prev, remark: e.target.value, error: '' }))}
              />

              <div className="decision-dialog-footer">
                <button
                  type="button"
                  className="reviewer-btn-secondary"
                  style={{ color: '#0F172A', borderColor: '#CBD5E1', background: '#FFFFFF' }}
                  onClick={() => setDecisionModal({ isOpen: false, decisionType: null, remark: '', error: '' })}
                  disabled={submittingDecision}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className={
                    decisionModal.decisionType === 'approve' ? 'btn-approve' :
                    decisionModal.decisionType === 'request_changes' ? 'btn-request-changes' : 'btn-reject'
                  }
                  onClick={handleConfirmDecision}
                  disabled={submittingDecision}
                >
                  <span>{submittingDecision ? 'Submitting...' : 'Confirm Decision'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
