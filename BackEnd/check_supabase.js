const { supabaseAdmin } = require('./src/config/supabaseConfig');

async function inspect() {
  console.log('--- Inspecting Supabase Tables ---');
  const tables = ['schemes', 'scheme', 'government_schemes', 'scheme_details', 'profiles', 'documents', 'user_documents', 'user_applications'];
  
  for (const table of tables) {
    const { data, error, count } = await supabaseAdmin
      .from(table)
      .select('*', { count: 'exact' })
      .limit(5);
      
    if (error) {
      console.log(`[TABLE] ${table}: ERROR - ${error.message} (${error.code})`);
    } else {
      console.log(`[TABLE] ${table}: EXISTS, total rows = ${count}, fetched sample = ${data.length}`);
      if (data.length > 0) {
        console.log(`  Sample keys: ${Object.keys(data[0]).join(', ')}`);
        console.log(`  Sample row 1:`, JSON.stringify(data[0], null, 2));
      }
    }
  }

  // Let's also check table columns for 'schemes' by inserting a dummy or checking postgrest schema
  const { data: cols, error: colErr } = await supabaseAdmin.from('schemes').select('*').limit(1);
  console.log('Schemes query result:', cols, colErr);
}

inspect().catch(console.error);
