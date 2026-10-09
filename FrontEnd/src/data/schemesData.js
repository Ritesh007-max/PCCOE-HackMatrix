// ============================================================================
// GOVERNMENT SCHEMES TAXONOMY
// Schemes are loaded dynamically from Supabase database (4,752+ schemes)
// ============================================================================

export const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'business', label: 'Business' },
  { id: 'agriculture', label: 'Agriculture' },
  { id: 'education', label: 'Education' },
  { id: 'women', label: 'Women' },
  { id: 'youth', label: 'Youth' },
  { id: 'health', label: 'Health' },
  { id: 'tax-benefits', label: 'Tax Benefits' },
  { id: 'social-welfare', label: 'Social Welfare' },
];

export const SCHEME_TYPES = [
  { id: 'central', label: 'Central Government' },
  { id: 'state', label: 'State Government' },
  { id: 'loan', label: 'Credit / Loan' },
  { id: 'subsidy', label: 'Subsidy' },
  { id: 'dbt', label: 'Direct Benefit Transfer' },
  { id: 'scholarship', label: 'Scholarship / Grant' },
  { id: 'insurance', label: 'Insurance & Health' },
];

// All schemes are fetched dynamically from the database.
export const SCHEMES = [];
