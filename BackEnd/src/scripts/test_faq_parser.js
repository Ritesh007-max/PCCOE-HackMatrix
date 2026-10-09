const fs = require('fs');
const path = require('path');
const readline = require('readline');

async function loadFaqs() {
    console.time('load_faqs');
    const faqPath = path.resolve(__dirname, '../../../Intelligence/data/raw/schemes_faqs_clean.csv');
    if (!fs.existsSync(faqPath)) {
        console.error('File not found:', faqPath);
        return;
    }

    const content = fs.readFileSync(faqPath, 'utf8');
    const lines = content.split('\n');
    const index = new Map();

    // Parse CSV lines
    // Header: scheme_slug,faq_number,question,answer
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        // Extract scheme_slug
        const c1 = line.indexOf(',');
        if (c1 === -1) continue;
        const slug = line.slice(0, c1).trim();

        // Extract faq_number
        const c2 = line.indexOf(',', c1 + 1);
        if (c2 === -1) continue;
        const faqNum = parseInt(line.slice(c1 + 1, c2).trim(), 10) || (index.get(slug)?.length || 0) + 1;

        // Remainder: question, answer
        const rest = line.slice(c2 + 1);
        let q = '', a = '';
        if (rest.startsWith('"')) {
            const endQ = rest.indexOf('",');
            if (endQ !== -1) {
                q = rest.slice(1, endQ).replace(/""/g, '"');
                a = rest.slice(endQ + 2);
            } else {
                q = rest;
            }
        } else {
            const c3 = rest.indexOf(',');
            if (c3 !== -1) {
                q = rest.slice(0, c3);
                a = rest.slice(c3 + 1);
            } else {
                q = rest;
            }
        }
        if (a.startsWith('"') && a.endsWith('"')) {
            a = a.slice(1, -1).replace(/""/g, '"');
        }

        if (!index.has(slug)) {
            index.set(slug, []);
        }
        index.get(slug).push({
            faq_number: faqNum,
            question: q.trim(),
            answer: a.trim()
        });
    }

    console.timeEnd('load_faqs');
    console.log('Total indexed schemes with FAQs:', index.size);
    console.log('Sample for 108easuk:', index.get('108easuk'));
    console.log('Sample for pmegp:', index.get('pmegp'));
}

loadFaqs().catch(console.error);
