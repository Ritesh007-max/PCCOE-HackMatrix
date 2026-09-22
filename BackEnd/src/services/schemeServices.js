const supabase = require("../config/supabaseConfig");
const { schemes: seedSchemes } = require("../data/schemes");
const { throwIfError } = require("../utils/supabaseErrors");

const toRow = (scheme) => ({
    id: scheme.id,
    name: scheme.name,
    full_name: scheme.fullName,
    category: scheme.category,
    state: scheme.state,
    status: scheme.status,
    ministry: scheme.ministry,
    keywords: scheme.keywords,
    tags: scheme.tags,
    estimated_benefit: scheme.estimatedBenefit,
    description: scheme.description,
    eligibility: scheme.eligibility,
    documents_required: scheme.documentsRequired
});

const fromRow = (row) => ({
    id: row.id,
    name: row.name,
    fullName: row.full_name,
    category: row.category,
    state: row.state,
    status: row.status,
    ministry: row.ministry,
    keywords: row.keywords || [],
    tags: row.tags || [],
    estimatedBenefit: row.estimated_benefit,
    description: row.description,
    eligibility: row.eligibility || [],
    documentsRequired: row.documents_required || []
});

const ensureSchemesSeeded = async () => {
    const { data, error } = await supabase.from("schemes").select("id").limit(1);
    throwIfError(error);

    if (data && data.length > 0) {
        return;
    }

    const { error: insertError } = await supabase.from("schemes").insert(seedSchemes.map(toRow));
    throwIfError(insertError);
};

const matchesFilter = (scheme, { category, state, status, keyword }) => {
    if (category && scheme.category !== category.toLowerCase()) {
        return false;
    }

    if (state) {
        const requested = state.toLowerCase();
        if (scheme.state !== "all" && scheme.state !== requested) {
            return false;
        }
    }

    if (status && scheme.status !== status.toLowerCase()) {
        return false;
    }

    if (keyword) {
        const haystack = [
            scheme.name,
            scheme.fullName,
            scheme.description,
            scheme.category,
            scheme.state,
            ...(scheme.keywords || []),
            ...(scheme.tags || [])
        ]
            .join(" ")
            .toLowerCase();

        if (!haystack.includes(keyword.toLowerCase())) {
            return false;
        }
    }

    return true;
};

const listSchemes = async (filters = {}) => {
    await ensureSchemesSeeded();

    const { data, error } = await supabase.from("schemes").select("*").order("name", { ascending: true });
    throwIfError(error);

    return (data || [])
        .map(fromRow)
        .filter((scheme) => matchesFilter(scheme, filters));
};

const getSchemeById = async (id) => {
    const { data, error } = await supabase.from("schemes").select("*").eq("id", id).maybeSingle();
    throwIfError(error);

    if (!data) {
        const err = new Error("Scheme not found");
        err.status = 404;
        throw err;
    }

    return fromRow(data);
};

module.exports = {
    listSchemes,
    getSchemeById
};
