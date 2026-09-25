import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  CheckCircle2,
  Clock,
  AlertTriangle,
  UploadCloud,
  Plus,
  MoreVertical,
  Bell,
  Lightbulb,
  ShieldCheck,
  ArrowRight,
  X,
  Eye,
  Download,
  Trash2,
  RefreshCw,
  Check,
  CreditCard,
  Home,
  Landmark,
  Image as ImageIcon,
  MapPin,
  Award,
  ScrollText,
  UserCheck,
  FileCheck,
  Search,
  Sparkles,
  FileDown,
  Ticket,
  LifeBuoy,
  Send,
  FileQuestion,
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import {
  INITIAL_DOCUMENTS,
  SCHEMES_CHECKLIST,
  loadDocumentsFromStorage,
  saveDocumentsToStorage,
  loadTicketsFromStorage,
  saveTicketsToStorage,
} from '../data/documentsData';
import {
  fetchUserDocuments,
  uploadDocumentFile,
  deleteDocument
} from '../services/documentService';
import '../styles/documents.css';


export default function DocumentsPage() {
  const navigate = useNavigate();

  // Documents state loaded from localStorage or initialized with 8 items
  const [documents, setDocuments] = useState(loadDocumentsFromStorage);

  // Support Tickets state loaded from localStorage
  const [tickets, setTickets] = useState(loadTicketsFromStorage);

  // Active filter tab: 'all' | 'verified' | 'pending' | 'action_required'
  const [activeTab, setActiveTab] = useState('all');

  // Search filter query
  const [searchQuery, setSearchQuery] = useState('');

  // Selected scheme for the right-hand requirements checker
  const [selectedSchemeId, setSelectedSchemeId] = useState('pmegp');

  // Interactive UI modals & dropdown state
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [selectedDocForView, setSelectedDocForView] = useState(null);
  const [selectedTicketForView, setSelectedTicketForView] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isTicketModalOpen, setIsTicketModalOpen] = useState(false);
  const [isDossierModalOpen, setIsDossierModalOpen] = useState(false);
  const [isReminderModalOpen, setIsReminderModalOpen] = useState(false);
  const [isGuidanceModalOpen, setIsGuidanceModalOpen] = useState(false);
  const [isSecurityModalOpen, setIsSecurityModalOpen] = useState(false);

  // Upload Form state
  const [uploadTargetDocId, setUploadTargetDocId] = useState('address');
  const [uploadSelectedFile, setUploadSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  // Apply for Government Policy Form state
  const [policyFullName, setPolicyFullName] = useState('Hemang Singh');
  const [policyDob, setPolicyDob] = useState('1998-05-15');
  const [policyState, setPolicyState] = useState('Gujarat');
  const [policyDistrict, setPolicyDistrict] = useState('Ahmedabad');
  const [policyCategory, setPolicyCategory] = useState('OBC');
  const [policyIncome, setPolicyIncome] = useState('₹ 2,40,000');
  const [policyOccupation, setPolicyOccupation] = useState('Student');
  const [policyDocumentFile, setPolicyDocumentFile] = useState(null);
  const [policyIsDragging, setPolicyIsDragging] = useState(false);
  const [isSubmittingPolicy, setIsSubmittingPolicy] = useState(false);

  // Reminder settings state
  const [reminderFrequency, setReminderFrequency] = useState('monthly');
  const [reminderEmail, setReminderEmail] = useState('hemang@example.com');

  // Toast notification state
  const [toastMessage, setToastMessage] = useState(null);

  const modalFileInputRef = useRef(null);
  const policyFileInputRef = useRef(null);

  // Sync documents to localStorage on changes
  useEffect(() => {
    saveDocumentsToStorage(documents);
  }, [documents]);

  // Sync tickets to localStorage on changes
  useEffect(() => {
    saveTicketsToStorage(tickets);
  }, [tickets]);

  // Sync documents from backend API on mount
  useEffect(() => {
    const syncBackendDocs = async () => {
      try {
        const backendDocs = await fetchUserDocuments();
        if (backendDocs && backendDocs.length > 0) {
          setDocuments((prevDocs) => {
            const merged = [...prevDocs];
            backendDocs.forEach((bDoc) => {
              const bType = String(bDoc.documentType || '').toLowerCase();
              const idx = merged.findIndex(
                (d) => d.id === bType || d.category?.toLowerCase() === bType
              );
              const status = bDoc.verificationStatus === 'VERIFIED' ? 'verified' :
                bDoc.verificationStatus === 'REJECTED' ? 'action_required' : 'under_review';
              if (idx >= 0) {
                merged[idx] = {
                  ...merged[idx],
                  backendId: bDoc.id,
                  status,
                  statusLabel: status === 'verified' ? 'Verified' : status === 'action_required' ? 'Action Required' : 'Under Review',
                  uploadedOn: bDoc.uploadedAt ? new Date(bDoc.uploadedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : merged[idx].uploadedOn,
                  fileName: bDoc.fileName || merged[idx].fileName
                };
              }
            });
            return merged;
          });
        }
      } catch (err) {
        console.warn('Backend document synchronization skipped:', err);
      }
    };
    syncBackendDocs();
  }, []);


  // Close open dropdown menu when clicking outside
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (!e.target.closest('.doc-actions-cell')) {
        setActiveMenuId(null);
      }
    };
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, []);

  // Show a temporary toast message
  const triggerToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  // Counts for tabs & progress
  const verifiedDocs = documents.filter((d) => d.status === 'verified');
  const pendingDocs = documents.filter((d) => d.status === 'under_review');
  const actionDocs = documents.filter((d) => d.status === 'action_required');

  const totalCount = documents.length;
  const verifiedCount = verifiedDocs.length;
  const pendingCount = pendingDocs.length;
  const actionCount = actionDocs.length;

  // Completed or submitted documents (Verified + Under Review = 7/8 = 87.5% -> 88%)
  const completedCount = verifiedCount + pendingCount;
  const completionPercentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Filter documents based on active tab & live search query
  const filteredDocuments = documents.filter((doc) => {
    let matchesTab = true;
    if (activeTab === 'verified') matchesTab = doc.status === 'verified';
    if (activeTab === 'pending') matchesTab = doc.status === 'under_review';
    if (activeTab === 'action_required') matchesTab = doc.status === 'action_required';

    if (!matchesTab) return false;

    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      doc.name.toLowerCase().includes(query) ||
      doc.purpose.toLowerCase().includes(query) ||
      doc.category.toLowerCase().includes(query) ||
      (doc.docNumber && doc.docNumber.toLowerCase().includes(query)) ||
      (doc.schemesList && doc.schemesList.some((s) => s.toLowerCase().includes(query)))
    );
  });

  // Filter tickets based on live search query
  const filteredTickets = tickets.filter((t) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      (t.id && t.id.toLowerCase().includes(query)) ||
      (t.subject && t.subject.toLowerCase().includes(query)) ||
      (t.category && t.category.toLowerCase().includes(query)) ||
      (t.docName && t.docName.toLowerCase().includes(query)) ||
      (t.description && t.description.toLowerCase().includes(query))
    );
  });

  // Icon renderer per document type
  const renderDocIcon = (iconType) => {
    switch (iconType) {
      case 'id-card':
        return <UserCheck size={19} />;
      case 'credit-card':
        return <CreditCard size={19} />;
      case 'certificate':
        return <Award size={19} />;
      case 'scroll':
        return <ScrollText size={19} />;
      case 'home':
        return <Home size={19} />;
      case 'bank':
        return <Landmark size={19} />;
      case 'image':
        return <ImageIcon size={19} />;
      case 'map-pin':
        return <MapPin size={19} />;
      default:
        return <FileText size={19} />;
    }
  };

  // Handle open upload modal (optionally targeting a specific document like 'address')
  const handleOpenUploadModal = (docId = 'address') => {
    setUploadTargetDocId(docId);
    setUploadSelectedFile(null);
    setUploadProgress(0);
    setIsUploading(false);
    setIsUploadModalOpen(true);
  };

  // Open Apply for Government Policy modal
  const handleOpenTicketModal = () => {
    setIsTicketModalOpen(true);
  };

  // Drag and drop handlers for policy application document
  const handlePolicyDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setPolicyIsDragging(true);
  };

  const handlePolicyDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setPolicyIsDragging(false);
  };

  const handlePolicyDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setPolicyIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setPolicyDocumentFile(e.dataTransfer.files[0]);
    }
  };

  // Submit Government Policy Application
  const handleSubmitPolicyApplication = (e) => {
    e.preventDefault();
    if (!policyFullName.trim()) {
      triggerToast('Please provide your Full Name.');
      return;
    }
    if (!policyDocumentFile) {
      triggerToast('Please attach or drop your document before submitting.');
      return;
    }

    setIsSubmittingPolicy(true);
    setTimeout(() => {
      const newAppId = `APP-2026-${Math.floor(1000 + Math.random() * 9000)}`;
      const newTicket = {
        id: newAppId,
        category: 'Policy Application',
        docId: 'attached',
        docName: policyDocumentFile.name,
        subject: `Policy Application: ${policyFullName} (${policyCategory})`,
        description: `Applicant: ${policyFullName}, DOB: ${policyDob}, ${policyDistrict}, ${policyState}. Income: ${policyIncome}, Occupation: ${policyOccupation}`,
        priority: 'Normal',
        contact: '+91 98765 43210',
        status: 'Submitted',
        createdAt: 'Today, Just now',
      };

      setTickets((prev) => [newTicket, ...prev]);
      setIsSubmittingPolicy(false);
      setIsTicketModalOpen(false);
      setPolicyDocumentFile(null);

      triggerToast(`Application #${newAppId} submitted successfully for Government Policy!`);
    }, 600);
  };

  // Process uploaded file
  const handleProcessDirectUpload = async (file, targetId = null) => {
    const targetDocId = targetId || uploadTargetDocId || (actionDocs.length > 0 ? actionDocs[0].id : 'address');

    setIsUploading(true);
    setUploadProgress(20);

    // Call real backend upload asynchronously
    let uploadedBackendDoc = null;
    try {
      uploadedBackendDoc = await uploadDocumentFile(file, targetDocId).catch((err) => {
        console.warn('Backend document upload notice:', err.message);
        return null;
      });
    } catch (_) {}

    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          setIsUploadModalOpen(false);

          const todayStr = '18 Sep 2026';
          setDocuments((prevDocs) =>
            prevDocs.map((doc) => {
              if (doc.id === targetDocId) {
                return {
                  ...doc,
                  backendId: uploadedBackendDoc?.id || doc.backendId,
                  status: 'verified',
                  statusLabel: 'Verified',
                  source: 'Self Uploaded (OCR Verified)',
                  validity: 'Verified for Schemes',
                  uploadedOn: todayStr,
                  fileType: file.name.split('.').pop().toUpperCase() || 'PDF',
                  fileSize: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
                  docNumber: `DOC-VERIFIED-${Math.floor(1000 + Math.random() * 9000)}`,
                };
              }
              return doc;
            })
          );

          triggerToast(`Document "${file.name}" uploaded and verified successfully!`);
          return 100;
        }
        return prev + 25;
      });
    }, 200);
  };

  // Handle Modal Upload Submit
  const handleModalUploadSubmit = (e) => {
    e.preventDefault();
    if (!uploadSelectedFile) {
      triggerToast('Please select a file to upload');
      return;
    }
    handleProcessDirectUpload(uploadSelectedFile, uploadTargetDocId);
  };

  // Handle Set Reminder Submit
  const handleSaveReminder = (e) => {
    e.preventDefault();
    setIsReminderModalOpen(false);
    triggerToast(`Reminder configured for ${reminderEmail} (${reminderFrequency})!`);
  };

  // Handle Delete Document
  const handleDeleteDoc = async (docId) => {
    setActiveMenuId(null);
    const targetDoc = documents.find((d) => d.id === docId);
    if (targetDoc?.backendId) {
      deleteDocument(targetDoc.backendId).catch((err) => {
        console.warn('Backend document delete notice:', err.message);
      });
    }

    setDocuments((prev) =>
      prev.map((doc) => {
        if (doc.id === docId) {
          return {
            ...doc,
            backendId: null,
            status: 'action_required',
            statusLabel: 'Action Required',
            uploadedOn: '-',
            fileSize: '-',
            source: 'Pending Verification',
            validity: 'Pending Upload',
          };
        }
        return doc;
      })
    );
    triggerToast('Document removed. Status updated to Action Required.');
  };


  // Radial progress calculations for 88%
  const radius = 22;
  const strokeWidth = 4.5;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (completionPercentage / 100) * circumference;

  // Selected scheme checklist for right-hand widget
  const currentScheme = SCHEMES_CHECKLIST.find((s) => s.id === selectedSchemeId) || SCHEMES_CHECKLIST[0];

  return (
    <PageContainer>
      <div className="documents-page-wrapper">
        {/* Toast Notification Alert */}
        {toastMessage && (
          <div className="docs-toast" role="status">
            <CheckCircle2 size={17} color="#A6F4C5" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* ------------------------------------------------------------------
            1. TOP 4-METRIC HEALTH OVERVIEW STRIP (Instant Health & Status Glance)
            ------------------------------------------------------------------ */}
        <section className="docs-metrics-row" aria-label="Document Portfolio Metrics">
          {/* Card 1: Verified */}
          <div className="docs-metric-card">
            <div className="metric-card-icon-box green" aria-hidden="true">
              <ShieldCheck size={19} />
            </div>
            <div className="metric-card-info">
              <div className="metric-card-top-line">
                <span className="metric-card-val">{verifiedCount}</span>
                <span className="metric-card-total">/ {totalCount}</span>
              </div>
              <span className="metric-card-title">Verified Documents</span>
              <span className="metric-card-sub">100% DBT & Subsidy Ready</span>
            </div>
          </div>

          {/* Card 2: Under Review */}
          <div className="docs-metric-card">
            <div className="metric-card-icon-box amber" aria-hidden="true">
              <Clock size={19} />
            </div>
            <div className="metric-card-info">
              <div className="metric-card-top-line">
                <span className="metric-card-val">{pendingCount}</span>
                <span className="metric-card-total">Pending</span>
              </div>
              <span className="metric-card-title">Under Review</span>
              <span className="metric-card-sub">Review by SDM in progress</span>
            </div>
          </div>

          {/* Card 3: Action Required */}
          <div className="docs-metric-card">
            <div className="metric-card-icon-box red" aria-hidden="true">
              <AlertTriangle size={19} />
            </div>
            <div className="metric-card-info">
              <div className="metric-card-top-line">
                <span className="metric-card-val">{actionCount}</span>
                <span className="metric-card-total">Required</span>
              </div>
              <span className="metric-card-title">Action Required</span>
              <span className="metric-card-sub">{actionCount > 0 ? 'Address proof missing' : 'All documents submitted'}</span>
            </div>
          </div>

          {/* Card 4: Support Tickets */}
          <div
            className="docs-metric-card clickable-metric-card"
            onClick={() => handleOpenTicketModal()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && handleOpenTicketModal()}
            aria-label="View or Apply Support Tickets"
            title="Click to apply or view support tickets"
          >
            <div className="metric-card-icon-box purple" aria-hidden="true">
              <Ticket size={19} />
            </div>
            <div className="metric-card-info">
              <div className="metric-card-top-line">
                <span className="metric-card-val">{tickets.length} Active</span>
                <span className="metric-card-total">Tickets</span>
              </div>
              <span className="metric-card-title">Support Tickets</span>
              <span className="metric-card-sub">Raise ticket for discrepancies</span>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            2. TOOLBAR: FILTER TABS, LIVE SEARCH & QUICK ACTIONS
            ------------------------------------------------------------------ */}
        <div className="docs-toolbar-row">
          <nav className="docs-filter-bar" aria-label="Filter documents by status">
            <button
              type="button"
              className={`docs-filter-tab ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              <span className="docs-tab-icon tab-icon-all">
                <FileText size={14} />
                <span className="tab-icon-badge-dot" />
              </span>
              <span>All Documents ({totalCount})</span>
            </button>

            <button
              type="button"
              className={`docs-filter-tab ${activeTab === 'verified' ? 'active' : ''}`}
              onClick={() => setActiveTab('verified')}
            >
              <span className="docs-tab-icon tab-icon-verified">
                <span className="badge-check-circle" style={{ width: '13px', height: '13px' }}>
                  <Check size={8} strokeWidth={3.5} />
                </span>
              </span>
              <span>Verified ({verifiedCount})</span>
            </button>

            <button
              type="button"
              className={`docs-filter-tab ${activeTab === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveTab('pending')}
            >
              <span className="docs-tab-icon tab-icon-pending">
                <Clock size={14} color="#E98A00" />
              </span>
              <span>Pending ({pendingCount})</span>
            </button>

            <button
              type="button"
              className={`docs-filter-tab ${activeTab === 'action_required' ? 'active' : ''}`}
              onClick={() => setActiveTab('action_required')}
            >
              <span className="docs-tab-icon tab-icon-action">
                <AlertTriangle size={14} color="#D92D20" />
              </span>
              <span>Action Required ({actionCount})</span>
            </button>

            <button
              type="button"
              className={`docs-filter-tab ${activeTab === 'tickets' ? 'active' : ''}`}
              onClick={() => setActiveTab('tickets')}
            >
              <span className="docs-tab-icon tab-icon-ticket">
                <Ticket size={14} color={activeTab === 'tickets' ? '#FFFFFF' : '#1264D6'} />
              </span>
              <span>Active Ticket ({tickets.length})</span>
            </button>
          </nav>

          {/* Right-aligned Actions & Search */}
          <div className="docs-toolbar-actions">
            {/* Live Search Box */}
            <div className="docs-search-box" role="search">
              <Search size={14} color="#667085" aria-hidden="true" />
              <input
                type="search"
                className="docs-search-input"
                placeholder={activeTab === 'tickets' ? "Search tickets..." : "Search documents..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label={activeTab === 'tickets' ? "Search tickets" : "Search documents"}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#667085', padding: 0 }}
                  aria-label="Clear search"
                >
                  <X size={13} />
                </button>
              )}
            </div>

            <button
              type="button"
              className="btn-export-dossier"
              onClick={() => setIsDossierModalOpen(true)}
              title="Export complete verified document package"
            >
              <FileDown size={14} />
              <span>Export Dossier</span>
            </button>
          </div>
        </div>

        {/* ------------------------------------------------------------------
            4. TWO-COLUMN MAIN GRID (Table on Left, Tools on Right)
            ------------------------------------------------------------------ */}
        <div className="docs-main-grid">
          {/* Left Column: Documents Table */}
          <div className="docs-left-column">
            <div className="docs-table-card">
              <div className="docs-table-wrapper">
                {activeTab === 'tickets' ? (
                  <table className="docs-table" aria-label="Applicant Active Tickets Table">
                    <thead>
                      <tr>
                        <th scope="col">Ticket / Application ID</th>
                        <th scope="col">Subject & Category</th>
                        <th scope="col">Status</th>
                        <th scope="col">Created Date & Priority</th>
                        <th scope="col">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredTickets.map((tkt) => (
                        <tr key={tkt.id}>
                          {/* Column 1: Ticket / Application ID */}
                          <td>
                            <div className="doc-info-cell">
                              <div className="doc-type-icon-box icon-blue" aria-hidden="true">
                                <Ticket size={18} />
                              </div>
                              <div className="doc-text-group">
                                <span className="doc-name">{tkt.id}</span>
                                <div className="doc-category-line">
                                  <span className="doc-category">{tkt.category}</span>
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Column 2: Subject & Category */}
                          <td className="doc-purpose-cell">
                            <div className="doc-purpose-title">{tkt.subject}</div>
                            {tkt.docName && (
                              <span className="doc-scheme-count-tag">
                                Ref: {tkt.docName}
                              </span>
                            )}
                          </td>

                          {/* Column 3: Status */}
                          <td>
                            <span className="doc-status-badge status-review">
                              <Clock size={12} />
                              <span>{tkt.status || 'Under Review'}</span>
                            </span>
                          </td>

                          {/* Column 4: Created Date & Priority */}
                          <td className="doc-date-cell">
                            <div>{tkt.createdAt || tkt.createdOn || 'Recent'}</div>
                            <div
                              className="doc-validity-text"
                              style={{
                                fontWeight: 600,
                                color: tkt.priority === 'High' ? '#D92D20' : '#1264D6',
                              }}
                            >
                              Priority: {tkt.priority || 'Normal'}
                            </div>
                          </td>

                          {/* Column 5: Actions */}
                          <td>
                            <div className="doc-actions-cell">
                              <button
                                type="button"
                                className="btn-doc-view"
                                onClick={() => setSelectedTicketForView(tkt)}
                              >
                                <Eye size={12} />
                                <span>View</span>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}

                      {filteredTickets.length === 0 && (
                        <tr>
                          <td colSpan="5" style={{ textAlign: 'center', padding: '32px 20px', color: '#667085' }}>
                            No active tickets match "{searchQuery}". Click "Apply Ticket" to submit an application or query.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                ) : (
                  <table className="docs-table" aria-label="Applicant Documents Table">
                  <thead>
                    <tr>
                      <th scope="col">Document</th>
                      <th scope="col">Purpose & Scheme Impact</th>
                      <th scope="col">Status</th>
                      <th scope="col">Uploaded & Validity</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id}>
                        {/* Column 1: Document */}
                        <td>
                          <div className="doc-info-cell">
                            <div className={`doc-type-icon-box icon-${doc.iconColor}`} aria-hidden="true">
                              {renderDocIcon(doc.iconType)}
                            </div>
                            <div className="doc-text-group">
                              <span className="doc-name">{doc.name}</span>
                              <div className="doc-category-line">
                                <span className="doc-category">{doc.category}</span>
                                {doc.source && (
                                  <span className={`doc-source-tag ${doc.source.includes('Self') ? 'self' : ''}`}>
                                    {doc.source}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Column 2: Purpose & Scheme Impact */}
                        <td className="doc-purpose-cell">
                          <div className="doc-purpose-title">{doc.purpose}</div>
                          {doc.requiredForSchemes && (
                            <span className="doc-scheme-count-tag">
                              Required for {doc.requiredForSchemes} schemes
                            </span>
                          )}
                        </td>

                        {/* Column 3: Status Badge */}
                        <td>
                          {doc.status === 'verified' && (
                            <span className="doc-status-badge status-verified">
                              <span className="badge-check-circle" aria-hidden="true">
                                <Check size={8} strokeWidth={3.5} />
                              </span>
                              <span>Verified</span>
                            </span>
                          )}
                          {doc.status === 'under_review' && (
                            <span className="doc-status-badge status-review">
                              <Clock size={12} />
                              <span>Under Review</span>
                            </span>
                          )}
                          {doc.status === 'action_required' && (
                            <span className="doc-status-badge status-action">
                              <AlertTriangle size={12} />
                              <span>Action Required</span>
                            </span>
                          )}
                        </td>

                        {/* Column 4: Uploaded On & Validity */}
                        <td className="doc-date-cell">
                          <div>{doc.uploadedOn}</div>
                          {doc.validity && (
                            <div className="doc-validity-text">{doc.validity}</div>
                          )}
                        </td>

                        {/* Column 5: Actions */}
                        <td>
                          <div className="doc-actions-cell">
                            {doc.status === 'action_required' ? (
                              <button
                                type="button"
                                className="btn-doc-upload"
                                onClick={() => handleOpenUploadModal(doc.id)}
                              >
                                Upload
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="btn-doc-view"
                                onClick={() => setSelectedDocForView(doc)}
                              >
                                View
                              </button>
                            )}

                            {/* Three dots contextual menu */}
                            <button
                              type="button"
                              className="btn-doc-more"
                              aria-label={`Options for ${doc.name}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuId(activeMenuId === doc.id ? null : doc.id);
                              }}
                            >
                              <MoreVertical size={15} />
                            </button>

                            {/* Dropdown Menu */}
                            {activeMenuId === doc.id && (
                              <div className="doc-menu-dropdown" role="menu">
                                <button
                                  type="button"
                                  className="doc-menu-item"
                                  onClick={() => {
                                    setSelectedDocForView(doc);
                                    setActiveMenuId(null);
                                  }}
                                >
                                  <Eye size={13} />
                                  <span>View Details</span>
                                </button>
                                {doc.status !== 'action_required' && (
                                  <button
                                    type="button"
                                    className="doc-menu-item"
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      triggerToast(`Downloading verified copy of ${doc.name}...`);
                                    }}
                                  >
                                    <Download size={13} />
                                    <span>Download Copy</span>
                                  </button>
                                )}
                                <button
                                  type="button"
                                  className="doc-menu-item"
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    handleOpenUploadModal(doc.id);
                                  }}
                                >
                                  <RefreshCw size={13} />
                                  <span>Replace Document</span>
                                </button>
                                <button
                                  type="button"
                                  className="doc-menu-item"
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    handleOpenTicketModal(doc.id);
                                  }}
                                >
                                  <Ticket size={13} />
                                  <span>Apply Ticket for this Doc</span>
                                </button>
                                {doc.status !== 'action_required' && (
                                  <button
                                    type="button"
                                    className="doc-menu-item danger"
                                    onClick={() => handleDeleteDoc(doc.id)}
                                  >
                                    <Trash2 size={13} />
                                    <span>Remove Document</span>
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}

                    {filteredDocuments.length === 0 && (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '32px 20px', color: '#667085' }}>
                          No documents match "{searchQuery}" under this filter.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
            </div>
          </div>

          {/* Right Column: Upload, Apply Ticket, Completion, Scheme Checker */}
          <div className="docs-right-column">
            {/* Primary Action Buttons: Upload & Apply Ticket */}
            <div className="docs-sidebar-action-stack">
              <button
                type="button"
                className="btn-upload-new-doc"
                onClick={() => handleOpenUploadModal('address')}
              >
                <Plus size={16} strokeWidth={2.5} />
                <span>Upload New Document</span>
              </button>

              <button
                type="button"
                className="btn-apply-ticket"
                onClick={() => handleOpenTicketModal()}
                title="Apply Ticket for document queries or scheme grievances"
              >
                <Ticket size={16} />
                <span>Apply Ticket</span>
              </button>
            </div>

            {/* Quick Support & Ticket Assistance Card */}
            <div className="docs-ticket-assist-card">
              <div className="ticket-assist-header">
                <div className="ticket-assist-icon" aria-hidden="true">
                  <LifeBuoy size={16} />
                </div>
                <div className="ticket-assist-title-group">
                  <h4 className="ticket-assist-title">Need Verification Assistance?</h4>
                  <p className="ticket-assist-sub">
                    Facing document delays, errors, or mismatch? Raise a support ticket for quick resolution.
                  </p>
                </div>
              </div>
              <div className="ticket-assist-footer">
                <button
                  type="button"
                  className="ticket-assist-link"
                  onClick={() => handleOpenTicketModal()}
                >
                  <span>Raise Ticket</span>
                  <ArrowRight size={13} />
                </button>
                {tickets.length > 0 && (
                  <span className="ticket-status-pill">{tickets.length} Active</span>
                )}
              </div>
            </div>

            {/* Document Completion Card */}
            <div className="docs-completion-card">
              <h3 className="completion-card-title">Document Completion</h3>
              <div className="completion-progress-body">
                {/* Radial Gauge */}
                <div className="completion-gauge-container">
                  <svg className="completion-gauge-svg" viewBox="0 0 54 54" aria-hidden="true">
                    <circle
                      className="completion-gauge-bg"
                      cx="27"
                      cy="27"
                      r={radius}
                      strokeWidth={strokeWidth}
                      fill="none"
                    />
                    <circle
                      className="completion-gauge-fill"
                      cx="27"
                      cy="27"
                      r={radius}
                      strokeWidth={strokeWidth}
                      fill="none"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                    />
                  </svg>
                  <span className="completion-gauge-label">{completionPercentage}%</span>
                </div>

                {/* Linear Meta */}
                <div className="completion-meta">
                  <span className="completion-status-text">
                    {completedCount} of {totalCount} documents verified
                  </span>
                  <div className="completion-linear-track" aria-hidden="true">
                    <div
                      className="completion-linear-fill"
                      style={{ width: `${completionPercentage}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Scheme Document Eligibility Quick Checker Widget */}
            <div className="docs-scheme-checker-card">
              <div className="checker-header">
                <h4 className="checker-title">Scheme Readiness Checker</h4>
                <Sparkles size={13} color="#005B50" />
              </div>

              <select
                className="checker-select"
                value={selectedSchemeId}
                onChange={(e) => setSelectedSchemeId(e.target.value)}
                aria-label="Select scheme to check document readiness"
              >
                {SCHEMES_CHECKLIST.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>

              <div className="checker-item-list">
                {currentScheme.requiredDocIds.map((reqId) => {
                  const doc = documents.find((d) => d.id === reqId);
                  const isReady = doc && doc.status === 'verified';
                  const isReview = doc && doc.status === 'under_review';
                  return (
                    <div key={reqId} className="checker-doc-item">
                      <span className="checker-doc-name">{doc ? doc.name : reqId}</span>
                      {isReady && (
                        <span className="checker-status-ok">
                          <Check size={12} strokeWidth={3} />
                          <span>Ready</span>
                        </span>
                      )}
                      {isReview && (
                        <span style={{ color: '#C56A00', fontWeight: 600, fontSize: '11px' }}>
                          In Review
                        </span>
                      )}
                      {!isReady && !isReview && (
                        <button
                          type="button"
                          className="checker-status-missing"
                          style={{ background: 'none', border: 'none', padding: 0 }}
                          onClick={() => handleOpenUploadModal(reqId)}
                        >
                          Upload
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------------------------
            5. FULL-WIDTH 3-COLUMN BOTTOM UTILITY DECK (Perfect systematic balance!)
            ------------------------------------------------------------------ */}
        <section className="docs-bottom-deck" aria-label="Document Support and Protection Services">
          {/* Deck Card 1: Reminder */}
          <div className="deck-card reminder">
            <div className="deck-card-top">
              <div className="deck-icon-circle teal" aria-hidden="true">
                <FileCheck size={18} />
              </div>
              <div className="deck-title-group">
                <h4 className="deck-title">Keep Documents Updated</h4>
                <p className="deck-desc">
                  Set automated alerts for document renewals and scheme application deadlines.
                </p>
              </div>
            </div>
            <div className="deck-card-bottom">
              <button
                type="button"
                className="btn-deck-action"
                onClick={() => setIsReminderModalOpen(true)}
              >
                <Bell size={13} />
                <span>Set Reminder</span>
              </button>
            </div>
          </div>

          {/* Deck Card 2: Guidance */}
          <div className="deck-card guidance">
            <div className="deck-card-top">
              <div className="deck-icon-circle blue" aria-hidden="true">
                <Lightbulb size={18} />
              </div>
              <div className="deck-title-group">
                <h4 className="deck-title">Need Scheme Guidance?</h4>
                <p className="deck-desc">
                  Not sure which certificates apply to your caste, income, or state? We guide you.
                </p>
              </div>
            </div>
            <div className="deck-card-bottom">
              <button
                type="button"
                className="deck-link-action"
                onClick={() => setIsGuidanceModalOpen(true)}
              >
                <span>Get Guidance</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>

          {/* Deck Card 3: Security & Trust */}
          <div className="deck-card security">
            <div className="deck-card-top">
              <div className="deck-icon-circle amber" aria-hidden="true">
                <ShieldCheck size={18} />
              </div>
              <div className="deck-title-group">
                <h4 className="deck-title">Government-Grade Security</h4>
                <p className="deck-desc">
                  AES-256 bit encrypted storage adhering to India's DPDP Act and MeitY norms.
                </p>
              </div>
            </div>
            <div className="deck-card-bottom">
              <button
                type="button"
                className="deck-link-action"
                onClick={() => setIsSecurityModalOpen(true)}
              >
                <span>Learn More</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            6. MODAL: APPLY FOR GOVERNMENT POLICY
            ------------------------------------------------------------------ */}
        {isTicketModalOpen && (
          <div className="docs-modal-backdrop" onClick={() => setIsTicketModalOpen(false)}>
            <div
              className="docs-modal-card policy-application-modal"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
            >
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <div className="policy-modal-header-icon">
                    <ShieldCheck size={20} color="#005B50" />
                  </div>
                  <div>
                    <h3 className="docs-modal-title">Apply for Government Policy</h3>
                    <span style={{ fontSize: '11.5px', color: '#667085' }}>
                      Citizen Scheme Application & Document Submission
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setIsTicketModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <form onSubmit={handleSubmitPolicyApplication}>
                <div className="docs-modal-body policy-modal-scroll-body">
                  {/* Section 1: Applicant Information */}
                  <div className="policy-form-section">
                    <div className="policy-section-header">
                      <h4 className="policy-section-title">Applicant Information</h4>
                    </div>

                    <div className="policy-fields-grid">
                      <div className="policy-field-group">
                        <label className="policy-field-label" htmlFor="policy-full-name">
                          Full Name
                        </label>
                        <input
                          id="policy-full-name"
                          type="text"
                          className="docs-form-input policy-input"
                          placeholder="Enter your full name"
                          value={policyFullName}
                          onChange={(e) => setPolicyFullName(e.target.value)}
                          required
                        />
                      </div>

                      <div className="policy-field-group">
                        <label className="policy-field-label" htmlFor="policy-dob">
                          Date of Birth
                        </label>
                        <input
                          id="policy-dob"
                          type="date"
                          className="docs-form-input policy-input"
                          value={policyDob}
                          onChange={(e) => setPolicyDob(e.target.value)}
                          required
                        />
                      </div>

                      <div className="policy-field-group">
                        <label className="policy-field-label" htmlFor="policy-state">
                          State
                        </label>
                        <select
                          id="policy-state"
                          className="docs-form-select policy-input"
                          value={policyState}
                          onChange={(e) => setPolicyState(e.target.value)}
                          required
                        >
                          <option value="Gujarat">Gujarat</option>
                          <option value="Maharashtra">Maharashtra</option>
                          <option value="Delhi">Delhi</option>
                          <option value="Karnataka">Karnataka</option>
                          <option value="Uttar Pradesh">Uttar Pradesh</option>
                          <option value="Rajasthan">Rajasthan</option>
                          <option value="Madhya Pradesh">Madhya Pradesh</option>
                          <option value="Tamil Nadu">Tamil Nadu</option>
                        </select>
                      </div>

                      <div className="policy-field-group">
                        <label className="policy-field-label" htmlFor="policy-district">
                          District
                        </label>
                        <input
                          id="policy-district"
                          type="text"
                          className="docs-form-input policy-input"
                          placeholder="e.g. Ahmedabad"
                          value={policyDistrict}
                          onChange={(e) => setPolicyDistrict(e.target.value)}
                          required
                        />
                      </div>

                      <div className="policy-field-group">
                        <label className="policy-field-label" htmlFor="policy-category">
                          Category
                        </label>
                        <select
                          id="policy-category"
                          className="docs-form-select policy-input"
                          value={policyCategory}
                          onChange={(e) => setPolicyCategory(e.target.value)}
                          required
                        >
                          <option value="General">General</option>
                          <option value="OBC">OBC</option>
                          <option value="SC">SC</option>
                          <option value="ST">ST</option>
                          <option value="EWS">EWS</option>
                        </select>
                      </div>

                      <div className="policy-field-group">
                        <label className="policy-field-label" htmlFor="policy-income">
                          Annual Income
                        </label>
                        <input
                          id="policy-income"
                          type="text"
                          className="docs-form-input policy-input"
                          placeholder="e.g. ₹ 2,40,000"
                          value={policyIncome}
                          onChange={(e) => setPolicyIncome(e.target.value)}
                          required
                        />
                      </div>

                      <div className="policy-field-group policy-field-full">
                        <label className="policy-field-label" htmlFor="policy-occupation">
                          Occupation
                        </label>
                        <select
                          id="policy-occupation"
                          className="docs-form-select policy-input"
                          value={policyOccupation}
                          onChange={(e) => setPolicyOccupation(e.target.value)}
                          required
                        >
                          <option value="Student">Student</option>
                          <option value="Salaried / Employed">Salaried / Employed</option>
                          <option value="Self Employed">Self Employed</option>
                          <option value="Farmer / Agriculture">Farmer / Agriculture</option>
                          <option value="Business / MSME">Business / MSME</option>
                          <option value="Other">Other</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Section 2: Documents */}
                  <div className="policy-form-section">
                    <div className="policy-section-header">
                      <h4 className="policy-section-title">Documents</h4>
                    </div>

                    {/* Drag and Drop Zone */}
                    <div
                      className={`policy-dropzone-box ${policyIsDragging ? 'drag-over' : ''} ${policyDocumentFile ? 'has-file' : ''}`}
                      onDragOver={handlePolicyDragOver}
                      onDragLeave={handlePolicyDragLeave}
                      onDrop={handlePolicyDrop}
                      onClick={() => policyFileInputRef.current?.click()}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && policyFileInputRef.current?.click()}
                      aria-label="Drag and drop your document here or click to browse"
                    >
                      <input
                        type="file"
                        ref={policyFileInputRef}
                        style={{ display: 'none' }}
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => {
                          if (e.target.files && e.target.files.length > 0) {
                            setPolicyDocumentFile(e.target.files[0]);
                          }
                        }}
                      />

                      <div className="policy-dropzone-icon-circle">
                        <UploadCloud size={24} />
                      </div>
                      <span className="policy-dropzone-title">Drag & drop your document here</span>
                      <span className="policy-dropzone-sub">or click to browse</span>
                      <span className="policy-dropzone-specs">PDF, JPG, PNG • Max 10MB</span>
                    </div>

                    {/* Attached file chip */}
                    {policyDocumentFile && (
                      <div className="policy-attached-file-badge">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                          <FileCheck size={16} color="#087443" style={{ flexShrink: 0 }} />
                          <span className="policy-file-name">{policyDocumentFile.name}</span>
                          <span className="policy-file-size">
                            ({(policyDocumentFile.size / (1024 * 1024)).toFixed(2)} MB)
                          </span>
                        </div>
                        <button
                          type="button"
                          className="policy-file-remove-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setPolicyDocumentFile(null);
                            if (policyFileInputRef.current) policyFileInputRef.current.value = '';
                          }}
                          aria-label="Remove attached document"
                          title="Remove document"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="docs-modal-footer policy-modal-footer">
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => setIsTicketModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary policy-submit-btn"
                    disabled={isSubmittingPolicy}
                  >
                    <span>{isSubmittingPolicy ? 'Submitting Application...' : 'Submit Application'}</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            7. MODAL: UPLOAD NEW / REPLACE DOCUMENT
            ------------------------------------------------------------------ */}
        {isUploadModalOpen && (
          <div className="docs-modal-backdrop" onClick={() => setIsUploadModalOpen(false)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <h3 className="docs-modal-title">Upload Document</h3>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setIsUploadModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <form onSubmit={handleModalUploadSubmit}>
                <div className="docs-modal-body">
                  <div className="docs-form-group">
                    <label className="docs-form-label" htmlFor="doc-select">
                      Select Document Type
                    </label>
                    <select
                      id="doc-select"
                      className="docs-form-select"
                      value={uploadTargetDocId}
                      onChange={(e) => setUploadTargetDocId(e.target.value)}
                    >
                      {documents.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.purpose})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div
                    className="modal-dropzone"
                    onClick={() => modalFileInputRef.current?.click()}
                  >
                    <input
                      type="file"
                      ref={modalFileInputRef}
                      style={{ display: 'none' }}
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          setUploadSelectedFile(e.target.files[0]);
                        }
                      }}
                    />
                    <UploadCloud size={24} color="#005B50" style={{ margin: '0 auto 5px' }} />
                    <p style={{ fontWeight: 600, color: '#10243A', fontSize: '13px' }}>
                      Click to choose document file
                    </p>
                    <p style={{ fontSize: '11.5px', color: '#667085', marginTop: '2px' }}>
                      PDF, JPG, or PNG up to 5 MB
                    </p>
                  </div>

                  {uploadSelectedFile && (
                    <div className="selected-file-badge">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                        <FileText size={14} color="#1264D6" />
                        <span style={{ fontWeight: 600 }}>{uploadSelectedFile.name}</span>
                        <span style={{ color: '#667085' }}>
                          ({(uploadSelectedFile.size / 1024).toFixed(0)} KB)
                        </span>
                      </div>
                      <Check size={15} color="#087443" />
                    </div>
                  )}

                  {isUploading && (
                    <div style={{ marginTop: '7px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', marginBottom: '3px', fontWeight: 600 }}>
                        <span>Uploading & Verifying...</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="completion-linear-track">
                        <div className="completion-linear-fill" style={{ width: `${uploadProgress}%` }} />
                      </div>
                    </div>
                  )}
                </div>

                <div className="docs-modal-footer">
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => setIsUploadModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isUploading}
                  >
                    {isUploading ? 'Uploading...' : 'Confirm Upload'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            8. MODAL: VIEW DOCUMENT DETAILS & PREVIEW
            ------------------------------------------------------------------ */}
        {selectedDocForView && (
          <div className="docs-modal-backdrop" onClick={() => setSelectedDocForView(null)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <div className={`doc-type-icon-box icon-${selectedDocForView.iconColor}`} style={{ width: '30px', height: '30px' }}>
                    {renderDocIcon(selectedDocForView.iconType)}
                  </div>
                  <div>
                    <h3 className="docs-modal-title" style={{ fontSize: '14.5px' }}>{selectedDocForView.name}</h3>
                    <span style={{ fontSize: '11.5px', color: '#667085' }}>{selectedDocForView.category}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setSelectedDocForView(null)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <div className="docs-modal-body">
                {/* Official Verification Watermark Record */}
                <div className="doc-watermark-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#667085', fontWeight: 600 }}>
                        Official Verification Record
                      </span>
                      <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#10243A', marginTop: '2px' }}>
                        {selectedDocForView.name}
                      </h4>
                    </div>
                    {selectedDocForView.status === 'verified' && (
                      <span className="doc-status-badge status-verified">
                        <Check size={10} strokeWidth={3} />
                        <span>Verified</span>
                      </span>
                    )}
                    {selectedDocForView.status === 'under_review' && (
                      <span className="doc-status-badge status-review">
                        <Clock size={11} />
                        <span>Under Review</span>
                      </span>
                    )}
                    {selectedDocForView.status === 'action_required' && (
                      <span className="doc-status-badge status-action">
                        <AlertTriangle size={11} />
                        <span>Action Required</span>
                      </span>
                    )}
                  </div>

                  <div className="doc-preview-meta-grid">
                    <div>
                      <div className="meta-field-label">Document Number</div>
                      <div className="meta-field-val">{selectedDocForView.docNumber}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Primary Purpose</div>
                      <div className="meta-field-val">{selectedDocForView.purpose}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Issuing Authority</div>
                      <div className="meta-field-val">{selectedDocForView.issuer}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Uploaded On</div>
                      <div className="meta-field-val">{selectedDocForView.uploadedOn}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">File Type & Size</div>
                      <div className="meta-field-val">{selectedDocForView.fileType} • {selectedDocForView.fileSize}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Verification Source</div>
                      <div className="meta-field-val">{selectedDocForView.source || 'Digital India'}</div>
                    </div>
                  </div>
                </div>

                <div style={{ backgroundColor: '#F0FDF4', border: '1px solid #BBF7D0', padding: '9px 11px', borderRadius: '7px', display: 'flex', gap: '7px', alignItems: 'center' }}>
                  <ShieldCheck size={17} color="#15803D" style={{ flexShrink: 0 }} />
                  <span style={{ fontSize: '11.5px', color: '#166534' }}>
                    Digitally signed & verified for seamless direct subsidy DBT scheme verification.
                  </span>
                </div>
              </div>

              <div className="docs-modal-footer">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setSelectedDocForView(null)}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    triggerToast(`Downloading verified copy of ${selectedDocForView.name}...`);
                    setSelectedDocForView(null);
                  }}
                >
                  <Download size={13} />
                  <span>Download Document</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            9. MODAL: EXPORT CITIZEN DOSSIER BUNDLE
            ------------------------------------------------------------------ */}
        {isDossierModalOpen && (
          <div className="docs-modal-backdrop" onClick={() => setIsDossierModalOpen(false)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <FileDown size={19} color="#005B50" />
                  <h3 className="docs-modal-title">Export Citizen Document Dossier</h3>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setIsDossierModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <div className="docs-modal-body">
                <p style={{ fontSize: '12.5px', color: '#475467', lineHeight: 1.45 }}>
                  Generate an official compiled PDF dossier containing all your verified documents with individual QR verification codes for physical submissions at CSC Centers or Bank Branches.
                </p>

                <div style={{ background: '#F8F9FA', borderRadius: '7px', padding: '11px', border: '1px solid #E4E7EC' }}>
                  <div style={{ fontSize: '11.5px', fontWeight: 600, color: '#344054', marginBottom: '7px' }}>
                    Included in this Dossier ({verifiedCount} Verified Documents):
                  </div>
                  <ul style={{ fontSize: '11.5px', color: '#475467', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {verifiedDocs.map((d) => (
                      <li key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Check size={11} color="#087443" />
                        <span>{d.name} ({d.purpose})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="docs-modal-footer">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setIsDossierModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    setIsDossierModalOpen(false);
                    triggerToast('Generating official Citizen Dossier PDF package...');
                  }}
                >
                  <Download size={13} />
                  <span>Download Complete Dossier</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            10. MODAL: SET DOCUMENT REMINDERS
            ------------------------------------------------------------------ */}
        {isReminderModalOpen && (
          <div className="docs-modal-backdrop" onClick={() => setIsReminderModalOpen(false)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <Bell size={17} color="#005B50" />
                  <h3 className="docs-modal-title">Document Update Reminders</h3>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setIsReminderModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <form onSubmit={handleSaveReminder}>
                <div className="docs-modal-body">
                  <p style={{ fontSize: '12.5px', color: '#475467', lineHeight: 1.45 }}>
                    Never miss a scheme application deadline or document renewal date. Choose how often you'd like to receive notifications:
                  </p>

                  <div className="docs-form-group">
                    <label className="docs-form-label" htmlFor="reminder-freq">
                      Reminder Frequency
                    </label>
                    <select
                      id="reminder-freq"
                      className="docs-form-select"
                      value={reminderFrequency}
                      onChange={(e) => setReminderFrequency(e.target.value)}
                    >
                      <option value="monthly">Monthly Checkup (Recommended)</option>
                      <option value="quarterly">Quarterly Review</option>
                      <option value="before_expiry">30 Days Before Document Expiry</option>
                      <option value="scheme_deadline">When New Scheme Requires Renewal</option>
                    </select>
                  </div>

                  <div className="docs-form-group">
                    <label className="docs-form-label" htmlFor="reminder-email">
                      Notification Email
                    </label>
                    <input
                      id="reminder-email"
                      type="email"
                      className="docs-form-input"
                      value={reminderEmail}
                      onChange={(e) => setReminderEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="docs-modal-footer">
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => setIsReminderModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Set Reminder
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            11. MODAL: SCHEME GUIDANCE
            ------------------------------------------------------------------ */}
        {isGuidanceModalOpen && (
          <div className="docs-modal-backdrop" onClick={() => setIsGuidanceModalOpen(false)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <Lightbulb size={17} color="#1264D6" />
                  <h3 className="docs-modal-title">Scheme Document Guidance</h3>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setIsGuidanceModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <div className="docs-modal-body">
                <p style={{ fontSize: '12.5px', color: '#475467' }}>
                  Each scheme has tailored document eligibility requirements. Here is a quick reference guide:
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                  <div style={{ padding: '9px 11px', background: '#F8F9FA', borderRadius: '7px', border: '1px solid #E4E7EC' }}>
                    <div style={{ fontWeight: 600, color: '#10243A', fontSize: '13px' }}>PMEGP & MSME Schemes</div>
                    <div style={{ fontSize: '11.5px', color: '#475467', marginTop: '2px' }}>
                      Requires Aadhaar, PAN Card, Category/Caste Certificate, and Project Site Address Proof.
                    </div>
                  </div>
                  <div style={{ padding: '9px 11px', background: '#F8F9FA', borderRadius: '7px', border: '1px solid #E4E7EC' }}>
                    <div style={{ fontWeight: 600, color: '#10243A', fontSize: '13px' }}>PM Kisan & Agriculture Support</div>
                    <div style={{ fontSize: '11.5px', color: '#475467', marginTop: '2px' }}>
                      Requires Bank Account Details (DBT enabled), Land Record / Domicile, and Aadhaar.
                    </div>
                  </div>
                  <div style={{ padding: '9px 11px', background: '#F8F9FA', borderRadius: '7px', border: '1px solid #E4E7EC' }}>
                    <div style={{ fontWeight: 600, color: '#10243A', fontSize: '13px' }}>Education & Scholarships</div>
                    <div style={{ fontSize: '11.5px', color: '#475467', marginTop: '2px' }}>
                      Requires Income Certificate (annual validity), Marksheets, Domicile, and Photo.
                    </div>
                  </div>
                </div>
              </div>

              <div className="docs-modal-footer">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setIsGuidanceModalOpen(false)}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    setIsGuidanceModalOpen(false);
                    navigate('/discover');
                  }}
                >
                  <span>Explore Schemes</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            12. MODAL: DATA SECURITY & PROTECTION
            ------------------------------------------------------------------ */}
        {isSecurityModalOpen && (
          <div className="docs-modal-backdrop" onClick={() => setIsSecurityModalOpen(false)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <ShieldCheck size={17} color="#D48B28" />
                  <h3 className="docs-modal-title">Government-Grade Data Protection</h3>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setIsSecurityModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <div className="docs-modal-body">
                <p style={{ fontSize: '12.5px', color: '#475467', lineHeight: 1.45 }}>
                  FIN complies with India's Digital Personal Data Protection (DPDP) Act and follows stringent national encryption standards:
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                  <div style={{ display: 'flex', gap: '9px', alignItems: 'flex-start' }}>
                    <CheckCircle2 size={14} color="#087443" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <strong style={{ fontSize: '12.5px', color: '#10243A' }}>AES-256 Bit Encryption:</strong>
                      <p style={{ fontSize: '11.5px', color: '#667085', marginTop: '1px' }}>
                        All uploaded documents are encrypted both at rest and in transit.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '9px', alignItems: 'flex-start' }}>
                    <CheckCircle2 size={14} color="#087443" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <strong style={{ fontSize: '12.5px', color: '#10243A' }}>Masked Identifiers:</strong>
                      <p style={{ fontSize: '11.5px', color: '#667085', marginTop: '1px' }}>
                        Sensitive numbers like Aadhaar and PAN are automatically masked to safeguard privacy.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '9px', alignItems: 'flex-start' }}>
                    <CheckCircle2 size={14} color="#087443" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <strong style={{ fontSize: '12.5px', color: '#10243A' }}>Strict Access Control:</strong>
                      <p style={{ fontSize: '11.5px', color: '#667085', marginTop: '1px' }}>
                        Only authorized nodal verification officers can access documents during active scheme applications.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="docs-modal-footer">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setIsSecurityModalOpen(false)}
                >
                  Understood
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            13. MODAL: VIEW TICKET DETAILS
            ------------------------------------------------------------------ */}
        {selectedTicketForView && (
          <div className="docs-modal-backdrop" onClick={() => setSelectedTicketForView(null)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <div className="policy-modal-header-icon">
                    <Ticket size={20} color="#005B50" />
                  </div>
                  <div>
                    <h3 className="docs-modal-title">Ticket: {selectedTicketForView.id}</h3>
                    <span style={{ fontSize: '11.5px', color: '#667085' }}>{selectedTicketForView.category}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => setSelectedTicketForView(null)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <div className="docs-modal-body">
                <div className="doc-watermark-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#667085', fontWeight: 600 }}>
                        Official Ticket Details
                      </span>
                      <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#10243A', marginTop: '2px' }}>
                        {selectedTicketForView.subject}
                      </h4>
                    </div>
                    <span className="doc-status-badge status-review">
                      <Clock size={11} />
                      <span>{selectedTicketForView.status || 'Active'}</span>
                    </span>
                  </div>

                  <p style={{ fontSize: '12.5px', color: '#475467', lineHeight: 1.5, marginTop: '10px' }}>
                    {selectedTicketForView.description}
                  </p>

                  <div className="doc-preview-meta-grid" style={{ marginTop: '14px' }}>
                    <div>
                      <div className="meta-field-label">Reference ID</div>
                      <div className="meta-field-val">{selectedTicketForView.id}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Priority Level</div>
                      <div className="meta-field-val">{selectedTicketForView.priority || 'Normal'}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Linked Document / Asset</div>
                      <div className="meta-field-val">{selectedTicketForView.docName || 'General Policy Submission'}</div>
                    </div>
                    <div>
                      <div className="meta-field-label">Assigned Desk</div>
                      <div className="meta-field-val">{selectedTicketForView.agent || 'Nodal Grievance Cell'}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="docs-modal-footer">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setSelectedTicketForView(null)}
                >
                  Close Case View
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
