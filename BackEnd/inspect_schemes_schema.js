const { supabaseAdmin } = require('./src/config/supabaseConfig');

async function checkColumns() {
  // Method 1: Try querying RPC or Postgres functions if any exist
  // Method 2: Insert an empty object {} to trigger error message listing valid columns or missing NOT NULL columns!
  const { data, error } = await supabaseAdmin.from('schemes').insert({}).select();
  console.log('Insert empty object result:');
  console.log('Error:', error);
  console.log('Data:', data);

  // Method 3: Try selecting common scheme columns
  const candidateCols = [
    'id', 'scheme_id', 'slug', 'name', 'scheme_name', 'title', 'description',
    'ministry', 'department', 'state', 'category', 'eligibility', 'benefits',
    'documents', 'application_process', 'application_url', 'created_at', 'updated_at'
  ];
  
  for (const col of candidateCols) {
    const { data: cData, error: cErr } = await supabaseAdmin.from('schemes').select(col).limit(1);
    if (cErr) {
      console.log(`Column '${col}': NOT FOUND (${cErr.message})`);
    } else {
      console.log(`Column '${col}': EXISTS`);
    }
  }
}

checkColumns().catch(console.error);
