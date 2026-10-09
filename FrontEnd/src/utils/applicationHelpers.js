/**
 * Universal Application Data & Presentation Helpers
 * FIN — Financial Policy Intelligence
 *
 * Implements authoritative mapping from persisted backend application records
 * to frontend application cards, status steppers, receipt generators, and details modals.
 */

export function downloadReceipt(app) {
  if (!app) return null;
  const lines = [
    '================================================================================',
    '           GOVERNMENT OF INDIA / STATE NODAL ADMINISTRATION',
    '                    FINANCIAL POLICY INTELLIGENCE (FIN)',
    '                 OFFICIAL SCHEME APPLICATION ACKNOWLEDGEMENT',
    '================================================================================',
    '',
    'APPLICATION REFERENCE',
    '--------------------------------------------------------------------------------',
    `Application Identifier : ${app.applicationId || 'N/A'}`,
    `Record Tracking ID     : ${app.dbId || app.id || 'N/A'}`,
    `Applicant Name         : ${app.applicantName || 'Applicant'}`,
    `Date of Submission     : ${app.appliedDate || 'Not specified'}`,
    `Last Updated           : ${app.lastUpdated || app.appliedDate || 'Not specified'}`,
    `Current Review Status  : ${app.statusBadge || 'Under Review'}`,
    '',
    'SCHEME & IMPLEMENTING DETAILS',
    '--------------------------------------------------------------------------------',
    `Scheme Title           : ${app.schemeTitle || 'Scheme Unavailable'}`,
    `Classification         : ${app.schemeSubtitle || 'Government Assistance'}`,
    `Benefit Category       : ${app.benefitSubtitle || 'Supported Benefit'}`,
    `Supported Benefit      : ${app.benefitAmount || 'Not specified'}`,
    '',
    'STATUS TIMELINE & VERIFICATION',
    '--------------------------------------------------------------------------------',
    ...(app.steps || []).map(s => `• ${s.label.padEnd(16)} : [${(s.status || '').toUpperCase()}] ${s.date || 'Pending'}`),
    '',
    'VERIFICATION SUMMARY',
    '--------------------------------------------------------------------------------',
    `Status Message         : ${app.statusMessage || ''}`,
    'Authority Notice       : This acknowledgement confirms the official record of your',
    '                         application submitted via the FIN Policy Intelligence Portal.',
    '                         Retain this receipt for tracking and grievance correspondence.',
    '================================================================================',
    `Generated on           : ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST`
  ];
  if (typeof document !== 'undefined' && typeof Blob !== 'undefined') {
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FIN-Receipt-${app.applicationId || 'APP'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  return lines.join('\n');
}

export function mapBackendApplication(bApp) {
  if (!bApp) return null;

  const status = (bApp.status || 'under_review').toLowerCase();
  const statusBadge = (status === 'under_review' || status === 'pending' || status === 'submitted') ? 'Under Review' :
    (status === 'approved' || status === 'sanctioned') ? 'Approved' :
    status === 'action_required' ? 'Action Required' :
    status === 'rejected' ? 'Rejected' :
    status === 'draft' ? 'Draft' : 'Submitted';

  const dateVal = bApp.submitted_at || bApp.created_at || bApp.applied_at;
  const appliedDate = dateVal
    ? new Date(dateVal).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
    : 'Not specified';

  const updatedVal = bApp.last_updated || bApp.updated_at || bApp.reviewed_at || dateVal;
  const lastUpdated = updatedVal
    ? new Date(updatedVal).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
    : appliedDate;

  // Scheme Identity
  const isAvailable = bApp.is_scheme_available !== false && Boolean(bApp.scheme_name || bApp.scheme);
  const title = isAvailable
    ? (bApp.scheme_name || (bApp.scheme && (bApp.scheme.scheme_name || bApp.scheme.name)))
    : 'Scheme Unavailable';
  const subtitle = isAvailable
    ? (bApp.scheme?.dbt_scheme ? 'Direct Benefit Transfer Scheme' : (bApp.scheme?.category || bApp.category || bApp.scheme?.benefit_type || 'Government Assistance Programme'))
    : 'Unlinked Scheme Record';

  // Financial Integrity
  let benefitAmount = 'Not specified';
  let benefitSubtitle = isAvailable ? 'Supported Benefit' : 'Benefit Information Unavailable';
  const benefitNum = typeof bApp.benefit_numeric === 'number'
    ? bApp.benefit_numeric
    : (bApp.estimated_benefit && bApp.estimated_benefit !== 175000 ? Number(bApp.estimated_benefit) : 0);

  if (bApp.benefit_display && bApp.benefit_display !== 'Not specified') {
    benefitAmount = bApp.benefit_display;
    benefitSubtitle = bApp.benefit_subtitle || 'Supported Benefit';
  } else if (bApp.financial_benefit?.amountDisplay && bApp.financial_benefit.amountDisplay !== 'Not specified') {
    benefitAmount = bApp.financial_benefit.amountDisplay;
    benefitSubtitle = bApp.financial_benefit.subtitle || 'Supported Benefit';
  } else if (benefitNum > 0) {
    benefitAmount = `₹${Number(benefitNum).toLocaleString('en-IN')}`;
    benefitSubtitle = bApp.benefit_subtitle || 'Estimated Benefit';
  } else {
    benefitAmount = 'Not specified';
    benefitSubtitle = isAvailable ? 'Not specified' : 'Benefit Information Unavailable';
  }

  const appId = bApp.id ? `FIN${String(bApp.id).replace(/-/g, '').slice(0, 8).toUpperCase()}` : 'FIN-APP';

  const logoType = String(title).toLowerCase().includes('msme') ? 'msme' :
    String(title).toLowerCase().includes('kisan') ? 'kisan' :
    String(title).toLowerCase().includes('mudra') ? 'mudra' :
    String(title).toLowerCase().includes('stand') ? 'standup' : 'ashoka';

  // Build steps progression based on real status without inventing disbursement
  const isApproved = status === 'approved' || status === 'sanctioned';
  const isRejected = status === 'rejected';
  const isAction = status === 'action_required';
  const isDraft = status === 'draft';

  const steps = [
    { label: 'Submitted', date: appliedDate, status: isDraft ? 'current-green' : 'completed' },
    {
      label: 'Verification',
      date: isDraft ? '' : isAction ? 'Action Required' : isApproved ? 'Verified' : isRejected ? 'Completed' : 'In Progress',
      status: isDraft ? 'upcoming' : isAction ? 'error' : isApproved || isRejected ? 'completed' : 'current-green'
    },
    {
      label: 'Approval',
      date: isApproved ? 'Approved' : isRejected ? 'Rejected' : '',
      status: isApproved ? 'completed' : isRejected ? 'error' : 'upcoming'
    },
    {
      label: 'Disbursement',
      date: isRejected ? 'Not Applicable' : '',
      status: isApproved ? 'current-green' : 'upcoming'
    }
  ];

  // Resolve submitted documents (with real verification status)
  const submittedDocs = Array.isArray(bApp.submitted_documents) && bApp.submitted_documents.length > 0
    ? bApp.submitted_documents
    : Array.isArray(bApp.documents) && bApp.documents.length > 0
    ? bApp.documents.map(d => ({
        id: d.id,
        name: d.file_name || d.name || d.document_type || 'Document',
        verified: (d.verification_status || '').toUpperCase() === 'VERIFIED',
        reason: (d.verification_status || '').toUpperCase() === 'VERIFIED' ? 'Verified ✓' :
          (d.verification_status || '').toUpperCase() === 'REJECTED' ? 'Rejected' : 'Pending Verification'
      }))
    : Array.isArray(bApp.rule_evaluations) && bApp.rule_evaluations.length > 0
    ? bApp.rule_evaluations
    : [];

  const requiredDocs = Array.isArray(bApp.required_documents) && bApp.required_documents.length > 0
    ? bApp.required_documents
    : Array.isArray(bApp.scheme?.documents_required)
    ? bApp.scheme.documents_required
    : Array.isArray(bApp.scheme?.required_documents)
    ? bApp.scheme.required_documents
    : [];

  return {
    id: bApp.scheme_id || bApp.id,
    applicationId: appId,
    dbId: bApp.id,
    schemeId: bApp.scheme_id,
    schemeTitle: title,
    schemeSubtitle: subtitle,
    isSchemeAvailable: Boolean(isAvailable),
    applicantName: bApp.applicant_name || bApp.applicantName || 'Applicant',
    appliedDate,
    lastUpdated,
    rawDate: dateVal ? String(dateVal).slice(0, 10) : new Date().toISOString().slice(0, 10),
    benefitAmount,
    benefitSubtitle,
    benefitNumeric: benefitNum,
    status,
    statusBadge,
    statusMessage: isApproved ? 'Your application has been approved.' :
      isRejected ? (bApp.rejection_reason || 'Your application has been rejected by the nodal authority.') :
      isAction ? (bApp.rejection_reason || 'Additional document verification is required.') :
      isDraft ? 'Application draft saved. Complete and submit when ready.' :
      'Your application is under active departmental review.',
    actionLabel: isAction ? 'Update Documents' : isDraft ? 'Continue Draft' : 'View Application',
    actionType: isAction ? 'continue' : isDraft ? 'continue' : 'view',
    logoType,
    submittedDocs,
    requiredDocs,
    remarks: bApp.remarks || bApp.decision_notes || null,
    steps,
    llmExplanation: bApp.llm_explanation || null,
    scheme: bApp.scheme || null
  };
}
