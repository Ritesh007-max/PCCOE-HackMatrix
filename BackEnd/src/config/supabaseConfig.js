const { createClient } = require('@supabase/supabase-js');
const path = require('path');

require('dotenv').config({
    path: path.join(__dirname, '../../.env')
});

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_ROLE_KEY;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl) {
    throw new Error('Missing required environment variable: SUPABASE_URL');
}
if (!supabaseAnonKey) {
    throw new Error('Missing required environment variable: SUPABASE_ANON_ROLE_KEY');
}
if (!supabaseServiceRoleKey) {
    throw new Error('Missing required environment variable: SUPABASE_SERVICE_ROLE_KEY');
}

const supabaseClient = createClient(supabaseUrl, supabaseAnonKey);

const supabaseAdmin = createClient(supabaseUrl, supabaseServiceRoleKey, {
    auth: {
        autoRefreshToken: false,
        persistSession: false
    }
});

module.exports = {
    supabaseClient,
    supabaseAdmin
};