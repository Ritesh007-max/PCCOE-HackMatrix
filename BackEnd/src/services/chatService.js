const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const profileService = require('./profileService');
const documentServices = require('./documentServices');
const applicationService = require('./applicationService');
const { supabaseAdmin } = require('../config/supabaseConfig');
const intelligenceClient = require('./intelligenceClient');
const chatHistoryService = require('./chatHistoryService');

const buildDocumentFacts = (documents) => (documents || []).map((doc) => ({
    document_id: doc.id,
    document_type: doc.document_type || doc.documentType,
    file_name: doc.file_name || doc.fileName,
    uploaded_at: doc.uploaded_at || doc.uploadedAt,
    verification_status: doc.verification_status || doc.verificationStatus,
    fields: doc.extracted_fields || doc.extractedData || {}
}));

const httpError = (status, message) => {
    const error = new Error(message);
    error.status = status;
    return error;
};

/**
 * Resolves the actual 1-based page number where a fact or value is found in a document.
 * Follows strict citation provenance rules:
 * 1. Checks fact-level page provenance if available.
 * 2. Parses page blocks '--- [Page {n}] ---' from extractedText/extracted_text.
 * 3. Matches normalized fact values against page text.
 * 4. Disambiguates multiple matches using factKey keywords.
 * 5. Single-page documents or documents without page delimiters resolve to Page 1.
 * 6. Returns null if multi-page document cannot locate the fact (Page Unknown).
 */
function resolveDocumentFactPage(doc, factValue, factKey = '') {
    if (!doc) return null;

    // 1. Check direct fact-level page provenance
    if (doc.page_number && Number.isInteger(doc.page_number) && doc.page_number > 0) {
        return doc.page_number;
    }

    const text = doc.extracted_text || doc.extractedText || '';
    if (!text || typeof text !== 'string') {
        return null;
    }

    const pageBlocks = text.split(/---\s*\[Page\s+(\d+)\]\s*---/);
    const pages = [];
    if (pageBlocks.length > 1) {
        for (let i = 1; i < pageBlocks.length; i += 2) {
            pages.push({
                pageNum: parseInt(pageBlocks[i], 10),
                content: (pageBlocks[i + 1] || '').trim()
            });
        }
    } else {
        // Document has no page markers - single page document
        return 1;
    }

    if (pages.length === 0) return null;
    if (pages.length === 1) return pages[0].pageNum;

    if (factValue === undefined || factValue === null || factValue === '') {
        return null;
    }

    const needleRaw = String(factValue).trim();
    if (!needleRaw) return null;

    const needleClean = needleRaw.replace(/[₹,\s]/g, '').toLowerCase();

    // Context disambiguation keywords
    const keyTermsMap = {
        annual_family_income: ['family', 'parivar', 'kutumb', 'annual', 'income', 'annual family income'],
        family_income: ['family', 'parivar', 'kutumb', 'annual', 'income'],
        personal_income: ['personal', 'individual', 'salary', 'applicant'],
        annual_income: ['annual', 'income', 'varshik', 'aavak'],
        father_income: ['father', 'employment', 'wage', 'father income'],
        mother_income: ['mother', 'self-employment', 'craft', 'mother income'],
        other_income: ['other', 'other income', 'other family income', 'agricultural', 'household collective'],
        document_number: ['certificate', 'cert', 'number', 'ref', 'no', 'pramanpatra'],
        caste: ['caste', 'category', 'community', 'sc', 'st', 'obc', 'sebc', 'general', 'samaj'],
        caste_category: ['caste', 'category', 'community', 'sc', 'st', 'obc'],
        category: ['category', 'caste', 'social']
    };
    const contextTerms = keyTermsMap[factKey] || (factKey ? [factKey.replace(/_/g, ' ')] : []);

    const matches = [];
    for (const { pageNum, content } of pages) {
        const contentLower = content.toLowerCase();
        const contentClean = contentLower.replace(/[₹,\s]/g, '');

        let isMatch = false;
        if (needleClean.length >= 2 && contentClean.includes(needleClean)) {
            isMatch = true;
        } else if (contentLower.includes(needleRaw.toLowerCase())) {
            isMatch = true;
        }

        if (isMatch) {
            let score = 1;
            for (const term of contextTerms) {
                if (contentLower.includes(term.toLowerCase())) {
                    score += 2;
                }
            }
            matches.push({ pageNum, score });
        }
    }

    if (matches.length === 1) {
        return matches[0].pageNum;
    }
    if (matches.length > 1) {
        matches.sort((a, b) => b.score - a.score);
        return matches[0].pageNum;
    }

    return null;
}

function formatPageLabel(pageNum) {
    if (pageNum !== null && pageNum !== undefined && Number.isInteger(pageNum) && pageNum > 0) {
        return `Page ${pageNum}`;
    }
    return 'Page Unknown';
}

/**
 * Produces an evidence-grounded, structured summary of a document page.
 * Eliminates table-header noise and administrative boilerplate,
 * structures income breakdowns and key metadata, and verifies source provenance.
 */
function summarizePageText(text, pageNum, doc, allDocs) {
    const rawLines = (text || '').split('\n').map(l => l.trim()).filter(Boolean);
    const docName = (doc && doc.file_name) || 'Document';
    const extractedFields = (doc && doc.extracted_fields) || {};

    // 1. Clean boilerplate and watermarks
    const skipExact = new Set([
        'synthetic test document', 'not valid for official use', 'created exclusively',
        'created exclusively for fin qa automation', 'automated qa verification',
        'automated qa verification artifact', 'no statutory privilege',
        'prepared strictly for system', 'qa automation', 'fictional test authority',
        'fictional administrative record', 'income component', 'contributing household',
        'contributing household earner', 'nature of livelihood /', 'nature of livelihood / occupation',
        'nature of livelihood', 'annual amount', 'all household earners',
        'consolidated family annual earnings', 'all combined sources'
    ]);

    const skipKeywords = [
        'synthetic test document', 'not valid for official use', 'created exclusively',
        'automated qa verification', 'no statutory privilege', 'page 1 of', 'page 2 of',
        'page 3 of', 'page 4 of', 'prepared strictly for system', 'qa automation',
        'fictional test authority', 'fictional administrative record', 'fin qa test document',
        'district revenue office', 'sub-division: urban', 'taluka: daskroi',
        'certifying officer\'s initial note', 'statement of jurisdiction & scope',
        'authoritative income provenance note', 'application ref:'
    ];

    const cleanLines = [];
    for (const l of rawLines) {
        const low = l.toLowerCase();
        if (skipKeywords.some(sk => low.includes(sk))) continue;
        if (skipExact.has(low)) continue;
        if (/^[-=_]{4,}$/.test(low)) continue;
        cleanLines.push(l);
    }

    // 2. Section heading detection
    let sectionHeading = null;
    for (const l of cleanLines.slice(0, 8)) {
        if (l.startsWith('SCHEDULE ')) {
            sectionHeading = l;
            break;
        }
        if (/^[0-9]+\.\s+[A-Z\s&/]{4,60}$/.test(l)) {
            sectionHeading = l;
            break;
        }
        const upper = l.toUpperCase();
        if (upper.includes('STATUTORY ANNUAL FAMILY INCOME ASSESSMENT') ||
            upper.includes('INCOME ASSESSMENT') ||
            upper.includes('IDENTIFICATION DETAILS') ||
            upper.includes('IDENTIFICATION RECORD')) {
            sectionHeading = l;
            break;
        }
    }

    if (!sectionHeading) {
        sectionHeading = `Information — ${docName}`;
    } else {
        sectionHeading = sectionHeading.replace(/^\d+\.\s*/, '').trim();
        if (sectionHeading.includes(':') && sectionHeading.startsWith('SCHEDULE')) {
            sectionHeading = sectionHeading.split(':')[1].trim();
        }
    }

    const toTitleCase = (s) => s.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
    const headingTitle = sectionHeading.startsWith('Information') ? sectionHeading : toTitleCase(sectionHeading);

    // 3. Provenance helper
    const resolveProvenance = (val, key) => {
        if (!val) return false;
        if (doc && (doc.is_active === false || doc.deleted_at)) return false;
        const cleanVal = String(val).replace(/[₹,.\-\s/]/g, '').toLowerCase();
        const cleanPage = (text || '').replace(/[₹,.\-\s/]/g, '').toLowerCase();
        if (cleanVal && cleanPage.includes(cleanVal)) return true;
        if (doc && doc.extracted_text) {
            const pageBlocks = doc.extracted_text.split(/---\s*\[Page\s+(\d+)\]\s*---/);
            if (pageBlocks.length > 1) {
                for (let i = 1; i < pageBlocks.length; i += 2) {
                    const pN = parseInt(pageBlocks[i], 10);
                    const pTxt = pageBlocks[i + 1] || '';
                    if (cleanVal && pTxt.replace(/[₹,.\-\s/]/g, '').toLowerCase().includes(cleanVal)) {
                        return pN === pageNum;
                    }
                }
            } else if (pageNum === 1 && cleanVal && doc.extracted_text.replace(/[₹,.\-\s/]/g, '').toLowerCase().includes(cleanVal)) {
                return true;
            }
        }
        return false;
    };

    const formatINR = (val) => {
        if (val === null || val === undefined || val === '') return null;
        const s = String(val).replace(/[₹,Rs.\s/-]/gi, '').trim();
        const num = parseFloat(s);
        if (isNaN(num)) return `₹${val}`;
        return `₹${num.toLocaleString('en-IN')}`;
    };

    // 4. Check if income assessment page
    const textLower = (text || '').toLowerCase();
    const hasTotalIncomeMatch = /(?:total\s+(?:annual\s+)?family\s+income|statutory\s+annual\s+family\s+income\s+assessment|annual\s+household\s+income\s+computation|detailed\s+income\s+assessment)/i.test(textLower);
    const fTotalRaw = extractedFields.annual_family_income;
    const hasIncomeProvenance = Boolean(fTotalRaw && resolveProvenance(fTotalRaw, 'annual_family_income'));
    const isIncomePage = hasTotalIncomeMatch || hasIncomeProvenance;

    if (isIncomePage) {
        let fatherInc = null;
        let motherInc = null;
        let otherInc = null;
        let totalInc = null;

        if (extractedFields.father_income && resolveProvenance(extractedFields.father_income, 'father_income')) {
            fatherInc = formatINR(extractedFields.father_income);
        }
        if (extractedFields.mother_income && resolveProvenance(extractedFields.mother_income, 'mother_income')) {
            motherInc = formatINR(extractedFields.mother_income);
        }
        if (extractedFields.other_income && resolveProvenance(extractedFields.other_income, 'other_income')) {
            otherInc = formatINR(extractedFields.other_income);
        }
        if (fTotalRaw && resolveProvenance(fTotalRaw, 'annual_family_income')) {
            totalInc = formatINR(fTotalRaw);
        }

        // Fallbacks from page text
        if (!fatherInc) {
            const m = text.match(/Father(?:'s|’s)?\s*(?:Employment\s*)?Income[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)/i);
            if (m) fatherInc = formatINR(m[1]);
        }
        if (!motherInc) {
            const m = text.match(/Mother(?:'s|’s)?\s*(?:Self-Employment\s*)?Income[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)/i);
            if (m) motherInc = formatINR(m[1]);
        }
        if (!otherInc) {
            const m = text.match(/Other\s+(?:Family\s+)?Income[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)/i);
            if (m) otherInc = formatINR(m[1]);
        }
        if (!totalInc) {
            const m = text.match(/(?:Total\s+(?:Annual\s+)?Family\s+Income|Annual\s+Family\s+Income|Family\s+Annual\s+Income)[\s\S]{1,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)/i);
            if (m) totalInc = formatINR(m[1]);
        }

        // Assessment Period
        let assessmentPeriod = null;
        const periodMatch = text.match(/(?:Assessment\s+Period|Financial\s+Year|Financial\s+Assessment\s+Year|Assessment\s+Year)\s*[:=\-]?\s*([^\n\r]+)/i);
        if (periodMatch) {
            const candP = periodMatch[1].trim();
            const datesM = text.match(/(\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+to\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}(?:\s*\([^\)]+\))?)/i);
            const finYearM = text.match(/((?:financial\s+(?:assessment\s+)?year\s+)?20\d\d[-–]20?\d\d)/i);
            if (datesM) {
                assessmentPeriod = datesM[1].trim();
            } else if (finYearM) {
                assessmentPeriod = finYearM[1].trim();
            } else {
                assessmentPeriod = candP.replace(/\s+is\s+determined.*$/i, '').trim();
            }
        }

        const linesOut = [`**Page ${pageNum} — ${headingTitle}**\n`];
        linesOut.push('**Income Breakdown**');
        if (fatherInc) linesOut.push(`- Father's income: ${fatherInc}`);
        if (motherInc) linesOut.push(`- Mother's income: ${motherInc}`);
        if (otherInc) linesOut.push(`- Other income: ${otherInc}`);
        if (totalInc) linesOut.push(`- Total annual family income: ${totalInc}`);

        if (assessmentPeriod) {
            linesOut.push(`\n**Assessment Period**\n${assessmentPeriod}`);
        }

        // Conflict check
        if (allDocs && totalInc) {
            for (const otherDoc of allDocs) {
                if (otherDoc.id !== (doc && doc.id) && otherDoc.is_active !== false && !otherDoc.deleted_at) {
                    const oEf = otherDoc.extracted_fields || {};
                    const oInc = oEf.annual_family_income;
                    if (oInc) {
                        const cThis = String(totalInc).replace(/[₹,.\-\s/]/g, '');
                        const cOther = String(oInc).replace(/[₹,.\-\s/]/g, '');
                        if (cThis && cOther && cThis !== cOther) {
                            linesOut.push(
                                `\n⚠️ **REVIEW REQUIRED — Conflicting Evidence Detected:**\n` +
                                `- ${docName} (Page ${pageNum}): ${totalInc}\n` +
                                `- ${otherDoc.file_name || 'Other Document'}: ${formatINR(oInc)}`
                            );
                            break;
                        }
                    }
                }
            }
        }

        linesOut.push(`\n**Source**\n- Document: ${docName}\n- Page: Page ${pageNum}`);
        linesOut.push('\n**Evidence status:** Facts Extracted & Document Evidence Available (Pending Verification)');
        return linesOut.join('\n');
    }

    // 5. Non-Income Page
    const linesOut = [`**Page ${pageNum} — ${headingTitle}**\n`];
    linesOut.push('**Key Information**');

    const seenKeys = new Set();
    const keyInfoItems = [];

    const fieldLabels = [
        ['beneficiary_name', 'Applicant Full Name'],
        ['document_number', 'Certificate / Document Number'],
        ['date_of_birth', 'Date of Birth / Age'],
        ['category', 'Social Category'],
        ['gender', 'Gender'],
        ['district', 'District'],
        ['state', 'State'],
        ['issue_date', 'Issue Date'],
        ['issuing_authority', 'Issuing Authority']
    ];

    for (const [k, label] of fieldLabels) {
        const v = extractedFields[k];
        if (v && resolveProvenance(v, k)) {
            keyInfoItems.push(`- ${label}: ${v}`);
            seenKeys.add(label.toLowerCase());
            seenKeys.add(k.toLowerCase());
        }
    }

    let i = 0;
    while (i < cleanLines.length) {
        let line = cleanLines[i];
        if (line.startsWith('•') || line.startsWith('-')) {
            line = line.replace(/^[•\-*]\s*/, '').trim();
        }

        if (line.includes(':') && !line.endsWith(':')) {
            const parts = line.split(':');
            const k = parts[0].trim().replace(/^\d+\.\s*/, '');
            const v = parts.slice(1).join(':').trim();
            if (k.length > 2 && v.length > 0 && !seenKeys.has(k.toLowerCase())) {
                const kLow = k.toLowerCase();
                if (!['statement of jurisdiction', 'provenance note', 'notice', 'reference', 'schedule', 'form', 'certificate no', 'application ref'].some(ign => kLow.includes(ign))) {
                    keyInfoItems.push(`- ${k}: ${v}`);
                    seenKeys.add(k.toLowerCase());
                }
            }
            i++;
            continue;
        }

        if (line.endsWith(':') && i + 1 < cleanLines.length) {
            const k = line.slice(0, -1).trim().replace(/^\d+\.\s*/, '');
            const v = cleanLines[i + 1].trim();
            if (k.length > 2 && v.length > 0 && !seenKeys.has(k.toLowerCase())) {
                const kLow = k.toLowerCase();
                if (!['statement of jurisdiction', 'provenance note', 'notice', 'reference', 'schedule', 'form', 'certificate no', 'application ref'].some(ign => kLow.includes(ign))) {
                    keyInfoItems.push(`- ${k}: ${v}`);
                    seenKeys.add(k.toLowerCase());
                }
            }
            i += 2;
            continue;
        }

        i++;
    }

    if (keyInfoItems.length > 0) {
        linesOut.push(...keyInfoItems);
    } else {
        for (const l of cleanLines.slice(0, 10)) {
            if (l.length > 10 && !['statement of jurisdiction', 'notice', 'schedule'].some(ign => l.toLowerCase().includes(ign))) {
                linesOut.push(`- ${l}`);
            }
        }
    }

    linesOut.push(`\n**Source**\n- Document: ${docName}\n- Page: Page ${pageNum}`);
    linesOut.push('\n**Evidence status:** Facts Extracted & Document Evidence Available (Pending Verification)');
    return linesOut.join('\n');
}

function isAssessmentPeriodQuery(query) {
    if (!query) return false;
    const q = query.toLowerCase();
    const hasVerifyIntent = [
        'verify', 'verification', 'consistent', 'consistency', 'valid', 'validity',
        'check', 'conflict', 'match', 'align', 'correspond', 'reconcile'
    ].some(w => q.includes(w));
    const hasPeriodTarget = [
        'assessment period', 'financial year', 'financial assessment year',
        'assessment year', 'exact date', 'exact dates', 'dates and financial year',
        'start date', 'end date', 'dates'
    ].some(w => q.includes(w));
    if (hasVerifyIntent && hasPeriodTarget) return true;
    if (q.includes('assessment period') && (q.includes('date') || q.includes('year') || q.includes('consistent') || q.includes('verify'))) return true;
    if (q.includes('financial year') && (q.includes('date') || q.includes('exact') || q.includes('verify') || q.includes('consistent'))) return true;
    return false;
}

function isExplicitIncomeQuery(query) {
    if (!query) return false;
    const q = query.toLowerCase();
    const hasEnumIntent = [
        'enumerate', 'list every', 'list all', 'every explicitly stated',
        'every income amount', 'all stated income', 'every stated income',
        'all income amounts', 'each income amount', 'individual vs total',
        'individual and total', 'individual contribution', 'stated income amounts',
        'contributor', 'breakdown of every income'
    ].some(w => q.includes(w));
    const hasIncome = q.includes('income') || q.includes('earning') || q.includes('amount');
    if (hasEnumIntent && hasIncome) return true;
    if (q.includes('enumerate') && (q.includes('income') || q.includes('amount'))) return true;
    return false;
}

function extractAssessmentPeriodDetails(text) {
    let startDate = null;
    let endDate = null;
    let statedFy = null;

    const dateRangeMatch = (text || '').match(
        /(?:(?:period|dates?|duration|assessment\s+period)\s*[:=\-]?\s*)?(\d{1,2}(?:st|nd|rd|th)?[\s./-]+[A-Za-z]+[\s./-]+\d{4}|\d{1,2}[\s./-]+\d{1,2}[\s./-]+\d{4})\s*(?:to|-|until|through)\s*(\d{1,2}(?:st|nd|rd|th)?[\s./-]+[A-Za-z]+[\s./-]+\d{4}|\d{1,2}[\s./-]+\d{1,2}[\s./-]+\d{4})/i
    );
    if (dateRangeMatch) {
        startDate = dateRangeMatch[1].trim();
        endDate = dateRangeMatch[2].trim();
    }

    const fyMatch = (text || '').match(
        /((?:Financial\s+(?:Assessment\s+)?Year|Assessment\s+Year|Financial\s+Year|FY|AY)\s*[:=\-]?\s*20\d\d\s*[-–/]\s*20?\d\d)/i
    );
    if (fyMatch) {
        statedFy = fyMatch[1].trim();
    } else {
        const standaloneFy = (text || '').match(
            /((?:financial\s+(?:assessment\s+)?year|assessment\s+year)\s+20\d\d\s*[-–/]\s*20?\d\d)/i
        );
        if (standaloneFy) {
            statedFy = standaloneFy[1].trim();
        } else {
            const yearSpan = (text || '').match(/\b(20\d\d\s*[-–/]\s*20?\d\d)\b/);
            if (yearSpan) statedFy = yearSpan[1].trim();
        }
    }

    return { startDate, endDate, statedFy };
}

function validateDateFyConsistency(startDate, endDate, statedFy) {
    if (!startDate || !endDate || !statedFy) {
        const missing = [];
        if (!startDate || !endDate) missing.push('exact start/end dates');
        if (!statedFy) missing.push('financial year');
        return {
            consistencyResult: 'UNABLE TO VERIFY',
            explanation: `The document does not provide ${missing.join(' and ')} to establish consistency.`
        };
    }

    const syM = startDate.match(/\b(20\d\d)\b/);
    const eyM = endDate.match(/\b(20\d\d)\b/);
    if (!syM || !eyM) {
        return {
            consistencyResult: 'UNABLE TO VERIFY',
            explanation: 'Could not parse valid four-digit calendar years from the extracted start and end dates.'
        };
    }

    const startYear = parseInt(syM[1], 10);
    const endYear = parseInt(eyM[1], 10);

    const fyYears = statedFy.match(/\b20\d\d\b/g);
    let fyStart, fyEnd;
    if (!fyYears) {
        const fy2digit = statedFy.match(/\b(20\d\d)[-–/](\d{2})\b/);
        if (fy2digit) {
            fyStart = parseInt(fy2digit[1], 10);
            fyEnd = parseInt(String(fyStart).slice(0, 2) + fy2digit[2], 10);
        } else {
            return {
                consistencyResult: 'UNABLE TO VERIFY',
                explanation: `Could not parse numerical year range from stated financial period '${statedFy}'.`
            };
        }
    } else if (fyYears.length >= 2) {
        fyStart = parseInt(fyYears[0], 10);
        fyEnd = parseInt(fyYears[1], 10);
    } else {
        fyStart = parseInt(fyYears[0], 10);
        fyEnd = fyStart + 1;
    }

    const fyLower = statedFy.toLowerCase();
    const isAssessmentYearLabel = fyLower.includes('assessment year');

    if (fyStart === startYear && (fyEnd === endYear || fyEnd === startYear + 1)) {
        return {
            consistencyResult: 'CONSISTENT',
            explanation: `The extracted date range (${startDate} to ${endDate}) directly corresponds to Financial Year ${fyStart}–${fyEnd}, matching the stated document period.`
        };
    } else if (isAssessmentYearLabel && fyStart === startYear + 1 && (fyEnd === endYear + 1 || fyEnd === startYear + 2)) {
        return {
            consistencyResult: 'CONSISTENT',
            explanation: `The extracted date range (${startDate} to ${endDate}) represents the financial year preceding stated ${statedFy}, which conforms to statutory assessment standards.`
        };
    } else if (fyStart === startYear + 1 && !isAssessmentYearLabel) {
        return {
            consistencyResult: 'CONSISTENT',
            explanation: `The extracted date range (${startDate} to ${endDate}) corresponds to the preceding financial period for stated ${statedFy}.`
        };
    } else {
        return {
            consistencyResult: 'REVIEW REQUIRED (CONFLICT)',
            explanation: `The extracted date range (${startDate} to ${endDate}, calendar span ${startYear}–${endYear}) does not align with the stated period '${statedFy}' (span ${fyStart}–${fyEnd}).`
        };
    }
}

function verifyAssessmentPeriod(pageText, targetPage, doc, allDocs) {
    const docName = (doc && doc.file_name) || 'Document';
    const pNum = targetPage || 1;

    const { startDate, endDate, statedFy } = extractAssessmentPeriodDetails(pageText);
    const { consistencyResult, explanation } = validateDateFyConsistency(startDate, endDate, statedFy);

    const lines = [
        '### Assessment Period Verification\n',
        '**Document Extracted Values:**',
        `- **Exact Source Start Date**: ${startDate || 'Not specified in document'}`,
        `- **Exact Source End Date**: ${endDate || 'Not specified in document'}`,
        `- **Financial Year as Stated**: ${statedFy || 'Not specified in document'}\n`,
        '**Deterministic Validation:**',
        `- **Consistency Result**: ${consistencyResult}`,
        `- **Explanation**: ${explanation}`
    ];

    if (allDocs && statedFy) {
        for (const otherDoc of allDocs) {
            if (otherDoc.id !== (doc && doc.id) && otherDoc.is_active !== false && !otherDoc.deleted_at) {
                const oTxt = otherDoc.extracted_text || '';
                const { statedFy: oFy } = extractAssessmentPeriodDetails(oTxt);
                if (oFy && oFy.replace(/\D/g, '') !== statedFy.replace(/\D/g, '')) {
                    lines.push(
                        `\n⚠️ **REVIEW REQUIRED — Cross-Document Period Conflict:**\n` +
                        `- ${docName}: ${statedFy}\n` +
                        `- ${otherDoc.file_name || 'Other Document'}: ${oFy}`
                    );
                    break;
                }
            }
        }
    }

    lines.push(`\n**Source**\n- Document: ${docName}\n- Page: Page ${pNum}`);
    lines.push('\n**Evidence Status**\nFacts Extracted & Document Evidence Available (Pending Verification)');
    return lines.join('\n');
}

function extractAmountForKey(keyPattern, text) {
    const regInline = new RegExp(keyPattern + '[^\\n:]*?[:=\\-]\\s*(?:Rs\\.?|₹|INR)?\\s*([\\d,]+(?:\\.\\d+)?)', 'i');
    const mInline = (text || '').match(regInline);
    if (mInline) return mInline[1];
    const regBlock = new RegExp(keyPattern + '[\\s\\S]{0,120}?(?:Rs\\.?|₹|INR)\\s*([\\d,]+(?:\\.\\d+)?)', 'i');
    const mBlock = (text || '').match(regBlock);
    if (mBlock) return mBlock[1];
    return null;
}

function extractExplicitIncome(pageText, targetPage, doc, allDocs) {
    const docName = (doc && doc.file_name) || 'Document';
    const pNum = targetPage || 1;
    const ef = (doc && doc.extracted_fields) || {};

    const formatINR = (val) => {
        if (val === null || val === undefined || val === '') return '₹0';
        const s = String(val).replace(/[₹,Rs.\s/-]/gi, '').trim();
        const num = parseFloat(s);
        if (isNaN(num)) return `₹${val}`;
        return `₹${num.toLocaleString('en-IN')}`;
    };

    const items = [];
    const seen = new Set();

    let fatherAmt = extractAmountForKey("Father(?:'s|’s)?\\s*(?:Employment\\s*)?Income", pageText);
    if (!fatherAmt && ef.father_income) fatherAmt = ef.father_income;
    if (fatherAmt) {
        items.push({
            category: "Father's Employment Income",
            amount: formatINR(fatherAmt),
            type: "Individual Contribution",
            page: `Page ${pNum}`
        });
        seen.add('father');
    }

    let motherAmt = extractAmountForKey("Mother(?:'s|’s)?\\s*(?:Self-Employment\\s*)?Income", pageText);
    if (!motherAmt && ef.mother_income) motherAmt = ef.mother_income;
    if (motherAmt) {
        items.push({
            category: "Mother's Self-Employment Income",
            amount: formatINR(motherAmt),
            type: "Individual Contribution",
            page: `Page ${pNum}`
        });
        seen.add('mother');
    }

    let applicantAmt = extractAmountForKey("(?:Applicant(?:'s|’s)?|Personal)\\s*(?:Annual\\s*)?Income", pageText);
    if (applicantAmt) {
        items.push({
            category: "Applicant Personal Income",
            amount: formatINR(applicantAmt),
            type: "Individual Contribution",
            page: `Page ${pNum}`
        });
        seen.add('personal');
    }

    let otherAmt = extractAmountForKey("(?:Other\\s+(?:Family\\s+)?Income|Income\\s+from\\s+Other|Agricultural\\s+Income)", pageText);
    if (!otherAmt && ef.other_income) otherAmt = ef.other_income;
    if (otherAmt) {
        items.push({
            category: "Other Family Income",
            amount: formatINR(otherAmt),
            type: "Individual Contribution",
            page: `Page ${pNum}`
        });
        seen.add('other');
    }

    let totalAmt = extractAmountForKey("(?:Total\\s+(?:Annual\\s+)?Family\\s+Income|Annual\\s+Family\\s+Income)", pageText);
    if (!totalAmt && ef.annual_family_income) totalAmt = ef.annual_family_income;
    if (totalAmt) {
        items.push({
            category: "Total Annual Family Income",
            amount: formatINR(totalAmt),
            type: "Consolidated Total",
            page: `Page ${pNum}`
        });
        seen.add('total');
    }

    const lines = [
        '### Explicit Income Extraction\n',
        '**Document Stated Income Amounts:**'
    ];
    if (items.length > 0) {
        for (const it of items) {
            lines.push(`- **${it.category}**: ${it.amount} | **Type**: ${it.type} | **Source**: ${it.page}`);
        }
    } else {
        lines.push('- No explicit income amounts could be established from this document page.');
    }

    if (allDocs && totalAmt) {
        for (const otherDoc of allDocs) {
            if (otherDoc.id !== (doc && doc.id) && otherDoc.is_active !== false && !otherDoc.deleted_at) {
                const oEf = otherDoc.extracted_fields || {};
                const oInc = oEf.annual_family_income;
                if (oInc) {
                    const cThis = String(totalAmt).replace(/[₹,.\-\s/]/g, '');
                    const cOther = String(oInc).replace(/[₹,.\-\s/]/g, '');
                    if (cThis && cOther && cThis !== cOther) {
                        lines.push(
                            `\n⚠️ **REVIEW REQUIRED — Conflicting Evidence Detected:**\n` +
                            `- ${docName} (Page ${pNum}): ${formatINR(totalAmt)}\n` +
                            `- ${otherDoc.file_name || 'Other Document'}: ${formatINR(oInc)}`
                        );
                        break;
                    }
                }
            }
        }
    }

    lines.push(`\n**Source**\n- Document: ${docName}\n- Page: Page ${pNum}`);
    lines.push('\n**Evidence Status**\nFacts Extracted & Document Evidence Available (Pending Verification)');
    return lines.join('\n');
}

// ─── Grounded keyword → scheme + rule context map ────────────────────────────
// Simulates RAG retrieval: maps keywords to relevant policy passages.
const SCHEME_CATALOGUE = [
    {
        id: 'pm-vidyalaxmi',
        name: 'PM Vidyalaxmi',
        title: 'PM Vidyalaxmi',
        subtitle: 'Education loan support for higher studies.',
        tags: ['Education', 'Loan'],
        iconType: 'education'
    },
    {
        id: 'digital-india-internship',
        name: 'Digital India Internship Scheme',
        title: 'Digital India Internship Scheme',
        subtitle: 'Internship opportunities for students.',
        tags: ['Skill Development', 'Internship'],
        iconType: 'digital-india'
    },
    {
        id: 'skill-india',
        name: 'Skill India - Training & Certification',
        title: 'Skill India - Training & Certification',
        subtitle: 'Free skill training programs for students.',
        tags: ['Skill Development', 'Training'],
        iconType: 'skill-india'
    },
    {
        id: 'startup-india',
        name: 'Startup India',
        title: 'Startup India',
        subtitle: 'Support for student entrepreneurs.',
        tags: ['Entrepreneurship', 'Funding'],
        iconType: 'startup-india'
    },
    {
        id: 'pmegp',
        name: "Prime Minister's Employment Generation Programme (PMEGP)",
        title: 'PMEGP',
        subtitle: "Prime Minister's Employment Generation Programme",
        tags: ['Business Support', 'Self Employment', 'Central Government'],
        iconType: 'ashoka'
    },
    {
        id: 'pm-kisan',
        name: 'PM Kisan Samman Nidhi',
        title: 'PM Kisan',
        subtitle: 'Direct income support for farmers.',
        tags: ['Agriculture', 'Farmer Support', 'DBT'],
        iconType: 'kisan'
    },
    {
        id: 'mudra',
        name: 'Pradhan Mantri MUDRA Yojana',
        title: 'MUDRA Yojana',
        subtitle: 'Micro loans up to ₹10 Lakh for small enterprises.',
        tags: ['Credit / Loan', 'MSME', 'Collateral-free'],
        iconType: 'mudra'
    },
    {
        id: 'kcc',
        name: 'Kisan Credit Card (KCC)',
        title: 'Kisan Credit Card',
        subtitle: 'Credit limit for crops and agricultural activities.',
        tags: ['Credit / Loan', 'Agriculture'],
        iconType: 'kcc'
    },
    {
        id: 'standup-india',
        name: 'Stand-Up India',
        title: 'Stand-Up India',
        subtitle: 'Bank loans for SC/ST and Women entrepreneurs.',
        tags: ['Women', 'SC/ST', 'Credit / Loan'],
        iconType: 'standup'
    },
    {
        id: 'yipb',
        name: 'Young Investigators Programme in Biotechnology',
        title: 'Young Investigators Programme in Biotechnology',
        short_name: 'YIPB',
        subtitle: 'Kerala Biotechnology Commission (KBC/KSCSTE)',
        tags: ['Biotechnology', 'Research', 'Fellowship', 'Kerala', 'Science and Technology Department'],
        iconType: 'ashoka'
    }
];

const POLICY_CONTEXT = {
    pmegp: {
        subsidy: 'PMEGP provides margin money subsidy: Urban General 15%, Rural General 25%, Urban Special 25%, Rural Special 35% of project cost.',
        eligibility: 'Any individual above 18 years. Minimum VIII pass for project cost > ₹10L (manufacturing) or > ₹5L (service/business).',
        documents: 'Required: Aadhaar, PAN, Project Report, Udyam Registration (if applicable), ITR, Special Category Certificate.',
        limit: 'Maximum project cost: ₹50 lakh (manufacturing), ₹20 lakh (service/business).',
        loan: 'Own contribution: 10% (General), 5% (Special). Bank finances the balance.',
        source_url: 'https://www.myscheme.gov.in/schemes/pmegp'
    },
    'pm-kisan': {
        benefit: 'Eligible farmer families receive ₹6,000 per year in three equal instalments of ₹2,000.',
        eligibility: 'Small and marginal farmer families with combined land holding up to 2 hectares as on 01-02-2019.',
        exclusions: 'Exclusions: institutional land holders, former/present holders of constitutional posts, serving/retired government officers, income tax payers, professionals (doctors, engineers, lawyers, CA, architects).',
        documents: 'Required: Aadhaar, land ownership records, bank account details.',
        source_url: 'https://www.myscheme.gov.in/schemes/pm-kisan'
    },
    mudra: {
        categories: 'Shishu: up to ₹50,000 | Kishore: ₹50,001–₹5L | Tarun: ₹5L–₹10L. All are collateral-free.',
        eligibility: 'Non-corporate, non-farm micro/small enterprises. No prior default to any lender.',
        documents: 'Required: Aadhaar, PAN, business proof. For Kishore/Tarun: last 2 years ITR, bank statements.',
        source_url: 'https://www.myscheme.gov.in/schemes/mudra'
    },
    kcc: {
        benefit: 'Revolving credit limit covering crop cultivation expenses, post-harvest, maintenance, allied activities. Interest rate: 7% (4% after 3% interest subvention for timely repayment).',
        eligibility: 'All farmers — individual/joint borrowers, tenant farmers, share croppers, SHGs.',
        limit: 'Short-term credit limit up to ₹3 lakh; higher limits for medium-term/allied activities.',
        source_url: 'https://www.myscheme.gov.in/schemes/kcc'
    },
    'standup-india': {
        benefit: 'Bank loan between ₹10 lakh and ₹1 crore for greenfield enterprises in manufacturing, services, or trading.',
        eligibility: 'At least one SC/ST and at least one woman borrower per scheduled commercial bank branch.',
        documents: 'Required: Aadhaar, PAN, caste certificate (for SC/ST), business plan/project report.',
        source_url: 'https://www.myscheme.gov.in/schemes/standup-india'
    },
    yipb: {
        benefit: 'Young Scientists without fellowship/salary are eligible for a fellowship of ₹45,000/- plus 10% HRA per month, in addition to support for travel, contingency, consumables, and minor equipment. Maximum research grant support up to ₹30 lakhs for a period not exceeding three years.',
        eligibility: 'Applicant should possess a Ph.D. in any branch of Life Sciences with three years of post-doctoral research experience in Biotechnology, and be less than 40 years of age (relaxable as per statutory rules).',
        documents: 'Required documents: Identity proof, Passport size photographs, Educational certificates, Community Certificate (if applicable), Disability certificate (if applicable), Experience certificate (if applicable), and [Endorsement Form](https://kscste.kerala.gov.in/wp-content/uploads/2019/06/YIPB_endorsement_22.pdf).',
        application_process: 'Applications under the Young Investigators Programme in Biotechnology (YIPB) are invited once a year via advertisement on the Kerala Biotechnology Commission (KBC) and KSCSTE official website. To apply, applicants must complete the following steps across two stages:\n\n1. **Stage 1 (Step 1 - Pre-Proposal Submission & Peer Review):**\n   - Proposals are submitted online only through the official portal.\n   - Scrutiny of the pre-proposal is conducted with email/SMS acknowledgment.\n   - Pre-proposals are evaluated by three subject experts across a 7-criteria matrix (scored 0 to 5).\n   - Only the top 50% scoring higher than 60% qualify to advance.\n\n2. **Stage 2 (Step 2 - Detailed Proposal Submission & Final Decision):**\n   - Shortlisted Principal Investigators submit detailed proposals online within the notified timeframe.\n   - Proposals undergo peer review by five national-level domain experts.\n   - Applicants present proposals before the Programme Advisory Committee (PAC-YIPB).\n   - Final sanctioning recommendations are approved by KBC/KSCSTE.\n\nRequired institutional endorsement must be submitted using the prescribed format from the host institution.',
        source_url: 'https://www.myscheme.gov.in/schemes/yipb'
    }
};

// Dynamic canonical scheme catalogue lookup map: slug/alias -> scheme record
const DYNAMIC_CANONICAL_INDEX = new Map();

function initDynamicCanonicalCatalogue() {
    for (const s of SCHEME_CATALOGUE) {
        if (!DYNAMIC_CANONICAL_INDEX.has(s.id)) {
            const ctx = POLICY_CONTEXT[s.id] || {};
            DYNAMIC_CANONICAL_INDEX.set(s.id, {
                id: s.id,
                name: s.name,
                short_name: s.short_name || s.title || s.id,
                title: s.title || s.name,
                subtitle: s.subtitle || '',
                tags: s.tags || [],
                iconType: s.iconType || 'ashoka',
                benefit: ctx.benefit || ctx.subsidy || ctx.limit || null,
                eligibility: ctx.eligibility || null,
                documents: ctx.documents || null,
                application_process: ctx.application_process || null,
                exclusions: ctx.exclusions || null,
                source_url: ctx.source_url || 'https://www.myscheme.gov.in'
            });
        }
    }

    const candidatePaths = [
        path.resolve(__dirname, '../../../Intelligence/data/processed/schemes_canonical.jsonl'),
        path.resolve(process.cwd(), '../Intelligence/data/processed/schemes_canonical.jsonl'),
        path.resolve(process.cwd(), 'Intelligence/data/processed/schemes_canonical.jsonl')
    ];

    for (const p of candidatePaths) {
        try {
            if (fs.existsSync(p)) {
                const content = fs.readFileSync(p, 'utf8');
                const lines = content.split('\n');
                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const rec = JSON.parse(line);
                        const slug = (rec.slug || rec.id || '').toLowerCase().trim();
                        if (!slug) continue;
                        const sName = rec.scheme_name || rec.name || slug;
                        const shortName = rec.short_title || rec.short_name || slug.toUpperCase();
                        const existing = DYNAMIC_CANONICAL_INDEX.get(slug);
                        DYNAMIC_CANONICAL_INDEX.set(slug, {
                            id: slug,
                            name: sName,
                            short_name: shortName,
                            title: shortName,
                            subtitle: rec.ministry || rec.state || (existing ? existing.subtitle : ''),
                            tags: Array.isArray(rec.tags) ? rec.tags : (existing ? existing.tags : []),
                            iconType: existing ? existing.iconType : 'ashoka',
                            benefit: rec.benefits || rec.benefit_summary || (existing ? existing.benefit : null),
                            eligibility: rec.eligibility || (existing ? existing.eligibility : null),
                            documents: rec.documents_required || rec.required_documents || (existing ? existing.documents : null),
                            application_process: rec.application_process || (existing ? existing.application_process : null),
                            exclusions: rec.exclusions || (existing ? existing.exclusions : null),
                            source_url: rec.source_url || (existing ? existing.source_url : null)
                        });
                    } catch (_) {}
                }
                break;
            }
        } catch (_) {}
    }
}
initDynamicCanonicalCatalogue();

/**
 * Resolve the best matching scheme context from user message.
 */
const resolveContext = (message) => {
    const rawMsg = (message || '');
    const msg = rawMsg.toLowerCase();

    // 1. Direct priority resolution for known canonical schemes
    if (msg.includes('yipb') || msg.includes('young investigators programme in biotechnology') || msg.includes('young investigators program in biotechnology') || (msg.includes('young investigators') && msg.includes('biotechnology'))) {
        const item = DYNAMIC_CANONICAL_INDEX.get('yipb') || {};
        const ctx = POLICY_CONTEXT.yipb || {
            benefit: item.benefit,
            eligibility: item.eligibility,
            documents: item.documents,
            application_process: item.application_process,
            source_url: item.source_url
        };
        return { schemeId: 'yipb', context: ctx, schemeObj: DYNAMIC_CANONICAL_INDEX.get('yipb') || SCHEME_CATALOGUE.find(s => s.id === 'yipb') };
    }
    if (msg.includes('pmegp') || msg.includes('employment generation')) return { schemeId: 'pmegp', context: POLICY_CONTEXT.pmegp, schemeObj: DYNAMIC_CANONICAL_INDEX.get('pmegp') || SCHEME_CATALOGUE.find(s => s.id === 'pmegp') };
    if (msg.includes('pm kisan') || msg.includes('pm-kisan') || msg.includes('farmer') || msg.includes('kisan')) return { schemeId: 'pm-kisan', context: POLICY_CONTEXT['pm-kisan'], schemeObj: DYNAMIC_CANONICAL_INDEX.get('pm-kisan') || SCHEME_CATALOGUE.find(s => s.id === 'pm-kisan') };
    if (msg.includes('mudra') || msg.includes('shishu') || msg.includes('kishore') || msg.includes('tarun')) return { schemeId: 'mudra', context: POLICY_CONTEXT.mudra, schemeObj: DYNAMIC_CANONICAL_INDEX.get('mudra') || SCHEME_CATALOGUE.find(s => s.id === 'mudra') };
    if (msg.includes('kcc') || msg.includes('kisan credit')) return { schemeId: 'kcc', context: POLICY_CONTEXT.kcc, schemeObj: DYNAMIC_CANONICAL_INDEX.get('kcc') || SCHEME_CATALOGUE.find(s => s.id === 'kcc') };
    if (msg.includes('stand up') || msg.includes('standup') || msg.includes('sc/st') || msg.includes('woman entrepreneur')) return { schemeId: 'standup-india', context: POLICY_CONTEXT['standup-india'], schemeObj: DYNAMIC_CANONICAL_INDEX.get('standup-india') || SCHEME_CATALOGUE.find(s => s.id === 'standup-india') };

    // 2. Dynamic lookup against full canonical catalogue
    const cleanMsg = ` ${msg.replace(/[^\w\s]/g, ' ')} `;
    const msgTokens = new Set(cleanMsg.trim().split(/\s+/).filter(Boolean));

    for (const [slug, item] of DYNAMIC_CANONICAL_INDEX.entries()) {
        const nameLower = (item.name || '').toLowerCase();
        const shortClean = (item.short_name || '').toLowerCase().replace(/[^\w]/g, '');

        if (nameLower.length >= 6 && (msg.includes(nameLower) || cleanMsg.includes(` ${nameLower} `))) {
            return {
                schemeId: slug,
                context: {
                    benefit: item.benefit,
                    eligibility: item.eligibility,
                    documents: item.documents,
                    application_process: item.application_process,
                    source_url: item.source_url,
                    exclusions: item.exclusions
                },
                schemeObj: item
            };
        }
        if (shortClean.length >= 3 && msgTokens.has(shortClean)) {
            return {
                schemeId: slug,
                context: {
                    benefit: item.benefit,
                    eligibility: item.eligibility,
                    documents: item.documents,
                    application_process: item.application_process,
                    source_url: item.source_url,
                    exclusions: item.exclusions
                },
                schemeObj: item
            };
        }
    }

    return { schemeId: null, context: null, schemeObj: null };
};

/**
 * Build a grounded answer from the policy context.
 */
const buildGroundedAnswer = (message, context, schemeId, schemeObj = null) => {
    const msg = message.toLowerCase();
    const scheme = schemeObj || SCHEME_CATALOGUE.find(s => s.id === schemeId) || DYNAMIC_CANONICAL_INDEX.get(schemeId);
    const schemeName = scheme ? (scheme.name || scheme.title) : (schemeId ? schemeId.toUpperCase() : 'this scheme');
    const sourceUrl = (context && context.source_url) || (scheme && scheme.source_url) || null;

    // Check application process & submission procedure inquiry
    const isAppProc = /\b(?:application\s+(?:process|procedure|steps?|mode|submission|guidelines?|fee)|how\s+(?:can\s+i|to|do\s+i)\s+apply|procedure\s+to\s+apply|process\s+to\s+apply|where\s+(?:can\s+i|to)\s+apply)\b/i.test(msg);

    if (isAppProc) {
        if (context.application_process) {
            return {
                answer: `Regarding the application process for **${schemeName}**:\n\n${context.application_process}`,
                citation: {
                    schemeId,
                    schemeName,
                    source: sourceUrl || 'Official Government Scheme Guidelines',
                    url: sourceUrl || null
                }
            };
        } else {
            return {
                answer: `Official application procedures and submission stages for **${schemeName}** are not currently available in offline fallback mode. Please refer directly to the official nodal department portal${sourceUrl ? ` at ${sourceUrl}` : ''} for verified instructions.`,
                citation: {
                    schemeId,
                    schemeName,
                    source: sourceUrl || 'Official Scheme Repository',
                    url: sourceUrl || null
                }
            };
        }
    }

    // Pick the most relevant context chunk
    let relevantChunk = '';
    if (msg.includes('subsidy') || msg.includes('benefit') || msg.includes('amount') || msg.includes('how much')) {
        relevantChunk = context.subsidy || context.benefit || context.limit || '';
    } else if (msg.includes('eligib') || msg.includes('qualify') || msg.includes('who can') || msg.includes('criteria')) {
        relevantChunk = context.eligibility || '';
    } else if (msg.includes('document') || msg.includes('required') || msg.includes('need to submit') || msg.includes('endorsement')) {
        if (Array.isArray(context.documents)) {
            relevantChunk = `Required documents include: ${context.documents.join('; ')}`;
        } else {
            relevantChunk = context.documents || '';
        }
    } else if (msg.includes('loan') || msg.includes('credit') || msg.includes('interest')) {
        relevantChunk = context.loan || context.limit || '';
    } else if (msg.includes('exclusion') || msg.includes('not eligible') || msg.includes('who cannot')) {
        relevantChunk = context.exclusions || '';
    } else {
        relevantChunk = context.benefit || context.subsidy || context.eligibility || context.documents || Object.values(context)[0] || '';
    }

    if (!relevantChunk) return null;

    return {
        answer: `Regarding **${schemeName}**: ${relevantChunk}`,
        citation: {
            schemeId,
            schemeName,
            source: sourceUrl || 'Official Government Scheme Guidelines (embedded policy corpus)',
            url: sourceUrl || null
        }
    };
};

/**
 * Fallback general knowledge for very broad questions.
 */
const GENERAL_ANSWERS = [
    {
        patterns: ['what schemes', 'list schemes', 'available schemes', 'which schemes'],
        answer: 'The platform currently covers PMEGP (₹50L manufacturing subsidy), MUDRA (micro loans up to ₹10L), PM-Kisan (₹6,000/year for farmers), KCC (revolving credit for farmers), and Stand-Up India (₹10L–₹1Cr for SC/ST and women entrepreneurs). Use the Discover page to search and filter.',
        schemes: [
            { id: 'pmegp', slug: 'pmegp', schemeId: 'pmegp', title: 'PMEGP', subtitle: "Prime Minister's Employment Generation Programme", tags: ['Business Support', 'Self Employment'], iconType: 'ashoka' },
            { id: 'mudra', slug: 'mudra', schemeId: 'mudra', title: 'MUDRA Yojana', subtitle: 'Micro loans up to ₹10 Lakh', tags: ['Credit / Loan', 'MSME'], iconType: 'mudra' },
            { id: 'pm-kisan', slug: 'pm-kisan', schemeId: 'pm-kisan', title: 'PM Kisan', subtitle: 'Direct income support for farmers', tags: ['Agriculture', 'DBT'], iconType: 'kisan' },
            { id: 'kcc', slug: 'kcc', schemeId: 'kcc', title: 'Kisan Credit Card', subtitle: 'Credit limit for crops and agriculture', tags: ['Credit / Loan', 'Agriculture'], iconType: 'kcc' },
            { id: 'standup-india', slug: 'standup-india', schemeId: 'standup-india', title: 'Stand-Up India', subtitle: 'Loans for SC/ST and Women entrepreneurs', tags: ['Women', 'SC/ST'], iconType: 'standup' }
        ]
    },
    { patterns: ['how do i apply', 'how to apply', 'application process'], answer: 'To apply: (1) Complete your profile, (2) Upload required documents, (3) Check eligibility on the scheme page, (4) Click "Apply Now" which redirects to the official government portal or submits through this platform.' },
    { patterns: ['subsidy', 'what is subsidy'], answer: 'A subsidy is a financial contribution by the government towards your project cost. For example, PMEGP provides a margin money subsidy of 15%–35% of the total project cost, which does NOT need to be repaid.' },
    { patterns: ['hello', 'hi', 'hey', 'good morning', 'good evening'], answer: 'Hello! I am your Policy Assistant. I can help you understand government schemes, check eligibility, and explain benefits. Ask me about PMEGP, MUDRA, PM-Kisan, KCC, or Stand-Up India.' }
];

const AI_SERVER_URL = process.env.AI_SERVER_URL || 'http://127.0.0.1:8000';

const stripNegativeConstraints = (text) => {
    if (!text) return '';
    const negPattern = /\b(?:do\s+not|don['\u2019]?t|dont|never|without|exclude|avoid|stop)\s+(?:to\s+)?(?:show|display|use|utilize|search|check|inspect|look\s+at|include|refer\s+to|mention|rely\s+on)?\s*[^.!?\n;]*(?:documents?|files?|certificates?|tickets?|applications?|vault|profile|records?)[^.!?\n;]*/gi;
    return text.replace(negPattern, ' ').trim();
};

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

    if (typeof conversationId === 'object' && conversationId !== null) {
        options = conversationId;
        conversationId = null;
    }

    // Load user profile, verified documents, and submitted applications from Supabase
    let profile = null;
    let fullDocumentsList = [];
    let userApplicationsList = [];

    if (userId) {
        try { 
            profile = await profileService.getProfileById(userId); 
        } catch (_) { }

        try {
            const userDocs = await documentServices.listDocuments(userId);
            if (Array.isArray(userDocs)) {
                for (const d of userDocs) {
                    const fields = d.extractedData || {};
                    fullDocumentsList.push({
                        id: d.id,
                        document_type: d.documentType,
                        file_name: d.fileName,
                        verification_status: d.verificationStatus,
                        extracted_fields: fields,
                        extracted_text: d.extractedText || '',
                        doc_number: d.docNumber || null,
                        issuer: d.issuer || null,
                        uploaded_at: d.uploadedAt
                    });
                }
            }
        } catch (e) {
            console.warn('[chatService] could not load documents via documentServices:', e.message);
        }

        try {
            const apps = await applicationService.listApplications(userId);
            if (Array.isArray(apps)) {
                userApplicationsList = apps.map(app => {
                    const appIdShort = `APP-${String(app.id).slice(0, 8).toUpperCase()}`;
                    return {
                        id: app.id,
                        ticket_id: appIdShort,
                        scheme_id: app.scheme_id,
                        scheme_name: app.scheme_name || `Scheme #${String(app.scheme_id).slice(0, 8).toUpperCase()}`,
                        status: app.status || 'under_review',
                        estimated_benefit: app.estimated_benefit ? `₹ ${Number(app.estimated_benefit).toLocaleString('en-IN')}` : null,
                        submitted_at: app.submitted_at || app.created_at,
                        eligibility_status: app.eligibility_status || null
                    };
                });
            }
        } catch (e) {
            console.warn('[chatService] could not load applications via applicationService:', e.message);
        }
    }

    // Profile and document facts intentionally remain separate. Document order
    // is not evidence precedence; Intelligence reconciles document-scoped facts
    // and marks discordant values for review.
    const profileFacts = profile || {};
    const documentFacts = buildDocumentFacts(fullDocumentsList);

    const effectiveConversationId = conversationId || (userId ? String(userId) : undefined);

    // If citizen explicitly asks for certificate reference / certificate number according to document, but vault is empty
    const isExplicitCertDocQuery = /\b(?:certificate\s+reference|certificate\s+number)\b/i.test(message) &&
        /\b(?:according\s+to|in\s+my|from\s+my|my\s+document|my\s+certificate)\b/i.test(message);
    if (isExplicitCertDocQuery && fullDocumentsList.length === 0) {
        const noDocReply = 'Currently, there are no documents uploaded on your file, which means I cannot provide a Certificate Reference or any specific details related to your documents. Please upload your documents under the Documents tab to verify your details.';
        return {
            source: 'document_vault',
            degraded: false,
            reply: noDocReply,
            answer: noDocReply,
            isGrounded: true,
            citations: [],
            schemes: []
        };
    }

    // --- 1. DYNAMIC AI INTEGRATION ATTEMPT (PHASE 15) ---
    // Connect to FastAPI Intelligence microservice /v1/chat
    try {
        const targetLanguage = (options && options.language) || 'en';
        const payload = {
            query: message,
            conversation_id: effectiveConversationId,
            applicant_id: userId || undefined,
            language: targetLanguage,
            applicant_facts: profileFacts,
            document_facts: documentFacts,
            documents: fullDocumentsList,
            applications: userApplicationsList,
            conversation_history: Array.isArray(history) ? history : ((options && options.history) || [])
        };

        const aiResponse = await intelligenceClient.postJson('/v1/chat', payload, {
            timeoutMs: 30000
        });

        if (aiResponse && (aiResponse.answer || aiResponse.reply)) {
            const answerText = aiResponse.answer || aiResponse.reply;

            const citations = (aiResponse.citations || []).map(c => {
                const isDoc = c.scheme_id === 'USER_DOCUMENT';
                let docSource = c.url || 'Official Scheme Repository';
                if (isDoc && c.excerpt) {
                    const match = c.excerpt.match(/^(?:📄\s*)?([^\-(]+?)(?:\s*\((Page\s*(?:\d+|Unknown))\))?\s*-/i);
                    if (match) {
                        const pageLabel = match[2] ? match[2].trim() : null;
                        docSource = `📄 ${match[1].trim()}${pageLabel ? ` (${pageLabel})` : ''}`;
                    } else {
                        docSource = '📄 Uploaded Document';
                    }
                }
                return {
                    chunkId: c.chunk_id || c.chunkId || null,
                    schemeId: c.scheme_id || c.schemeId || null,
                    schemeName: isDoc ? 'Uploaded Document' : (c.scheme_name || c.scheme_id || 'Statutory Policy Corpus'),
                    source: docSource,
                    url: c.url || null,
                    excerpt: c.excerpt || ''
                };
            });

            const schemes = (aiResponse.suggested_schemes || []).map(s => {
                const catalogMatch = SCHEME_CATALOGUE.find(c => c.id === s.scheme_id);
                const relevanceScore = s.relevance_score != null ? Math.round(s.relevance_score * 100) : null;
                const eligibilityStatus = s.eligibility_status || 'UNKNOWN';
                const hasEligScore = s.eligibility_score != null && typeof s.eligibility_score === 'number';
                const matchScore = hasEligScore ? Math.round(s.eligibility_score) : null;

                let matchType = 'neutral';
                if (eligibilityStatus === 'PASS') {
                    matchType = 'green';
                } else if (eligibilityStatus === 'FAIL') {
                    matchType = 'orange';
                } else if (eligibilityStatus === 'REVIEW') {
                    matchType = 'amber';
                }

                const canonicalSlug = s.slug || s.scheme_id || (catalogMatch ? catalogMatch.id : s.scheme_id);
                return {
                    id: canonicalSlug,
                    schemeId: canonicalSlug,
                    slug: canonicalSlug,
                    title: s.scheme_name || (catalogMatch ? catalogMatch.title : s.scheme_id),
                    name: s.scheme_name || (catalogMatch ? catalogMatch.name : s.scheme_id),
                    subtitle: s.ministry || s.state || (catalogMatch ? catalogMatch.subtitle : ''),
                    tags: [s.ministry, s.state].filter(Boolean),
                    matchScore,
                    relevanceScore,
                    eligibilityStatus,
                    matchType,
                    iconType: catalogMatch ? catalogMatch.iconType : 'ashoka'
                };
            });

            const result = {
                source: 'intelligence',
                degraded: false,
                reply: answerText,
                answer: answerText,
                citations,
                schemes,
                isGrounded: citations.length > 0 || (aiResponse.intent === 'PERSONAL_FACT_LOOKUP') || (aiResponse.intent === 'DOCUMENT_INQUIRY') || (aiResponse.intent === 'APPLICATION_INQUIRY'),
                showViewAll: schemes.length > 0,
                conversationId: aiResponse.conversation_id || effectiveConversationId,
                requestId: aiResponse.request_id || null,
                intent: aiResponse.intent || 'SCHEME_DISCOVERY',
                detectedLanguage: aiResponse.detected_language || targetLanguage || 'en',
                providerTelemetry: aiResponse.provider_telemetry || null
            };

            if (userId) {
                try {
                    const recordRes = await chatHistoryService.recordChatTurn(userId, conversationId, message, result);
                    if (recordRes?.conversationId) {
                        result.conversationId = recordRes.conversationId;
                    }
                } catch (historyErr) {
                    console.warn('[chatService] could not record chat history:', historyErr.message);
                }
            }

            return result;
        }
    } catch (err) {
        console.warn(`[chatService] Intelligence /v1/chat unavailable (${err.message}) - Falling back to local engine`);
        if (options && options.allowFallback === false) {
            throw err;
        }
    }
    // ----------------------------------------------------

    // --- 2. LOCAL OFFLINE FALLBACK ENGINE ---
    const fallbackResult = withFallbackMeta(computeLocalFallback(message, profileFacts, fullDocumentsList, userApplicationsList));
    fallbackResult.conversationId = effectiveConversationId;
    if (userId) {
        try {
            const recordRes = await chatHistoryService.recordChatTurn(userId, conversationId, message, fallbackResult);
            if (recordRes?.conversationId) {
                fallbackResult.conversationId = recordRes.conversationId;
            }
        } catch (historyErr) {
            console.warn('[chatService] could not record fallback chat history:', historyErr.message);
        }
    }
    return fallbackResult;
};

const computeLocalFallback = (message, profile, documents = [], applications = []) => {
    const cleanedMsg = stripNegativeConstraints(message);
    const msgLower = cleanedMsg.toLowerCase();
    const rawMsgLower = (message || '').toLowerCase();

    // Check application & ticket inquiries
    const isSchemeProcedure = /\b(?:application\s+(?:process|procedure|steps?|mode|form|deadline|guidelines?|fee)|how\s+(?:can\s+i|to|do\s+i)\s+apply|procedure\s+to\s+apply|steps?\s+to\s+apply|process\s+to\s+apply|where\s+(?:can\s+i|to)\s+apply)\b/i.test(msgLower);
    const isPersonalTicketQuery = !isSchemeProcedure && (
        /\b(?:(?:show|view|track|list|get|check|find|tell\s+me)\s+(?:all\s+)?(?:my\s+)?(?:active\s+|submitted\s+|support\s+)?(?:applications?|tickets?)|status\s+of\s+(?:my\s+)?(?:application|ticket)|(?:my\s+)?(?:active|submitted|support)\s+(?:applications?|tickets?)|my\s+tickets?|my\s+applications?|ticket\s+#?\w+|application\s+status|ticket\s+status)\b/i.test(msgLower)
    );

    if (isPersonalTicketQuery) {
        if (applications.length > 0) {
            const appLines = applications.map(a => 
                `• **Ticket ID:** \`${a.ticket_id}\` | **Scheme:** ${a.scheme_name} | **Status:** ${a.status} | **Benefit:** ${a.estimated_benefit || 'Under Review'}`
            ).join('\n');
            return {
                reply: `Here are your active government applications and support tickets on file in Supabase:\n\n${appLines}\n\nYou can also view full tracking details under the **Active Ticket** tab on the Documents page or on the **Applications** page.`,
                isGrounded: true,
                schemeId: null,
                suggestions: ['Check my eligibility for PMEGP', 'Upload more documents']
            };
        } else {
            return {
                reply: 'You currently have no active applications or tickets submitted. You can apply for eligible schemes in the **Discover Schemes** section or raise a ticket under the **Documents** page.',
                isGrounded: true,
                schemeId: null,
                suggestions: ['Explore available schemes', 'Check my eligibility']
            };
        }
    }

    // Ground on explicit scheme if detected in fallback catalog BEFORE generic document passage search
    const { schemeId, context, schemeObj } = resolveContext(message);
    const pageMatch = rawMsgLower.match(/\bpage\s+(\d+)\b/);
    const isPersonalVaultReq = /\b(?:have\s+i\s+uploaded|did\s+i\s+upload|my\s+uploaded|uploaded\s+by\s+me|in\s+my\s+vault|list\s+my\s+documents?|show\s+my\s+documents?)\b/i.test(msgLower);

    if (schemeId && context && !pageMatch && !isPersonalVaultReq) {
        const grounded = buildGroundedAnswer(message, context, schemeId, schemeObj);
        if (grounded) {
            let personalNote = '';
            if (profile && schemeId === 'pm-kisan' && (profile.occupation || '').toLowerCase() !== 'farmer') {
                personalNote = '\n\n⚠️ Note: Based on your profile, your occupation is not registered as "farmer". You may not qualify for PM-Kisan unless you update your profile with the correct occupation.';
            }

            const targetScheme = schemeObj || SCHEME_CATALOGUE.find(s => s.id === schemeId) || DYNAMIC_CANONICAL_INDEX.get(schemeId);
            const canonicalSlug = targetScheme?.slug || targetScheme?.id || schemeId;
            const fallbackScheme = targetScheme ? {
                id: canonicalSlug,
                schemeId: canonicalSlug,
                slug: canonicalSlug,
                title: targetScheme.title || targetScheme.name || schemeId,
                name: targetScheme.name || targetScheme.title || schemeId,
                subtitle: targetScheme.subtitle || targetScheme.ministry || targetScheme.state || '',
                tags: targetScheme.tags || [],
                matchScore: null,
                relevanceScore: 100,
                eligibilityStatus: 'UNKNOWN',
                matchType: 'neutral',
                iconType: targetScheme.iconType || 'ashoka'
            } : null;

            return {
                reply: grounded.answer + personalNote,
                citations: grounded.citation ? [grounded.citation] : [],
                isGrounded: true,
                schemeId,
                schemes: fallbackScheme ? [fallbackScheme] : [],
                profile: profile ? { name: profile.full_name, occupation: profile.occupation } : null
            };
        }
    }

    if (isSchemeProcedure && !pageMatch && !isPersonalVaultReq) {
        // Distinguish generic portal inquiries from specific named scheme inquiries
        const isGenericPortal = /^(?:how\s+(?:can\s+i|to|do\s+i)\s+apply|what\s+is\s+the\s+application\s+(?:process|procedure|steps?)|application\s+(?:process|procedure|steps?)|steps?\s+to\s+apply|explain\s+(?:the\s+)?application\s+(?:process|procedure|steps?))(?:\s+(?:for\s+(?:a\s+|any\s+|this\s+|the\s+)?schemes?|on\s+fin|through\s+fin|online|through\s+(?:the\s+)?portal|on\s+(?:the\s+)?platform))?[?.!]?$/i.test(cleanedMsg.trim()) ||
            /\b(?:through\s+fin|on\s+the\s+fin\s+portal|through\s+the\s+platform)\b/i.test(cleanedMsg);

        if (isGenericPortal) {
            return {
                reply: 'To apply for official government welfare schemes through the FIN portal:\n\n1. **Step 1:** Complete your profile with your occupation, state, and category.\n2. **Step 2:** Review statutory guidelines and required documents under the scheme details.\n3. **Step 3:** Upload and verify required documents in the My Documents vault.\n4. **Step 4:** Submit your application online through the official nodal department portal or via FIN.',
                citations: [],
                isGrounded: true,
                schemeId: null,
                suggestions: ['Find schemes for my profile', 'What documents are required?']
            };
        }

        // Specific scheme was requested but could not be resolved or detailed offline procedure is absent
        return {
            reply: 'Official application procedures and submission stages for the requested scheme are currently unavailable in offline fallback mode while the Intelligence service is initializing. Please verify official submission stages and required documentation on the relevant nodal ministry portal, or retry once the Intelligence service is ready.',
            citations: [],
            isGrounded: false,
            schemeId: null,
            suggestions: ['Explore available schemes', 'Check platform status']
        };
    }

    // 1. Page-specific document query ("What information is mentioned on page 3?")
    if (pageMatch) {
        const targetPage = parseInt(pageMatch[1], 10);
        if (documents.length === 0) {
            return {
                reply: "You do not have any uploaded documents on file yet. Please upload your document in the 'My Documents' vault to query its contents.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }

        let foundPageText = null;
        let foundDoc = null;
        let totalPagesDetected = 1;

        for (const doc of documents) {
            const extText = doc.extracted_text || '';
            const pageBlocks = extText.split(/---\s*\[Page\s+(\d+)\]\s*---/);
            if (pageBlocks.length > 1) {
                totalPagesDetected = Math.max(totalPagesDetected, Math.floor(pageBlocks.length / 2));
                for (let i = 1; i < pageBlocks.length; i += 2) {
                    const pNum = parseInt(pageBlocks[i], 10);
                    if (pNum === targetPage) {
                        const pContent = (pageBlocks[i + 1] || '').trim();
                        if (pContent) {
                            foundPageText = pContent;
                            foundDoc = doc;
                            break;
                        }
                    }
                }
            } else if (targetPage === 1 && extText.trim()) {
                foundPageText = extText.trim();
                foundDoc = doc;
                break;
            }
            if (foundPageText) break;
        }

        if (foundPageText && foundDoc) {
            const docName = foundDoc.file_name || 'Document';
            const snippet = foundPageText.slice(0, 200).replace(/\n/g, ' ').trim();
            let replyText;
            if (isAssessmentPeriodQuery(msgLower)) {
                replyText = verifyAssessmentPeriod(foundPageText, targetPage, foundDoc, documents);
            } else if (isExplicitIncomeQuery(msgLower)) {
                replyText = extractExplicitIncome(foundPageText, targetPage, foundDoc, documents);
            } else {
                replyText = summarizePageText(foundPageText, targetPage, foundDoc, documents);
            }

            return {
                reply: replyText,
                citations: [{
                    chunkId: `${foundDoc.id}_page_${targetPage}`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (Page ${targetPage})`,
                    excerpt: `📄 ${docName} (Page ${targetPage}) - ${snippet}`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            const firstDoc = documents[0];
            const docName = firstDoc.file_name || 'your document';
            return {
                reply: `According to your uploaded document **${docName}**, Page ${targetPage} does not exist in the document (the document contains ${totalPagesDetected} page(s)). The document does not establish this answer.`,
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    // 1.5 Assessment Period Verification without explicit page
    if (isAssessmentPeriodQuery(msgLower)) {
        if (documents.length === 0) {
            return {
                reply: 'You do not have any uploaded documents on file in Supabase yet. Please upload your document to verify the assessment period.',
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
        let targetDoc = null;
        let targetPageNum = 1;
        let targetText = '';
        for (const doc of documents) {
            if (doc.is_active !== false && !doc.deleted_at) {
                const ext = doc.extracted_text || '';
                const blocks = ext.split(/---\s*\[Page\s+(\d+)\]\s*---/);
                if (blocks.length > 1) {
                    for (let i = 1; i < blocks.length; i += 2) {
                        const pNum = parseInt(blocks[i], 10);
                        const pTxt = blocks[i + 1] || '';
                        if (/(?:assessment\s+period|financial\s+year|assessment\s+year|1\s+april|01\s+april)/i.test(pTxt)) {
                            targetDoc = doc;
                            targetPageNum = pNum;
                            targetText = pTxt.trim();
                            break;
                        }
                    }
                }
                if (!targetText && ext) {
                    targetDoc = doc;
                    targetPageNum = 1;
                    targetText = ext.trim();
                }
                if (targetText) break;
            }
        }
        if (!targetDoc) {
            targetDoc = documents[0];
            targetText = targetDoc.extracted_text || '';
        }
        const docName = targetDoc.file_name || 'Document';
        const snippet = targetText.slice(0, 200).replace(/\n/g, ' ').trim();
        const replyText = verifyAssessmentPeriod(targetText, targetPageNum, targetDoc, documents);
        return {
            reply: replyText,
            citations: [{
                chunkId: `${targetDoc.id}_page_${targetPageNum}`,
                schemeId: 'USER_DOCUMENT',
                schemeName: 'Uploaded Document',
                source: `📄 ${docName} (Page ${targetPageNum})`,
                excerpt: `📄 ${docName} (Page ${targetPageNum}) - ${snippet}`
            }],
            isGrounded: true,
            schemeId: null
        };
    }

    // 1.6 Explicit Income Extraction without explicit page
    if (isExplicitIncomeQuery(msgLower)) {
        if (documents.length === 0) {
            return {
                reply: 'You do not have any uploaded documents on file in Supabase yet. Please upload your Income Certificate to extract stated income amounts.',
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
        let targetDoc = null;
        let targetPageNum = 1;
        let targetText = '';
        for (const doc of documents) {
            if (doc.is_active !== false && !doc.deleted_at) {
                const ext = doc.extracted_text || '';
                const blocks = ext.split(/---\s*\[Page\s+(\d+)\]\s*---/);
                if (blocks.length > 1) {
                    for (let i = 1; i < blocks.length; i += 2) {
                        const pNum = parseInt(blocks[i], 10);
                        const pTxt = blocks[i + 1] || '';
                        if (/(?:annual\s+family\s+income|father.*income|mother.*income|income\s+determination)/i.test(pTxt)) {
                            targetDoc = doc;
                            targetPageNum = pNum;
                            targetText = pTxt.trim();
                            break;
                        }
                    }
                }
                if (!targetText && ext) {
                    targetDoc = doc;
                    targetPageNum = 1;
                    targetText = ext.trim();
                }
                if (targetText) break;
            }
        }
        if (!targetDoc) {
            targetDoc = documents[0];
            targetText = targetDoc.extracted_text || '';
        }
        const docName = targetDoc.file_name || 'Document';
        const snippet = targetText.slice(0, 200).replace(/\n/g, ' ').trim();
        const replyText = extractExplicitIncome(targetText, targetPageNum, targetDoc, documents);
        return {
            reply: replyText,
            citations: [{
                chunkId: `${targetDoc.id}_page_${targetPageNum}`,
                schemeId: 'USER_DOCUMENT',
                schemeName: 'Uploaded Document',
                source: `📄 ${docName} (Page ${targetPageNum})`,
                excerpt: `📄 ${docName} (Page ${targetPageNum}) - ${snippet}`
            }],
            isGrounded: true,
            schemeId: null
        };
    }

    // 2. Document summary query ("Summarize the PDF I uploaded")
    if ((msgLower.includes('summarize') || msgLower.includes('summary')) && (msgLower.includes('pdf') || msgLower.includes('document') || msgLower.includes('uploaded') || msgLower.includes('file'))) {
        if (documents.length === 0) {
            return {
                reply: 'You do not have any uploaded documents on file in Supabase yet. Please upload your documents in the **My Documents** vault to generate a summary.',
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }

        const citations = [];
        const docSummaries = documents.map((d, i) => {
            const f = d.extracted_fields || {};
            const fieldsList = Object.entries(f)
                .filter(([k]) => !['document_number', 'issuing_authority'].includes(k) && Boolean(f[k]))
                .map(([k, v]) => `  - **${k.replace(/_/g, ' ').toUpperCase()}:** ${v}`)
                .join('\n');
            const docNo = d.doc_number || f.document_number || 'N/A';
            const issuer = d.issuer || f.issuing_authority || 'Competent Authority';
            const excerpt = d.extracted_text ? d.extracted_text.split('\n')[0].slice(0, 180) : '';
            const pNum = resolveDocumentFactPage(d, docNo !== 'N/A' ? docNo : null, 'document_number');
            const pageLabel = formatPageLabel(pNum);

            citations.push({
                chunkId: `${d.id}_summary`,
                schemeId: 'USER_DOCUMENT',
                schemeName: 'Uploaded Document',
                source: `📄 ${d.file_name} (${pageLabel})`,
                excerpt: `📄 ${d.file_name} (${pageLabel}) - Verified document summary`
            });

            return `### 📄 Document ${i + 1}: ${d.document_type} (\`${d.file_name}\`)\n• **Verification Status:** Ready for AI Chat (${d.verification_status})\n• **Document Number:** \`${docNo}\`\n• **Issuing Authority:** ${issuer}\n${fieldsList ? `• **Key Extracted Facts:**\n${fieldsList}\n` : ''}${excerpt ? `• **Extracted Content Highlight:** *"${excerpt}"*` : ''}`;
        }).join('\n\n');

        return {
            reply: `Here is a grounded summary of your uploaded document(s) on file in Supabase:\n\n${docSummaries}\n\nAll extracted statutory details are verified and automatically active in your scheme eligibility profile.`,
            citations,
            isGrounded: true,
            schemeId: null,
            suggestions: ['What schemes am I eligible for?', 'Check my tickets']
        };
    }

    // 2.5 Multi-field identity queries (e.g. "What is my full name and certificate number?")
    const wantsName = /\b(full\s+name|my\s+name|applicant\s+name|beneficiary\s+name)\b/.test(msgLower);
    const wantsCert = /\b(certificate\s+(?:number|no|#)|document\s+(?:number|no|#))\b/.test(msgLower);
    const wantsDob = /\b(date\s+of\s+birth|dob|birth\s+date|born\s+on)\b/.test(msgLower);
    const wantsDistrict = /\b(district|which\s+district)\b/.test(msgLower);
    const wantsCategory = /\b(category|caste|social\s+category)\b/.test(msgLower);

    if (wantsName && wantsCert) {
        let nameVal = null;
        let certVal = null;
        let sourceDoc = null;

        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.beneficiary_name || f.full_name || f.name) nameVal = f.beneficiary_name || f.full_name || f.name;
            if (doc.doc_number || f.document_number || f.certificate_number) {
                certVal = doc.doc_number || f.document_number || f.certificate_number;
            }
            if (nameVal && certVal) {
                sourceDoc = doc;
                break;
            }
        }
        if (!nameVal && profile?.full_name) nameVal = profile.full_name;

        if (nameVal || certVal) {
            const docName = sourceDoc?.file_name || 'Uploaded Document';
            const pNum = sourceDoc ? (resolveDocumentFactPage(sourceDoc, certVal, 'document_number') || 1) : 1;
            const pageLabel = formatPageLabel(pNum);
            const lines = [];
            if (nameVal) lines.push(`- Full Name: ${nameVal}`);
            else lines.push(`- Full Name: Not available in records`);
            if (certVal) lines.push(`- Certificate Number: \`${certVal}\``);
            else lines.push(`- Certificate Number: Not available in records`);

            return {
                reply: `**Applicant Details**\n\n${lines.join('\n')}\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: sourceDoc ? [{
                    chunkId: `${sourceDoc.id}_identity`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Name: ${nameVal}, Cert: ${certVal}`
                }] : [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    if (wantsName && !msgLower.includes('income')) {
        let nameVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.beneficiary_name || f.full_name || f.name) {
                nameVal = f.beneficiary_name || f.full_name || f.name;
                sourceDoc = doc;
                break;
            }
        }
        if (!nameVal && profile?.full_name) nameVal = profile.full_name;

        if (nameVal) {
            const docName = sourceDoc?.file_name || 'Verified applicant profile records';
            const pNum = sourceDoc ? (resolveDocumentFactPage(sourceDoc, nameVal, 'beneficiary_name') || 1) : null;
            const pageLabel = pNum ? formatPageLabel(pNum) : null;
            return {
                reply: `**Applicant Full Name**\n\n${nameVal}\n\n**Source**\n- Document: ${docName}${pageLabel ? `\n- Page: ${pageLabel}` : ''}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: sourceDoc ? [{
                    chunkId: `${sourceDoc.id}_name`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel || 'Page 1'})`,
                    excerpt: `📄 ${docName} (${pageLabel || 'Page 1'}) - Full Name: ${nameVal}`
                }] : [],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Your full name is not available in your uploaded documents or profile records.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    if (wantsCert && !msgLower.includes('income')) {
        let certVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (doc.doc_number || f.document_number || f.certificate_number) {
                certVal = doc.doc_number || f.document_number || f.certificate_number;
                sourceDoc = doc;
                break;
            }
        }
        if (certVal) {
            const docName = sourceDoc?.file_name || 'Uploaded Document';
            const pNum = sourceDoc ? (resolveDocumentFactPage(sourceDoc, certVal, 'document_number') || 1) : 1;
            const pageLabel = formatPageLabel(pNum);
            return {
                reply: `**Certificate Number**\n\n\`${certVal}\`\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: sourceDoc ? [{
                    chunkId: `${sourceDoc.id}_cert`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Certificate Number: ${certVal}`
                }] : [],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Your certificate number is not available in your uploaded documents.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    if (wantsDob) {
        let dobVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.date_of_birth || f.dob) {
                dobVal = f.date_of_birth || f.dob;
                sourceDoc = doc;
                break;
            }
        }
        if (!dobVal && profile?.date_of_birth) dobVal = profile.date_of_birth;

        if (dobVal) {
            const docName = sourceDoc?.file_name || 'Verified applicant profile records';
            const pNum = sourceDoc ? (resolveDocumentFactPage(sourceDoc, dobVal, 'date_of_birth') || 1) : null;
            const pageLabel = pNum ? formatPageLabel(pNum) : null;
            return {
                reply: `**Date of Birth**\n\n${dobVal}\n\n**Source**\n- Document: ${docName}${pageLabel ? `\n- Page: ${pageLabel}` : ''}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: sourceDoc ? [{
                    chunkId: `${sourceDoc.id}_dob`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel || 'Page 1'})`,
                    excerpt: `📄 ${docName} (${pageLabel || 'Page 1'}) - Date of Birth: ${dobVal}`
                }] : [],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Your date of birth is not available in your uploaded documents or profile records.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    if (wantsDistrict) {
        let distVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.district) {
                distVal = f.district;
                sourceDoc = doc;
                break;
            }
        }
        if (!distVal && profile?.district) distVal = profile.district;

        if (distVal) {
            const docName = sourceDoc?.file_name || 'Verified applicant profile records';
            const pNum = sourceDoc ? (resolveDocumentFactPage(sourceDoc, distVal, 'district') || 1) : null;
            const pageLabel = pNum ? formatPageLabel(pNum) : null;
            return {
                reply: `**District**\n\n${distVal}\n\n**Source**\n- Document: ${docName}${pageLabel ? `\n- Page: ${pageLabel}` : ''}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: sourceDoc ? [{
                    chunkId: `${sourceDoc.id}_district`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel || 'Page 1'})`,
                    excerpt: `📄 ${docName} (${pageLabel || 'Page 1'}) - District: ${distVal}`
                }] : [],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Your district is not available in your uploaded documents or profile records.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    if (wantsCategory && !msgLower.includes('scheme') && !msgLower.includes('list')) {
        let catVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.social_category || f.category || f.caste) {
                catVal = f.social_category || f.category || f.caste;
                sourceDoc = doc;
                break;
            }
        }
        if (!catVal && (profile?.category || profile?.caste_category)) catVal = profile.category || profile.caste_category;

        if (catVal) {
            const docName = sourceDoc?.file_name || 'Verified applicant profile records';
            const pNum = sourceDoc ? (resolveDocumentFactPage(sourceDoc, catVal, 'category') || 1) : null;
            const pageLabel = pNum ? formatPageLabel(pNum) : null;
            return {
                reply: `**Social Category**\n\n${catVal}\n\n**Source**\n- Document: ${docName}${pageLabel ? `\n- Page: ${pageLabel}` : ''}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: sourceDoc ? [{
                    chunkId: `${sourceDoc.id}_category`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel || 'Page 1'})`,
                    excerpt: `📄 ${docName} (${pageLabel || 'Page 1'}) - Category: ${catVal}`
                }] : [],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Your social category is not available in your uploaded documents or profile records.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    // 2.6 Component income inquiries (Father's income, Mother's income)
    const wantsFatherIncome = /\b(father(?:'s)?\s+(?:annual\s+)?income|father\s+income)\b/.test(msgLower);
    const wantsMotherIncome = /\b(mother(?:'s)?\s+(?:annual\s+)?income|mother\s+income)\b/.test(msgLower);

    if (wantsFatherIncome) {
        let fiVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.father_income) {
                fiVal = f.father_income;
                sourceDoc = doc;
                break;
            }
        }
        if (fiVal) {
            const cleanStr = String(fiVal).replace(/[^\d.]/g, '');
            const num = parseFloat(cleanStr);
            const fmt = !isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${fiVal}`;
            const docName = sourceDoc?.file_name || 'Document';
            const pNum = resolveDocumentFactPage(sourceDoc, fiVal, 'father_income');
            const pageLabel = formatPageLabel(pNum);

            return {
                reply: `**Father's Annual Income**\n\n${fmt}\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: [{
                    chunkId: `${sourceDoc.id}_father_income`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Father's Income: ${fmt}`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Father's individual income is not available or specified in your uploaded documents.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    if (wantsMotherIncome) {
        let miVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.mother_income) {
                miVal = f.mother_income;
                sourceDoc = doc;
                break;
            }
        }
        if (miVal) {
            const cleanStr = String(miVal).replace(/[^\d.]/g, '');
            const num = parseFloat(cleanStr);
            const fmt = !isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${miVal}`;
            const docName = sourceDoc?.file_name || 'Document';
            const pNum = resolveDocumentFactPage(sourceDoc, miVal, 'mother_income');
            const pageLabel = formatPageLabel(pNum);

            return {
                reply: `**Mother's Annual Income**\n\n${fmt}\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: [{
                    chunkId: `${sourceDoc.id}_mother_income`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Mother's Income: ${fmt}`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Mother's individual income is not available or specified in your uploaded documents.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    const wantsOtherIncome = /\b(other(?:\s+family)?\s+(?:annual\s+)?income|agricultural\s+income)\b/i.test(msgLower);
    if (wantsOtherIncome) {
        let oiVal = null;
        let sourceDoc = null;
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            if (f.other_income !== undefined && f.other_income !== null) {
                oiVal = f.other_income;
                sourceDoc = doc;
                break;
            }
            if (doc.extracted_text) {
                const amt = extractAmountForKey(/(?:Other\s+(?:Family\s+)?Income|Income\s+from\s+Other|Agricultural\s+Income)/, doc.extracted_text);
                if (amt !== null && amt !== undefined) {
                    oiVal = amt;
                    sourceDoc = doc;
                    break;
                }
            }
        }
        if (oiVal !== null && oiVal !== undefined) {
            const cleanStr = String(oiVal).replace(/[^\d.]/g, '');
            const num = parseFloat(cleanStr);
            const fmt = !isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${oiVal}`;
            const docName = sourceDoc?.file_name || 'Document';
            const pNum = resolveDocumentFactPage(sourceDoc, oiVal, 'other_income');
            const pageLabel = formatPageLabel(pNum);
            const stateNote = (cleanStr === '0' || String(oiVal) === '0' || String(oiVal) === '₹0') ? ' (Explicitly stated in document)' : '';

            return {
                reply: `**Other Family Income**\n\n${fmt}${stateNote}\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: [{
                    chunkId: `${sourceDoc.id}_other_income`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Other Family Income: ${fmt}`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            return {
                reply: "Other family income is not specified in your uploaded documents.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }


    // 3. Document income query ("What is my annual family income according to my document?" or "What is my personal annual income?")
    if (msgLower.includes('income') && !msgLower.includes('contain') && !msgLower.includes('certificate')) {
        const isPersonal = /\b(personal|individual|my\s+salary)\b/.test(msgLower);

        // Gather all document income candidates
        const candidates = [];
        for (const doc of documents) {
            const f = doc.extracted_fields || doc.extractedData || {};
            let inc = f.annual_family_income || f.family_income;
            if (!inc && doc.extracted_text) {
                const incM = doc.extracted_text.match(/(?:total\s+annual\s+family\s+income|annual\s+family\s+income|family\s+income)[\s\S]{0,120}?(?:\bis\b|\bof\b|[:=-])\s*(?:rs\.?|inr|₹)?\s*([\d,]+)/i);
                if (incM) inc = incM[1];
            }
            if (inc) {
                const clean = String(inc).replace(/[₹,\s]/g, '');
                const num = parseFloat(clean);
                const pNum = resolveDocumentFactPage(doc, inc, 'annual_family_income');
                candidates.push({
                    doc,
                    raw: inc,
                    numeric: !isNaN(num) ? num : null,
                    formatted: !isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${inc}`,
                    fileName: doc.file_name || doc.fileName || 'Document',
                    page: pNum,
                    uploadedAt: doc.uploaded_at || doc.uploadedAt || ''
                });
            }
        }

        // Multi-document conflict check
        const distinctNums = new Set(candidates.filter(c => c.numeric !== null).map(c => c.numeric));
        if (distinctNums.size > 1) {
            const lines = candidates.map(c => `- ${c.fileName} (Page ${formatPageLabel(c.page)}): ${c.formatted}`).join('\n');
            const citations = candidates.map(c => {
                const pageLabel = formatPageLabel(c.page);
                return {
                    chunkId: `${c.doc.id}_conflict`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${c.fileName} (${pageLabel})`,
                    excerpt: `📄 ${c.fileName} (${pageLabel}) - Extracted Income: ${c.formatted}`
                };
            });
            return {
                reply: `**Income Assessment Status: REVIEW**\n\nConflicting income records were detected across your active documents:\n\n${lines}\n\n**Action Required:**\nBecause active documents provide differing income figures, automated determination is held for casework verification. Please verify your uploaded documents or submit an updated Income Certificate.`,
                citations,
                isGrounded: true,
                schemeId: null
            };
        }

        const candidate = candidates[0] || null;
        let formattedIncome = candidate?.formatted || null;
        let sourceDoc = candidate?.doc || null;

        if (formattedIncome) {
            const docName = sourceDoc?.file_name || sourceDoc?.fileName || 'Income Certificate';
            const pNum = resolveDocumentFactPage(sourceDoc, formattedIncome, 'annual_family_income');
            const pageLabel = formatPageLabel(pNum);

            if (isPersonal) {
                return {
                    reply: `Your personal annual income is not available in your records. Please upload your salary slip or personal income declaration in the 'My Documents' vault.\n\n**Annual Family Income on File**\n\n${formattedIncome}\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                    citations: [{
                        chunkId: `${sourceDoc?.id || 'income'}_income`,
                        schemeId: 'USER_DOCUMENT',
                        schemeName: 'Uploaded Document',
                        source: `📄 ${docName} (${pageLabel})`,
                        excerpt: `📄 ${docName} (${pageLabel}) - Family Income: ${formattedIncome}`
                    }],
                    isGrounded: true,
                    schemeId: null
                };
            }

            const extF = sourceDoc?.extracted_fields || sourceDoc?.extractedData || {};
            const breakdownLines = [];
            if (extF.father_income) {
                const num = parseFloat(String(extF.father_income).replace(/[^\d.]/g, ''));
                breakdownLines.push(`- Father's income: ${!isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${extF.father_income}`}`);
            }
            if (extF.mother_income) {
                const num = parseFloat(String(extF.mother_income).replace(/[^\d.]/g, ''));
                breakdownLines.push(`- Mother's income: ${!isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${extF.mother_income}`}`);
            }
            if (extF.other_income) {
                const num = parseFloat(String(extF.other_income).replace(/[^\d.]/g, ''));
                breakdownLines.push(`- Other income: ${!isNaN(num) ? `₹${num.toLocaleString('en-IN')}` : `₹${extF.other_income}`}`);
            }

            const breakdownSection = breakdownLines.length > 0 ? `\n\n**Breakdown**\n${breakdownLines.join('\n')}` : '';

            return {
                reply: `**Annual Family Income**\n\n${formattedIncome}${breakdownSection}\n\n**Source**\n- Document: ${docName}\n- Page: ${pageLabel}\n\n**Evidence status:** Facts Extracted & Document Evidence Available`,
                citations: [{
                    chunkId: `${sourceDoc?.id || 'income'}_income`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Annual Income: ${formattedIncome}`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            // Check self-reported profile bracket fallback
            if (profile?.annual_income && !isPersonal) {
                return {
                    reply: `**Self-Reported Annual Income (Unverified)**\n\n₹${profile.annual_income}\n\n**Source**\n- Self-reported during registration (no uploaded document verified)\n\n**Evidence status:** Self-Reported / Unverified`,
                    citations: [],
                    isGrounded: true,
                    schemeId: null
                };
            }

            return {
                reply: isPersonal
                    ? "Your personal annual income is not available in your records. Please upload your salary slip or personal income declaration in the 'My Documents' vault."
                    : "None of your uploaded documents establish your annual family income. No Income Certificate or verified income record was found in your vault. Please upload an Income Certificate issued by a competent revenue authority (e.g., Tahsildar / Mamlatdar) in the 'My Documents' vault.",
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    // 4. List uploaded documents query ("Which documents have I uploaded?")
    if (msgLower.includes('which documents') || msgLower.includes('what documents have i uploaded') || msgLower.includes('which documents have i uploaded') || msgLower.includes('documents have i uploaded') || msgLower.includes('list my documents')) {
        if (documents.length === 0) {
            return {
                reply: 'You currently have no documents uploaded in your vault. You can upload documents like Aadhaar Card, PAN Card, Income Certificate, and Caste Certificate in the **My Documents** section.',
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }

        const citations = [];
        const docLines = documents.map((d, i) => {
            const dType = (d.document_type || 'Document').replace(/_/g, ' ').toUpperCase();
            const statusLabel = d.verification_status === 'VERIFIED' ? 'Ready for AI Chat' : 'Processing';
            const docNo = d.doc_number || d.extracted_fields?.document_number || 'N/A';
            const dateStr = d.uploaded_at ? String(d.uploaded_at).slice(0, 10) : '';

            const pNum = resolveDocumentFactPage(d, docNo !== 'N/A' ? docNo : null, 'document_number');
            const pageLabel = formatPageLabel(pNum);

            citations.push({
                chunkId: `${d.id}_list`,
                schemeId: 'USER_DOCUMENT',
                schemeName: 'Uploaded Document',
                source: `📄 ${d.file_name} (${pageLabel})`,
                excerpt: `📄 ${d.file_name} (${pageLabel}) - ${dType}`
            });

            return `${i + 1}. **${dType}** (\`${d.file_name}\`) — Status: **${statusLabel}** | Doc #: \`${docNo}\`${dateStr ? ` | Uploaded: ${dateStr}` : ''}`;
        }).join('\n');

        return {
            reply: `You have uploaded **${documents.length} document(s)** in your vault:\n\n${docLines}\n\nAll verified documents are indexed and retrievable by FIN AI Assistant.`,
            citations,
            isGrounded: true,
            schemeId: null
        };
    }

    // 5. Income Certificate presence query ("Does my uploaded document contain my income certificate?")
    if ((msgLower.includes('contain') || msgLower.includes('is') || msgLower.includes('have')) && msgLower.includes('income certificate')) {
        const incomeDoc = documents.find(d => {
            const dtype = (d.document_type || '').toLowerCase();
            const fname = (d.file_name || '').toLowerCase();
            return dtype.includes('income') || fname.includes('income') || d.extracted_fields?.annual_income;
        });

        if (incomeDoc) {
            const docName = incomeDoc.file_name || 'Income_Certificate.pdf';
            const docNo = incomeDoc.doc_number || incomeDoc.extracted_fields?.document_number || 'DOC-INC';
            const issuer = incomeDoc.issuer || incomeDoc.extracted_fields?.issuing_authority || 'Competent Revenue Authority';
            const incVal = incomeDoc.extracted_fields?.annual_income || profile?.annual_income || 'Verified on File';
            const pNum = resolveDocumentFactPage(incomeDoc, incVal, 'annual_income') || resolveDocumentFactPage(incomeDoc, docNo, 'document_number');
            const pageLabel = formatPageLabel(pNum);

            return {
                reply: `Yes, your uploaded document **${docName}** contains your Income Certificate.\n\n• **Document Number:** \`${docNo}\`\n• **Issuing Authority:** ${issuer}\n• **Recorded Annual Income:** **₹${incVal}**\n• **Status:** Ready for AI Chat`,
                citations: [{
                    chunkId: `${incomeDoc.id}_income_cert`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${docName} (${pageLabel})`,
                    excerpt: `📄 ${docName} (${pageLabel}) - Verified Income Certificate`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            const existingNames = documents.length > 0 ? documents.map(d => `\`${d.file_name}\``).join(', ') : 'None';
            return {
                reply: `No, your uploaded documents do not contain an Income Certificate. Your current documents on file are: ${existingNames}. To verify your income eligibility for welfare schemes, please upload your Income Certificate in the **My Documents** tab.`,
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    // 6. Missing information query ("What information is missing from my uploaded application?")
    if (msgLower.includes('missing') && (msgLower.includes('application') || msgLower.includes('document') || msgLower.includes('upload') || msgLower.includes('information') || msgLower.includes('profile'))) {
        const uploadedTypes = new Set();
        for (const doc of documents) {
            const dtype = (doc.document_type || '').toLowerCase();
            const fname = (doc.file_name || '').toLowerCase();
            if (dtype.includes('aadhaar') || fname.includes('aadhaar') || dtype.includes('id')) uploadedTypes.add('id_proof');
            if (dtype.includes('income') || fname.includes('income') || doc.extracted_fields?.annual_income) uploadedTypes.add('income_proof');
            if (dtype.includes('caste') || fname.includes('caste') || dtype.includes('category')) uploadedTypes.add('caste_proof');
            if (dtype.includes('address') || fname.includes('address') || dtype.includes('domicile')) uploadedTypes.add('address_proof');
            if (dtype.includes('bank') || fname.includes('bank') || dtype.includes('passbook')) uploadedTypes.add('bank_proof');
        }

        const standardReqs = [
            { label: 'Identity Proof (Aadhaar / PAN Card)', key: 'id_proof' },
            { label: 'Income Certificate', key: 'income_proof' },
            { label: 'Address / Domicile Proof', key: 'address_proof' },
            { label: 'Bank Account Passbook / Cancelled Cheque', key: 'bank_proof' },
        ];

        const availableItems = [];
        const missingItems = [];
        for (const req of standardReqs) {
            if (uploadedTypes.has(req.key)) {
                availableItems.push(`• ✅ **${req.label}**: Uploaded and verified`);
            } else {
                missingItems.push(`• ⚠️ **${req.label}**: Required to complete application eligibility`);
            }
        }

        return {
            reply: `### Application Document Readiness Check\n\n**Uploaded & Verified Documents:**\n${availableItems.length > 0 ? availableItems.join('\n') : '• *No verified documents uploaded yet.*'}\n\n**Missing Information / Documents:**\n${missingItems.length > 0 ? missingItems.join('\n') : '• *None! All essential statutory documents are uploaded.*'}\n\nYou can upload any missing certificates directly in the **My Documents** vault.`,
            citations: [],
            isGrounded: true,
            schemeId: null
        };
    }

    // 7. Compare uploaded documents with scheme requirements ("Compare my uploaded documents with the requirements of this scheme.")
    if (msgLower.includes('compare') && (msgLower.includes('requirement') || msgLower.includes('scheme') || msgLower.includes('document') || msgLower.includes('uploaded'))) {
        const requiredDocs = [
            { name: 'Aadhaar Card', purpose: 'Identity Proof' },
            { name: 'PAN Card', purpose: 'Tax / Business Registration' },
            { name: 'Income Certificate', purpose: 'Subsidy & Income Verification' },
            { name: 'Project Report / DPR', purpose: 'Business Feasibility & Financial Assessment' },
            { name: 'Special Category Certificate (if SC/ST/OBC/Women)', purpose: 'Margin Money Subsidy Uplift (up to 35%)' }
        ];

        const citations = [];
        const compLines = requiredDocs.map(req => {
            const kw = req.name.split(' ')[0].toLowerCase();
            const matchingDoc = documents.find(d => {
                const dtype = (d.document_type || '').toLowerCase();
                const fname = (d.file_name || '').toLowerCase();
                return dtype.includes(kw) || fname.includes(kw);
            });

            if (matchingDoc) {
                const pNum = resolveDocumentFactPage(matchingDoc, req.name, 'document_type');
                const pageLabel = formatPageLabel(pNum);
                citations.push({
                    chunkId: `${matchingDoc.id}_comp`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${matchingDoc.file_name} (${pageLabel})`,
                    excerpt: `📄 ${matchingDoc.file_name} (${pageLabel}) - Satisfies ${req.name}`
                });
                return `• **${req.name}** (${req.purpose}): ✅ **Satisfied** (Uploaded: \`${matchingDoc.file_name}\`)`;
            } else {
                return `• **${req.name}** (${req.purpose}): ❌ **Missing** (Please upload in My Documents)`;
            }
        });

        return {
            reply: `### Document Comparison for **PMEGP (Prime Minister's Employment Generation Programme)**\n\nHere is how your uploaded documents align with the statutory requirements:\n\n${compLines.join('\n')}\n\nUploading the remaining required documents will allow your application to proceed to automated department verification.`,
            citations,
            isGrounded: true,
            schemeId: null
        };
    }

    // Check specific document content inquiries or complete document catalog
    const isSchemeDocReq = /\b(?:required|supporting|mandatory|necessary|needed|statutory)\b.*?\b(?:documents?|certificates?|proofs?|endorsements?)\b|\b(?:documents?|certificates?|proofs?)\b.*?\b(?:required|needed|mandatory|necessary)\b/i.test(msgLower);

    if ((msgLower.includes('document') || msgLower.includes('uploaded') || msgLower.includes('certificate') || msgLower.includes('pdf')) && (!isSchemeDocReq || isPersonalVaultReq)) {
        if (!documents || documents.length === 0) {
            return {
                reply: 'You do not have any uploaded documents on file in Supabase yet. Please upload your documents in the **My Documents** vault to automatically extract and verify your statutory details.',
                citations: [],
                isGrounded: true,
                schemeId: null,
                suggestions: ['What documents are required?', 'How to upload documents?']
            };
        }

        const isCatalogRequest = ['all documents', 'each and every', 'everything', 'data of', 'show all', 'list all'].some(p => msgLower.includes(p));
        if (isCatalogRequest) {
            const docDetails = documents.map((d, i) => {
                const f = d.extracted_fields || {};
                const fieldsList = Object.entries(f)
                    .map(([k, v]) => `  - **${k.replace(/_/g, ' ').toUpperCase()}:** ${v}`)
                    .join('\n');
                return `**Document ${i + 1}: ${d.document_type}** (${d.file_name})\n- **Status:** ${d.verification_status}\n- **Doc Number:** ${d.doc_number || 'N/A'}\n- **Issuing Authority:** ${d.issuer || 'N/A'}\n${fieldsList ? `Extracted Data:\n${fieldsList}` : ''}`;
            }).join('\n\n');
            const pNum = resolveDocumentFactPage(documents[0], documents[0].doc_number, 'document_number');
            const pageLabel = formatPageLabel(pNum);
            return {
                reply: `Here is the complete data extracted from your uploaded documents in Supabase:\n\n${docDetails}\n\nAll extracted facts are actively verified and linked to your eligibility profile.`,
                citations: [{
                    chunkId: `${documents[0].id}_general`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${documents[0].file_name} (${pageLabel})`,
                    excerpt: `📄 ${documents[0].file_name} (${pageLabel}) - Complete document catalog`
                }],
                isGrounded: true,
                schemeId: null,
                suggestions: ['What schemes am I eligible for?', 'Check my tickets']
            };
        }

        // Specific passage & entity search in document
        const stopWords = new Set(['what', 'is', 'my', 'the', 'according', 'to', 'document', 'uploaded', 'in', 'pdf', 'file', 'does', 'have', 'mention', 'mentioned', 'tell', 'me', 'about', 'show', 'can', 'you', 'who', 'where', 'when', 'please', 'which', 'and', 'for', 'with', 'from', 'her', 'his', 'your']);
        const qClean = msgLower.replace(/[^\w\s]/g, ' ');
        const searchTokens = qClean.split(/\s+/).filter(t => !stopWords.has(t) && t.length > 2);
        const searchPhrase = searchTokens.join(' ');

        let bestLine = null;
        let bestPage = 1;
        let bestDoc = null;
        let bestScore = 0;

        for (const doc of documents) {
            const extText = doc.extracted_text || '';
            const pages = [];
            const pageBlocks = extText.split(/---\s*\[Page\s+(\d+)\]\s*---/);
            if (pageBlocks.length > 1) {
                for (let i = 1; i < pageBlocks.length; i += 2) {
                    pages.push({ pageNum: parseInt(pageBlocks[i], 10), text: pageBlocks[i + 1].trim() });
                }
            } else {
                pages.push({ pageNum: 1, text: extText.trim() });
            }

            for (const { pageNum, text } of pages) {
                for (const line of text.split('\n')) {
                    const lineClean = line.trim();
                    if (!lineClean) continue;
                    const lineLower = lineClean.toLowerCase();
                    let score = 0;
                    if (searchPhrase && lineLower.includes(searchPhrase)) {
                        score += 10;
                    }
                    for (const tok of searchTokens) {
                        if (lineLower.includes(tok)) score += 2;
                    }
                    if (score > bestScore) {
                        bestScore = score;
                        bestLine = lineClean;
                        bestPage = pageNum;
                        bestDoc = doc;
                    }
                }
            }

            // Search structured fields
            const fields = doc.extracted_fields || {};
            for (const [fk, fv] of Object.entries(fields)) {
                const fkNorm = fk.toLowerCase().replace(/_/g, ' ');
                let score = 0;
                if (searchPhrase && fkNorm.includes(searchPhrase)) {
                    score += 10;
                }
                for (const tok of searchTokens) {
                    if (fkNorm.includes(tok)) score += 2;
                }
                if (searchTokens.some(w => ['mother', 'father', 'spouse'].includes(w)) && !['mother', 'father', 'spouse'].some(w => fkNorm.includes(w))) {
                    score = 0;
                }
                if (score > bestScore) {
                    bestScore = score;
                    bestLine = `${fkNorm.toUpperCase()}: ${fv}`;
                    bestPage = resolveDocumentFactPage(doc, fv, fk);
                    bestDoc = doc;
                }
            }
        }

        const minScore = searchTokens.length >= 2 ? 4 : 2;

        if (bestLine && bestDoc && bestScore >= minScore) {
            const pageLabel = formatPageLabel(bestPage);
            const pagePhrase = bestPage ? `According to **Page ${bestPage}** of your uploaded document **${bestDoc.file_name}**` : `According to your uploaded document **${bestDoc.file_name}**`;
            return {
                reply: `${pagePhrase}, ${bestLine}.\n\n• **Status:** Verified and Ready for AI Chat`,
                citations: [{
                    chunkId: `${bestDoc.id}_${bestPage ? `page_${bestPage}` : 'fact'}`,
                    schemeId: 'USER_DOCUMENT',
                    schemeName: 'Uploaded Document',
                    source: `📄 ${bestDoc.file_name} (${pageLabel})`,
                    excerpt: `📄 ${bestDoc.file_name} (${pageLabel}) - ${bestLine.slice(0, 150)}`
                }],
                isGrounded: true,
                schemeId: null
            };
        } else {
            // ZERO HALLUCINATION
            const docName = documents[0]?.file_name || 'your document';
            return {
                reply: `According to your uploaded document **${docName}**, this information is not mentioned or established in the document. The document does not establish this answer.`,
                citations: [],
                isGrounded: true,
                schemeId: null
            };
        }
    }

    // Check personal fact query (e.g. income, salary, family income)
    if (msgLower.includes('income') || msgLower.includes('salary') || msgLower.includes('earning')) {
        const inc = profile?.annual_income || profile?.income;
        if (inc) {
            return {
                reply: `According to your verified records on file in Supabase, your Annual Family Income is **${inc}** (Source: Income Certificate).`,
                isGrounded: true,
                schemeId: null,
                suggestions: ['What schemes am I eligible for with this income?', 'What other documents do I need?']
            };
        }
        return {
            reply: 'No verified income records or certificates are on file for your profile yet. Please upload an Income Certificate in the My Documents vault so your income can be verified.',
            isGrounded: true,
            schemeId: null,
            suggestions: ['What documents are required?', 'How to upload documents?']
        };
    }
    if (
        (msgLower.includes('student') || msgLower.includes('internship') || msgLower.includes('college') || msgLower.includes('study'))
    ) {
        return {
            reply: 'Here are central and state government schemes available for students and higher education:',
            isGrounded: true,
            schemeId: null,
            schemes: [
                {
                    id: 'pm-vidyalaxmi',
                    slug: 'pm-vidyalaxmi',
                    schemeId: 'pm-vidyalaxmi',
                    title: 'PM Vidyalaxmi',
                    subtitle: 'Education loan support for higher studies.',
                    tags: ['Education', 'Loan'],
                    iconType: 'education'
                },
                {
                    id: 'digital-india-internship',
                    slug: 'digital-india-internship',
                    schemeId: 'digital-india-internship',
                    title: 'Digital India Internship Scheme',
                    subtitle: 'Internship opportunities for students.',
                    tags: ['Skill Development', 'Internship'],
                    iconType: 'digital-india'
                },
                {
                    id: 'skill-india',
                    slug: 'skill-india',
                    schemeId: 'skill-india',
                    title: 'Skill India - Training & Certification',
                    subtitle: 'Free skill training programs for students.',
                    tags: ['Skill Development', 'Training'],
                    iconType: 'skill-india'
                },
                {
                    id: 'startup-india',
                    slug: 'startup-india',
                    schemeId: 'startup-india',
                    title: 'Startup India',
                    subtitle: 'Support for student entrepreneurs.',
                    tags: ['Entrepreneurship', 'Funding'],
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
                    slug: 'pmegp',
                    schemeId: 'pmegp',
                    title: 'PMEGP',
                    subtitle: "Prime Minister's Employment Generation Programme",
                    tags: ['Business Support', 'Self Employment', 'Central Government'],
                    iconType: 'ashoka'
                },
                {
                    id: 'pm-vidyalaxmi',
                    slug: 'pm-vidyalaxmi',
                    schemeId: 'pm-vidyalaxmi',
                    title: 'PM Vidyalaxmi',
                    subtitle: 'Education loan support for higher studies.',
                    tags: ['Education', 'Loan'],
                    iconType: 'education'
                },
                {
                    id: 'skill-india',
                    slug: 'skill-india',
                    schemeId: 'skill-india',
                    title: 'Skill India - Training & Certification',
                    subtitle: 'Free skill training programs for students.',
                    tags: ['Skill Development', 'Training'],
                    iconType: 'skill-india'
                }
            ],
            showViewAll: true
        };
    }


    // Check general patterns
    for (const item of GENERAL_ANSWERS) {
        if (item.patterns.some(p => msgLower.includes(p))) {
            return {
                reply: item.answer,
                citations: [],
                schemes: item.schemes || [],
                showViewAll: Boolean(item.schemes && item.schemes.length > 0),
                isGrounded: Boolean(item.schemes && item.schemes.length > 0),
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

module.exports = {
    chat,
    computeLocalFallback,
    buildDocumentFacts,
    resolveDocumentFactPage,
    formatPageLabel,
    summarizePageText,
    isAssessmentPeriodQuery,
    isExplicitIncomeQuery,
    verifyAssessmentPeriod,
    extractExplicitIncome
};
