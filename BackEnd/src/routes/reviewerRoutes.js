const express = require('express');
const authMiddleware = require('../middleware/authMiddleware');
const { requireReviewer } = require('../middleware/roleMiddleware');
const reviewerController = require('../controllers/reviewerController');

const router = express.Router();

// Strict server-side reviewer authorization guard
router.use(authMiddleware);
router.use(requireReviewer);

router.get('/dashboard', reviewerController.getDashboardStats);
router.get('/applications', reviewerController.getApplicationsQueue);
router.get('/applications/:id', reviewerController.getApplicationDetails);
router.post('/applications/:id/decision', reviewerController.submitDecision);

module.exports = router;
