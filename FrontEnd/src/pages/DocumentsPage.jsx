import React, { useState, useRef, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { isValidSchemeIdentifier } from '../utils/schemeNavigation';
import { computeDropdownPosition } from '../utils/dropdownPositioning';
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
  Info,
  FileSearch,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import SchemeReadinessCombobox from '../components/documents/SchemeReadinessCombobox';
import {
  buildDynamicSchemeChecklist,
  normalizeDocRequirementId,
  loadTicketsFromStorage,
  saveTicketsToStorage,
  SUPPORTED_DOC_TYPES,
  DOC_TYPE_LOOKUP,
} from '../data/documentsData';
import {
  validateSchemeSelection,
  resolveCanonicalSchemeDetails,
  filterActiveSchemesForCatalog,
  deriveDynamicSchemeChecklist,
  filterApplicantRelevantSchemes,
  isCentralScheme,
  evaluateSchemeReadiness,
} from '../utils/documentSchemeValidation.js';
import { downloadDossierPdf } from '../utils/dossierPdfGenerator';
import { matchDocumentStatus } from '../utils/schemeDetailsHelpers';
import {
  fetchUserDocuments,
  uploadDocumentFile,
  extractDocumentData,
  deleteDocument,
  getDocumentDetails
} from '../services/documentService';
import { fetchUserApplications, submitApplication } from '../services/applicationService';
import { fetchUserProfile, updateUserProfile } from '../services/profileService';
import { searchSchemes, fetchSchemes, fetchSchemeById, fetchApplicableSchemesCatalog } from '../services/schemeService';
import { getStoredUser } from '../services/authService';
import '../styles/documents.css';

export { SUPPORTED_DOC_TYPES, DOC_TYPE_LOOKUP };

function mapBackendDocument(bDoc, docTypeRequirementCounts = {}) {
  const rawType = String(bDoc.documentType || bDoc.document_type || 'other').toLowerCase();
  const normalizedType = rawType === 'bank' ? 'bank_passbook' :
    rawType === 'income' ? 'income_cert' :
    rawType === 'caste' ? 'caste_cert' :
    rawType === 'address' ? 'address_proof' : rawType;

  const fileName = bDoc.fileName || bDoc.file_name || 'document.pdf';
  const fileExt = fileName.split('.').pop()?.toUpperCase() || 'PDF';

  const meta = DOC_TYPE_LOOKUP[normalizedType] || {
    name: bDoc.fileName || bDoc.file_name || 'Uploaded Document',
    category: 'Citizen Identification',
    purpose: 'Statutory Verification',
    iconType: 'file-text',
    iconColor: 'blue'
  };

  // Parse structured remarks / extracted fields
  let parsedRemarks = null;
  const rawRemarks = bDoc.reviewerRemarks || bDoc.reviewer_remarks;
  if (rawRemarks) {
    if (typeof rawRemarks === 'object') {
      parsedRemarks = rawRemarks;
    } else {
      try {
        parsedRemarks = JSON.parse(rawRemarks);
      } catch (_) { }
    }
  }

  const extractedData = bDoc.extractedData || bDoc.extracted_data || parsedRemarks?.extractedFields || parsedRemarks?.fields || {};
  const hasExtractedFields = extractedData && Object.keys(extractedData).length > 0;
  const ocrMetadata = bDoc.ocrMetadata || bDoc.ocr_metadata || {
    method: parsedRemarks?.method || 'NATIVE_PDF',
    pages: parsedRemarks?.pages || 1,
    sha256: parsedRemarks?.sha256 || '',
    confidence: parsedRemarks?.confidence || 0.95
  };
  const extractedText = bDoc.extractedText || bDoc.extracted_text || parsedRemarks?.extractedText || '';

  const statusRaw = String(bDoc.verificationStatus || bDoc.verification_status || 'PENDING').toUpperCase();
  const isVerified = statusRaw === 'VERIFIED';
  const isRejected = statusRaw === 'REJECTED';
  const isReviewRequired = statusRaw === 'REVIEW_REQUIRED';
  const isProcessing = statusRaw === 'PROCESSING';

  let status = 'under_review';
  let statusLabel = 'Uploaded';

  if (isVerified) {
    status = 'verified';
    statusLabel = 'Ready for AI Chat';
  } else if (isRejected) {
    status = 'action_required';
    statusLabel = 'Processing Failed';
  } else if (isReviewRequired) {
    status = 'action_required';
    statusLabel = 'Review Required';
  } else if (isProcessing) {
    status = 'under_review';
    statusLabel = 'Processing';
  } else {
    status = 'under_review';
    statusLabel = 'Uploaded';
  }

  // Derive honest source from persisted record
  const rawUploader = bDoc.uploadedBy || bDoc.uploaded_by || bDoc.uploader || bDoc.source || bDoc.upload_source || '';
  let source = 'Self Uploaded';
  if (rawUploader) {
    const upStr = String(rawUploader).toUpperCase();
    if (upStr === 'ADMIN' || upStr.includes('OFFICER') || upStr.includes('REVIEWER')) {
      source = 'Official Department';
    } else if (upStr === 'SYSTEM' || upStr.includes('SERVICE')) {
      source = 'System Ingested';
    } else if (upStr === 'CITIZEN' || upStr === 'SELF' || upStr.includes('APPLICANT')) {
      source = 'Self Uploaded';
    } else {
      source = String(rawUploader);
    }
  } else if (isVerified) {
    source = 'Self Uploaded';
  }

  // Derive descriptive validity label based on extraction & verification lifecycle
  let validity = 'Uploaded (Pending Review)';
  if (isVerified) {
    validity = 'Verified & Ready for AI Chat';
  } else if (isRejected) {
    validity = 'Processing Failed';
  } else if (isReviewRequired) {
    validity = 'Review Required';
  } else if (isProcessing) {
    validity = 'Processing';
  } else if (hasExtractedFields) {
    validity = 'Uploaded (Pending Review)';
  } else {
    validity = 'Uploaded (Pending Review)';
  }

  const uploadedDate = bDoc.uploadedAt || bDoc.uploaded_at || bDoc.createdAt || bDoc.created_at;
  const uploadedOn = uploadedDate
    ? new Date(uploadedDate).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
    : 'Recently';

  const docNumber = bDoc.docNumber || extractedData.document_number || parsedRemarks?.docNumber || (
    (!rawRemarks || String(rawRemarks).includes('AI OCR Parsed'))
      ? `DOC-${String(bDoc.id).slice(0, 8).toUpperCase()}`
      : rawRemarks
  );

  const issuer = bDoc.issuer || extractedData.issuing_authority || parsedRemarks?.issuer || 'State Competent Authority';
  const beneficiaryName = extractedData.beneficiary_name || null;

  // Derive dynamic requirement count across applicable scheme catalog
  const requiredCount = docTypeRequirementCounts[normalizedType] ?? 0;

  return {
    id: bDoc.id,
    backendId: bDoc.id,
    documentType: normalizedType,
    name: meta.name,
    category: meta.category,
    purpose: meta.purpose,
    fileName,
    fileUrl: bDoc.fileUrl || bDoc.file_url || null,
    fileType: fileExt,
    fileSize: bDoc.fileSize || 'Standard',
    status,
    statusLabel,
    source,
    validity,
    uploadedOn,
    docNumber,
    issuer,
    beneficiaryName,
    extractedData,
    extractedText,
    ocrMetadata,
    iconType: meta.iconType,
    iconColor: meta.iconColor,
    requiredForSchemes: requiredCount
  };
}

export default function DocumentsPage() {
  const navigate = useNavigate();

  // User session derived dynamically
  const storedUser = getStoredUser() || {};

  // Documents dynamic state from backend API
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  // Associated Applications state loaded from user-namespaced storage
  const [tickets, setTickets] = useState(() => loadTicketsFromStorage(storedUser?.id));

  // Active filter tab: 'all' | 'verified' | 'pending' | 'action_required'
  const [activeTab, setActiveTab] = useState('all');

  // Search filter query
  const [searchQuery, setSearchQuery] = useState('');

  // URL search params for deep-linkable scheme readiness selection
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSchemeId = (searchParams.get('schemeId') || '').trim();

  // Selected scheme for the right-hand requirements checker (persisted across session refreshes)
  const [applicantState, setApplicantState] = useState(() => storedUser.state || 'Gujarat');
  const [schemeSearchQuery, setSchemeSearchQuery] = useState('');
  const [selectedSchemeId, setSelectedSchemeId] = useState(() => {
    if (urlSchemeId) return urlSchemeId;
    return '';
  });

  // Direct scheme fetching states for deep links not yet in local catalog
  const [directScheme, setDirectScheme] = useState(null);
  const [directSchemeNotFound, setDirectSchemeNotFound] = useState(false);
  const [isDirectSchemeLoading, setIsDirectSchemeLoading] = useState(false);

  // Auto-scroll ref and guard for direct navigation
  const checkerCardRef = useRef(null);
  const hasScrolledRef = useRef(false);

  // Sync selectedSchemeId when URL search param changes
  useEffect(() => {
    if (urlSchemeId && urlSchemeId !== selectedSchemeId) {
      setSelectedSchemeId(urlSchemeId);
    }
  }, [urlSchemeId]);

  const handleSelectReadinessScheme = (schemeId) => {
    const cleanId = (schemeId || '').trim();
    setSelectedSchemeId(cleanId);
    setDirectScheme(null);
    setDirectSchemeNotFound(false);

    if (cleanId) {
      setSearchParams({ schemeId: cleanId }, { replace: true });
      if (typeof window !== 'undefined' && window.sessionStorage) {
        window.sessionStorage.setItem('fin_selected_readiness_scheme_id', cleanId);
      }
    } else {
      setSearchParams({}, { replace: true });
      if (typeof window !== 'undefined' && window.sessionStorage) {
        window.sessionStorage.removeItem('fin_selected_readiness_scheme_id');
      }
    }
  };

  // Interactive UI modals & dropdown state
  const [activeMenu, setActiveMenu] = useState(null); // { id: string, doc: Object, anchorRect: DOMRect }
  const activeMenuRef = useRef(null);
  const activeMenuId = activeMenu?.id || null;
  const setActiveMenuId = (id) => {
    if (!id) {
      setActiveMenu(null);
    } else {
      const doc = documents.find((d) => d.id === id);
      const btn = typeof document !== 'undefined' ? document.querySelector(`[data-doc-menu-btn="${id}"]`) : null;
      const anchorRect = btn ? btn.getBoundingClientRect() : null;
      setActiveMenu(doc ? { id, doc, anchorRect } : null);
    }
  };

  // Compute floating portal position for active three-dot menu
  const menuPlacement = useMemo(() => {
    if (!activeMenu?.anchorRect || typeof window === 'undefined') return null;
    return computeDropdownPosition(
      activeMenu.anchorRect,
      window.innerWidth,
      window.innerHeight,
      { menuWidth: 180, menuHeight: 185, gap: 4, edgeMargin: 12 }
    );
  }, [activeMenu?.anchorRect]);

  // Outside click, Escape key, and scroll listener for floating menu
  useEffect(() => {
    if (!activeMenu) return;

    const handleOutsideClick = (e) => {
      if (activeMenuRef.current && activeMenuRef.current.contains(e.target)) {
        return;
      }
      const triggerBtn = document.querySelector(`[data-doc-menu-btn="${activeMenu.id}"]`);
      if (triggerBtn && triggerBtn.contains(e.target)) {
        return;
      }
      setActiveMenu(null);
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveMenu(null);
      }
    };

    const handleScrollOrResize = () => {
      const triggerBtn = document.querySelector(`[data-doc-menu-btn="${activeMenu.id}"]`);
      if (!triggerBtn) {
        setActiveMenu(null);
        return;
      }
      const rect = triggerBtn.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) {
        setActiveMenu(null);
      } else {
        setActiveMenu((prev) => (prev ? { ...prev, anchorRect: rect } : null));
      }
    };

    window.addEventListener('mousedown', handleOutsideClick);
    window.addEventListener('touchstart', handleOutsideClick);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      window.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('touchstart', handleOutsideClick);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [activeMenu?.id]);

  const [selectedDocForView, setSelectedDocForView] = useState(null);
  const [selectedTicketForView, setSelectedTicketForView] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isTicketModalOpen, setIsTicketModalOpen] = useState(false);
  const [isDossierModalOpen, setIsDossierModalOpen] = useState(false);
  const [isReminderModalOpen, setIsReminderModalOpen] = useState(false);
  const [isGuidanceModalOpen, setIsGuidanceModalOpen] = useState(false);
  const [isSecurityModalOpen, setIsSecurityModalOpen] = useState(false);

  // AI OCR Inspection and Pipeline states
  const [ocrModalTab, setOcrModalTab] = useState('facts'); // 'facts' | 'pipeline' | 'raw'
  const [isReExtracting, setIsReExtracting] = useState(false);
  const [uploadStatusStage, setUploadStatusStage] = useState('');

  // Upload Form state
  const [uploadTargetDocId, setUploadTargetDocId] = useState('address_proof');
  const [uploadSelectedFile, setUploadSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  // Apply for Government Policy Form state (derived dynamically from user session)
  const [policyFullName, setPolicyFullName] = useState(() => storedUser.fullName || storedUser.name || '');
  const [policyDob, setPolicyDob] = useState(() => storedUser.dob || '');
  const [policyState, setPolicyState] = useState(() => storedUser.state || 'Gujarat');
  const [policyDistrict, setPolicyDistrict] = useState(() => storedUser.district || '');
  const [policyCategory, setPolicyCategory] = useState(() => storedUser.socialCategory || storedUser.casteCategory || '');
  const [policyIncome, setPolicyIncome] = useState(() => storedUser.income || '');
  const [policyOccupation, setPolicyOccupation] = useState(() => storedUser.occupation || '');
  const [policyDocumentFile, setPolicyDocumentFile] = useState(null);
  const [policyIsDragging, setPolicyIsDragging] = useState(false);
  const [isSubmittingPolicy, setIsSubmittingPolicy] = useState(false);

  // Dynamic Scheme Selection & Guidance state
  const [selectedTargetSchemeId, setSelectedTargetSchemeId] = useState('');
  const [availableSchemesList, setAvailableSchemesList] = useState([]);
  const [isSchemesLoading, setIsSchemesLoading] = useState(false);
  const [schemesFetchError, setSchemesFetchError] = useState(null);
  const [schemeGuidanceResult, setSchemeGuidanceResult] = useState(null);

  // Reminder settings state
  const [reminderFrequency, setReminderFrequency] = useState('monthly');
  const [reminderEmail, setReminderEmail] = useState(() => storedUser.email || '');

  // Toast notification state
  const [toastMessage, setToastMessage] = useState(null);

  const modalFileInputRef = useRef(null);
  const policyFileInputRef = useRef(null);

  // Sync applications to namespaced localStorage on changes
  useEffect(() => {
    saveTicketsToStorage(tickets, storedUser?.id);
  }, [tickets, storedUser?.id]);

  // Load applications dynamically from Supabase
  const loadApplicationsAsTickets = async () => {
    try {
      const apps = await fetchUserApplications();
      if (apps && Array.isArray(apps)) {
        const mappedTickets = apps.map((app) => {
          const appIdShort = `APP-${String(app.id).slice(0, 8).toUpperCase()}`;
          const formattedDate = app.submitted_at || app.created_at
            ? new Date(app.submitted_at || app.created_at).toLocaleDateString('en-IN', {
                day: '2-digit',
                month: 'short',
                year: 'numeric'
              })
            : 'Recent';

          let statusLabel = 'Under Review';
          if (app.status === 'draft') statusLabel = 'Draft';
          if (app.status === 'approved' || app.status === 'sanctioned' || app.status === 'verified') statusLabel = 'Approved';
          if (app.status === 'rejected') statusLabel = 'Rejected';
          if (app.status === 'action_required') statusLabel = 'Action Required';

          const benefitStr = app.estimated_benefit ? `₹ ${Number(app.estimated_benefit).toLocaleString('en-IN')}` : null;
          const schemeName = app.scheme_name || (app.scheme && (app.scheme.scheme_name || app.scheme.name)) || `Scheme #${String(app.scheme_id).slice(0, 8).toUpperCase()}`;

          return {
            id: appIdShort,
            backendId: app.id,
            category: 'Government Scheme Application',
            docId: app.scheme_id,
            docName: schemeName,
            subject: `Application: ${schemeName}`,
            description: `Application #${appIdShort} is currently ${statusLabel}. Submitted for statutory verification and benefit processing.${benefitStr ? ` Supported benefit: ${benefitStr}.` : ''}`,
            priority: 'Normal',
            status: statusLabel,
            createdAt: formattedDate,
            benefit: benefitStr,
            rawApp: app
          };
        });
        setTickets(mappedTickets);
        return mappedTickets;
      }
    } catch (err) {
      console.warn('Could not load applications from Supabase:', err);
    }
  };

  // Load documents dynamically from backend API on mount
  const loadDocuments = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const backendDocs = await fetchUserDocuments();
      if (backendDocs && Array.isArray(backendDocs)) {
        const mapped = backendDocs.map(mapBackendDocument);
        setDocuments(mapped);
        return mapped;
      } else {
        setDocuments([]);
        return [];
      }
    } catch (err) {
      console.warn('Backend document synchronization skipped:', err);
      setFetchError(err.message || 'Failed to load documents');
      setDocuments([]);
      return [];
    } finally {
      setIsLoading(false);
    }
  };

  // Dynamically load real schemes for applicant state & Central jurisdiction
  const loadOfficialSchemes = async (targetState) => {
    setIsSchemesLoading(true);
    setSchemesFetchError(null);
    try {
      const stateParam = targetState || applicantState || storedUser.state || 'Gujarat';

      // Unified canonical catalog fetch directly from backend single source of truth
      try {
        const catalog = await fetchApplicableSchemesCatalog(stateParam);
        if (catalog && Array.isArray(catalog.schemes) && catalog.schemes.length > 0) {
          setAvailableSchemesList(catalog.schemes);
          return;
        }
      } catch (catErr) {
        console.warn('Unified catalog fetch notice:', catErr.message);
      }

      const [stateRes, centralRes] = await Promise.allSettled([
        fetchSchemes({ state: stateParam, limit: 2000 }),
        fetchSchemes({ state: 'All India', type: 'Central', limit: 1000 }),
      ]);

      const combined = [];
      const seenIds = new Set();
      const ingest = (res) => {
        if (res.status === 'fulfilled' && res.value) {
          const list = filterActiveSchemesForCatalog(res.value);
          list.forEach((s) => {
            const sid = s.id || s.scheme_id;
            if (sid && !seenIds.has(sid)) {
              seenIds.add(sid);
              combined.push(s);
            }
          });
        }
      };

      ingest(stateRes);
      ingest(centralRes);

      // If state query returned empty (e.g. backend offline or state empty), fallback to broad search
      if (combined.length === 0) {
        const fallbackRes = await fetchSchemes({ limit: 1000 }).catch(() => null);
        if (fallbackRes) {
          const list = filterActiveSchemesForCatalog(fallbackRes);
          list.forEach((s) => {
            const sid = s.id || s.scheme_id;
            if (sid && !seenIds.has(sid)) {
              seenIds.add(sid);
              combined.push(s);
            }
          });
        }
      }

      setAvailableSchemesList(combined);
    } catch (primaryErr) {
      console.warn('Official schemes fetch notice:', primaryErr.message);
      searchSchemes({ limit: 1000 }).then((res) => {
        const schemes = filterActiveSchemesForCatalog(res);
        setAvailableSchemesList(schemes);
      }).catch((searchErr) => {
        console.warn('Schemes search fallback failed:', searchErr.message);
        setSchemesFetchError(searchErr.message || 'Failed to load official schemes');
        setAvailableSchemesList([]);
      });
    } finally {
      setIsSchemesLoading(false);
    }
  };

  // Load documents, applications, user profile, and schemes dynamically on mount
  useEffect(() => {
    loadDocuments();
    loadApplicationsAsTickets();

    const initialTargetState = storedUser.state || 'Gujarat';
    loadOfficialSchemes(initialTargetState);

    // Dynamically load real user profile from Supabase
    fetchUserProfile().then((prof) => {
      if (prof) {
        if (prof.full_name) setPolicyFullName(prof.full_name);
        if (prof.date_of_birth) setPolicyDob(prof.date_of_birth);
        if (prof.state) {
          setPolicyState(prof.state);
          setApplicantState(prof.state);
          if (prof.state !== initialTargetState) {
            loadOfficialSchemes(prof.state);
          }
        }
        if (prof.city) setPolicyDistrict(prof.city);
        if (prof.caste_category) setPolicyCategory(prof.caste_category.toUpperCase());
        if (prof.annual_income) setPolicyIncome(String(prof.annual_income));
        if (prof.occupation) setPolicyOccupation(prof.occupation);
      }
    }).catch((err) => console.debug('Profile fetch notice:', err));
  }, []);

  // Re-run AI OCR pipeline on demand
  const handleReRunOcr = async (docId) => {
    if (!docId) return;
    setIsReExtracting(true);
    try {
      await extractDocumentData(docId);
      const reloaded = await loadDocuments();
      const updated = reloaded?.find(d => d.backendId === docId || d.id === docId);
      if (updated) {
        setSelectedDocForView(updated);
      }
      triggerToast('AI OCR re-analysis completed successfully!');
    } catch (err) {
      triggerToast(`Re-extraction failed: ${err.message || 'Service error'}`);
    } finally {
      setIsReExtracting(false);
    }
  };

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

  // Filter schemes applicable to applicant's state and Central jurisdiction
  const applicantSchemes = useMemo(() => {
    return filterApplicantRelevantSchemes(availableSchemesList, policyState || applicantState);
  }, [availableSchemesList, policyState, applicantState]);

  // Dynamic schemes for right-hand widget (strictly derived from applicant-relevant catalog)
  const dynamicSchemes = useMemo(() => {
    return deriveDynamicSchemeChecklist(applicantSchemes);
  }, [applicantSchemes]);

  // Load direct scheme if selectedSchemeId is a deep link not present in local list
  useEffect(() => {
    if (!selectedSchemeId) {
      setDirectScheme(null);
      setDirectSchemeNotFound(false);
      return;
    }

    const inDynamic = dynamicSchemes?.some(
      (s) => s.id === selectedSchemeId || (s.slug && s.slug === selectedSchemeId)
    );
    const inAvailable = availableSchemesList?.some(
      (s) => s.id === selectedSchemeId || s.scheme_id === selectedSchemeId || (s.slug && s.slug === selectedSchemeId)
    );

    if (inDynamic || inAvailable) {
      setDirectSchemeNotFound(false);
      return;
    }

    if (isSchemesLoading) return;

    let isMounted = true;
    setIsDirectSchemeLoading(true);
    setDirectSchemeNotFound(false);

    fetchSchemeById(selectedSchemeId)
      .then((data) => {
        if (!isMounted) return;
        if (data) {
          const parsed = buildDynamicSchemeChecklist([data])[0];
          setDirectScheme(parsed || null);
          setDirectSchemeNotFound(!parsed);
        } else {
          setDirectScheme(null);
          setDirectSchemeNotFound(true);
        }
      })
      .catch(() => {
        if (!isMounted) return;
        setDirectScheme(null);
        setDirectSchemeNotFound(true);
      })
      .finally(() => {
        if (isMounted) setIsDirectSchemeLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedSchemeId, dynamicSchemes, availableSchemesList, isSchemesLoading]);

  // Calculate dynamic scheme impact counts across applicable catalog
  const docTypeRequirementCounts = useMemo(() => {
    const counts = {};
    const schemes = applicantSchemes && applicantSchemes.length > 0 ? applicantSchemes : availableSchemesList;
    (schemes || []).forEach((s) => {
      const rawDocs = s.documents_required || s.required_documents || s.documents || [];
      const docList = Array.isArray(rawDocs) ? rawDocs : (typeof rawDocs === 'string' ? rawDocs.split(/[;\n|,]+/) : []);
      const seenInScheme = new Set();
      docList.forEach((d) => {
        const norm = normalizeDocRequirementId(d);
        if (norm && !seenInScheme.has(norm)) {
          seenInScheme.add(norm);
          counts[norm] = (counts[norm] || 0) + 1;
        }
      });
    });
    return counts;
  }, [applicantSchemes, availableSchemesList]);

  // Enhance documents with dynamic requiredForSchemes counts
  const enhancedDocuments = useMemo(() => {
    return documents.map((d) => ({
      ...d,
      requiredForSchemes: docTypeRequirementCounts[d.documentType] ?? d.requiredForSchemes ?? 0
    }));
  }, [documents, docTypeRequirementCounts]);

  // Counts for tabs & progress
  const verifiedDocs = enhancedDocuments.filter((d) => d.status === 'verified');
  const pendingDocs = enhancedDocuments.filter((d) => d.status === 'under_review');
  const actionDocs = enhancedDocuments.filter((d) => d.status === 'action_required');

  const totalCount = enhancedDocuments.length;
  const verifiedCount = verifiedDocs.length;
  const pendingCount = pendingDocs.length;
  const actionCount = actionDocs.length;

  // Completion percentage reflects genuinely verified documents
  const completionPercentage = totalCount > 0 ? Math.round((verifiedCount / totalCount) * 100) : 0;

  // Filter documents based on active tab & live search query
  const filteredDocuments = enhancedDocuments.filter((doc) => {
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

  // Handle open upload modal (optionally targeting a specific document like 'address_proof')
  const handleOpenUploadModal = (docId = 'address_proof') => {
    setUploadTargetDocId(docId);
    setUploadSelectedFile(null);
    setUploadProgress(0);
    setIsUploading(false);
    setIsUploadModalOpen(true);
  };

  // Open Apply for Government Policy modal
  const handleOpenTicketModal = (preselectedSchemeId = null) => {
    setSchemeGuidanceResult(null);
    let target = preselectedSchemeId;
    if (!target && selectedTargetSchemeId) {
      target = selectedTargetSchemeId;
    }
    if (!target && selectedSchemeId) {
      target = selectedSchemeId;
    }
    // Verify target exists in availableSchemesList before setting
    if (target && availableSchemesList.some(s => s.id === target || s.scheme_id === target)) {
      setSelectedTargetSchemeId(target);
    } else {
      setSelectedTargetSchemeId('');
    }
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

  // Submit Government Policy Application & Direct Scheme Guidance
  const handleSubmitPolicyApplication = async (e) => {
    e.preventDefault();
    if (!policyFullName.trim()) {
      triggerToast('Please provide your Full Name.');
      return;
    }

    setIsSubmittingPolicy(true);
    try {
      if (policyDocumentFile) {
        try {
          await uploadDocumentFile(policyDocumentFile, 'income_cert');
        } catch (uploadErr) {
          console.warn('Document attachment upload notice:', uploadErr);
        }
      }

      // 1. Update real citizen profile in Supabase
      try {
        await updateUserProfile({
          full_name: policyFullName,
          date_of_birth: policyDob || null,
          state: policyState || null,
          city: policyDistrict || null,
          caste_category: policyCategory ? policyCategory.toLowerCase() : null,
          annual_income: policyIncome ? String(policyIncome).replace(/[^0-9]/g, '') : null,
          occupation: policyOccupation || null
        });
      } catch (profErr) {
        console.warn('Profile sync notice:', profErr.message);
      }

      // 1. Validate selected scheme strictly against loaded canonical catalog
      const validation = validateSchemeSelection(selectedTargetSchemeId, availableSchemesList);
      if (!validation.valid) {
        triggerToast(validation.message);
        setIsSubmittingPolicy(false);
        return;
      }

      // 2. Resolve authoritative scheme details (never fabricated)
      const targetScheme = await resolveCanonicalSchemeDetails(validation.matchingScheme, fetchSchemeById);
      if (!targetScheme) {
        triggerToast('Selected scheme could not be verified against the official catalog. Please select a valid scheme.');
        setIsSubmittingPolicy(false);
        return;
      }

      // 4. Submit real application to Supabase (authentic benefit amount without fabricated defaults)
      const createdApp = await submitApplication({
        schemeId: targetScheme.id,
        schemeName: targetScheme.name,
        benefitAmount: targetScheme.max_benefit || null,
        applicantDetails: {
          fullName: policyFullName,
          dob: policyDob,
          state: policyState,
          district: policyDistrict,
          category: policyCategory,
          income: policyIncome,
          occupation: policyOccupation
        }
      });

      // 4. Reload active applications and documents directly from Supabase
      await loadApplicationsAsTickets();
      await loadDocuments();

      const appIdShort = createdApp?.id ? `APP-${String(createdApp.id).slice(0, 8).toUpperCase()}` : 'APP-REGISTERED';

      // 5. Directly guide citizen with their matched scheme and ticket status
      setSchemeGuidanceResult({
        ticketId: appIdShort,
        backendId: createdApp?.id,
        schemeId: targetScheme.id,
        schemeName: targetScheme.name,
        ministry: targetScheme.ministry || 'Government of India',
        benefit: targetScheme.benefit,
        matchScore: targetScheme.matchScore || 95,
        verdict: 'ELIGIBLE & APPLICATION SUBMITTED',
        reason: targetScheme.reason,
        submittedAt: 'Just now'
      });

      triggerToast(`Application #${appIdShort} recorded in Supabase!`);
    } catch (err) {
      console.error('Application submit error:', err);
      triggerToast(`Submission notice: ${err.message || 'Error creating application'}`);
    } finally {
      setIsSubmittingPolicy(false);
    }
  };

  // Process uploaded file through 3-tier OCR verification pipeline
  const handleProcessDirectUpload = async (file, targetId = null) => {
    const targetDocId = targetId || uploadTargetDocId || 'aadhaar';

    setIsUploading(true);
    setUploadProgress(20);
    setUploadStatusStage('1/3: Ingesting file & verifying integrity checksum...');

    try {
      const uploadedBackendDoc = await uploadDocumentFile(file, targetDocId);
      setUploadProgress(60);
      setUploadStatusStage('2/3: Running Layered OCR Vision Pipeline (PyMuPDF / PaddleOCR)...');

      if (uploadedBackendDoc && uploadedBackendDoc.id) {
        try {
          await extractDocumentData(uploadedBackendDoc.id);
        } catch (extractErr) {
          console.warn('AI OCR extraction non-blocking notice:', extractErr.message);
        }
      }

      setUploadProgress(90);
      setUploadStatusStage('3/3: Extracting statutory fields & registering in vault...');

      const refreshed = await loadDocuments();
      setUploadProgress(100);
      setUploadStatusStage('OCR Extraction Complete (Pending Statutory Verification)');

      setTimeout(() => {
        setIsUploadModalOpen(false);
        setUploadSelectedFile(null);
        setUploadProgress(0);
        setUploadStatusStage('');

        // Find the newly uploaded/updated document and open its verification modal
        if (refreshed && uploadedBackendDoc) {
          const matched = refreshed.find(d => d.backendId === uploadedBackendDoc.id || d.id === uploadedBackendDoc.id);
          if (matched) {
            setSelectedDocForView(matched);
            setOcrModalTab('facts');
          }
        }
        triggerToast(`Document "${file.name}" uploaded. OCR extraction complete (Pending Statutory Review).`);
      }, 500);
    } catch (err) {
      console.warn('Backend document upload error:', err.message);
      triggerToast(`Document upload failed: ${err.message || 'Service unavailable'}`);
      setIsUploading(false);
      setUploadStatusStage('');
    } finally {
      setIsUploading(false);
    }
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
    try {
      await deleteDocument(docId);
      await loadDocuments();
      triggerToast('Document removed successfully.');
    } catch (err) {
      console.warn('Backend document delete error:', err.message);
      triggerToast(`Failed to remove document: ${err.message || 'Network error'}`);
    }
  };

  // Re-run AI OCR Extraction pipeline for a document
  const handleReExtractDoc = async (doc) => {
    const backendId = doc.backendId || doc.id;
    if (!backendId) return;
    setIsReExtracting(true);
    try {
      triggerToast('Running Layered OCR Vision Pipeline...');
      await extractDocumentData(backendId);
      const refreshed = await loadDocuments();
      if (refreshed) {
        const updated = refreshed.find(d => d.backendId === backendId || d.id === backendId);
        if (updated) setSelectedDocForView(updated);
      }
      triggerToast('AI OCR facts extracted and saved successfully!');
    } catch (err) {
      console.warn('Re-extraction error:', err);
      triggerToast(`OCR notice: ${err.message || 'Processing fallback used'}`);
    } finally {
      setIsReExtracting(false);
    }
  };

  // Handle Document File Download via Supabase Storage signed URL
  const handleDownloadDoc = async (doc) => {
    if (!doc) return;
    try {
      triggerToast(`Preparing download for ${doc.name || 'document'}...`);
      let url = doc.fileUrl;
      const docId = doc.backendId || doc.id;
      if (!url && docId) {
        try {
          const details = await getDocumentDetails(docId);
          url = details?.fileUrl;
        } catch (fetchErr) {
          console.warn('Could not fetch signed url:', fetchErr);
        }
      }

      if (!url) {
        triggerToast('Document file URL is not available in storage.');
        return;
      }

      // Download file using blob fetch so browser saves with correct name
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network fetch failed');
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = doc.fileName || `${(doc.name || 'document').replace(/\s+/g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
        triggerToast(`Downloaded ${doc.name || 'document'} successfully!`);
      } catch (blobErr) {
        // Fallback: direct window.open
        window.open(url, '_blank');
        triggerToast(`Opening ${doc.name || 'document'}...`);
      }
    } catch (err) {
      console.error('Download error:', err);
      triggerToast(`Download failed: ${err.message || 'Unknown error'}`);
    }
  };

  // Dossier Export handler
  const handleExportDossier = () => {
    try {
      if (!documents || documents.length === 0) {
        triggerToast('No documents found in vault to generate a dossier.');
        return;
      }
      setIsDossierModalOpen(false);
      triggerToast('Compiling document dossier...');
      const success = downloadDossierPdf(documents, storedUser, { title: 'Citizen Document Dossier' });
      if (success) {
        triggerToast('Citizen Document Dossier downloaded successfully.');
      } else {
        triggerToast('No valid documents available to compile dossier.');
      }
    } catch (err) {
      console.error('Dossier export failed:', err);
      triggerToast(`Dossier generation failed: ${err.message || 'Error creating PDF'}`);
    }
  };

  // Radial progress calculations for 88%
  const radius = 22;
  const strokeWidth = 4.5;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (completionPercentage / 100) * circumference;

  // Filter schemes based on in-widget search query
  const filteredDynamicSchemes = useMemo(() => {
    if (!schemeSearchQuery.trim()) return dynamicSchemes;
    const q = schemeSearchQuery.toLowerCase().trim();
    return dynamicSchemes.filter((s) => {
      const name = (s.name || '').toLowerCase();
      const id = (s.id || '').toLowerCase();
      const benefit = (s.benefit || '').toLowerCase();
      return name.includes(q) || id.includes(q) || benefit.includes(q);
    });
  }, [dynamicSchemes, schemeSearchQuery]);

  // Selected scheme checklist for right-hand widget (strictly matching selectedSchemeId; no arbitrary fallback)
  const currentScheme = useMemo(() => {
    if (!selectedSchemeId) return null;

    // 1. Direct match in applicant dynamic schemes (id or slug)
    const dynMatch = dynamicSchemes?.find(
      (s) => s.id === selectedSchemeId || (s.slug && s.slug === selectedSchemeId)
    );
    if (dynMatch) return dynMatch;

    // 2. Match in broad available schemes list (id, scheme_id, or slug)
    const availMatch = availableSchemesList?.find(
      (s) => s.id === selectedSchemeId || s.scheme_id === selectedSchemeId || (s.slug && s.slug === selectedSchemeId)
    );
    if (availMatch) {
      const parsed = buildDynamicSchemeChecklist([availMatch])[0];
      if (parsed) return parsed;
    }

    // 3. Match from direct API fetch
    if (directScheme && (directScheme.id === selectedSchemeId || (directScheme.slug && directScheme.slug === selectedSchemeId))) {
      return directScheme;
    }

    return null;
  }, [dynamicSchemes, availableSchemesList, directScheme, selectedSchemeId]);

  // Combined schemes list for Combobox (ensures deep-linked / other-state scheme is selectable in dropdown trigger)
  const comboboxSchemes = useMemo(() => {
    if (!currentScheme) return dynamicSchemes;
    const exists = dynamicSchemes.some(
      (s) => s.id === currentScheme.id || (s.slug && s.slug === currentScheme.slug)
    );
    if (!exists) {
      return [currentScheme, ...dynamicSchemes];
    }
    return dynamicSchemes;
  }, [dynamicSchemes, currentScheme]);

  // Auto-scroll / focus when navigating with schemeId
  useEffect(() => {
    if (urlSchemeId && checkerCardRef.current && !hasScrolledRef.current && (currentScheme || directSchemeNotFound)) {
      hasScrolledRef.current = true;
      const timer = setTimeout(() => {
        if (checkerCardRef.current) {
          checkerCardRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
          const focusTarget =
            checkerCardRef.current.querySelector('.checker-selected-card') ||
            checkerCardRef.current.querySelector('.checker-not-found-state') ||
            checkerCardRef.current;
          if (focusTarget) {
            focusTarget.setAttribute('tabindex', '-1');
            focusTarget.focus({ preventScroll: true });
          }
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [urlSchemeId, currentScheme, directSchemeNotFound]);

  // Strict readiness evaluation (four-tier status: Verified, Pending Verification, Review Required, Missing)
  const readinessEvaluation = useMemo(() => {
    return evaluateSchemeReadiness(currentScheme, enhancedDocuments, storedUser?.id);
  }, [currentScheme, enhancedDocuments, storedUser?.id]);

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
              <span className="metric-card-sub">
                {verifiedCount === totalCount && totalCount > 0
                  ? 'All Documents Verified'
                  : `${verifiedCount} verified, ${pendingCount} pending review`}
              </span>
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
              <span className="metric-card-sub">{actionCount > 0 ? `${actionCount} document${actionCount > 1 ? 's' : ''} require action` : 'All documents submitted'}</span>
            </div>
          </div>

          {/* Card 4: Associated Applications */}
          <div
            className="docs-metric-card clickable-metric-card"
            onClick={() => setActiveTab('tickets')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && setActiveTab('tickets')}
            aria-label="View Associated Applications"
            title="Click to view associated applications"
          >
            <div className="metric-card-icon-box purple" aria-hidden="true">
              <FileText size={19} />
            </div>
            <div className="metric-card-info">
              <div className="metric-card-top-line">
                <span className="metric-card-val">{tickets.length} Active</span>
                <span className="metric-card-total">Applications</span>
              </div>
              <span className="metric-card-title">Associated Applications</span>
              <span className="metric-card-sub">Applications linked to vault</span>
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
                <FileText size={14} color={activeTab === 'tickets' ? '#FFFFFF' : '#1264D6'} />
              </span>
              <span>Applications ({tickets.length})</span>
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
                placeholder={activeTab === 'tickets' ? "Search applications..." : "Search documents..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label={activeTab === 'tickets' ? "Search applications" : "Search documents"}
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
                  <table className="docs-table" aria-label="Associated Applications Table">
                    <thead>
                      <tr>
                        <th scope="col">Application ID</th>
                        <th scope="col">Target Scheme</th>
                        <th scope="col">Status</th>
                        <th scope="col">Submission Date & Priority</th>
                        <th scope="col">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredTickets.map((tkt) => (
                        <tr key={tkt.id}>
                          {/* Column 1: Application ID */}
                          <td>
                            <div className="doc-info-cell">
                              <div className="doc-type-icon-box icon-blue" aria-hidden="true">
                                <FileText size={18} />
                              </div>
                              <div className="doc-text-group">
                                <span className="doc-name">{tkt.id}</span>
                                <div className="doc-category-line">
                                  <span className="doc-category">{tkt.category || 'Government Scheme Application'}</span>
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Column 2: Target Scheme */}
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

                          {/* Column 4: Submission Date & Priority */}
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
                            No applications match "{searchQuery}". Click "Apply for Scheme" to submit an application.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                ) : isLoading ? (
                  <div style={{ textAlign: 'center', padding: '48px 20px', color: '#667085' }}>
                    <Clock size={24} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 8px', display: 'block' }} />
                    <p style={{ fontWeight: 600, color: '#10243A' }}>Loading your documents...</p>
                  </div>
                ) : fetchError ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: '#D92D20' }}>
                    <AlertTriangle size={24} style={{ margin: '0 auto 8px', display: 'block' }} />
                    <p style={{ fontWeight: 600 }}>{fetchError}</p>
                    <button type="button" className="btn btn-outline" onClick={loadDocuments} style={{ marginTop: '12px' }}>
                      Retry
                    </button>
                  </div>
                ) : documents.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '56px 24px' }}>
                    <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: '#F0F9FF', color: '#026AA2', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                      <UploadCloud size={28} />
                    </div>
                    <h3 style={{ fontSize: '17px', fontWeight: 600, color: '#10243A', marginBottom: '8px' }}>
                      No Documents Uploaded Yet
                    </h3>
                    <p style={{ fontSize: '13.5px', color: '#475467', maxWidth: '420px', margin: '0 auto 20px', lineHeight: 1.5 }}>
                      Upload your Aadhaar, PAN, Income or Category certificates to automatically verify eligibility across government schemes.
                    </p>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleOpenUploadModal('aadhaar')}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                    >
                      <Plus size={16} />
                      <span>Upload Your First Document</span>
                    </button>
                  </div>
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
                              {doc.extractedData && Object.keys(doc.extractedData).length > 0 && (
                                <span
                                  className="doc-extracted-summary-pill"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedDocForView(doc);
                                    setOcrModalTab('facts');
                                  }}
                                  style={{ cursor: 'pointer', marginTop: '4px' }}
                                  title="View extracted facts from AI OCR"
                                >
                                  <Sparkles size={10} color="#026AA2" />
                                  <span>AI OCR Extracted</span>
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Column 2: Purpose & Scheme Impact */}
                        <td className="doc-purpose-cell">
                          <div className="doc-purpose-title">{doc.purpose}</div>
                          {doc.requiredForSchemes > 0 && (
                            <span className="doc-scheme-count-tag">
                              Required for {doc.requiredForSchemes} scheme{doc.requiredForSchemes > 1 ? 's' : ''}
                            </span>
                          )}
                        </td>

                        {/* Column 3: Status Badge */}
                        <td>
                          {doc.statusLabel === 'Ready for AI Chat' && (
                            <span className="doc-status-badge status-verified">
                              <span className="badge-check-circle" aria-hidden="true">
                                <Check size={8} strokeWidth={3.5} />
                              </span>
                              <span>Ready for AI Chat</span>
                            </span>
                          )}
                          {doc.statusLabel === 'Processing' && (
                            <span className="doc-status-badge status-review">
                              <Clock size={12} />
                              <span>Processing</span>
                            </span>
                          )}
                          {doc.statusLabel === 'Uploaded' && (
                            <span className="doc-status-badge status-review">
                              <Clock size={12} />
                              <span>Uploaded</span>
                            </span>
                          )}
                          {doc.statusLabel === 'Review Required' && (
                            <span className="doc-status-badge status-action">
                              <AlertTriangle size={12} />
                              <span>Review Required</span>
                            </span>
                          )}
                          {doc.statusLabel === 'Processing Failed' && (
                            <span className="doc-status-badge status-action">
                              <AlertTriangle size={12} />
                              <span>Processing Failed</span>
                            </span>
                          )}
                          {!['Ready for AI Chat', 'Processing', 'Uploaded', 'Review Required', 'Processing Failed'].includes(doc.statusLabel) && (
                            <span className="doc-status-badge status-review">
                              <Clock size={12} />
                              <span>{doc.statusLabel || 'Uploaded'}</span>
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

                            {/* Three dots contextual menu trigger */}
                            <button
                              type="button"
                              className="btn-doc-more"
                              data-doc-menu-btn={doc.id}
                              aria-label={`Options for ${doc.name}`}
                              aria-haspopup="menu"
                              aria-expanded={activeMenu?.id === doc.id}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (activeMenu?.id === doc.id) {
                                  setActiveMenu(null);
                                } else {
                                  const rect = e.currentTarget.getBoundingClientRect();
                                  setActiveMenu({ id: doc.id, doc, anchorRect: rect });
                                }
                              }}
                            >
                              <MoreVertical size={15} />
                            </button>
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

          {/* Right Column: Upload, Apply for Scheme, Completion, Scheme Checker */}
          <div className="docs-right-column">
            {/* Primary Action Buttons: Upload & Apply for Scheme */}
            <div className="docs-sidebar-action-stack">
              <button
                type="button"
                className="btn-upload-new-doc"
                onClick={() => handleOpenUploadModal('address_proof')}
              >
                <Plus size={16} strokeWidth={2.5} />
                <span>Upload New Document</span>
              </button>

              <button
                type="button"
                className="btn-apply-ticket"
                onClick={() => handleOpenTicketModal()}
                title="Apply for Government Policy or Scheme"
              >
                <FileText size={16} />
                <span>Apply for Scheme</span>
              </button>
            </div>

            {/* Quick Support & Scheme Assistance Card */}
            <div className="docs-ticket-assist-card">
              <div className="ticket-assist-header">
                <div className="ticket-assist-icon" aria-hidden="true">
                  <LifeBuoy size={16} />
                </div>
                <div className="ticket-assist-title-group">
                  <h4 className="ticket-assist-title">Need Scheme Application Support?</h4>
                  <p className="ticket-assist-sub">
                    Have questions regarding required documents or application status? Submit a scheme inquiry.
                  </p>
                </div>
              </div>
              <div className="ticket-assist-footer">
                <button
                  type="button"
                  className="ticket-assist-link"
                  onClick={() => handleOpenTicketModal()}
                >
                  <span>Apply for Scheme</span>
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
                    {verifiedCount} of {totalCount} documents verified{pendingCount > 0 ? ` (${pendingCount} pending review)` : ''}
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
            <div className="docs-scheme-checker-card" ref={checkerCardRef} id="scheme-readiness-checker">
              <div className="checker-header">
                <div>
                  <h4 className="checker-title">Scheme Readiness Checker</h4>
                  <span className="checker-subtitle">
                    Evaluating vault against {policyState || applicantState || 'Gujarat'} & Central schemes
                  </span>
                </div>
                <Sparkles size={13} color="#005B50" />
              </div>

              {comboboxSchemes.length > 0 || isSchemesLoading || isDirectSchemeLoading ? (
                <>
                  {/* Accessible Searchable Scheme Combobox (Replaces Oversized Native Select) */}
                  {/* Renders .checker-search-input and bounded viewport-safe popover */}
                  <SchemeReadinessCombobox
                    schemes={comboboxSchemes}
                    selectedSchemeId={selectedSchemeId}
                    onSelectScheme={(id) => {
                      handleSelectReadinessScheme(id);
                      setSchemeSearchQuery('');
                    }}
                    isLoading={isSchemesLoading || isDirectSchemeLoading}
                    error={schemesFetchError}
                    policyState={policyState || applicantState || 'Gujarat'}
                  />

                  {/* Selected Scheme Card for Clarity & Preventing Name Clipping */}
                  {selectedSchemeId && currentScheme && (
                    <div className="checker-selected-card">
                      <div className="checker-selected-header">
                        <div className="checker-selected-title-group">
                          <span className="checker-selected-badge">
                            {currentScheme.state || (isCentralScheme(currentScheme) ? 'Central Scheme' : (policyState || applicantState || 'Gujarat'))}
                          </span>
                          <h5 className="checker-selected-name" title={currentScheme.name}>
                            {currentScheme.name}
                          </h5>
                          {currentScheme.benefit && (
                            <span className="checker-selected-benefit" title={currentScheme.benefit}>
                              {currentScheme.benefit}
                            </span>
                          )}
                        </div>
                        <button
                          type="button"
                          className="checker-change-btn"
                          onClick={() => handleSelectReadinessScheme('')}
                          title="Change selected scheme"
                          aria-label="Change selected scheme"
                        >
                          <RefreshCw size={11} />
                          <span>Change</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {selectedSchemeId && !currentScheme && isDirectSchemeLoading ? (
                    <div className="checker-neutral-state">
                      <Loader2 size={22} className="spin" color="#005B50" style={{ margin: '0 auto 6px', display: 'block' }} />
                      <p className="checker-neutral-title">Loading scheme requirements...</p>
                      <p className="checker-neutral-sub">
                        Fetching authentic statutory policy details for &quot;{selectedSchemeId}&quot;.
                      </p>
                    </div>
                  ) : selectedSchemeId && !currentScheme && (directSchemeNotFound || (!isSchemesLoading && !isDirectSchemeLoading)) ? (
                    <div className="checker-neutral-state checker-not-found-state">
                      <AlertCircle size={22} color="#D92D20" style={{ margin: '0 auto 6px', display: 'block' }} />
                      <p className="checker-neutral-title" style={{ color: '#D92D20' }}>
                        Scheme could not be found.
                      </p>
                      <p className="checker-neutral-sub">
                        The requested scheme &quot;{selectedSchemeId}&quot; is not available in the official policy registry. Please select an active scheme from the search dropdown above.
                      </p>
                    </div>
                  ) : !selectedSchemeId || !currentScheme ? (
                    <div className="checker-neutral-state">
                      <FileSearch size={22} color="#005B50" style={{ margin: '0 auto 6px', display: 'block' }} />
                      <p className="checker-neutral-title">Select a scheme to check document readiness.</p>
                      <p className="checker-neutral-sub">
                        Choose an applicable government scheme to evaluate required statutory documents against your vault.
                      </p>
                    </div>
                  ) : readinessEvaluation.status === 'REQUIREMENTS_UNAVAILABLE' ? (
                    <div className="checker-no-req-state">
                      <Info size={16} color="#475467" style={{ margin: '0 auto 6px', display: 'block' }} />
                      <p className="checker-no-req-title">Requirements unavailable</p>
                      <p className="checker-no-req-sub">
                        Official document requirements are not specified in the canonical registry for this scheme.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="checker-item-list">
                        {readinessEvaluation.requirements.map((req) => (
                          <div key={req.id} className="checker-doc-item">
                            <span className="checker-doc-name">{req.label}</span>
                            {req.status === 'Verified' && (
                              <span className="checker-status-ok">
                                <Check size={12} strokeWidth={3} />
                                <span>Verified</span>
                              </span>
                            )}
                            {req.status === 'Pending Verification' && (
                              <span className="checker-status-pending">
                                <Clock size={11} />
                                <span>Pending Verification</span>
                              </span>
                            )}
                            {req.status === 'Review Required' && (
                              <span className="checker-status-action">
                                <AlertTriangle size={11} />
                                <span>Review Required</span>
                              </span>
                            )}
                            {req.status === 'Missing' && (
                              <button
                                type="button"
                                className="checker-status-missing"
                                style={{ background: 'none', border: 'none', padding: 0 }}
                                onClick={() => handleOpenUploadModal(req.id)}
                              >
                                Upload
                              </button>
                            )}
                          </div>
                        ))}
                      </div>

                      <div className="checker-summary-box">
                        <div className="checker-summary-text">
                          {readinessEvaluation.summaryMessage}
                        </div>
                        <p className="checker-disclaimer">
                          {readinessEvaluation.disclaimer}
                        </p>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div style={{ padding: '24px 16px', textAlign: 'center', color: '#667085', fontSize: '12.5px' }}>
                  {isSchemesLoading
                    ? 'Loading official catalog schemes...'
                    : 'Official scheme catalog is currently unavailable. No fallback schemes loaded.'}
                </div>
              )}
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
          <div
            className="docs-modal-backdrop"
            onClick={() => {
              setIsTicketModalOpen(false);
              setSchemeGuidanceResult(null);
            }}
          >
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
                    <h3 className="docs-modal-title">
                      {schemeGuidanceResult ? 'Scheme Eligibility & Application' : 'Apply for Government Policy'}
                    </h3>
                    <span style={{ fontSize: '11.5px', color: '#667085' }}>
                      {schemeGuidanceResult
                        ? 'Official Statutory Guidance & Application Submission'
                        : 'Citizen Scheme Application & Document Submission'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="docs-modal-close-btn"
                  onClick={() => {
                    setIsTicketModalOpen(false);
                    setSchemeGuidanceResult(null);
                  }}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>

              <form onSubmit={handleSubmitPolicyApplication}>
                <div className="docs-modal-body policy-modal-scroll-body">
                  {/* Section 0: Target Scheme Selection */}
                  <div className="policy-form-section">
                    <div className="policy-section-header">
                      <h4 className="policy-section-title">Target Government Scheme</h4>
                    </div>
                    <div className="policy-fields-grid">
                      <div className="policy-field-group policy-field-full">
                        <label className="policy-field-label" htmlFor="policy-target-scheme">
                          Select Scheme from Official Catalog *
                        </label>
                        <select
                          id="policy-target-scheme"
                          className="docs-form-select policy-input"
                          value={selectedTargetSchemeId}
                          onChange={(e) => setSelectedTargetSchemeId(e.target.value)}
                          required
                          disabled={availableSchemesList.length === 0}
                        >
                          <option value="">
                            {isSchemesLoading
                              ? '-- Loading Official Schemes from Catalog... --'
                              : availableSchemesList.length === 0
                              ? '-- Official Scheme Catalog Unavailable --'
                              : '-- Select a Scheme from Catalog --'}
                          </option>
                          {availableSchemesList.map((s) => (
                            <option key={s.id || s.scheme_id} value={s.id || s.scheme_id}>
                              {s.name || s.scheme_name || s.title} {s.department ? `(${s.department})` : ''}
                            </option>
                          ))}
                        </select>
                        {availableSchemesList.length === 0 && !isSchemesLoading && (
                          <span style={{ fontSize: '11.5px', color: '#B42318', marginTop: '4px', display: 'block' }}>
                            Catalog unavailable. Applications cannot be submitted without an authentic scheme from the catalog.
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

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
                    disabled={isSubmittingPolicy || availableSchemesList.length === 0 || !selectedTargetSchemeId}
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
                      {SUPPORTED_DOC_TYPES.map((d) => (
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
                        <span style={{ color: '#005B50' }}>{uploadStatusStage || 'Uploading & Verifying...'}</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="completion-linear-track">
                        <div className="completion-linear-fill" style={{ width: `${uploadProgress}%`, transition: 'width 0.3s ease' }} />
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
            <div className="docs-modal-card ocr-inspection-modal" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <div className={`doc-type-icon-box icon-${selectedDocForView.iconColor}`} style={{ width: '32px', height: '32px' }}>
                    {renderDocIcon(selectedDocForView.iconType)}
                  </div>
                  <div>
                    <h3 className="docs-modal-title" style={{ fontSize: '15px' }}>{selectedDocForView.name}</h3>
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
                {/* OCR Inspection Navigation Tabs */}
                <div className="ocr-view-tabs">
                  <button
                    type="button"
                    className={`ocr-view-tab ${ocrModalTab === 'facts' ? 'active' : ''}`}
                    onClick={() => setOcrModalTab('facts')}
                  >
                    <Sparkles size={13} />
                    <span>Extracted Facts</span>
                  </button>
                  <button
                    type="button"
                    className={`ocr-view-tab ${ocrModalTab === 'overview' ? 'active' : ''}`}
                    onClick={() => setOcrModalTab('overview')}
                  >
                    <FileText size={13} />
                    <span>Document Record</span>
                  </button>
                  <button
                    type="button"
                    className={`ocr-view-tab ${ocrModalTab === 'pipeline' ? 'active' : ''}`}
                    onClick={() => setOcrModalTab('pipeline')}
                  >
                    <ShieldCheck size={13} />
                    <span>Pipeline Telemetry</span>
                  </button>
                  {selectedDocForView.extractedText && (
                    <button
                      type="button"
                      className={`ocr-view-tab ${ocrModalTab === 'raw' ? 'active' : ''}`}
                      onClick={() => setOcrModalTab('raw')}
                    >
                      <ScrollText size={13} />
                      <span>Raw Text</span>
                    </button>
                  )}
                </div>

                {/* TAB 1: EXTRACTED FACTS */}
                {ocrModalTab === 'facts' && (
                  <div className="ocr-facts-section">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC', padding: '10px 14px', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981' }} />
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#1E293B' }}>
                          Extracted Statutory Fields (Pending Verification) ({Object.keys(selectedDocForView.extractedData || {}).length} detected)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleReExtractDoc(selectedDocForView)}
                        disabled={isReExtracting}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          fontSize: '11.5px',
                          fontWeight: 600,
                          color: '#005B50',
                          background: '#E6F4F1',
                          border: 'none',
                          padding: '4px 8px',
                          borderRadius: '5px',
                          cursor: isReExtracting ? 'not-allowed' : 'pointer'
                        }}
                      >
                        <RefreshCw size={12} style={{ animation: isReExtracting ? 'spin 1s linear infinite' : 'none' }} />
                        <span>{isReExtracting ? 'Re-extracting...' : 'Re-extract with AI'}</span>
                      </button>
                    </div>

                    <div className="ocr-facts-grid">
                      <div className="ocr-fact-card highlight-blue">
                        <span className="ocr-fact-label">Beneficiary Full Name</span>
                        <span className="ocr-fact-val">
                          {selectedDocForView.extractedData?.fullName ||
                           selectedDocForView.extractedData?.beneficiary_name ||
                           selectedDocForView.extractedData?.name ||
                           selectedDocForView.beneficiaryName ||
                           'Applicant'}
                        </span>
                      </div>

                      <div className="ocr-fact-card">
                        <span className="ocr-fact-label">Document / ID Number</span>
                        <span className="ocr-fact-val" style={{ fontFamily: 'monospace', letterSpacing: '0.04em' }}>
                          {selectedDocForView.extractedData?.document_number ||
                           selectedDocForView.extractedData?.aadhaar_last4 ||
                           selectedDocForView.extractedData?.pan_number ||
                           selectedDocForView.docNumber ||
                           'RECORDED'}
                        </span>
                      </div>

                      {selectedDocForView.extractedData?.dob && (
                        <div className="ocr-fact-card">
                          <span className="ocr-fact-label">Date of Birth</span>
                          <span className="ocr-fact-val">{selectedDocForView.extractedData.dob}</span>
                        </div>
                      )}

                      {selectedDocForView.extractedData?.gender && (
                        <div className="ocr-fact-card">
                          <span className="ocr-fact-label">Gender</span>
                          <span className="ocr-fact-val">{selectedDocForView.extractedData.gender}</span>
                        </div>
                      )}

                      {(selectedDocForView.extractedData?.category || selectedDocForView.extractedData?.socialCategory) && (
                        <div className="ocr-fact-card">
                          <span className="ocr-fact-label">Caste / Social Category</span>
                          <span className="ocr-fact-val" style={{ color: '#026AA2' }}>
                            {selectedDocForView.extractedData.category || selectedDocForView.extractedData.socialCategory}
                          </span>
                        </div>
                      )}

                      {/* Family Income (Document) */}
                      {(selectedDocForView.extractedData?.annual_family_income || selectedDocForView.extractedData?.family_income) && (
                        <div className="ocr-fact-card highlight-green">
                          <span className="ocr-fact-label">Annual Family Income (Document)</span>
                          <span className="ocr-fact-val ocr-income-text">
                            {String(selectedDocForView.extractedData.annual_family_income || selectedDocForView.extractedData.family_income).startsWith('₹')
                              ? (selectedDocForView.extractedData.annual_family_income || selectedDocForView.extractedData.family_income)
                              : `₹ ${selectedDocForView.extractedData.annual_family_income || selectedDocForView.extractedData.family_income}`}
                          </span>
                          <span style={{ fontSize: '10px', color: '#667085', marginTop: '3px', display: 'block' }}>
                            Source: {selectedDocForView.name} • Page 1
                          </span>
                        </div>
                      )}

                      {/* Father's Income component if present */}
                      {selectedDocForView.extractedData?.father_income && (
                        <div className="ocr-fact-card">
                          <span className="ocr-fact-label">Father's Income</span>
                          <span className="ocr-fact-val">
                            {String(selectedDocForView.extractedData.father_income).startsWith('₹')
                              ? selectedDocForView.extractedData.father_income
                              : `₹ ${selectedDocForView.extractedData.father_income}`}
                          </span>
                          <span style={{ fontSize: '10px', color: '#667085', marginTop: '3px', display: 'block' }}>
                            Source: {selectedDocForView.name} • Page 1
                          </span>
                        </div>
                      )}

                      {/* Mother's Income component if present */}
                      {selectedDocForView.extractedData?.mother_income && (
                        <div className="ocr-fact-card">
                          <span className="ocr-fact-label">Mother's Income</span>
                          <span className="ocr-fact-val">
                            {String(selectedDocForView.extractedData.mother_income).startsWith('₹')
                              ? selectedDocForView.extractedData.mother_income
                              : `₹ ${selectedDocForView.extractedData.mother_income}`}
                          </span>
                          <span style={{ fontSize: '10px', color: '#667085', marginTop: '3px', display: 'block' }}>
                            Source: {selectedDocForView.name} • Page 1
                          </span>
                        </div>
                      )}

                      {/* Personal Income if explicitly present */}
                      {selectedDocForView.extractedData?.personal_income && (
                        <div className="ocr-fact-card highlight-green">
                          <span className="ocr-fact-label">Personal Income (Document)</span>
                          <span className="ocr-fact-val ocr-income-text">
                            {String(selectedDocForView.extractedData.personal_income).startsWith('₹')
                              ? selectedDocForView.extractedData.personal_income
                              : `₹ ${selectedDocForView.extractedData.personal_income}`}
                          </span>
                          <span style={{ fontSize: '10px', color: '#667085', marginTop: '3px', display: 'block' }}>
                            Source: {selectedDocForView.name} • Page 1
                          </span>
                        </div>
                      )}

                      {/* Generic fallback if no specific family or personal income was detected */}
                      {!selectedDocForView.extractedData?.annual_family_income &&
                       !selectedDocForView.extractedData?.family_income &&
                       !selectedDocForView.extractedData?.personal_income &&
                       (selectedDocForView.extractedData?.income || selectedDocForView.extractedData?.annual_income) && (
                        <div className="ocr-fact-card highlight-green">
                          <span className="ocr-fact-label">Extracted Income</span>
                          <span className="ocr-fact-val ocr-income-text">
                            {String(selectedDocForView.extractedData.income || selectedDocForView.extractedData.annual_income).startsWith('₹')
                              ? (selectedDocForView.extractedData.income || selectedDocForView.extractedData.annual_income)
                              : `₹ ${selectedDocForView.extractedData.income || selectedDocForView.extractedData.annual_income}`}
                          </span>
                          <span style={{ fontSize: '10px', color: '#667085', marginTop: '3px', display: 'block' }}>
                            Source: {selectedDocForView.name} • Page 1
                          </span>
                        </div>
                      )}

                      {(selectedDocForView.extractedData?.state || selectedDocForView.extractedData?.district) && (
                        <div className="ocr-fact-card">
                          <span className="ocr-fact-label">Domicile / District</span>
                          <span className="ocr-fact-val">
                            {[selectedDocForView.extractedData?.district, selectedDocForView.extractedData?.state].filter(Boolean).join(', ') || 'National'}
                          </span>
                        </div>
                      )}

                      <div className="ocr-fact-card">
                        <span className="ocr-fact-label">Issuing Authority</span>
                        <span className="ocr-fact-val" style={{ fontSize: '12px' }}>
                          {selectedDocForView.extractedData?.issuing_authority || selectedDocForView.issuer || 'Government of India'}
                        </span>
                      </div>
                    </div>

                    <div style={{ backgroundColor: '#F0F9FF', border: '1px solid #BAE6FD', padding: '10px 12px', borderRadius: '7px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <Clock size={16} color="#0284C7" style={{ flexShrink: 0 }} />
                      <span style={{ fontSize: '11.5px', color: '#0369A1', lineHeight: 1.4 }}>
                        These statutory fields have been extracted via OCR. Official statutory verification is managed by departmental authorities upon scheme submission.
                      </span>
                    </div>
                  </div>
                )}

                {/* TAB 2: OVERVIEW RECORD */}
                {ocrModalTab === 'overview' && (
                  <>
                    <div className="doc-watermark-card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#667085', fontWeight: 600 }}>
                            Official Document Record
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

                    <div style={{ backgroundColor: selectedDocForView.status === 'verified' ? '#F0FDF4' : '#F0F9FF', border: `1px solid ${selectedDocForView.status === 'verified' ? '#BBF7D0' : '#BAE6FD'}`, padding: '9px 11px', borderRadius: '7px', display: 'flex', gap: '7px', alignItems: 'center' }}>
                      {selectedDocForView.status === 'verified' ? (
                        <ShieldCheck size={17} color="#15803D" style={{ flexShrink: 0 }} />
                      ) : (
                        <Clock size={17} color="#0284C7" style={{ flexShrink: 0 }} />
                      )}
                      <span style={{ fontSize: '11.5px', color: selectedDocForView.status === 'verified' ? '#166534' : '#0369A1' }}>
                        {selectedDocForView.status === 'verified'
                          ? 'Digitally verified for seamless direct subsidy DBT scheme submission.'
                          : 'OCR extraction complete. Pending statutory departmental verification upon scheme application.'}
                      </span>
                    </div>
                  </>
                )}

                {/* TAB 3: PIPELINE TELEMETRY */}
                {ocrModalTab === 'pipeline' && (
                  <div className="ocr-pipeline-box">
                    <div className="ocr-pipeline-header">
                      <div className="ocr-pipeline-title">
                        <Sparkles size={14} />
                        <span>Layered OCR Vision Telemetry</span>
                      </div>
                      <span style={{ fontSize: '11px', color: '#10B981', fontWeight: 600 }}>
                        {selectedDocForView.ocrMetadata?.confidence ? `${Math.round(selectedDocForView.ocrMetadata.confidence * 100)}% Confidence` : 'Verified 98%'}
                      </span>
                    </div>

                    <div className="ocr-pipeline-steps">
                      <div className="ocr-pipeline-step-item">
                        <div className="ocr-step-number">1</div>
                        <div className="ocr-step-info">
                          <span className="ocr-step-title">Ingestion & Document Integrity</span>
                          <span className="ocr-step-detail">
                            Method: {selectedDocForView.ocrMetadata?.method || 'NATIVE_PDF_STREAM'} • Pages: {selectedDocForView.ocrMetadata?.pages || 1}
                          </span>
                        </div>
                      </div>

                      <div className="ocr-pipeline-step-item">
                        <div className="ocr-step-number">2</div>
                        <div className="ocr-step-info">
                          <span className="ocr-step-title">Optical Character Recognition</span>
                          <span className="ocr-step-detail">
                            Engine: {selectedDocForView.ocrMetadata?.engine || 'PyMuPDF Native Text Parser + OCR Layer'}
                          </span>
                        </div>
                      </div>

                      <div className="ocr-pipeline-step-item">
                        <div className="ocr-step-number">3</div>
                        <div className="ocr-step-info">
                          <span className="ocr-step-title">Field Normalization & Canonical Schema</span>
                          <span className="ocr-step-detail">
                            Mapped to Indian Statutory Identification Schema (Aadhaar/PAN/DBT)
                          </span>
                        </div>
                      </div>

                      <div className="ocr-pipeline-step-item">
                        <div className="ocr-step-number">4</div>
                        <div className="ocr-step-info">
                          <span className="ocr-step-title">Scheme Readiness Indexing</span>
                          <span className="ocr-step-detail">
                            {(selectedDocForView.requiredForSchemes ?? docTypeRequirementCounts[selectedDocForView.documentType] ?? 0) > 0
                              ? `Linked to ${selectedDocForView.requiredForSchemes ?? docTypeRequirementCounts[selectedDocForView.documentType]} central & state welfare scheme${(selectedDocForView.requiredForSchemes ?? docTypeRequirementCounts[selectedDocForView.documentType]) > 1 ? 's' : ''}`
                              : 'Indexed for matching against central & state welfare schemes'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 4: RAW EXTRACTED TEXT */}
                {ocrModalTab === 'raw' && selectedDocForView.extractedText && (
                  <div className="ocr-raw-text-container">
                    <pre className="ocr-raw-text-content">{selectedDocForView.extractedText}</pre>
                  </div>
                )}
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
                  onClick={() => handleDownloadDoc(selectedDocForView)}
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
                  Export a compiled document portfolio summary PDF containing all active documents in your vault, their statutory categories, document numbers, issuers, and current verification statuses.
                </p>

                <div style={{ background: '#F8F9FA', borderRadius: '7px', padding: '11px', border: '1px solid #E4E7EC' }}>
                  <div style={{ fontSize: '11.5px', fontWeight: 600, color: '#344054', marginBottom: '7px' }}>
                    Included in this Dossier ({documents.length} Vault Documents):
                  </div>
                  {documents.length === 0 ? (
                    <div style={{ fontSize: '11.5px', color: '#667085', fontStyle: 'italic' }}>
                      No documents currently available in your vault.
                    </div>
                  ) : (
                    <ul style={{ fontSize: '11.5px', color: '#475467', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {documents.map((d) => (
                        <li key={d.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '5px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                            {d.status === 'verified' ? (
                              <Check size={11} color="#087443" />
                            ) : (
                              <Clock size={11} color="#E98A00" />
                            )}
                            <span>{d.name} ({d.purpose})</span>
                          </div>
                          <span style={{ fontSize: '10.5px', color: d.status === 'verified' ? '#087443' : '#E98A00', fontWeight: 600 }}>
                            {d.status === 'verified' ? 'Verified' : 'Pending Review'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
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
                  disabled={documents.length === 0}
                  onClick={handleExportDossier}
                >
                  <Download size={13} />
                  <span>Download Dossier PDF</span>
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
                  {dynamicSchemes.length > 0 ? (
                    dynamicSchemes.slice(0, 4).map((s) => (
                      <div key={s.id} style={{ padding: '9px 11px', background: '#F8F9FA', borderRadius: '7px', border: '1px solid #E4E7EC' }}>
                        <div style={{ fontWeight: 600, color: '#10243A', fontSize: '13px' }}>{s.name}</div>
                        <div style={{ fontSize: '11.5px', color: '#475467', marginTop: '2px' }}>
                          Requires: {Array.isArray(s.requiredDocIds) && s.requiredDocIds.length > 0
                            ? s.requiredDocIds.map(d => typeof d === 'object' ? d.label : (DOC_TYPE_LOOKUP[d]?.name || d)).join(', ')
                            : 'Standard verification documents'}.
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: '14px', background: '#F8F9FA', borderRadius: '7px', border: '1px solid #E4E7EC', color: '#475467', fontSize: '12px' }}>
                      Official scheme document requirements are retrieved dynamically from the active Government scheme registry.
                    </div>
                  )}
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
            13. MODAL: VIEW APPLICATION DETAILS
            ------------------------------------------------------------------ */}
        {selectedTicketForView && (
          <div className="docs-modal-backdrop" onClick={() => setSelectedTicketForView(null)}>
            <div className="docs-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
              <div className="docs-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                  <div className="policy-modal-header-icon">
                    <FileText size={20} color="#005B50" />
                  </div>
                  <div>
                    <h3 className="docs-modal-title">Application: {selectedTicketForView.id}</h3>
                    <span style={{ fontSize: '11.5px', color: '#667085' }}>{selectedTicketForView.category || 'Government Scheme Application'}</span>
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
                        Official Application Record
                      </span>
                      <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#10243A', marginTop: '2px' }}>
                        {selectedTicketForView.subject}
                      </h4>
                    </div>
                    <span className="doc-status-badge status-review">
                      <Clock size={11} />
                      <span>{selectedTicketForView.status || 'Under Review'}</span>
                    </span>
                  </div>

                  <p style={{ fontSize: '12.5px', color: '#475467', lineHeight: 1.5, marginTop: '10px' }}>
                    {selectedTicketForView.description}
                  </p>

                  <div className="doc-preview-meta-grid" style={{ marginTop: '14px' }}>
                    <div>
                      <div className="meta-field-label">Application ID</div>
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
                      <div className="meta-field-val">{selectedTicketForView.agent || 'Departmental Review Desk'}</div>
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
                  Close Application View
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Floating Portal Action Menu (Completely escapes table clipping and viewport edges) */}
        {activeMenu && activeMenu.doc && menuPlacement && typeof document !== 'undefined' && createPortal(
          <div
            ref={activeMenuRef}
            className={`doc-menu-dropdown portal-positioned ${menuPlacement.openUpward ? 'open-upward' : 'open-downward'}`}
            role="menu"
            aria-label={`Options for ${activeMenu.doc.name}`}
            style={menuPlacement.style}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="doc-menu-item"
              role="menuitem"
              onClick={() => {
                const targetDoc = activeMenu.doc;
                setActiveMenu(null);
                setSelectedDocForView(targetDoc);
              }}
            >
              <Eye size={13} />
              <span>View Details</span>
            </button>
            {activeMenu.doc.status !== 'action_required' && (
              <button
                type="button"
                className="doc-menu-item"
                role="menuitem"
                onClick={() => {
                  const targetDoc = activeMenu.doc;
                  setActiveMenu(null);
                  handleDownloadDoc(targetDoc);
                }}
              >
                <Download size={13} />
                <span>Download Copy</span>
              </button>
            )}
            <button
              type="button"
              className="doc-menu-item"
              role="menuitem"
              onClick={() => {
                const targetDoc = activeMenu.doc;
                setActiveMenu(null);
                handleOpenUploadModal(targetDoc.id);
              }}
            >
              <RefreshCw size={13} />
              <span>Replace Document</span>
            </button>
            <button
              type="button"
              className="doc-menu-item"
              role="menuitem"
              onClick={() => {
                const targetDoc = activeMenu.doc;
                setActiveMenu(null);
                handleOpenTicketModal(targetDoc.id);
              }}
            >
              <FileText size={13} />
              <span>Apply for Scheme</span>
            </button>
            {activeMenu.doc.status !== 'action_required' && (
              <button
                type="button"
                className="doc-menu-item danger"
                role="menuitem"
                onClick={() => {
                  const targetDoc = activeMenu.doc;
                  setActiveMenu(null);
                  handleDeleteDoc(targetDoc.id);
                }}
              >
                <Trash2 size={13} />
                <span>Remove Document</span>
              </button>
            )}
          </div>,
          document.body
        )}
      </div>
    </PageContainer>
  );
}
