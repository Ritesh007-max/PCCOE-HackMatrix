const path = require('path');
const crypto = require('crypto');
const { supabaseAdmin } = require('../config/supabaseConfig');
const profileService = require('./profileService');
const { throwIfError } = require('../utils/supabaseErrors');
const intelligenceClient = require('./intelligenceClient');

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DOCUMENTS_BUCKET = process.env.SUPABASE_DOCUMENTS_BUCKET || 'documents';
const ALLOWED_TYPES = new Set([
    'aadhaar', 'pan', 'udyam', 'itr', 'land', 'income_cert',
    'caste_cert', 'disability_cert', 'domicile', 'bank_passbook', 'photo', 'address_proof'
]);
const TYPE_ALIASES = {
    aadhar: 'aadhaar',
    adhaar: 'aadhaar',
    id: 'aadhaar',
    identity: 'aadhaar',
    identity_proof: 'aadhaar',
    'land records': 'land',
    land_records: 'land',
    landrecords: 'land',
    'income certificate': 'income_cert',
    income_certificate: 'income_cert',
    income: 'income_cert',
    'caste certificate': 'caste_cert',
    caste_certificate: 'caste_cert',
    caste: 'caste_cert',
    'domicile certificate': 'domicile',
    'bank passbook': 'bank_passbook',
    bank: 'bank_passbook',
    'passport size photo': 'photo',
    'address proof': 'address_proof',
    address: 'address_proof',
    other: 'address_proof',
    general: 'address_proof'
};

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

const normalizeDocumentType = (value = '') => {
    const key = String(value || 'address_proof').trim().toLowerCase();
    const type = TYPE_ALIASES[key] || key;
    if (!ALLOWED_TYPES.has(type)) {
        return 'address_proof';
    }
    return type;
};

const mapDocument = (row, signedUrl = null, { includeFileUrl = false } = {}) => {
    let parsedRemarks = null;
    if (row.reviewer_remarks) {
        try {
            parsedRemarks = JSON.parse(row.reviewer_remarks);
        } catch (_) {
            // legacy plain text string
        }
    }

    const fields = parsedRemarks?.extractedFields || parsedRemarks?.fields || {};
    const docNumber = fields.document_number || parsedRemarks?.docNumber || (
        (!row.reviewer_remarks || row.reviewer_remarks.includes('AI OCR Parsed'))
            ? `DOC-${String(row.id).slice(0, 8).toUpperCase()}`
            : row.reviewer_remarks
    );
    const issuer = fields.issuing_authority || parsedRemarks?.issuer || 'State Competent Authority';

    const result = {
        id: row.id,
        applicationId: row.application_id,
        documentType: row.document_type,
        fileName: row.file_name,
        verificationStatus: row.verification_status,
        reviewerRemarks: row.reviewer_remarks,
        docNumber,
        issuer,
        extractedData: fields,
        extractedText: parsedRemarks?.extractedText || '',
        ocrMetadata: {
            method: parsedRemarks?.method || 'AI_OCR_ENGINE',
            pages: parsedRemarks?.pages || 1,
            sha256: parsedRemarks?.sha256 || '',
            confidence: parsedRemarks?.confidence || 0.95
        },
        uploadedAt: row.uploaded_at,
        updatedAt: row.updated_at
    };
    if (includeFileUrl) result.fileUrl = signedUrl;
    return result;
};

const getApplicantId = async (userId) => {
    let profile = null;
    try {
        profile = await profileService.getProfileById(userId);
    } catch (_) { }

    if (profile && profile.id) return profile.id;

    // Auto-ensure applicant profile row exists so user can upload documents immediately
    try {
        const { data: userRow } = await supabaseAdmin
            .from('users')
            .select('full_name, email')
            .eq('id', userId)
            .maybeSingle();

        const fallbackName = userRow?.full_name || (userRow?.email ? userRow.email.split('@')[0] : 'Applicant');

        const { data, error } = await supabaseAdmin
            .from('applicant_profiles')
            .upsert({ id: userId, full_name: fallbackName }, { onConflict: 'id' })
            .select('id')
            .maybeSingle();

        if (!error && data) return data.id;
    } catch (_) { }

    return userId;
};

const getOwnedApplication = async (applicationId, userId) => {
    if (!applicationId) return null;
    const applicantId = await getApplicantId(userId);
    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('id')
        .eq('id', applicationId)
        .eq('applicant_id', applicantId)
        .maybeSingle();
    throwIfError(error);
    if (!data) throw httpError(404, 'Application not found');
    return data;
};

const getOrCreateDefaultApplication = async (userId) => {
    const applicantId = await getApplicantId(userId);
    
    // Check if user already has an application
    const { data: existingApp } = await supabaseAdmin
        .from('applications')
        .select('id')
        .eq('applicant_id', applicantId)
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();

    if (existingApp) return existingApp;

    // Auto-create a default application row for the user's document vault
    const defaultSchemeUuid = crypto.randomUUID();
    const { data: newApp, error } = await supabaseAdmin
        .from('applications')
        .insert({
            applicant_id: applicantId,
            scheme_id: defaultSchemeUuid,
            status: 'draft'
        })
        .select('id')
        .single();

    if (error && !newApp) {
        throwIfError(error);
    }

    return newApp;
};

const getOwnedApplicationIds = async (userId) => {
    let applicantId = userId;
    try {
        applicantId = await getApplicantId(userId);
    } catch (_) { }

    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('id')
        .eq('applicant_id', applicantId);
    throwIfError(error);
    return (data || []).map((application) => application.id);
};

const getSignedFileUrl = async (storagePath) => {
    if (!storagePath) return null;
    const { data, error } = await supabaseAdmin.storage
        .from(DOCUMENTS_BUCKET)
        .createSignedUrl(storagePath, 60 * 60);
    if (error) throwIfError(error);
    return data?.signedUrl || null;
};

const fetchDocumentRow = async (id, userId) => {
    const cleanId = String(id || '').trim();
    if (!cleanId || !UUID_REGEX.test(cleanId)) throw httpError(404, 'Document not found');
    const { data, error } = await supabaseAdmin
        .from('documents')
        .select('*')
        .eq('id', cleanId)
        .maybeSingle();
    throwIfError(error);
    if (!data) throw httpError(404, 'Document not found');

    try {
        await getOwnedApplication(data.application_id, userId);
    } catch (error) {
        if (error.status === 404) throw httpError(404, 'Document not found');
        throw error;
    }
    return data;
};

const uploadDocument = async ({ file, documentType, applicationId, userId }) => {
    if (!file) throw httpError(400, 'Document file is required');
    if (!userId) throw httpError(400, 'User ID is required');

    // Buffer verification: check actual PDF signature (%PDF-)
    const ext = path.extname(path.basename(file.originalname || '')).toLowerCase();
    const buffer = file.buffer || Buffer.alloc(0);
    const headerSnippet = buffer.subarray(0, Math.min(1024, buffer.length));
    const isPdfSig = headerSnippet.indexOf(Buffer.from("%PDF-")) !== -1;

    if (ext === '.pdf' || file.mimetype === 'application/pdf') {
        if (!isPdfSig) {
            throw httpError(400, 'Invalid PDF file: Missing %PDF- signature');
        }
        file.mimetype = 'application/pdf';
    }

    let application = null;
    if (applicationId) {
        application = await getOwnedApplication(applicationId, userId);
    } else {
        application = await getOrCreateDefaultApplication(userId);
    }

    const type = normalizeDocumentType(documentType);
    const id = crypto.randomUUID();
    const extension = ext.slice(0, 16);
    const storagePath = `${application.id}/${id}${extension}`;

    const { error: storageError } = await supabaseAdmin.storage
        .from(DOCUMENTS_BUCKET)
        .upload(storagePath, file.buffer, {
            contentType: file.mimetype || 'application/pdf',
            upsert: false
        });
    throwIfError(storageError);

    const { data, error } = await supabaseAdmin
        .from('documents')
        .insert({
            id,
            application_id: application.id,
            document_type: type,
            file_name: path.basename(file.originalname),
            file_url: storagePath,
            verification_status: 'PENDING'
        })
        .select('*')
        .single();

    if (error) {
        await supabaseAdmin.storage.from(DOCUMENTS_BUCKET).remove([storagePath]);
        throwIfError(error);
    }

    return mapDocument(data);
};

/**
 * POST /api/documents/extract
 * Forwards user document bytes from Supabase Storage to Intelligence /v1/documents/process
 * and persists the verification and extraction status back to Supabase.
 */
const extractDocument = async ({ documentId, userId }) => {
    if (!documentId) throw httpError(400, 'documentId is required');
    if (!userId) throw httpError(400, 'User ID is required');

    // 1. Verify document ownership and load metadata
    const docRow = await fetchDocumentRow(documentId, userId);
    if (!docRow.file_url) throw httpError(404, 'Document file storage path not found');

    // 2. Download file bytes from Supabase Storage
    const { data: fileBlob, error: downloadError } = await supabaseAdmin
        .storage
        .from(DOCUMENTS_BUCKET)
        .download(docRow.file_url);

    if (downloadError || !fileBlob) {
        throw httpError(500, `Failed to retrieve document from storage: ${downloadError?.message || 'Empty file'}`);
    }

    const fileBuffer = Buffer.from(await fileBlob.arrayBuffer());

    // 3. Build multipart form data for Intelligence /v1/documents/process
    const formData = new FormData();
    const fileName = docRow.file_name || 'document.pdf';
    const ext = path.extname(fileName).toLowerCase();
    let docMime = 'application/pdf';
    if (ext === '.png') docMime = 'image/png';
    else if (ext === '.jpg' || ext === '.jpeg') docMime = 'image/jpeg';
    else if (ext === '.webp') docMime = 'image/webp';

    const blob = new Blob([fileBuffer], { type: docMime });
    formData.append('files', blob, fileName);

    let aiResponse;
    try {
        aiResponse = await intelligenceClient.postMultipart(`/v1/documents/process?applicant_id=${encodeURIComponent(userId)}`, formData, {
            headers: {
                'X-Applicant-ID': userId
            },
            timeoutMs: 30000
        });
    } catch (err) {
        console.warn(`[documentServices] Intelligence /v1/documents/process failed: ${err.message}`);
        throw httpError(
            err.status || 503,
            `Document processing failed: ${err.message || 'Intelligence service unavailable'}`
        );
    }

    const processedItem = aiResponse?.documents?.[0] || null;

    // 4. OCR/extraction is not statutory verification.  The deployed enum has
    // PENDING/VERIFIED/REJECTED/REVIEW_REQUIRED only, so retain PENDING until
    // an authorised verification workflow marks the document VERIFIED.
    const isSuccess = processedItem && (processedItem.status === 'VALID' || processedItem.status === 'valid');
    const fields = processedItem?.extracted_fields || {};
    const ocrSummary = {
        status: isSuccess ? 'OCR_EXTRACTED' : 'REJECTED',
        statutoryVerificationStatus: isSuccess ? 'PENDING' : 'REJECTED',
        method: processedItem?.extraction_method || 'NATIVE_PDF',
        pages: processedItem?.page_count || 1,
        sha256: (processedItem?.sha256 || '').slice(0, 16),
        confidence: processedItem?.confidence_score || 0.95,
        extractedFields: fields,
        extractedText: processedItem?.extracted_text || '',
        docNumber: fields.document_number || `DOC-${String(documentId).slice(0, 8).toUpperCase()}`,
        issuer: fields.issuing_authority || 'State Authority / Revenue Dept'
    };

    const updatePayload = {
        verification_status: isSuccess ? 'PENDING' : 'REJECTED',
        reviewer_remarks: JSON.stringify(ocrSummary),
        updated_at: new Date().toISOString()
    };

    const { data: updatedDoc, error: updateError } = await supabaseAdmin
        .from('documents')
        .update(updatePayload)
        .eq('id', documentId)
        .select()
        .single();

    if (updateError) {
        console.warn(`[documentServices] Could not update document row: ${updateError.message}`);
    }

    // Do not copy OCR values into the profile.  That loses document provenance
    // and can silently overwrite a self-reported fact. Consumers receive these
    // facts with their document id and extraction status instead.

    const signedUrl = await getSignedFileUrl(docRow.file_url);

    return {
        ...mapDocument(updatedDoc || { ...docRow, ...updatePayload }, signedUrl, { includeFileUrl: true }),
        extraction: processedItem,
        requestId: aiResponse?.request_id || null
    };
};

const listDocuments = async (userId) => {
    if (!userId) throw httpError(400, 'User ID is required');
    const applicationIds = await getOwnedApplicationIds(userId);
    
    if (!applicationIds || applicationIds.length === 0) {
        return [];
    }

    const { data, error } = await supabaseAdmin
        .from('documents')
        .select('*')
        .in('application_id', applicationIds)
        .order('uploaded_at', { ascending: false });
    throwIfError(error);
    const docs = await Promise.all((data || []).map(async (row) => {
        let signedUrl = null;
        if (row.file_url) {
            try {
                signedUrl = await getSignedFileUrl(row.file_url);
            } catch (_) { }
        }
        return mapDocument(row, signedUrl, { includeFileUrl: true });
    }));
    return docs;
};

const getDocumentById = async (id, userId) => {
    if (!userId) throw httpError(400, 'User ID is required');
    const row = await fetchDocumentRow(id, userId);
    const signedUrl = await getSignedFileUrl(row.file_url);
    return mapDocument(row, signedUrl, { includeFileUrl: true });
};

const deleteDocument = async (id, userId) => {
    if (!userId) throw httpError(400, 'User ID is required');
    const row = await fetchDocumentRow(id, userId);

    const { error: deleteError } = await supabaseAdmin
        .from('documents')
        .delete()
        .eq('id', id);
    throwIfError(deleteError);

    if (row.file_url) {
        const { error: storageError } = await supabaseAdmin.storage
            .from(DOCUMENTS_BUCKET)
            .remove([row.file_url]);
        throwIfError(storageError);
    }

    // Prune document from Intelligence context repository
    try {
        await intelligenceClient.del(`/v1/documents/${id}`, {
            headers: { 'X-Applicant-ID': userId }
        });
    } catch (_) { }

    return { id };
};

module.exports = {
    uploadDocument,
    extractDocument,
    listDocuments,
    getDocumentById,
    deleteDocument,
    normalizeDocumentType
};
