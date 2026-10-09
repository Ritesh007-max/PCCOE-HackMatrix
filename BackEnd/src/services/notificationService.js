const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { supabaseAdmin } = require('../config/supabaseConfig');

const DATA_DIR = path.resolve(__dirname, '../../.data');
const NOTIFICATIONS_FILE = path.join(DATA_DIR, 'notifications.json');

if (!fs.existsSync(DATA_DIR)) {
    try {
        fs.mkdirSync(DATA_DIR, { recursive: true });
    } catch (_) {}
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ensureUuid = (val) => {
    if (!val) return crypto.randomUUID();
    if (UUID_REGEX.test(val)) return String(val).toLowerCase();
    const hash = crypto.createHash('md5').update(String(val)).digest('hex');
    return `${hash.slice(0, 8)}-${hash.slice(8, 12)}-4${hash.slice(13, 16)}-8${hash.slice(17, 20)}-${hash.slice(20, 32)}`.toLowerCase();
};

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// Local cache for resiliency / high performance
let memoryStore = new Map();

const loadLocalFileStore = () => {
    try {
        if (fs.existsSync(NOTIFICATIONS_FILE)) {
            const raw = fs.readFileSync(NOTIFICATIONS_FILE, 'utf8');
            if (raw.trim()) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                    for (const notif of parsed) {
                        if (notif && notif.id && notif.recipientUserId) {
                            memoryStore.set(notif.id, notif);
                        }
                    }
                }
            }
        }
    } catch (err) {
        console.warn('[notificationService] Error reading local notifications store:', err.message);
    }
    return memoryStore;
};

// Initialize memory store on startup
loadLocalFileStore();

const persistLocalStore = () => {
    try {
        if (!fs.existsSync(DATA_DIR)) {
            fs.mkdirSync(DATA_DIR, { recursive: true });
        }
        const arrayData = Array.from(memoryStore.values());
        fs.writeFileSync(NOTIFICATIONS_FILE, JSON.stringify(arrayData, null, 2), 'utf8');
    } catch (err) {
        console.warn('[notificationService] Failed to persist notifications locally:', err.message);
    }
};

/**
 * Format raw database row or cached item into standard notification contract
 */
const formatNotificationRecord = (row) => {
    if (!row) return null;
    const values = row.new_values || row;
    const meta = row.metadata || {};
    const id = values.id || row.id;
    const recipientUserId = row.applicant_id || values.recipientUserId || meta.recipientUserId;
    const applicationId = values.applicationId || (row.entity_id && UUID_REGEX.test(row.entity_id) ? row.entity_id : null);
    const read = Boolean(values.read !== undefined ? values.read : meta.read);
    const createdAt = row.created_at || values.createdAt || new Date().toISOString();

    return {
        id,
        recipientUserId: String(recipientUserId || '').trim(),
        applicationId: applicationId ? String(applicationId).trim() : null,
        type: String(values.type || meta.type || 'status_update'),
        title: String(values.title || meta.title || 'Application Update'),
        message: String(values.message || meta.message || ''),
        read,
        unread: !read,
        createdAt,
        time: createdAt ? new Date(createdAt).toLocaleDateString('en-GB') : 'Recent',
        link: applicationId ? `/applications?open=${applicationId}` : '/applications'
    };
};

/**
 * Create a persistent notification for a user.
 * Writes to Supabase audit_logs (authoritative database persistence)
 * and keeps local memory/file cache updated.
 */
const createNotification = async ({
    recipientUserId,
    applicationId = null,
    type = 'status_update',
    title,
    message
}) => {
    if (!recipientUserId) {
        throw httpError(400, 'recipientUserId is required for notification');
    }

    const cleanRecipient = String(recipientUserId).trim();
    const cleanAppId = applicationId ? String(applicationId).trim() : null;
    const id = ensureUuid(crypto.randomUUID());
    const timestamp = new Date().toISOString();

    const notifPayload = {
        id,
        recipientUserId: cleanRecipient,
        applicationId: cleanAppId,
        type: String(type || 'status_update'),
        title: String(title || 'Application Update'),
        message: String(message || ''),
        read: false,
        createdAt: timestamp,
        updatedAt: timestamp
    };

    // 1. Authoritative Persistence: Save to existing Auth/Application Supabase DB
    try {
        const userUuid = UUID_REGEX.test(cleanRecipient) ? cleanRecipient : null;
        const entityUuid = cleanAppId && UUID_REGEX.test(cleanAppId) ? cleanAppId : id;

        await supabaseAdmin.from('audit_logs').insert({
            id,
            applicant_id: userUuid,
            action: 'USER_NOTIFICATION',
            entity_type: 'notification',
            entity_id: entityUuid,
            new_values: notifPayload,
            metadata: {
                recipientUserId: cleanRecipient,
                applicationId: cleanAppId,
                type: notifPayload.type,
                title: notifPayload.title,
                read: false,
                timestamp
            }
        });
    } catch (dbErr) {
        console.warn('[notificationService] Supabase notification persist warning:', dbErr.message);
    }

    // 2. Update local resilient cache
    memoryStore.set(id, notifPayload);
    persistLocalStore();

    return formatNotificationRecord(notifPayload);
};

/**
 * Fetch tenant-isolated notifications for authenticated user.
 * Queries Supabase audit_logs first (authoritative), merging with local cache.
 */
const getUserNotifications = async (userId) => {
    if (!userId) return { notifications: [], unreadCount: 0 };
    const cleanId = String(userId).trim();
    const isUuid = UUID_REGEX.test(cleanId);

    const notificationsMap = new Map();

    // 1. Fetch from Supabase database (Auth/Application DB)
    try {
        let query = supabaseAdmin
            .from('audit_logs')
            .select('*')
            .eq('action', 'USER_NOTIFICATION')
            .order('created_at', { ascending: false })
            .limit(100);

        if (isUuid) {
            query = query.or(`applicant_id.eq.${cleanId},metadata->>recipientUserId.eq.${cleanId}`);
        }

        const { data: dbRows, error } = await query;
        if (!error && Array.isArray(dbRows)) {
            for (const row of dbRows) {
                const formatted = formatNotificationRecord(row);
                if (formatted && formatted.recipientUserId === cleanId) {
                    notificationsMap.set(formatted.id, formatted);
                }
            }
        }
    } catch (err) {
        console.warn('[notificationService] Failed to query Supabase notifications:', err.message);
    }

    // 2. Merge local cache (ensures zero loss if offline or during sync)
    loadLocalFileStore();
    for (const cached of memoryStore.values()) {
        if (cached && cached.recipientUserId === cleanId) {
            if (!notificationsMap.has(cached.id)) {
                notificationsMap.set(cached.id, formatNotificationRecord(cached));
            } else {
                // If local cache has newer read status, honor it
                const existing = notificationsMap.get(cached.id);
                if (cached.read && !existing.read) {
                    existing.read = true;
                    existing.unread = false;
                }
            }
        }
    }

    const notificationsList = Array.from(notificationsMap.values());
    notificationsList.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    const unreadCount = notificationsList.filter(n => !n.read).length;

    return {
        notifications: notificationsList,
        unreadCount
    };
};

/**
 * Mark a single notification as read (with strict tenant isolation)
 */
const markAsRead = async (notificationId, userId) => {
    if (!notificationId || !userId) return null;
    const cleanId = String(userId).trim();
    const cleanNotifId = String(notificationId).trim();

    // 1. Update in Supabase
    try {
        const { data: row } = await supabaseAdmin
            .from('audit_logs')
            .select('*')
            .eq('id', cleanNotifId)
            .maybeSingle();

        if (row) {
            const rowRecipient = row.applicant_id || row.new_values?.recipientUserId || row.metadata?.recipientUserId;
            if (rowRecipient && rowRecipient !== cleanId) {
                throw httpError(403, 'Access denied: Unauthorized notification access');
            }

            const updatedNewValues = { ...(row.new_values || {}), read: true, updatedAt: new Date().toISOString() };
            const updatedMeta = { ...(row.metadata || {}), read: true };

            await supabaseAdmin
                .from('audit_logs')
                .update({
                    new_values: updatedNewValues,
                    metadata: updatedMeta
                })
                .eq('id', cleanNotifId);
        }
    } catch (dbErr) {
        if (dbErr.status === 403) throw dbErr;
        console.warn('[notificationService] Supabase mark-read warning:', dbErr.message);
    }

    // 2. Update local cache
    const cached = memoryStore.get(cleanNotifId);
    if (cached) {
        if (cached.recipientUserId !== cleanId) {
            throw httpError(403, 'Access denied: Unauthorized notification access');
        }
        cached.read = true;
        cached.updatedAt = new Date().toISOString();
        memoryStore.set(cleanNotifId, cached);
        persistLocalStore();
        return formatNotificationRecord(cached);
    }

    return { id: cleanNotifId, read: true, unread: false };
};

/**
 * Mark all notifications as read for a user
 */
const markAllAsRead = async (userId) => {
    if (!userId) return 0;
    const cleanId = String(userId).trim();
    let updatedCount = 0;

    // 1. Update in Supabase
    try {
        const { data: rows } = await supabaseAdmin
            .from('audit_logs')
            .select('*')
            .eq('action', 'USER_NOTIFICATION')
            .eq('applicant_id', cleanId);

        if (Array.isArray(rows)) {
            for (const r of rows) {
                if (!r.new_values?.read) {
                    await supabaseAdmin
                        .from('audit_logs')
                        .update({
                            new_values: { ...(r.new_values || {}), read: true, updatedAt: new Date().toISOString() },
                            metadata: { ...(r.metadata || {}), read: true }
                        })
                        .eq('id', r.id);
                    updatedCount++;
                }
            }
        }
    } catch (dbErr) {
        console.warn('[notificationService] Supabase mark-all-read warning:', dbErr.message);
    }

    // 2. Update local cache
    for (const notif of memoryStore.values()) {
        if (notif.recipientUserId === cleanId && !notif.read) {
            notif.read = true;
            notif.updatedAt = new Date().toISOString();
            memoryStore.set(notif.id, notif);
            if (updatedCount === 0) updatedCount++;
        }
    }

    if (updatedCount > 0) {
        persistLocalStore();
    }

    return updatedCount;
};

module.exports = {
    createNotification,
    getUserNotifications,
    markAsRead,
    markAllAsRead
};
