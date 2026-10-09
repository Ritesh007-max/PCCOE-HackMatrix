const path = require("path");
const multer = require("multer");

const ALLOWED_MIME_TYPES = new Set([
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/x-png",
    "image/webp"
]);

const GENERIC_MIME_TYPES = new Set([
    "application/octet-stream",
    "binary/octet-stream",
    "application/octetstream",
    ""
]);

const ALLOWED_EXTENSIONS = new Set([
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
]);

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * Multer filter: allows legitimate MIME types or candidate allowed extensions for buffer-level signature inspection.
 */
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: MAX_FILE_SIZE },
    fileFilter: (_req, file, cb) => {
        const rawExt = path.extname(file.originalname || "").toLowerCase();
        const mime = (file.mimetype || "").toLowerCase().trim();

        const isAllowedMime = ALLOWED_MIME_TYPES.has(mime);
        const isGenericMimeWithAllowedExt = (GENERIC_MIME_TYPES.has(mime) || !mime) && ALLOWED_EXTENSIONS.has(rawExt);
        const isAllowedExt = ALLOWED_EXTENSIONS.has(rawExt);

        if (!isAllowedMime && !isGenericMimeWithAllowedExt && !isAllowedExt) {
            const error = new Error("Unsupported file type: Only PDF, JPEG, PNG, and WEBP files are allowed");
            error.status = 400;
            return cb(error);
        }

        cb(null, true);
    }
});

/**
 * Deep buffer verification middleware to prevent file extension spoofing and validate %PDF- magic bytes.
 */
const validateUploadedFile = (req, _res, next) => {
    const file = req.file;
    if (!file) return next();

    // 1. File size check
    if (!file.buffer || file.buffer.length === 0) {
        const error = new Error("Uploaded file is empty (0 bytes)");
        error.status = 400;
        return next(error);
    }

    if (file.buffer.length > MAX_FILE_SIZE) {
        const error = new Error(`File exceeds maximum permissible size of ${MAX_FILE_SIZE / (1024 * 1024)}MB`);
        error.status = 400;
        return next(error);
    }

    const ext = path.extname(file.originalname || "").toLowerCase();
    const buffer = file.buffer;
    const headerSnippet = buffer.subarray(0, Math.min(1024, buffer.length));

    // 2. Reject known dangerous / unsupported extensions even if MIME was spoofed
    if (!ALLOWED_EXTENSIONS.has(ext) && ext !== "") {
        const error = new Error(`Unsupported file extension '${ext}'. Allowed: .pdf, .jpg, .jpeg, .png, .webp`);
        error.status = 400;
        return next(error);
    }

    // 3. Deep Magic Byte Inspection
    // PDF Magic bytes: %PDF- (hex: 25 50 44 46 2d) within first 1024 bytes (per ISO 32000-1)
    const pdfSigIndex = headerSnippet.indexOf(Buffer.from("%PDF-"));
    const isPdfSignature = pdfSigIndex !== -1;

    // PNG Magic bytes: 89 50 4e 47 0d 0a 1a 0a
    const isPngSignature = buffer.length >= 8 &&
        buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4e && buffer[3] === 0x47 &&
        buffer[4] === 0x0d && buffer[5] === 0x0a && buffer[6] === 0x1a && buffer[7] === 0x0a;

    // JPEG Magic bytes: ff d8 ff
    const isJpegSignature = buffer.length >= 3 &&
        buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff;

    // WEBP Magic bytes: RIFF....WEBP
    const isWebpSignature = buffer.length >= 12 &&
        buffer.subarray(0, 4).toString("ascii") === "RIFF" &&
        buffer.subarray(8, 12).toString("ascii") === "WEBP";

    // Validate claimed PDF
    if (ext === ".pdf" || file.mimetype === "application/pdf") {
        if (!isPdfSignature) {
            if (isPngSignature) {
                const error = new Error("Invalid PDF file: PNG image was renamed with a .pdf extension");
                error.status = 400;
                return next(error);
            }
            if (isJpegSignature) {
                const error = new Error("Invalid PDF file: JPEG image was renamed with a .pdf extension");
                error.status = 400;
                return next(error);
            }
            const error = new Error("Invalid PDF file: File content does not match PDF signature (%PDF-)");
            error.status = 400;
            return next(error);
        }
        // Normalize MIME type
        file.mimetype = "application/pdf";
        return next();
    }

    // Validate claimed PNG
    if (ext === ".png" || file.mimetype === "image/png") {
        if (!isPngSignature) {
            const error = new Error("Invalid PNG file: File content does not match PNG signature");
            error.status = 400;
            return next(error);
        }
        file.mimetype = "image/png";
        return next();
    }

    // Validate claimed JPEG
    if (ext === ".jpg" || ext === ".jpeg" || file.mimetype === "image/jpeg") {
        if (!isJpegSignature) {
            const error = new Error("Invalid JPEG file: File content does not match JPEG signature");
            error.status = 400;
            return next(error);
        }
        file.mimetype = "image/jpeg";
        return next();
    }

    // Validate claimed WEBP
    if (ext === ".webp" || file.mimetype === "image/webp") {
        if (!isWebpSignature) {
            const error = new Error("Invalid WEBP file: File content does not match WEBP signature");
            error.status = 400;
            return next(error);
        }
        file.mimetype = "image/webp";
        return next();
    }

    // Generic fallback: check if buffer has PDF signature
    if (isPdfSignature) {
        file.mimetype = "application/pdf";
        return next();
    }

    const error = new Error("Unsupported file type: File signature could not be verified");
    error.status = 400;
    return next(error);
};

module.exports = {
    upload,
    validateUploadedFile,
    MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS
};
