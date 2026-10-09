const express = require('express');
const authMiddleware = require('../middleware/authMiddleware');
const notificationController = require('../controllers/notificationController');

const router = express.Router();

router.use(authMiddleware);

router.get('/', notificationController.getNotifications);
router.patch('/:id/read', notificationController.markNotificationRead);
router.post('/read-all', notificationController.markAllNotificationsRead);

module.exports = router;
