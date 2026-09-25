const profileService = require('./profileService');
const { supabaseAdmin } = require('../config/supabaseConfig');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// ─── Grounded keyword → scheme + rule context map ────────────────────────────
// Simulates RAG retrieval: maps keywords to relevant policy passages.
const POLICY_CONTEXT = {
    pmegp: {
        subsidy: 'PMEGP provides margin money subsidy: Urban General 15%, Rural General 25%, Urban Special 25%, Rural Special 35% of project cost.',
        eligibility: 'Any individual above 18 years. Minimum VIII pass for project cost > ₹10L (manufacturing) or > ₹5L (service/business).',
        documents: 'Required: Aadhaar, PAN, Project Report, Udyam Registration (if applicable), ITR, Special Category Certificate.',
        limit: 'Maximum project cost: ₹50 lakh (manufacturing), ₹20 lakh (service/business).',
        loan: 'Own contribution: 10% (General), 5% (Special). Bank finances the balance.'
    },
    'pm-kisan': {
        benefit: 'Eligible farmer families receive ₹6,000 per year in three equal instalments of ₹2,000.',
        eligibility: 'Small and marginal farmer families with combined land holding up to 2 hectares as on 01-02-2019.',
        exclusions: 'Exclusions: institutional land holders, former/present holders of constitutional posts, serving/retired government officers, income tax payers, professionals (doctors, engineers, lawyers, CA, architects).',
        documents: 'Required: Aadhaar, land ownership records, bank account details.'
    },
    mudra: {
        categories: 'Shishu: up to ₹50,000 | Kishore: ₹50,001–₹5L | Tarun: ₹5L–₹10L. All are collateral-free.',
        eligibility: 'Non-corporate, non-farm micro/small enterprises. No prior default to any lender.',
        documents: 'Required: Aadhaar, PAN, business proof. For Kishore/Tarun: last 2 years ITR, bank statements.'
    },
    kcc: {
        benefit: 'Revolving credit limit covering crop cultivation expenses, post-harvest, maintenance, allied activities. Interest rate: 7% (4% after 3% interest subvention for timely repayment).',
        eligibility: 'All farmers — individual/joint borrowers, tenant farmers, share croppers, SHGs.',
        limit: 'Short-term credit limit up to ₹3 lakh; higher limits for medium-term/allied activities.'
    },
    'standup-india': {
        benefit: 'Bank loan between ₹10 lakh and ₹1 crore for greenfield enterprises in manufacturing, services, or trading.',
        eligibility: 'At least one SC/ST and at least one woman borrower per scheduled commercial bank branch.',
        documents: 'Required: Aadhaar, PAN, caste certificate (for SC/ST), business plan/project report.'
    }
};

/**
 * Resolve the best matching scheme context from user message.
 */
const resolveContext = (message) => {
    const msg = message.toLowerCase();
    if (msg.includes('pmegp') || msg.includes('employment generation')) return { schemeId: 'pmegp', context: POLICY_CONTEXT.pmegp };
    if (msg.includes('pm kisan') || msg.includes('pm-kisan') || msg.includes('farmer') || msg.includes('kisan')) return { schemeId: 'pm-kisan', context: POLICY_CONTEXT['pm-kisan'] };
    if (msg.includes('mudra') || msg.includes('shishu') || msg.includes('kishore') || msg.includes('tarun')) return { schemeId: 'mudra', context: POLICY_CONTEXT.mudra };
    if (msg.includes('kcc') || msg.includes('kisan credit')) return { schemeId: 'kcc', context: POLICY_CONTEXT.kcc };
    if (msg.includes('stand up') || msg.includes('standup') || msg.includes('sc/st') || msg.includes('woman entrepreneur')) return { schemeId: 'standup-india', context: POLICY_CONTEXT['standup-india'] };
    return { schemeId: null, context: null };
};

/**
 * Build a grounded answer from the policy context.
 */
const buildGroundedAnswer = (message, context, schemeId) => {
    const msg = message.toLowerCase();
    const scheme = SCHEME_CATALOGUE.find(s => s.id === schemeId);
    const schemeName = scheme ? scheme.name : 'this scheme';

    // Pick the most relevant context chunk
    let relevantChunk = '';
    if (msg.includes('subsidy') || msg.includes('benefit') || msg.includes('amount') || msg.includes('how much')) {
        relevantChunk = context.subsidy || context.benefit || context.limit || '';
    } else if (msg.includes('eligib') || msg.includes('qualify') || msg.includes('who can') || msg.includes('criteria')) {
        relevantChunk = context.eligibility || '';
    } else if (msg.includes('document') || msg.includes('required') || msg.includes('need to submit')) {
        relevantChunk = context.documents || '';
    } else if (msg.includes('loan') || msg.includes('credit') || msg.includes('interest')) {
        relevantChunk = context.loan || context.limit || '';
    } else if (msg.includes('exclusion') || msg.includes('not eligible') || msg.includes('who cannot')) {
        relevantChunk = context.exclusions || '';
    } else {
        // Return first available context chunk
        relevantChunk = Object.values(context)[0] || '';
    }

    if (!relevantChunk) return null;

    return {
        answer: `Regarding **${schemeName}**: ${relevantChunk}`,
        citation: {
            schemeId,
            schemeName,
            source: 'Official Government Scheme Guidelines (embedded policy corpus)'
        }
    };
};

/**
 * Fallback general knowledge for very broad questions.
 */
const GENERAL_ANSWERS = [
    { patterns: ['what schemes', 'list schemes', 'available schemes', 'which schemes'], answer: 'The platform currently covers PMEGP (₹50L manufacturing subsidy), MUDRA (micro loans up to ₹10L), PM-Kisan (₹6,000/year for farmers), KCC (revolving credit for farmers), and Stand-Up India (₹10L–₹1Cr for SC/ST and women entrepreneurs). Use the Discover page to search and filter.' },
    { patterns: ['how do i apply', 'how to apply', 'application process'], answer: 'To apply: (1) Complete your profile, (2) Upload required documents, (3) Check eligibility on the scheme page, (4) Click "Apply Now" which redirects to the official government portal or submits through this platform.' },
    { patterns: ['subsidy', 'what is subsidy'], answer: 'A subsidy is a financial contribution by the government towards your project cost. For example, PMEGP provides a margin money subsidy of 15%–35% of the total project cost, which does NOT need to be repaid.' },
    { patterns: ['hello', 'hi', 'hey', 'good morning', 'good evening'], answer: 'Hello! I am your Policy Assistant. I can help you understand government schemes, check eligibility, and explain benefits. Ask me about PMEGP, MUDRA, PM-Kisan, KCC, or Stand-Up India.' }
];

const AI_SERVER_URL = process.env.AI_SERVER_URL || 'http://127.0.0.1:8000';

/**
 * Main chat service.
 * @param {string} userId - Authenticated user ID (may be null for anonymous)
 * @param {string} message - User's question
 * @param {Array}  history - Conversation history [{role, content}]
 */
const chat = async (userId, message, history = []) => {
    if (!message || !message.trim()) throw httpError(400, 'Message is required');

    // Load user profile for personalization (optional, non-blocking)
    let profile = null;
    if (userId) {
        try { profile = await profileService.getProfileById(userId); } catch (_) { }
    }

    // --- 1. DYNAMIC AI INTEGRATION ATTEMPT ---
    // Try to call the real Python AI server first
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout

        const aiResponse = await fetch(`${AI_SERVER_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, history, profile }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (aiResponse.ok) {
            const data = await aiResponse.json();
            console.log("✅ Successfully retrieved response from Python AI Server");
            return data; // Return the real AI response!
        }
    } catch (err) {
        console.log(`⚠️ AI Server unreachable (${err.message}) - Falling back to local Mock Engine`);
    }
    // -----------------------------------------

    // --- 2. FALLBACK MOCK LOGIC ---
    // Try to ground on a specific scheme
    const { schemeId, context } = resolveContext(message);

    if (schemeId && context) {
        const grounded = buildGroundedAnswer(message, context, schemeId);
        if (grounded) {
            // Personalise if profile exists
            let personalNote = '';
            if (profile && schemeId === 'pm-kisan' && (profile.occupation || '').toLowerCase() !== 'farmer') {
                personalNote = '\n\n⚠️ Note: Based on your profile, your occupation is not registered as "farmer". You may not qualify for PM-Kisan unless you update your profile with the correct occupation.';
            }

            return {
                reply: grounded.answer + personalNote,
                citations: [grounded.citation],
                isGrounded: true,
                schemeId,
                profile: profile ? { name: profile.full_name, occupation: profile.occupation } : null
            };
        }
    }

    // Check general patterns
    const msgLower = message.toLowerCase();
    for (const item of GENERAL_ANSWERS) {
        if (item.patterns.some(p => msgLower.includes(p))) {
            return {
                reply: item.answer,
                citations: [],
                isGrounded: false,
                schemeId: null
            };
        }
    }

    // Default fallback
    return {
        reply: `I found your question about "${message.slice(0, 60)}". I can provide detailed information about PMEGP, MUDRA, PM-Kisan, KCC, and Stand-Up India schemes. Could you specify which scheme you are asking about, or describe your situation so I can guide you better?`,
        citations: [],
        isGrounded: false,
        schemeId: null,
        suggestions: ['Tell me about PMEGP subsidies', 'What are the PM Kisan eligibility rules?', 'Which documents do I need for MUDRA?']
    };
};

module.exports = { chat };
