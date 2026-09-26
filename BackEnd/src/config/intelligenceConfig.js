const path = require('path');

require('dotenv').config({
    path: path.join(__dirname, '../../.env')
});

const getBaseUrl = () => (process.env.AI_SERVER_URL || 'http://localhost:8000').trim().replace(/\/+$/, '');
const getApiKey = () => (process.env.AI_SERVICE_API_KEY || '').trim();

module.exports = {
    getBaseUrl,
    getApiKey,
    get AI_SERVER_URL() { return getBaseUrl(); },
    get AI_SERVICE_API_KEY() { return getApiKey(); },
    HEADER_NAME: 'X-AI-Service-Key',
    DEFAULT_TIMEOUT_MS: 30000,
    LONG_TIMEOUT_MS: 60000
};
