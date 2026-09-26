const crypto = require('crypto');
const profileService = require('./profileService');
const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

// ─── Grounded keyword → scheme + rule context map ────────────────────────────
// Simulates RAG retrieval: maps keywords to relevant policy passages.
const SCHEME_CATALOGUE = [
    {
        id: 'pm-vidyalaxmi',
        name: 'PM Vidyalaxmi',
        title: 'PM Vidyalaxmi',
        subtitle: 'Education loan support for higher studies.',
        tags: ['Education', 'Loan'],
        matchScore: 92,
        iconType: 'education'
    },
    {
        id: 'digital-india-internship',
        name: 'Digital India Internship Scheme',
        title: 'Digital India Internship Scheme',
        subtitle: 'Internship opportunities for students.',
        tags: ['Skill Development', 'Internship'],
        matchScore: 85,
        iconType: 'digital-india'
    },
    {
        id: 'skill-india',
        name: 'Skill India - Training & Certification',
        title: 'Skill India - Training & Certification',
        subtitle: 'Free skill training programs for students.',
        tags: ['Skill Development', 'Training'],
        matchScore: 78,
        iconType: 'skill-india'
    },
    {
        id: 'startup-india',
        name: 'Startup India',
        title: 'Startup India',
        subtitle: 'Support for student entrepreneurs.',
        tags: ['Entrepreneurship', 'Funding'],
        matchScore: 72,
        iconType: 'startup-india'
    },
    {
        id: 'pmegp',
        name: "Prime Minister's Employment Generation Programme (PMEGP)",
        title: 'PMEGP',
        subtitle: "Prime Minister's Employment Generation Programme",
        tags: ['Business Support', 'Self Employment', 'Central Government'],
        matchScore: 96,
        iconType: 'ashoka'
    },
    {
        id: 'pm-kisan',
        name: 'PM Kisan Samman Nidhi',
        title: 'PM Kisan',
        subtitle: 'Direct income support for farmers.',
        tags: ['Agriculture', 'Farmer Support', 'DBT'],
        matchScore: 94,
        iconType: 'kisan'
    },
    {
        id: 'mudra',
        name: 'Pradhan Mantri MUDRA Yojana',
        title: 'MUDRA Yojana',
        subtitle: 'Micro loans up to ₹10 Lakh for small enterprises.',
        tags: ['Credit / Loan', 'MSME', 'Collateral-free'],
        matchScore: 90,
        iconType: 'mudra'
    },
    {
        id: 'kcc',
        name: 'Kisan Credit Card (KCC)',
        title: 'Kisan Credit Card',
        subtitle: 'Credit limit for crops and agricultural activities.',
        tags: ['Credit / Loan', 'Agriculture'],
        matchScore: 88,
        iconType: 'kcc'
    },
    {
        id: 'standup-india',
        name: 'Stand-Up India',
        title: 'Stand-Up India',
        subtitle: 'Bank loans for SC/ST and Women entrepreneurs.',
        tags: ['Women', 'SC/ST', 'Credit / Loan'],
        matchScore: 89,
        iconType: 'standup'
    }
];

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

const withFallbackMeta = (obj) => ({
    source: 'local_fallback',
    degraded: true,
    ...obj
});

/**
 * Main chat service.
 * @param {string} userId - Authenticated user ID (may be null for anonymous)
 * @param {string} message - User's question
 * @param {Array}  history - Conversation history [{role, content}]
 * @param {string} [conversationId] - Distinct conversation session ID
 * @param {object} [options] - Options (e.g. { allowFallback: false })
 */
const chat = async (userId, message, history = [], conversationId = null, options = {}) => {
    if (!message || !message.trim()) throw httpError(400, 'Message is required');

    // Load user profile for personalization (optional, non-blocking)
    let profile = null;
    if (userId) {
        try { profile = await profileService.getProfileById(userId); } catch (_) { }
    }

    const effectiveConversationId = conversationId || (userId ? String(userId) : undefined);

    // --- 1. DYNAMIC AI INTEGRATION ATTEMPT (PHASE 15) ---
    // Connect to FastAPI Intelligence microservice /v1/chat
    try {
        const payload = {
            query: message,
            conversation_id: effectiveConversationId,
            language: 'en',
            applicant_facts: profile || undefined
        };

        const aiResponse = await intelligenceClient.postJson('/v1/chat', payload, {
            timeoutMs: 30000
        });

        if (aiResponse && (aiResponse.answer || aiResponse.reply)) {
            const answerText = aiResponse.answer || aiResponse.reply;

            const citations = (aiResponse.citations || []).map(c => ({
                chunkId: c.chunk_id || c.chunkId || null,
                schemeId: c.scheme_id || c.schemeId || null,
                schemeName: c.scheme_name || c.scheme_id || 'Statutory Policy Corpus',
                source: c.url || 'Official Scheme Repository',
                url: c.url || null,
                excerpt: c.excerpt || ''
            }));

            const schemes = (aiResponse.suggested_schemes || []).map(s => {
                const catalogMatch = SCHEME_CATALOGUE.find(c => c.id === s.scheme_id);
                return {
                    id: s.scheme_id,
                    schemeId: s.scheme_id,
                    title: s.scheme_name || (catalogMatch ? catalogMatch.title : s.scheme_id),
                    name: s.scheme_name || (catalogMatch ? catalogMatch.name : s.scheme_id),
                    subtitle: s.ministry || s.state || (catalogMatch ? catalogMatch.subtitle : ''),
                    tags: [s.ministry, s.state].filter(Boolean),
                    matchScore: Math.round((s.relevance_score || 0.8) * 100),
                    matchType: (s.relevance_score || 0.8) >= 0.8 ? 'green' : 'orange',
                    iconType: catalogMatch ? catalogMatch.iconType : 'ashoka'
                };
            });

            return {
                source: 'intelligence',
                degraded: false,
                reply: answerText,
                answer: answerText,
                citations,
                schemes,
                isGrounded: citations.length > 0,
                showViewAll: schemes.length > 0,
                conversationId: aiResponse.conversation_id || effectiveConversationId,
                requestId: aiResponse.request_id || null,
                intent: aiResponse.intent || 'SCHEME_DISCOVERY',
                providerTelemetry: aiResponse.provider_telemetry || null
            };
        }
    } catch (err) {
        console.warn(`[chatService] Intelligence /v1/chat unavailable (${err.message}) - Falling back to local engine`);
        if (options && options.allowFallback === false) {
            throw err;
        }
    }
    // ----------------------------------------------------

    // --- 2. FALLBACK MOCK LOGIC ---
    return withFallbackMeta(computeLocalFallback(message, profile));
};

const computeLocalFallback = (message, profile) => {
    // Check student / Gujarat / education schemes query
    const msgLower = message.toLowerCase();
    if (
        (msgLower.includes('student') || msgLower.includes('gujarat') || msgLower.includes('internship') || msgLower.includes('college') || msgLower.includes('study'))
    ) {
        return {
            reply: 'Based on your profile (Student, Gujarat), here are some government schemes you may be eligible for:',
            isGrounded: true,
            schemeId: null,
            schemes: [
                {
                    id: 'pm-vidyalaxmi',
                    title: 'PM Vidyalaxmi',
                    subtitle: 'Education loan support for higher studies.',
                    tags: ['Education', 'Loan'],
                    matchScore: 92,
                    matchType: 'green',
                    iconType: 'education'
                },
                {
                    id: 'digital-india-internship',
                    title: 'Digital India Internship Scheme',
                    subtitle: 'Internship opportunities for students.',
                    tags: ['Skill Development', 'Internship'],
                    matchScore: 85,
                    matchType: 'green',
                    iconType: 'digital-india'
                },
                {
                    id: 'skill-india',
                    title: 'Skill India - Training & Certification',
                    subtitle: 'Free skill training programs for students.',
                    tags: ['Skill Development', 'Training'],
                    matchScore: 78,
                    matchType: 'green',
                    iconType: 'skill-india'
                },
                {
                    id: 'startup-india',
                    title: 'Startup India',
                    subtitle: 'Support for student entrepreneurs.',
                    tags: ['Entrepreneurship', 'Funding'],
                    matchScore: 72,
                    matchType: 'orange',
                    iconType: 'startup-india'
                }
            ],
            showViewAll: true,
            citations: [
                {
                    schemeName: 'Ministry of Education & MeitY Guidelines',
                    source: 'Official Central & Gujarat Student Portals'
                }
            ]
        };
    }

    if (msgLower.includes('document') || msgLower.includes('what documents')) {
        return {
            reply: 'Here are the primary documents required for most central and state government schemes:\n\n1. **Identity & Address Proof:** Aadhaar Card (linked with mobile number)\n2. **Financial Proof:** PAN Card, Bank Account Passbook / Cancelled Cheque\n3. **Income & Category:** Income Certificate, Caste Certificate (SC/ST/OBC if applicable)\n4. **Business / Educational:** Detailed Project Report (DPR), Educational Marksheets / Degree\n5. **Registration:** Udyam Registration (for MSME/PMEGP)',
            isGrounded: true,
            schemeId: null,
            suggestions: ['Check my eligibility for PMEGP', 'Schemes for students in Gujarat', 'How to apply for a scheme?']
        };
    }

    if (msgLower.includes('how to apply') || msgLower.includes('application process')) {
        return {
            reply: 'To apply for any government scheme through the FIN portal:\n\n1. **Step 1:** Complete your profile with your occupation, state, and category.\n2. **Step 2:** Upload and verify required documents in the My Documents vault.\n3. **Step 3:** Use Discover Schemes to check your exact match score and criteria.\n4. **Step 4:** Click "Apply Now" to submit directly or access the nodal ministry portal with pre-filled details.',
            isGrounded: true,
            schemeId: null,
            suggestions: ['Find schemes for my profile', 'What documents are required?']
        };
    }

    if (msgLower.includes('find scheme') || msgLower.includes('my profile') || msgLower.includes('for my profile')) {
        return {
            reply: 'Based on your applicant profile, here are the top recommended schemes matched for you:',
            isGrounded: true,
            schemeId: null,
            schemes: [
                {
                    id: 'pmegp',
                    title: 'PMEGP',
                    subtitle: "Prime Minister's Employment Generation Programme",
                    tags: ['Business Support', 'Self Employment', 'Central Government'],
                    matchScore: 96,
                    matchType: 'green',
                    iconType: 'ashoka'
                },
                {
                    id: 'pm-vidyalaxmi',
                    title: 'PM Vidyalaxmi',
                    subtitle: 'Education loan support for higher studies.',
                    tags: ['Education', 'Loan'],
                    matchScore: 92,
                    matchType: 'green',
                    iconType: 'education'
                },
                {
                    id: 'skill-india',
                    title: 'Skill India - Training & Certification',
                    subtitle: 'Free skill training programs for students.',
                    tags: ['Skill Development', 'Training'],
                    matchScore: 78,
                    matchType: 'green',
                    iconType: 'skill-india'
                }
            ],
            showViewAll: true
        };
    }

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

            const schemeObj = SCHEME_CATALOGUE.find(s => s.id === schemeId);

            return {
                reply: grounded.answer + personalNote,
                citations: [grounded.citation],
                isGrounded: true,
                schemeId,
                schemes: schemeObj ? [schemeObj] : [],
                profile: profile ? { name: profile.full_name, occupation: profile.occupation } : null
            };
        }
    }

    // Check general patterns
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
