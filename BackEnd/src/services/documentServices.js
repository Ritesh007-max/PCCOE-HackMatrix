const path = require('path');
const crypto = require('crypto');
const { supabaseAdmin } = require('../config/supabaseConfig');
const profileService = require('./profileService');
const { throwIfError } = require('../utils/supabaseErrors');

const DOCUMENTS_BUCKET = process.env.SUPABASE_DOCUMENTS_BUCKET || 'documents';
const ALLOWED_TYPES = new Set([
    'aadhaar', 'pan', 'udyam', 'itr', 'land', 'income_cert',
    'caste_cert', 'disability_cert', 'domicile', 'bank_passbook', 'photo', 'address_proof'
]);
const TYPE_ALIASES = {
    aadhar: 'aadhaar',
    adhaar: 'aadhaar',
    'land records': 'land',
    land_records: 'land',
    landrecords: 'land',
    'income certificate': 'income_cert',
    'caste certificate': 'caste_cert',
    'domicile certificate': 'domicile',
    'bank passbook': 'bank_passbook',
    'passport size photo': 'photo',
    'address proof': 'address_proof'
};

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

const normalizeDocumentType = (value = '') => {
    const key = String(value).trim().toLowerCase();
    const type = TYPE_ALIASES[key] || key;
    if (!ALLOWED_TYPES.has(type)) throw httpError(400, 'Unsupported documentType');
    return type;
};

const mapDocument = (row, signedUrl = null, { includeFileUrl = false } = {}) => {
    const result = {
        id: row.id,
        applicationId: row.application_id,
        documentType: row.document_type,
        fileName: row.file_name,
        verificationStatus: row.verification_status,
        reviewerRemarks: row.reviewer_remarks,
        uploadedAt: row.uploaded_at,
        updatedAt: row.updated_at
    };
    if (includeFileUrl) result.fileUrl = signedUrl;
    return result;
};

const getApplicantId = async (userId) => {
    const profile = await profileService.getProfileById(userId);
    if (!profile) throw httpError(403, 'Create an applicant profile before attaching documents');
    return profile.id;
};

const getOwnedApplication = async (applicationId, userId) => {
    if (!applicationId) throw httpError(400, 'applicationId is required');
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

const getOwnedApplicationIds = async (userId) => {
    const profile = await profileService.getProfileById(userId);
    if (!profile) return [];
    const { data, error } = await supabaseAdmin
        .from('applications')
        .select('id')
        .eq('applicant_id', profile.id);
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
    const { data, error } = await supabaseAdmin
        .from('documents')
        .select('*')
        .eq('id', id)
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
    const application = await getOwnedApplication(applicationId, userId);
    const type = normalizeDocumentType(documentType);
    const id = crypto.randomUUID();
    const extension = path.extname(path.basename(file.originalname || '')).slice(0, 16);
    const storagePath = `${application.id}/${id}${extension}`;

    const { error: storageError } = await supabaseAdmin.storage
        .from(DOCUMENTS_BUCKET)
        .upload(storagePath, file.buffer, {
            contentType: file.mimetype,
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

// The supplied documents table has no extraction-result columns. Avoid returning
// mock extraction as if it were saved; OCR can be wired when its storage contract exists.
const extractDocument = async () => {
    throw httpError(501, 'Document extraction is not configured for the current documents schema');
};

const listDocuments = async (userId) => {
    if (!userId) throw httpError(400, 'User ID is required');
    const applicationIds = await getOwnedApplicationIds(userId);
    if (applicationIds.length === 0) return [];

    const { data, error } = await supabaseAdmin
        .from('documents')
        .select('*')
        .in('application_id', applicationIds)
        .order('uploaded_at', { ascending: false });
    throwIfError(error);
    return (data || []).map((row) => mapDocument(row));
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
    return { id };
};

module.exports = {
    uploadDocument,
    extractDocument,
    listDocuments,
    getDocumentById,
    deleteDocument
};
