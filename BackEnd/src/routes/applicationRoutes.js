const express = require('express');
const {
    analyzeApplication,
    listApplications,
    createApplication,
    getApplicationById
} = require('../controllers/applicationController');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

router.get('/', authMiddleware, listApplications);
router.post('/', authMiddleware, createApplication);
router.get('/:id', authMiddleware, getApplicationById);
router.post('/analyze', authMiddleware, analyzeApplication);

module.exports = router;

