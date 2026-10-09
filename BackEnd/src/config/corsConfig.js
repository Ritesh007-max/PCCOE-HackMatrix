/**
 * FIN Backend CORS Configuration & Security Hardening Module.
 * 
 * Strict Principle:
 * - Fail-closed in production deployments.
 * - Production origins must come from explicit environment configuration (FRONTEND_ORIGINS).
 * - Reject wildcard origins ('*') in production.
 * - Reject localhost / loopback origins in production.
 * - Require HTTPS in production.
 * - Normalize and validate configured origins.
 * - Allow only necessary HTTP methods and required headers.
 * - Maintain development compatibility when NODE_ENV !== 'production'.
 * - CORS is never treated as authentication or authorization.
 */

const cors = require('cors');

/**
 * Validates and normalizes an individual origin string.
 * @param {string} origin
 * @param {boolean} isProduction
 * @returns {string} Normalized origin (scheme + host + optional port, no trailing slash or path)
 */
function validateAndNormalizeOrigin(origin, isProduction = false) {
    if (!origin || typeof origin !== 'string') {
        throw new Error('CORS configuration error: Origin must be a non-empty string.');
    }

    const trimmed = origin.trim().replace(/\/+$/, '');
    if (!trimmed) {
        throw new Error('CORS configuration error: Origin cannot be empty.');
    }

    // 1. Wildcard check
    if (trimmed === '*' || trimmed.includes('*')) {
        if (isProduction) {
            throw new Error(`Production CORS configuration error: Wildcard origin ('${trimmed}') is strictly prohibited in production.`);
        }
        return '*';
    }

    // 2. Parse URL structure
    let parsed;
    try {
        parsed = new URL(trimmed);
    } catch (_) {
        throw new Error(`CORS configuration error: Invalid origin URL format '${trimmed}'.`);
    }

    // 3. Loopback / localhost check
    const hostname = parsed.hostname.toLowerCase();
    const isLoopback = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0' || hostname === '::1' || hostname.endsWith('.local');

    if (isProduction && isLoopback) {
        throw new Error(`Production CORS configuration error: Localhost/loopback origin '${trimmed}' is strictly prohibited in production.`);
    }

    // 4. Scheme check
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error(`CORS configuration error: Invalid protocol '${parsed.protocol}' for origin '${trimmed}'. Must be http or https.`);
    }

    if (isProduction && parsed.protocol !== 'https:') {
        throw new Error(`Production CORS configuration error: Insecure HTTP origin '${trimmed}' is strictly prohibited in production. Use HTTPS.`);
    }

    // 5. Reject paths, queries, and hash fragments in origin definitions
    if (parsed.pathname !== '/' && parsed.pathname !== '') {
        throw new Error(`CORS configuration error: Origin '${trimmed}' cannot include a path ('${parsed.pathname}'). Specify origin only (e.g., https://example.com).`);
    }
    if (parsed.search || parsed.hash) {
        throw new Error(`CORS configuration error: Origin '${trimmed}' cannot include query parameters or hash fragments.`);
    }

    // Return normalized origin without trailing slash: scheme + host (+ optional port)
    return `${parsed.protocol}//${parsed.host}`;
}

/**
 * Resolves the list of allowed origins based on environment settings.
 * @param {string} env
 * @param {string} rawOriginsEnv
 * @returns {string[]} Normalized list of allowed origins
 */
function resolveAllowedOrigins(env = process.env.NODE_ENV, rawOriginsEnv = (process.env.FRONTEND_ORIGINS || process.env.CORS_ORIGINS)) {
    const isProduction = env === 'production';

    if (isProduction) {
        if (!rawOriginsEnv || !rawOriginsEnv.trim()) {
            throw new Error('Production CORS configuration error: FRONTEND_ORIGINS environment variable is required and must be explicitly configured in production.');
        }

        const entries = rawOriginsEnv
            .split(',')
            .map(s => s.trim())
            .filter(Boolean);

        if (entries.length === 0) {
            throw new Error('Production CORS configuration error: FRONTEND_ORIGINS list cannot be empty in production.');
        }

        const normalized = entries.map(o => validateAndNormalizeOrigin(o, true));
        return [...new Set(normalized)];
    }

    // Development / Test environment defaults
    const devDefaults = [
        'http://localhost:5173',
        'http://localhost:5174',
        'http://localhost:5175',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:5174',
        'http://127.0.0.1:5175',
        'http://localhost:3000',
        'http://127.0.0.1:3000'
    ];

    if (!rawOriginsEnv || !rawOriginsEnv.trim()) {
        return devDefaults;
    }

    const configured = rawOriginsEnv
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
        .map(o => {
            try {
                return validateAndNormalizeOrigin(o, false);
            } catch (_) {
                return null;
            }
        })
        .filter(Boolean);

    return [...new Set([...devDefaults, ...configured])];
}

/**
 * Creates the Express CORS options object.
 * @param {Object} options
 * @returns {Object}
 */
function getCorsOptions(options = {}) {
    const env = options.env || process.env.NODE_ENV;
    const isProduction = env === 'production';
    const allowedOrigins = options.allowedOrigins || resolveAllowedOrigins(env, options.frontendOrigins);

    return {
        origin(origin, callback) {
            // Allow requests with no origin (mobile applications, curl, server-to-server, etc.)
            if (!origin) {
                return callback(null, true);
            }

            const normOrigin = origin.trim().replace(/\/+$/, '');
            const isLoopback = /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$/.test(normOrigin);

            // In production, strictly reject any localhost or loopback origin
            if (isProduction && isLoopback) {
                const err = new Error(`CORS error: Localhost origin ${origin} is strictly prohibited in production`);
                err.status = 403;
                return callback(err);
            }

            // Check if origin is explicitly allowed
            if (allowedOrigins.includes(normOrigin)) {
                return callback(null, true);
            }

            // In development, allow localhost and 127.0.0.1 on any port
            if (!isProduction && isLoopback) {
                return callback(null, true);
            }

            // Reject untrusted origin
            const err = new Error(`CORS error: Origin ${origin} not allowed`);
            err.status = 403;
            return callback(err);
        },
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allowedHeaders: [
            'Content-Type',
            'Authorization',
            'X-Requested-With',
            'X-Correlation-ID'
        ],
        maxAge: 86400, // 24 hours preflight cache
        optionsSuccessStatus: 204
    };
}

/**
 * Creates the Express CORS middleware.
 * @param {Object} options
 * @returns {Function} Express middleware
 */
function createCorsMiddleware(options = {}) {
    const corsOptions = getCorsOptions(options);
    return cors(corsOptions);
}

module.exports = {
    validateAndNormalizeOrigin,
    resolveAllowedOrigins,
    getCorsOptions,
    createCorsMiddleware
};
