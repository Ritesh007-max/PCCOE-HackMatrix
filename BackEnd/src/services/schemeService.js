const { supabaseAdmin } = require('../config/supabaseConfig');
const profileService = require('./profileService');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// ─── Scheme catalogue (Supabase `schemes` table) ─────────────────────────────

/**
 * Search schemes. If a `schemes` table exists we query it; otherwise we fall
 * back to the rich in-memory catalogue so the API is always useful.
 */
const SCHEME_CATALOGUE = [
    {
        id: 'pmegp',
        name: 'Prime Minister Employment Generation Programme',
        short_name: 'PMEGP',
        ministry: 'Ministry of MSME',
        type: 'MSME',
        max_benefit: 5000000,
        benefit_summary: 'Margin money subsidy of 15–35% on project cost up to ₹50 lakh (manufacturing) / ₹20 lakh (service)',
        eligibility_summary: 'Any individual above 18 years. Minimum VIII standard pass for projects above ₹10 lakh (manufacturing) / ₹5 lakh (service).',
        required_documents: ['aadhaar', 'pan', 'udyam', 'itr'],
        tags: ['employment', 'msme', 'subsidy', 'loan'],
        active: true
    },
    {
        id: 'mudra-shishu',
        name: 'Pradhan Mantri MUDRA Yojana – Shishu',
        short_name: 'MUDRA Shishu',
        ministry: 'Ministry of Finance',
        type: 'Loan',
        max_benefit: 50000,
        benefit_summary: 'Collateral-free micro-loan up to ₹50,000 for micro enterprises.',
        eligibility_summary: 'Non-corporate, non-farm micro/small enterprises. No prior default to any lender.',
        required_documents: ['aadhaar', 'pan'],
        tags: ['loan', 'micro-enterprise', 'mudra'],
        active: true
    },
    {
        id: 'mudra-kishore',
        name: 'Pradhan Mantri MUDRA Yojana – Kishore',
        short_name: 'MUDRA Kishore',
        ministry: 'Ministry of Finance',
        type: 'Loan',
        max_benefit: 500000,
        benefit_summary: 'Loan between ₹50,001 and ₹5 lakh for established micro enterprises.',
        eligibility_summary: 'Existing micro/small businesses seeking expansion capital.',
        required_documents: ['aadhaar', 'pan', 'itr'],
        tags: ['loan', 'msme', 'mudra'],
        active: true
    },
    {
        id: 'pm-kisan',
        name: 'PM Kisan Samman Nidhi',
        short_name: 'PM Kisan',
        ministry: 'Ministry of Agriculture',
        type: 'Agriculture',
        max_benefit: 6000,
        benefit_summary: '₹6,000 per year in three equal instalments directly to eligible farmer families.',
        eligibility_summary: 'Small and marginal farmer families with combined land holding up to 2 hectares.',
        required_documents: ['aadhaar', 'land'],
        tags: ['farmer', 'agriculture', 'income-support'],
        active: true
    },
    {
        id: 'kcc',
        name: 'Kisan Credit Card',
        short_name: 'KCC',
        ministry: 'Ministry of Agriculture',
        type: 'Agriculture',
        max_benefit: 300000,
        benefit_summary: 'Revolving credit up to ₹3 lakh at 7% interest (4% post subvention) for crop needs.',
        eligibility_summary: 'All farmers – individual / joint borrowers, tenant farmers, sharecroppers.',
        required_documents: ['aadhaar', 'land'],
        tags: ['farmer', 'credit', 'agriculture'],
        active: true
    },
    {
        id: 'standup-india',
        name: 'Stand-Up India Scheme',
        short_name: 'Stand-Up India',
        ministry: 'Ministry of Finance',
        type: 'MSME',
        max_benefit: 10000000,
        benefit_summary: 'Bank loan between ₹10 lakh and ₹1 crore to at least one SC/ST and one woman borrower per bank branch.',
        eligibility_summary: 'SC/ST or woman entrepreneur above 18 years setting up a greenfield enterprise in manufacturing, services, or trading.',
        required_documents: ['aadhaar', 'pan', 'caste_cert'],
        tags: ['sc', 'st', 'women', 'loan', 'msme'],
        active: true
    }
];

/**
 * Text-match helper: checks if any scheme field contains the query string.
 */
const schemeMatchesQuery = (scheme, query = '') => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
        scheme.name.toLowerCase().includes(q) ||
        scheme.short_name.toLowerCase().includes(q) ||
        scheme.ministry.toLowerCase().includes(q) ||
        scheme.benefit_summary.toLowerCase().includes(q) ||
        scheme.eligibility_summary.toLowerCase().includes(q) ||
        (scheme.tags || []).some(t => t.toLowerCase().includes(q))
    );
};

/**
 * POST /api/schemes/search
 * Body: { query?, filters?: { type?, ministry?, tags?, maxBenefit? }, limit? }
 */
const searchSchemes = async ({ query, filters = {}, limit = 20 } = {}) => {
    // Try Supabase `schemes` table first
    try {
        let dbQuery = supabaseAdmin.from('schemes').select('*').eq('active', true);
        if (filters.type) dbQuery = dbQuery.eq('type', filters.type);
        if (filters.ministry) dbQuery = dbQuery.ilike('ministry', `%${filters.ministry}%`);
        const { data, error } = await dbQuery.limit(limit);

        if (!error && data && data.length > 0) {
            const results = query
                ? data.filter(s => schemeMatchesQuery(s, query))
                : data;
            return {
                source: 'database',
                total: results.length,
                schemes: results
            };
        }
    } catch (_) {
        // table may not exist yet — fall through to catalogue
    }

    // Fallback: in-memory catalogue
    let results = SCHEME_CATALOGUE.filter(s => s.active);
    if (query) results = results.filter(s => schemeMatchesQuery(s, query));
    if (filters.type) results = results.filter(s => s.type.toLowerCase() === filters.type.toLowerCase());
    if (filters.ministry) results = results.filter(s => s.ministry.toLowerCase().includes(filters.ministry.toLowerCase()));
    if (filters.maxBenefit) results = results.filter(s => s.max_benefit <= Number(filters.maxBenefit));
    if (filters.tags && filters.tags.length > 0) {
        const requiredTags = filters.tags.map(t => t.toLowerCase());
        results = results.filter(s => requiredTags.some(tag => (s.tags || []).includes(tag)));
    }

    return {
        source: 'catalogue',
        total: results.length,
        schemes: results.slice(0, limit)
    };
};

/**
 * GET /api/schemes/:id
 */
const getSchemeById = async (id) => {
    if (!id) throw httpError(400, 'Scheme ID is required');

    // Try Supabase first
    try {
        const { data, error } = await supabaseAdmin
            .from('schemes')
            .select('*')
            .eq('id', id)
            .maybeSingle();

        if (!error && data) return { source: 'database', scheme: data };
    } catch (_) { /* fall through */ }

    // Fallback: in-memory catalogue
    const scheme = SCHEME_CATALOGUE.find(s => s.id === id);
    if (!scheme) throw httpError(404, `Scheme '${id}' not found`);
    return { source: 'catalogue', scheme };
};

module.exports = { searchSchemes, getSchemeById, SCHEME_CATALOGUE };
