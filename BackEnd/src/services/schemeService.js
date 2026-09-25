const { supabaseAdmin } = require('../config/supabaseConfig');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

/**
 * Text-match helper: checks if any scheme field contains the query string.
 */
const schemeMatchesQuery = (scheme, query = '') => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
        (scheme.name && scheme.name.toLowerCase().includes(q)) ||
        (scheme.short_name && scheme.short_name.toLowerCase().includes(q)) ||
        (scheme.ministry && scheme.ministry.toLowerCase().includes(q)) ||
        (scheme.benefit_summary && scheme.benefit_summary.toLowerCase().includes(q)) ||
        (scheme.eligibility_summary && scheme.eligibility_summary.toLowerCase().includes(q)) ||
        (scheme.tags || []).some(t => String(t).toLowerCase().includes(q))
    );
};

/**
 * POST /api/schemes/search
 * Queries Supabase `schemes` table directly.
 */
const searchSchemes = async ({ query, filters = {}, limit = 20 } = {}) => {
    let dbQuery = supabaseAdmin.from('schemes').select('*').eq('active', true);
    
    if (filters.type) dbQuery = dbQuery.eq('type', filters.type);
    if (filters.ministry) dbQuery = dbQuery.ilike('ministry', `%${filters.ministry}%`);
    if (filters.maxBenefit) dbQuery = dbQuery.lte('max_benefit', Number(filters.maxBenefit));
    if (filters.tags && Array.isArray(filters.tags) && filters.tags.length > 0) {
        dbQuery = dbQuery.contains('tags', filters.tags);
    }
    
    const { data, error } = await dbQuery.limit(limit);
    if (error) throw httpError(500, `Database query error: ${error.message}`);

    const results = query ? (data || []).filter(s => schemeMatchesQuery(s, query)) : (data || []);

    return {
        source: 'database',
        total: results.length,
        schemes: results
    };
};

/**
 * GET /api/schemes/:id
 * Fetches scheme details directly from Supabase `schemes` table.
 */
const getSchemeById = async (id) => {
    if (!id) throw httpError(400, 'Scheme ID is required');

    const { data, error } = await supabaseAdmin
        .from('schemes')
        .select('*')
        .eq('id', id)
        .maybeSingle();

    if (error) throw httpError(500, `Database query error: ${error.message}`);
    if (!data) throw httpError(404, `Scheme '${id}' not found in database`);

    return { source: 'database', scheme: data };
};

module.exports = { searchSchemes, getSchemeById };
