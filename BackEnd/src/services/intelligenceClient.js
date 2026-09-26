const crypto = require('crypto');
const {
    getBaseUrl,
    getApiKey,
    HEADER_NAME,
    DEFAULT_TIMEOUT_MS,
    LONG_TIMEOUT_MS
} = require('../config/intelligenceConfig');

class IntelligenceClientError extends Error {
    constructor(message, status = 502, code = 'INTELLIGENCE_ERROR', details = null) {
        super(message);
        this.name = 'IntelligenceClientError';
        this.status = status;
        this.code = code;
        this.details = details;
    }
}

/**
 * Strips sensitive data like keys, passwords, or full local filesystem paths from error messages.
 */
const sanitizeErrorMessage = (rawMessage) => {
    if (!rawMessage || typeof rawMessage !== 'string') return 'Intelligence service request failed';
    const apiKey = getApiKey();
    let sanitized = rawMessage;
    if (apiKey) {
        sanitized = sanitized.replace(new RegExp(apiKey, 'gi'), '[REDACTED_KEY]');
    }
    sanitized = sanitized
        .replace(/[A-Z]:\\[^\s:"']+/gi, '[INTERNAL_PATH]')
        .replace(/\/home\/[^\s:"']+/gi, '[INTERNAL_PATH]')
        .replace(/\b(bearer\s+)[^\s"']+/gi, '$1[REDACTED]')
        .trim();
    return sanitized.length > 300 ? sanitized.slice(0, 300) + '...' : sanitized;
};

/**
 * Normalizes HTTP response errors from FastAPI into standard application errors.
 */
const handleHttpErrorResponse = async (response) => {
    let errorDetail = null;
    try {
        const json = await response.json();
        if (json?.error?.message) {
            errorDetail = json.error.message;
        } else if (typeof json?.detail === 'string') {
            errorDetail = json.detail;
        } else if (Array.isArray(json?.detail)) {
            // FastAPI validation error (422)
            errorDetail = json.detail.map((d) => `${d.loc ? d.loc.join('.') : 'field'}: ${d.msg}`).join('; ');
        } else if (json?.message) {
            errorDetail = json.message;
        }
    } catch (_) {
        // Response was not JSON
    }

    const sanitized = sanitizeErrorMessage(errorDetail || `HTTP ${response.status} ${response.statusText}`);
    let code = 'INTELLIGENCE_HTTP_ERROR';
    if (response.status === 401 || response.status === 403) code = 'INTELLIGENCE_AUTH_ERROR';
    else if (response.status === 404) code = 'INTELLIGENCE_NOT_FOUND';
    else if (response.status === 422) code = 'INTELLIGENCE_VALIDATION_ERROR';
    else if (response.status === 429) code = 'INTELLIGENCE_RATE_LIMITED';
    else if (response.status >= 500) code = 'INTELLIGENCE_SERVER_ERROR';

    return new IntelligenceClientError(sanitized, response.status, code);
};

/**
 * Internal executor supporting JSON and multipart requests with timeouts and correlation headers.
 */
const executeRequest = async (path, options = {}) => {
    const {
        method = 'GET',
        body = null,
        headers = {},
        timeoutMs = DEFAULT_TIMEOUT_MS,
        correlationId = crypto.randomUUID()
    } = options;

    const baseUrl = getBaseUrl();
    const apiKey = getApiKey();
    const targetUrl = `${baseUrl}${path.startsWith('/') ? path : '/' + path}`;

    const requestHeaders = {
        [HEADER_NAME]: apiKey,
        'X-Request-ID': correlationId,
        ...headers
    };

    let controller;
    let timeoutId;
    let signal;

    if (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) {
        signal = AbortSignal.timeout(timeoutMs);
    } else {
        controller = new AbortController();
        timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        signal = controller.signal;
    }

    try {
        const response = await fetch(targetUrl, {
            method,
            headers: requestHeaders,
            body,
            signal
        });

        if (timeoutId) clearTimeout(timeoutId);

        if (!response.ok) {
            throw await handleHttpErrorResponse(response);
        }

        const data = await response.json();
        return data;
    } catch (err) {
        if (timeoutId) clearTimeout(timeoutId);

        if (err instanceof IntelligenceClientError) {
            throw err;
        }

        if (err.name === 'TimeoutError' || err.name === 'AbortError') {
            throw new IntelligenceClientError(
                `Intelligence service timed out after ${timeoutMs}ms`,
                504,
                'INTELLIGENCE_TIMEOUT'
            );
        }

        // Connection refused / unreachable / network error
        const sanitized = sanitizeErrorMessage(err.message || 'Network error');
        throw new IntelligenceClientError(
            `Intelligence service communication error: ${sanitized}`,
            503,
            'INTELLIGENCE_UNAVAILABLE'
        );
    }
};

/**
 * POST JSON helper.
 */
const postJson = async (path, payload, options = {}) => {
    return executeRequest(path, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        },
        body: JSON.stringify(payload),
        timeoutMs: options.timeoutMs || DEFAULT_TIMEOUT_MS,
        correlationId: options.correlationId
    });
};

/**
 * POST multipart/form-data helper.
 */
const postMultipart = async (path, formData, options = {}) => {
    // Note: Fetch sets boundary automatically when body is FormData and Content-Type is omitted
    return executeRequest(path, {
        method: 'POST',
        headers: {
            ...(options.headers || {})
        },
        body: formData,
        timeoutMs: options.timeoutMs || LONG_TIMEOUT_MS,
        correlationId: options.correlationId
    });
};

/**
 * GET helper.
 */
const get = async (path, options = {}) => {
    return executeRequest(path, {
        method: 'GET',
        headers: options.headers || {},
        timeoutMs: options.timeoutMs || DEFAULT_TIMEOUT_MS,
        correlationId: options.correlationId
    });
};

module.exports = {
    IntelligenceClientError,
    postJson,
    postMultipart,
    get,
    getBaseUrl,
    getApiKey,
    HEADER_NAME
};
