const path = require('path');
const fs = require('fs');
const readline = require('readline');
const { supabaseAdmin } = require('../config/supabaseConfig');
const schemeService = require('../services/schemeService');

async function runAudit() {
    console.log('--- AUDITING ALL 4,752 CANONICAL SCHEMES ---');
    
    // Fetch all schemes from Supabase
    let allDbSchemes = [];
    let from = 0;
    const step = 1000;
    while (true) {
        const { data, error } = await supabaseAdmin
            .from('schemes')
            .select('*')
            .order('id', { ascending: true })
            .range(from, from + step - 1);
        if (error) {
            console.error('Database fetch error:', error.message);
            break;
        }
        allDbSchemes.push(...data);
        if (data.length < step) break;
        from += step;
    }

    console.log(`Fetched ${allDbSchemes.length} schemes from database.`);

    const report = {
        total: allDbSchemes.length,
        officialUrl: { complete: 0, missing: 0, invalid: 0 },
        overview: { complete: 0, incomplete: 0 },
        eligibility: { complete: 0, incomplete: 0 },
        benefits: { complete: 0, incomplete: 0 },
        documents: { complete: 0, incomplete: 0 },
        howToApply: { complete: 0, incomplete: 0 },
        sourceAndRules: { complete: 0, incomplete: 0 },
        faqs: { available: 0, unavailable: 0 },
        incompleteSchemes: []
    };

    for (const raw of allDbSchemes) {
        const formatted = schemeService.formatSchemeRecord(raw);

        // 1. Official URL
        const url = formatted.source_url;
        if (!url) {
            report.officialUrl.missing++;
        } else {
            const valid = schemeService.validateOfficialUrl(url);
            if (valid) {
                report.officialUrl.complete++;
            } else {
                report.officialUrl.invalid++;
            }
        }

        // 2. Overview: name, description, ministry/department, level/state
        const hasName = Boolean(formatted.scheme_name || formatted.title);
        const hasDesc = Boolean(formatted.brief_description || formatted.detailed_description || formatted.description);
        const hasMinistry = Boolean(formatted.ministry || formatted.department);
        const hasCoverage = Boolean(formatted.state || formatted.level);
        if (hasName && hasDesc && hasMinistry && hasCoverage) {
            report.overview.complete++;
        } else {
            report.overview.incomplete++;
        }

        // 3. Eligibility: eligibility string exists and > 10 chars
        const elig = formatted.eligibility || formatted.eligibility_summary;
        if (elig && typeof elig === 'string' && elig.trim().length > 10 && !elig.includes('[in progress]')) {
            report.eligibility.complete++;
        } else {
            report.eligibility.incomplete++;
        }

        // 4. Benefits: benefits string exists and > 5 chars
        const ben = formatted.benefits || formatted.benefit_summary;
        if (ben && typeof ben === 'string' && ben.trim().length > 5 && !ben.includes('[in progress]')) {
            report.benefits.complete++;
        } else {
            report.benefits.incomplete++;
        }

        // 5. Documents: documents_required array has items or valid string
        const docs = formatted.documents_required || formatted.required_documents;
        if (Array.isArray(docs) && docs.length > 0 && docs[0] !== 'Not specified in available official source' && docs[0] !== '[in progress]') {
            report.documents.complete++;
        } else {
            report.documents.incomplete++;
        }

        // 6. How To Apply: application_process string exists and not placeholder
        const app = formatted.application_process;
        if (app && typeof app === 'string' && app.trim().length > 5 && !app.includes('[in progress]')) {
            report.howToApply.complete++;
        } else {
            report.howToApply.incomplete++;
        }

        // 7. Source & Rules: has verified source_url or references
        const hasSource = Boolean(formatted.source_url);
        const hasRefs = Array.isArray(formatted.references) && formatted.references.length > 0;
        if (hasSource || hasRefs) {
            report.sourceAndRules.complete++;
        } else {
            report.sourceAndRules.incomplete++;
        }

        // Check if any missing
        const missingFields = [];
        if (!formatted.source_url) missingFields.push('source_url');
        if (!hasDesc) missingFields.push('description');
        if (!elig || elig.trim().length <= 10) missingFields.push('eligibility');
        if (!ben || ben.trim().length <= 5) missingFields.push('benefits');
        if (!docs || (Array.isArray(docs) && docs.length === 0)) missingFields.push('documents');
        if (!app || app.includes('[in progress]')) missingFields.push('how_to_apply');

        if (missingFields.length > 0) {
            report.incompleteSchemes.push({
                id: formatted.id,
                name: formatted.scheme_name || formatted.title,
                missing: missingFields
            });
        }
    }

    console.log(JSON.stringify({
        total: report.total,
        officialUrl: report.officialUrl,
        overview: report.overview,
        eligibility: report.eligibility,
        benefits: report.benefits,
        documents: report.documents,
        howToApply: report.howToApply,
        sourceAndRules: report.sourceAndRules,
        incompleteCount: report.incompleteSchemes.length,
        sampleIncomplete: report.incompleteSchemes.slice(0, 5)
    }, null, 2));
}

runAudit().catch(console.error);
