const documentServices = require("../services/documentServices");
const authMiddleware = require("../middleware/authMiddleware");

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

const uploadDocument = async (req, res, next) => {
    if (!req.file) {
        return next(httpError(400, "File is required"));
    }
    try {
        const document = await documentServices.uploadDocument({
            file: req.file,
            documentType: req.body.documentType || req.body.type,
            userId: req.user.id
        });

        res.status(201).json({
            success: true,
            message: "Document uploaded",
            data: document
        });
    } catch (error) {
        next(error);
    }
};

const extractDocument = async (req, res, next) => {
    try {
        const document = await documentServices.extractDocument({
            documentId: req.body.documentId || req.body.id,
            userId: req.user.id
        });

        res.json({
            success: true,
            message: "Applicant data extracted",
            data: document
        });
    } catch (error) {
        next(error);
    }
};

const listDocuments = async (req, res, next) => {
    try {
        const data = await documentServices.listDocuments(req.user.id);
        res.json({
            success: true,
            count: data.length,
            data
        });
    } catch (error) {
        next(error);
    }
};

const getDocument = async (req, res, next) => {
    try {
        const document = await documentServices.getDocumentById(req.params.id, req.user.id);
        res.json({ success: true, data: document });
    } catch (error) {
        next(error);
    }
};

const deleteDocument = async (req, res, next) => {
    try {
        const result = await documentServices.deleteDocument(req.params.id, req.user.id);
        res.json({
            success: true,
            message: "Document deleted",
            data: result
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    uploadDocument,
    extractDocument,
    listDocuments,
    getDocument,
    deleteDocument
};
