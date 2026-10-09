const notificationService = require('../services/notificationService');

const getNotifications = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const result = await notificationService.getUserNotifications(userId);
        return res.status(200).json({
            success: true,
            data: result.notifications,
            unreadCount: result.unreadCount
        });
    } catch (err) {
        next(err);
    }
};

const markNotificationRead = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const notificationId = req.params.id;
        const updated = await notificationService.markAsRead(notificationId, userId);
        return res.status(200).json({
            success: true,
            message: 'Notification marked as read',
            data: updated
        });
    } catch (err) {
        next(err);
    }
};

const markAllNotificationsRead = async (req, res, next) => {
    try {
        const userId = req.user.id;
        const count = await notificationService.markAllAsRead(userId);
        return res.status(200).json({
            success: true,
            message: `Marked ${count} notifications as read`
        });
    } catch (err) {
        next(err);
    }
};

module.exports = {
    getNotifications,
    markNotificationRead,
    markAllNotificationsRead
};
