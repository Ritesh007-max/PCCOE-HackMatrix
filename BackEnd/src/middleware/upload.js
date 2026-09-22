const multer = require("multer");

const allowedMimeTypes = new Set([
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp"
]);

const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 10 * 1024 * 1024 },
    fileFilter: (_req, file, cb) => {
        if (!allowedMimeTypes.has(file.mimetype)) {
            const error = new Error("Only PDF, JPEG, PNG, and WEBP files are allowed");
            error.status = 400;
            return cb(error);
        }
        cb(null, true);
    }
});

module.exports = {
    upload
};
