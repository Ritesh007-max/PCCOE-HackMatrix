const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');

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
 * Hybrid strategy: calls Intelligence /v1/schemes/search for semantic ranking
 * and hydrates results with full database metadata from Supabase.
 */
const searchSchemes = async ({ query, filters = {}, limit = 20, allowFallback = true } = {}) => {
    // 1. If query is provided, attempt Intelligence semantic search first
    if (query && query.trim()) {
        try {
            const aiSearchRes = await intelligenceClient.postJson('/v1/schemes/search', {
                query: query.trim(),
                language: 'en',
                top_k: limit || 20,
                state: filters.state || undefined,
                social_category: filters.socialCategory || filters.casteCategory || filters.category || undefined,
                beneficiary_type: filters.type || filters.beneficiaryType || undefined
            }, { timeoutMs: 30000 });

            if (aiSearchRes && Array.isArray(aiSearchRes.results) && aiSearchRes.results.length > 0) {
                // Fetch Supabase schemes to hydrate complete database fields
                const { data: dbSchemes } = await supabaseAdmin.from('schemes').select('*').eq('active', true);
                const allDbSchemes = dbSchemes || [];

                const hydrated = aiSearchRes.results.map((aiItem) => {
                    const match = allDbSchemes.find(s => 
                        s.id === aiItem.scheme_id || 
                        (s.slug && s.slug === aiItem.scheme_id) ||
                        (s.name && s.name.toLowerCase() === (aiItem.scheme_name || '').toLowerCase())
                    );

                    if (match) {
                        return {
                            ...match,
                            relevanceScore: aiItem.relevance_score,
                            matchScore: Math.round(aiItem.relevance_score * 100),
                            evidenceSnippets: aiItem.evidence_snippets || [],
                            sourceAuthority: aiItem.source_authority || match.ministry
                        };
                    }

                    // Return adapted scheme object if not present in DB
                    return {
                        id: aiItem.scheme_id,
                        name: aiItem.scheme_name,
                        title: aiItem.scheme_name,
                        ministry: aiItem.source_authority || 'Government of India',
                        state: aiItem.state || 'All India',
                        benefit_summary: aiItem.details?.benefit_summary || '',
                        eligibility_summary: aiItem.details?.eligibility_summary || '',
                        relevanceScore: aiItem.relevance_score,
                        matchScore: Math.round(aiItem.relevance_score * 100),
                        evidenceSnippets: aiItem.evidence_snippets || [],
                        tags: [aiItem.source_authority, aiItem.state].filter(Boolean),
                        active: true
                    };
                });

                return {
                    source: 'hybrid_intelligence',
                    degraded: false,
                    total: hydrated.length,
                    schemes: hydrated,
                    requestId: aiSearchRes.request_id || null
                };
            }
        } catch (err) {
            console.warn(`[schemeService] Intelligence /v1/schemes/search unavailable (${err.message}) - Falling back to database`);
            if (allowFallback === false) {
                throw err;
            }
        }
    }

    // 2. Fallback or no-query search: direct Supabase query
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
        degraded: Boolean(query),
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
