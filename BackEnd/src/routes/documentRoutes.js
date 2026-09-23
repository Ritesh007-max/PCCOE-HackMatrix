const express = require("express");
const { upload } = require("../middleware/upload");
const documentController = require("../controllers/documentController");

const router = express.Router();

router.post("/process", upload.single("file"), documentController.uploadDocument);
router.post("/extract", documentController.extractDocument);
router.get("/", documentController.listDocuments);
router.get("/:id", documentController.getDocument);
router.delete("/:id", documentController.deleteDocument);

module.exports = router;
