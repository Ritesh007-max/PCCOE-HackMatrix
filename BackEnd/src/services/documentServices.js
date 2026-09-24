const path = require("path");
const crypto = require("crypto");
const { supabaseClient: supabase, supabaseAdmin } = require("../config/supabaseConfig");
const { throwIfError } = require("../utils/supabaseErrors");

const DOCUMENTS_BUCKET = process.env.SUPABASE_DOCUMENTS_BUCKET || "documents";

const ALLOWED_TYPES = new Set([
    "aadhaar", "pan", "udyam", "itr", "land", "income_cert",
    "caste_cert", "disability_cert", "domicile", "bank_passbook", "photo", "address_proof"
]);

const TYPE_ALIASES = {
    aadhar: "aadhaar",
    adhaar: "aadhaar",
    "land records": "land",
    land_records: "land",
    landrecords: "land",
    "income certificate": "income_cert",
    "caste certificate": "caste_cert",
    "domicile certificate": "domicile",
    "bank passbook": "bank_passbook",
    "passport size photo": "photo",
    "address proof": "address_proof"
};

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

const normalizeDocumentType = (value = "") => {
    const key = String(value).trim().toLowerCase();
    const type = TYPE_ALIASES[key] || key;
    if (!ALLOWED_TYPES.has(type)) {
        throw httpError(400, "Unsupported documentType");
    }
    return type;
};

const mapDocument = (row, signedUrl = null, { includeExtraction = false } = {}) => {
    const payload = {
        id: row.id,
        documentType: row.document_type,
        originalName: row.original_name,
        mimeType: row.mime_type,
        size: row.size,
        verificationStatus: row.verification_status,
        confidenceScore: row.confidence_score,
        extracted: Boolean(row.extracted_at),
        createdAt: row.created_at,
        updatedAt: row.updated_at
    };

    if (includeExtraction) {
        payload.extractedData = row.extracted_data;
        payload.extractionNotes = row.extraction_notes;
        payload.extractedAt = row.extracted_at;
        payload.fileUrl = signedUrl;
        payload.storagePath = row.storage_path;
    }

    return payload;
};

const getSignedFileUrl = async (storagePath) => {
    if (!storagePath) {
        return null;
    }

    const { data, error } = await supabaseAdmin.storage
        .from(DOCUMENTS_BUCKET)
        .createSignedUrl(storagePath, 60 * 60);

    if (error) {
        return null;
    }

    return data?.signedUrl || null;
};

const fetchDocumentRow = async (id, userId) => {
    const { data, error } = await supabase
        .from("documents")
        .select("*")
        .eq("id", id)
        .eq("user_id", userId)
        .maybeSingle();

    throwIfError(error);

    if (!data) {
        throw httpError(404, "Document not found");
    }

    return data;
};

const mockExtract = (documentType, originalName) => {
    const baseName = path.parse(originalName).name;

    const templates = {
        aadhaar: {
            applicantName: "Applicant Name",
            dateOfBirth: null,
            gender: null,
            aadhaarLast4: null,
            address: null,
            state: null
        },
        pan: {
            applicantName: "Applicant Name",
            panNumber: null,
            dateOfBirth: null,
            fatherName: null
        },
        udyam: {
            enterpriseName: baseName || "Enterprise",
            udyamNumber: null,
            organisationType: null,
            majorActivity: null
        },
        itr: {
            assessmentYear: null,
            panNumber: null,
            totalIncome: null,
            filingStatus: "uploaded"
        },
        land: {
            ownerName: "Applicant Name",
            surveyNumber: null,
            village: null,
            district: null,
            area: null
        },
        disability_cert: {
            applicantName: "Applicant Name",
            disabilityType: null,
            disabilityPercentage: null,
            issuingAuthority: null
        }
    };

    return {
        extracted_data: {
            documentType,
            sourceFile: originalName,
            fields: templates[documentType],
            ocrEngine: "heuristic-v1"
        },
        confidence_score: 0.62,
        extraction_notes: "Placeholder OCR/AI extraction. Replace with production OCR to fill verified field values.",
        verification_status: "under_review"
    };
};

const uploadDocument = async ({ file, documentType, userId }) => {
    if (!file) {
        throw httpError(400, "Document file is required");
    }
    if (!userId) {
        throw httpError(400, "User ID is required");
    }

    const type = normalizeDocumentType(documentType);
    const id = crypto.randomUUID();
    const ext = path.extname(file.originalname) || "";
    const storagePath = `${userId}/${id}/${Date.now()}${ext}`;

    const { error: storageError } = await supabaseAdmin.storage
        .from(DOCUMENTS_BUCKET)
        .upload(storagePath, file.buffer, {
            contentType: file.mimetype,
            upsert: false
        });

    throwIfError(storageError);

    const now = new Date().toISOString();
    const row = {
        id,
        user_id: userId,
        document_type: type,
        original_name: file.originalname,
        storage_path: storagePath,
        mime_type: file.mimetype,
        size: file.size,
        verification_status: "uploaded",
        confidence_score: null,
        extracted_data: null,
        extraction_notes: null,
        extracted_at: null,
        created_at: now,
        updated_at: now
    };

    const { data, error } = await supabase
        .from("documents")
        .insert(row)
        .select("*")
        .single();

    if (error) {
        await supabaseAdmin.storage.from(DOCUMENTS_BUCKET).remove([storagePath]);
        throwIfError(error);
    }

    return mapDocument(data);
};

const extractDocument = async ({ documentId, userId }) => {
    if (!documentId) {
        throw httpError(400, "documentId is required");
    }
    if (!userId) {
        throw httpError(400, "User ID is required");
    }

    const existing = await fetchDocumentRow(documentId, userId);
    const extracted = mockExtract(existing.document_type, existing.original_name);
    const updatedAt = new Date().toISOString();

    const { data, error } = await supabase
        .from("documents")
        .update({
            ...extracted,
            extracted_at: updatedAt,
            updated_at: updatedAt
        })
        .eq("id", documentId)
        .eq("user_id", userId)
        .select("*")
        .single();

    throwIfError(error);

    const signedUrl = await getSignedFileUrl(data.storage_path);
    return mapDocument(data, signedUrl, { includeExtraction: true });
};

const listDocuments = async (userId) => {
    if (!userId) {
        throw httpError(400, "User ID is required");
    }
    const { data, error } = await supabase
        .from("documents")
        .select("*")
        .eq("user_id", userId)
        .order("created_at", { ascending: false });

    throwIfError(error);

    return (data || []).map((row) => mapDocument(row));
};

const getDocumentById = async (id, userId) => {
    if (!userId) {
        throw httpError(400, "User ID is required");
    }
    const row = await fetchDocumentRow(id, userId);
    const signedUrl = await getSignedFileUrl(row.storage_path);
    return mapDocument(row, signedUrl, { includeExtraction: true });
};

const deleteDocument = async (id, userId) => {
    if (!userId) {
        throw httpError(400, "User ID is required");
    }
    const row = await fetchDocumentRow(id, userId);

    if (row.storage_path) {
        const { error: storageError } = await supabaseAdmin.storage
            .from(DOCUMENTS_BUCKET)
            .remove([row.storage_path]);
        throwIfError(storageError);
    }

    const { error } = await supabase.from("documents").delete().eq("id", id).eq("user_id", userId);
    throwIfError(error);

    return { id };
};

module.exports = {
    uploadDocument,
    extractDocument,
    listDocuments,
    getDocumentById,
    deleteDocument
};
