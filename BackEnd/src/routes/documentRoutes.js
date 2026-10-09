const express = require("express");
const { upload, validateUploadedFile } = require("../middleware/upload");
const documentController = require("../controllers/documentController");
const authMiddleware = require("../middleware/authMiddleware");

const router = express.Router();

router.post("/process", authMiddleware, upload.single("file"), validateUploadedFile, documentController.uploadDocument);
router.post("/upload", authMiddleware, upload.single("file"), validateUploadedFile, documentController.uploadDocument);
router.post("/extract", authMiddleware, documentController.extractDocument);
router.get("/", authMiddleware, documentController.listDocuments);
router.get("/:id", authMiddleware, documentController.getDocument);
router.delete("/:id", authMiddleware, documentController.deleteDocument);

module.exports = router;
