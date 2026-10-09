/**
 * seed_schemes.js
 * Seeds the Supabase `schemes` table from Intelligence/data/processed/schemes_canonical.jsonl
 * Maps canonical fields -> DB columns: id, name, short_name, ministry, type, max_benefit,
 *   benefit_summary, eligibility_summary, required_documents, tags, active
 */

const fs = require('fs');
const readline = require('readline');
const path = require('path');
const { supabaseAdmin: sb } = require('../config/supabaseConfig');

const CANONICAL_FILE = path.join(
  __dirname,
  '../../../Intelligence/data/processed/schemes_canonical.jsonl'
);
const BATCH_SIZE = 200;

function mapScheme(raw) {
  const name = (raw.scheme_name || raw.name || '').trim();
  if (!name) return null;

  // Derive a short slug-style ID (<=80 chars) from slug or scheme_name
  const id = (raw.slug || name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')).substring(0, 80);

  const tags = Array.isArray(raw.tags) ? raw.tags.filter(Boolean) : [];
  if (raw.categories) {
    const cats = Array.isArray(raw.categories) ? raw.categories : [raw.categories];
    tags.push(...cats.filter(c => c && !tags.includes(c)));
  }
  if (raw.state && raw.state !== 'All India') tags.push(raw.state);

  // Extract max_benefit from benefits text
  let max_benefit = null;
  const benefitText = raw.benefits || raw.benefit_type || '';
  const match = benefitText.match(/(?:Rs\.?|Rs |INR |₹)\s*([\d,]+)/i);
  if (match) {
    max_benefit = parseInt(match[1].replace(/,/g, ''), 10) || null;
  }

  return {
    id,
    name,
    short_name: (raw.short_title || '').substring(0, 50) || null,
    ministry: (raw.ministry || raw.department || 'Government of India').substring(0, 200),
    type: raw.beneficiary_type || raw.level || 'Individual',
    max_benefit,
    benefit_summary: (raw.benefits || raw.brief_description || '').substring(0, 1000),
    eligibility_summary: (raw.eligibility || '').substring(0, 1000),
    required_documents: (raw.documents_required || '')
      .split(/[;|]+/)
      .map(s => s.trim())
      .filter(Boolean)
      .slice(0, 20),
    tags: tags.slice(0, 20),
    active: true,
  };
}

async function seed() {
  console.log('Reading canonical dataset...');
  const rows = [];
  const seen = new Set();

  const rl = readline.createInterface({ input: fs.createReadStream(CANONICAL_FILE, 'utf8') });
  for await (const line of rl) {
    if (!line.trim()) continue;
    try {
      const raw = JSON.parse(line);
      const mapped = mapScheme(raw);
      if (mapped && !seen.has(mapped.id)) {
        seen.add(mapped.id);
        rows.push(mapped);
      }
    } catch (_) {}
  }

  console.log('Mapped ' + rows.length + ' unique schemes. Upserting in batches of ' + BATCH_SIZE + '...');

  let inserted = 0;
  let errors = 0;
  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE);
    const { error } = await sb.from('schemes').upsert(batch, { onConflict: 'id', ignoreDuplicates: false });
    if (error) {
      console.error('Batch ' + (Math.floor(i / BATCH_SIZE) + 1) + ' error: ' + error.message);
      errors += batch.length;
    } else {
      inserted += batch.length;
    }
    if (Math.floor(i / BATCH_SIZE) % 10 === 0) {
      process.stdout.write('\r  Progress: ' + (i + batch.length) + '/' + rows.length + ' (' + errors + ' errors)');
    }
  }

  console.log('\nDone. Inserted/updated: ' + inserted + ', Errors: ' + errors);

  // Verify
  const { data: check } = await sb.from('schemes').select('id', { count: 'exact' });
  console.log('Final scheme count in DB:', check ? check.length : '?');
}

seed().catch(console.error);
